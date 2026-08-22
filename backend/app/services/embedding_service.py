"""Embedding service for text vectorization"""
from sentence_transformers import SentenceTransformer
from typing import List
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Global embedding model (singleton)
_embedding_model = None


def _get_embedding_model():
    """Get or initialize the embedding model"""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        self.model = _get_embedding_model()
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts).tolist()
            return embeddings
        except Exception as e:
            logger.error(f"Error embedding texts: {str(e)}")
            raise
    
    def get_model_name(self) -> str:
        """Get the name of the embedding model"""
        return settings.EMBEDDING_MODEL
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        # Generate a dummy embedding to get dimension
        dummy_embedding = self.embed_text("test")
        return len(dummy_embedding)
