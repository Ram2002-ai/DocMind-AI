"""Text cleaning service"""
import re
from core.logging import get_logger

logger = get_logger(__name__)


class TextCleaningService:
    """Service for cleaning and normalizing extracted text"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean extracted text by removing noise and normalizing formatting.
        
        Handles:
        - Extra whitespace
        - Multiple line breaks
        - Tabs
        - Leading/trailing spaces
        - OCR artifacts
        
        Args:
            text: Raw extracted text
        
        Returns:
            Cleaned text
        """
        try:
            logger.debug("Starting text cleaning")
            
            # Remove multiple spaces
            text = re.sub(r"[ ]+", " ", text)
            
            # Remove multiple blank lines (keep single line breaks)
            text = re.sub(r"\n+", "\n", text)
            
            # Remove tabs and replace with space
            text = text.replace("\t", " ")
            
            # Remove leading/trailing spaces
            text = text.strip()
            
            # Remove common OCR artifacts
            text = TextCleaningService._remove_ocr_artifacts(text)
            
            logger.debug("Text cleaning completed")
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            return text
    
    @staticmethod
    def _remove_ocr_artifacts(text: str) -> str:
        """Remove common OCR recognition errors"""
        # Replace common OCR mistakes
        replacements = {
            r'l0': '10',  # letter 'l' misread as '1' and '0'
            r'O0': '00',  # letter 'O' misread as '0'
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace while preserving structure"""
        # Split by line, clean each line, rejoin
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)
