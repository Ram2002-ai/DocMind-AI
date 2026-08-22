"""Vector database service for ChromaDB integration"""
from typing import List, Dict, Optional, Any
import chromadb
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Global ChromaDB client
_chroma_client = None
_collections = {}


def _get_chroma_client():
    """Get or initialize the ChromaDB client"""
    global _chroma_client
    if _chroma_client is None:
        logger.info(f"Connecting to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        try:
            # Try to connect to remote ChromaDB server
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
        except Exception:
            logger.warning("Failed to connect to ChromaDB server, using in-memory client")
            _chroma_client = chromadb.Client()
    return _chroma_client


class VectorService:
    """Service for vector database operations (ChromaDB)"""
    
    def __init__(self):
        self.client = _get_chroma_client()
    
    def get_or_create_collection(self, collection_name: str = None) -> Any:
        """Get or create a collection"""
        if collection_name is None:
            collection_name = settings.CHROMA_COLLECTION_NAME
        
        if collection_name not in _collections:
            logger.info(f"Creating/getting collection: {collection_name}")
            _collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        
        return _collections[collection_name]
    
    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        collection_name: str = None
    ) -> None:
        """Add documents to the vector database"""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            logger.info(f"Adding {len(documents)} documents to collection {collection.name}")
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully added documents to collection")
            
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {str(e)}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 3,
        where_filter: Optional[Dict] = None,
        collection_name: str = None
    ) -> Dict:
        """Search for similar documents"""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            logger.debug(f"Searching for {n_results} results with filters: {where_filter}")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {str(e)}")
            raise
    
    def delete_documents_by_metadata(
        self,
        where_filter: Dict,
        collection_name: str = None
    ) -> None:
        """Delete documents by metadata filter"""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            logger.info(f"Deleting documents with filter: {where_filter}")
            collection.delete(where=where_filter)
            logger.info("Documents deleted successfully")
            
        except Exception as e:
            logger.error(f"Error deleting documents from ChromaDB: {str(e)}")
            raise
    
    def delete_document_by_id(self, doc_id: str, collection_name: str = None) -> None:
        """Delete a document by ID"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            raise
    
    def clear_collection(self, collection_name: str = None) -> None:
        """Clear all documents from a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            existing = collection.get()
            
            if existing and existing.get("ids"):
                collection.delete(ids=existing["ids"])
                logger.info(f"Cleared collection {collection.name}")
            
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            raise
    
    def get_collection_stats(self, collection_name: str = None) -> Dict:
        """Get statistics about a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            data = collection.get()
            
            return {
                "name": collection.name,
                "document_count": len(data.get("ids", [])),
                "documents_sample": data.get("documents", [])[:5] if data.get("documents") else []
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise

    def count_for_document(self, document_id: int, user_id: int, collection_name: str = None) -> int:
        """Count how many chunks are stored for a specific document"""
        try:
            collection = self.get_or_create_collection(collection_name)
            result = collection.get(where={"document_id": str(document_id), "user_id": str(user_id)})
            return len(result.get("ids", []))
        except Exception as e:
            logger.error(f"Error counting chunks for document {document_id}: {str(e)}")
            return 0
