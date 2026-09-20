"""OCR service for image text extraction"""
import cv2
import numpy as np
import easyocr
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global EasyOCR reader
_ocr_reader = None


def _get_ocr_reader():
    """Get or initialize the EasyOCR reader (singleton pattern)"""
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Initializing EasyOCR reader")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader


class OCRService:
    """Service for optical character recognition from images"""
    
    def __init__(self):
        self.reader = _get_ocr_reader()
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using EasyOCR.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Extracted text from the image
        """
        try:
            logger.info(f"Extracting text from image: {image_path}")
            
            # Preprocess image for better OCR results
            preprocessed_image = self.preprocess_image(image_path)
            
            # Extract text using EasyOCR
            result = self.reader.readtext(preprocessed_image, detail=0)
            text = "\n".join(result)
            
            logger.info(f"Successfully extracted text from image")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Applies:
        - Grayscale conversion
        - Denoising
        - Thresholding
        - Contrast enhancement
        
        Args:
            image_path: Path to the image
        
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Unable to read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 10, 21)
            
            # Thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # Contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(cleaned)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {str(e)}")
            # Fall back to original image if preprocessing fails
            image = cv2.imread(image_path)
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
