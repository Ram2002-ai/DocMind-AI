"""Entity extraction service"""
import re
from typing import Dict, List
from core.logging import get_logger

logger = get_logger(__name__)


class EntityExtractionService:
    """Service for extracting entities (emails, phones, dates) from text"""
    
    @staticmethod
    def extract_entities(text: str) -> Dict[str, List[str]]:
        """
        Extract structured entities from text using regex patterns.
        
        Extracts:
        - Email addresses
        - Phone numbers
        - Dates (multiple formats)
        
        Args:
            text: Text to extract entities from
        
        Returns:
            Dictionary with lists of extracted entities
        """
        try:
            logger.debug("Extracting entities from text")
            
            entities = {
                "emails": EntityExtractionService._extract_emails(text),
                "phone_numbers": EntityExtractionService._extract_phone_numbers(text),
                "dates": EntityExtractionService._extract_dates(text)
            }
            
            logger.info(f"Extracted entities: {sum(len(v) for v in entities.values())} items")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {"emails": [], "phone_numbers": [], "dates": []}
    
    @staticmethod
    def _extract_emails(text: str) -> List[str]:
        """Extract email addresses from text"""
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        matches = re.findall(pattern, text)
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for match in matches:
            if match.lower() not in seen:
                seen.add(match.lower())
                unique.append(match)
        return unique
    
    @staticmethod
    def _extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers from text"""
        # Pattern for: +1 (123) 456-7890, (123) 456-7890, 123-456-7890, +91 xxxxx xxxxx, etc.
        patterns = [
            r'\+?\d[\d\s()-]{8,15}\d',  # International and US formats
            r'\+\d{1,3}\s?\d{6,14}',     # +country code
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # (123) 456-7890
        ]
        
        matches = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text))
        
        # Remove duplicates
        unique = list(set(matches))
        return unique
    
    @staticmethod
    def _extract_dates(text: str) -> List[str]:
        """Extract dates from text in various formats"""
        patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}',  # Month DD, YYYY
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',  # DD Month YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
        ]
        
        matches = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Remove duplicates
        unique = list(set(matches))
        return unique
