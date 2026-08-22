"""RAG (Retrieval-Augmented Generation) service"""
from typing import List, Dict, Optional
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.llm_service import LLMService
from services.cleaning_service import TextCleaningService
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation pipeline"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()
        self.llm_service = LLMService()
    
    def store_document_chunks(
        self,
        document_id: int,
        filename: str,
        text: str,
        user_id: int,
        page_wise_text: Optional[List[Dict]] = None
    ) -> None:
        """
        Store document chunks in vector database.
        
        Args:
            document_id: ID of the document in database
            filename: Original filename
            text: Full extracted text
            user_id: Owner user ID
            page_wise_text: Optional list of page-wise text with page numbers
        """
        try:
            logger.info(f"Storing document chunks for document {document_id}")
            
            # Split text into chunks
            chunks = self._chunk_text(text)
            
            if not chunks:
                logger.warning(f"No chunks generated for document {document_id}")
                return
            
            # Generate embeddings for all chunks
            embeddings = self.embedding_service.embed_texts(chunks)
            
            # Prepare IDs and metadata
            ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": str(document_id),
                    "filename": filename,
                    "chunk_index": i,
                    "user_id": str(user_id),
                    "page": page if page_wise_text else None
                }
                for i, page in self._get_page_numbers(text, chunks, page_wise_text)
            ]
            
            # Store in ChromaDB
            self.vector_service.add_documents(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully stored {len(chunks)} chunks for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {str(e)}")
            raise
    
    def search_documents(
        self,
        query: str,
        user_id: int,
        document_ids: Optional[List[int]] = None,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for relevant document chunks using semantic similarity.
        
        Args:
            query: Search query
            user_id: User ID for filtering
            document_ids: Optional list of specific documents to search in
            top_k: Number of results to return (defaults to config)
        
        Returns:
            List of relevant chunks with metadata
        """
        try:
            if top_k is None:
                top_k = settings.TOP_K
            
            logger.info(f"Searching documents for query: {query[:100]}")
            
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)
            
            # Build metadata filter for user isolation and document selection
            where_filter = {"user_id": str(user_id)}
            
            if document_ids:
                # Filter by specific documents
                if len(document_ids) == 1:
                    where_filter["document_id"] = str(document_ids[0])
                else:
                    where_filter["document_id"] = {"$in": [str(did) for did in document_ids]}
            
            # Search in vector database
            results = self.vector_service.search(
                query_embedding=query_embedding,
                n_results=top_k,
                where_filter=where_filter
            )
            
            # Format results
            formatted_results = self._format_search_results(results)
            
            logger.info(f"Found {len(formatted_results)} relevant chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise
    
    def answer_question(
        self,
        question: str,
        user_id: int,
        document_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Answer a question using RAG pipeline.
        
        Args:
            question: User question
            user_id: User ID for filtering
            document_ids: Optional list of documents to search
        
        Returns:
            Dictionary with answer and sources
        """
        try:
            logger.info(f"Processing RAG question for user {user_id}")
            
            # Search for relevant chunks
            relevant_chunks = self.search_documents(
                query=question,
                user_id=user_id,
                document_ids=document_ids
            )
            
            if not relevant_chunks:
                return {
                    "answer": "No relevant information found in the documents.",
                    "sources": [],
                    "confidence": "low"
                }
            
            # Build context from retrieved chunks
            context = self._build_context(relevant_chunks)
            
            # Generate answer using LLM with context
            answer = self.llm_service.answer_question(context, question)
            
            # Extract sources
            sources = self._extract_sources(relevant_chunks)
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": "high" if len(relevant_chunks) > 0 else "low"
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            raise
    
    def answer_question_stream(
        self, question: str, user_id: int, document_ids: Optional[List[int]] = None,
        history: Optional[List[Dict]] = None,
    ):
        """Return answer chunks and sources for a threaded chat turn."""
        chunks = self.search_documents(question, user_id, document_ids)
        if not chunks:
            return iter(["No relevant information found in the documents."]), []
        history_text = "\n".join(
            f"{item['role'].title()}: {item['content']}" for item in (history or [])
            if item.get("content")
        )
        prompt = f"""You are an AI document assistant. Answer only from the document context.
Use conversation history only to resolve references, never as a factual source.

Conversation history:
{history_text or '(No earlier messages)'}

Document context:
{self._build_context(chunks)}

Question: {question}
Answer:"""
        return self.llm_service.generate_stream(prompt), self._extract_sources(chunks)

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        chunks = []
        chunk_size = settings.CHUNK_SIZE
        chunk_overlap = settings.CHUNK_OVERLAP
        
        # Clean text first
        text = TextCleaningService.clean_text(text)
        
        step = chunk_size - chunk_overlap
        for i in range(0, len(text), step):
            chunk = text[i:i + chunk_size]
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
        
        return chunks
    
    def _get_page_numbers(
        self,
        full_text: str,
        chunks: List[str],
        page_wise_text: Optional[List[Dict]]
    ) -> List[tuple]:
        """Get page numbers for chunks"""
        if not page_wise_text:
            return [(i, None) for i in range(len(chunks))]
        
        # Map chunks to pages based on position in text
        page_map = []
        current_page = 1
        text_pos = 0
        
        for chunk in chunks:
            # Find which page this chunk belongs to
            while current_page < len(page_wise_text):
                page_text = page_wise_text[current_page - 1]['text']
                if text_pos < len(full_text) and chunk[:50] in full_text[text_pos:text_pos + 1000]:
                    break
                current_page += 1
            
            page_map.append((len(page_map), current_page))
            text_pos += len(chunk)
        
        return page_map
    
    def _format_search_results(self, raw_results: Dict) -> List[Dict]:
        """Format ChromaDB search results"""
        formatted = []
        
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]
        
        for doc, meta, distance in zip(documents, metadatas, distances):
            # Convert distance to similarity score (cosine distance -> similarity)
            similarity = 1 - distance
            
            formatted.append({
                "text": doc,
                "document_id": int(meta.get("document_id", 0)),
                "filename": meta.get("filename", "unknown"),
                "page": meta.get("page"),
                "chunk_index": meta.get("chunk_index"),
                "similarity_score": round(similarity, 3)
            })
        
        return formatted
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context string from retrieved chunks"""
        context_parts = []
        
        for chunk in chunks:
            source_info = f"[Source: {chunk['filename']}"
            if chunk.get('page'):
                source_info += f", Page {chunk['page']}"
            source_info += f", Relevance: {chunk['similarity_score']}]"
            
            context_parts.append(f"{source_info}\n{chunk['text']}")
        
        return "\n\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Extract unique sources from chunks"""
        sources = []
        seen = set()
        
        for chunk in chunks:
            source_key = (chunk['document_id'], chunk['filename'])
            if source_key not in seen:
                seen.add(source_key)
                sources.append({
                    "document_id": chunk['document_id'],
                    "filename": chunk['filename'],
                    "page": chunk.get('page'),
                    "relevance_score": chunk['similarity_score']
                })
        
        return sources
