"""Document management service"""
import os
import shutil
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from models.document import Document
from models.summary import Summary
from services.extraction_service import ExtractionService
from services.cleaning_service import TextCleaningService
from services.rag_service import RAGService
from services.llm_service import LLMService
from services.entity_service import EntityExtractionService
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for document management and processing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extraction_service = ExtractionService()
        self.cleaning_service = TextCleaningService()
        self.rag_service = RAGService()
        self.llm_service = LLMService()
        self.entity_service = EntityExtractionService()
    
    def create_document(
        self,
        user_id: int,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        file_path: str
    ) -> Document:
        """Create a new document in the database"""
        try:
            doc = Document(
                user_id=user_id,
                filename=filename,
                original_filename=original_filename,
                file_type=file_type,
                file_size=file_size,
                file_path=file_path,
                status="UPLOADED"
            )
            
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)
            
            logger.info(f"Created document {doc.id} for user {user_id}")
            return doc
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating document: {str(e)}")
            raise
    
    def process_document(self, document_id: int) -> None:
        """
        Process a document:
        1. Extract text
        2. Clean text
        3. Generate embeddings
        4. Store in vector DB
        5. Update status
        """
        try:
            # Get document
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            logger.info(f"Processing document {document_id}: {doc.filename}")
            
            # Update status
            doc.status = "PROCESSING"
            self.db.commit()
            
            # Extract text
            logger.info("Extracting text...")
            doc.status = "EXTRACTING"
            self.db.commit()
            
            raw_text, page_count, page_wise_text = self.extraction_service.extract_text(
                doc.file_path,
                doc.file_type
            )
            
            # Clean text
            logger.info("Cleaning text...")
            doc.status = "CLEANING"
            self.db.commit()
            
            cleaned_text = self.cleaning_service.clean_text(raw_text)
            doc.extracted_text = cleaned_text
            doc.page_count = page_count
            doc.word_count = len(cleaned_text.split())
            
            # Store in vector DB
            logger.info("Embedding and indexing...")
            doc.status = "EMBEDDING"
            self.db.commit()
            
            self.rag_service.store_document_chunks(
                document_id=doc.id,
                filename=doc.filename,
                text=cleaned_text,
                user_id=doc.user_id,
                page_wise_text=page_wise_text
            )
            
            # Mark as completed
            doc.status = "COMPLETED"
            doc.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Successfully processed document {document_id}")
            
        except Exception as e:
            # Mark as failed
            doc.status = "FAILED"
            doc.error_message = str(e)
            self.db.commit()
            
            logger.error(f"Error processing document {document_id}: {str(e)}")
            raise
    
    def generate_summary(self, document_id: int) -> Summary:
        """Generate summary for a document"""
        try:
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            if not doc.extracted_text:
                raise ValueError(f"Document {document_id} has no extracted text")
            
            logger.info(f"Generating summary for document {document_id}")
            
            # Check if summary already exists
            existing_summary = self.db.query(Summary).filter(
                Summary.document_id == document_id
            ).first()
            
            if existing_summary:
                logger.info("Summary already exists, returning cached summary")
                return existing_summary
            
            # Generate summary using LLM
            summary_text = self.llm_service.summarize(doc.extracted_text)
            
            # Store summary
            summary = Summary(
                document_id=document_id,
                summary_text=summary_text
            )
            
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            
            logger.info(f"Summary generated and stored for document {document_id}")
            return summary
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generating summary: {str(e)}")
            raise
    
    def get_entities(self, document_id: int) -> dict:
        """Extract entities from a document"""
        try:
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            if not doc.extracted_text:
                raise ValueError(f"Document {document_id} has no extracted text")
            
            logger.info(f"Extracting entities from document {document_id}")
            
            entities = self.entity_service.extract_entities(doc.extracted_text)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            raise
    
    def delete_document(self, document_id: int, user_id: int) -> None:
        """Delete a document and its associated data"""
        try:
            doc = self.db.query(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id
            ).first()
            
            if not doc:
                raise ValueError(f"Document {document_id} not found or access denied")
            
            logger.info(f"Deleting document {document_id}")
            
            # Delete file from storage
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
                logger.info(f"Deleted file: {doc.file_path}")
            
            # Delete from vector database
            self.rag_service.vector_service.delete_documents_by_metadata(
                where_filter={"document_id": str(document_id)}
            )
            
            # Delete from database
            self.db.delete(doc)
            self.db.commit()
            
            logger.info(f"Document {document_id} deleted successfully")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document: {str(e)}")
            raise
    
    def get_user_documents(self, user_id: int, skip: int = 0, limit: int = 20):
        """Get paginated list of user's documents"""
        try:
            query = self.db.query(Document).filter(Document.user_id == user_id)
            total = query.count()
            
            documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
            
            return documents, total
            
        except Exception as e:
            logger.error(f"Error getting user documents: {str(e)}")
            raise

    def get_chunk_count(self, document_id: int, user_id: int) -> int:
        """Number of vector chunks stored for a document, once processed"""
        try:
            return self.rag_service.vector_service.count_for_document(document_id, user_id)
        except Exception as e:
            logger.error(f"Error getting chunk count for document {document_id}: {str(e)}")
            return 0
