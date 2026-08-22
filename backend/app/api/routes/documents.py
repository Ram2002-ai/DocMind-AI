"""Document management routes"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
import os
import uuid
from sqlalchemy.orm import Session
from schemas import DocumentResponse, DocumentListResponse
from api.deps import get_db, get_current_user
from models.user import User
from models.document import Document
from services.document_service import DocumentService
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document"""
    try:
        # Validate file type
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in settings.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Supported: {', '.join(settings.SUPPORTED_FORMATS)}"
            )
        
        # Validate file size
        file_content = await file.read()
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE} bytes"
            )
        
        # Create upload directory
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create document record
        doc_service = DocumentService(db)
        document = doc_service.create_document(
            user_id=current_user.id,
            filename=file.filename,
            original_filename=file.filename,
            file_type=file_ext,
            file_size=len(file_content),
            file_path=file_path
        )
        
        # Process document in background (TODO: implement background tasks)
        # For now, process synchronously
        try:
            doc_service.process_document(document.id)
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            # Don't fail the upload, but mark document as failed
        
        logger.info(f"Document uploaded: {document.id} by user {current_user.id}")
        
        response = DocumentResponse.model_validate(document)
        if document.status == "COMPLETED":
            response.chunk_count = doc_service.get_chunk_count(document.id, current_user.id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's documents"""
    try:
        doc_service = DocumentService(db)
        documents, total = doc_service.get_user_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        response = DocumentResponse.model_validate(document)
        if document.status == "COMPLETED":
            doc_service = DocumentService(db)
            response.chunk_count = doc_service.get_chunk_count(document.id, current_user.id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )


@router.get("/{document_id}/text")
async def get_document_text(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get extracted text from document"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if not document.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document text not yet extracted"
            )
        
        return {
            "document_id": document.id,
            "filename": document.filename,
            "text": document.extracted_text,
            "word_count": document.word_count,
            "page_count": document.page_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document text"
        )


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document processing status"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            "document_id": document.id,
            "status": document.status,
            "error": document.error_message,
            "page_count": document.page_count,
            "word_count": document.word_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document status"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    try:
        doc_service = DocumentService(db)
        doc_service.delete_document(document_id, current_user.id)
        
        logger.info(f"Document {document_id} deleted by user {current_user.id}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
