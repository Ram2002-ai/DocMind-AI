"""Document extraction service (PDF, DOCX, TXT, images)"""
import fitz
from pdf2image import convert_from_path
import tempfile
import os
from typing import Optional, Tuple
from docx import Document as DocxFile
from core.logging import get_logger
from services.ocr_service import OCRService

logger = get_logger(__name__)


class PDFExtractionService:
    """Service for extracting text from PDF files"""
    
    def __init__(self):
        self.ocr_service = OCRService()
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int, Optional[list]]:
        """
        Extract text from PDF using PyMuPDF.
        Falls back to OCR for scanned PDFs.
        
        Returns:
            Tuple of (extracted_text, page_count, page_wise_text)
        """
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            text = ""
            page_texts = []
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text
                page_texts.append({
                    "page": page_num + 1,
                    "text": page_text
                })
            
            doc.close()
            
            # If text extraction failed (scanned PDF), use OCR fallback
            if not text.strip():
                logger.info(f"No text found in {pdf_path}, using OCR fallback")
                text, page_texts = self._extract_with_ocr_fallback(pdf_path)
            
            logger.info(f"Successfully extracted {page_count} pages from PDF")
            return text, page_count, page_texts
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def _extract_with_ocr_fallback(self, pdf_path: str) -> Tuple[str, list]:
        """Extract text from PDF using OCR as fallback for scanned PDFs"""
        try:
            logger.info(f"Converting PDF to images for OCR: {pdf_path}")
            
            # Check for poppler path on Windows
            poppler_path = os.getenv("POPPLER_PATH")
            images = convert_from_path(pdf_path, poppler_path=poppler_path)
            
            text = ""
            page_texts = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                for page_num, image in enumerate(images):
                    image_path = os.path.join(temp_dir, f"page_{page_num}.png")
                    image.save(image_path)
                    
                    page_text = self.ocr_service.extract_text_from_image(image_path)
                    text += page_text + "\n"
                    page_texts.append({
                        "page": page_num + 1,
                        "text": page_text
                    })
            
            return text, page_texts
            
        except Exception as e:
            logger.error(f"OCR fallback failed: {str(e)}")
            raise


class DocxExtractionService:
    """Service for extracting text from Word (.docx) files"""

    def extract_text_from_docx(self, docx_path: str) -> Tuple[str, int, Optional[list]]:
        """
        Extract text from a .docx file, including paragraphs and table cells.
        DOCX has no fixed "page" concept, so the whole document is treated as one page.

        Returns:
            Tuple of (extracted_text, page_count, page_wise_text)
        """
        try:
            logger.info(f"Extracting text from DOCX: {docx_path}")
            doc = DocxFile(docx_path)

            parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))

            text = "\n".join(parts)
            logger.info(f"Successfully extracted DOCX with {len(parts)} text blocks")
            return text, 1, [{"page": 1, "text": text}]

        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise


class TextExtractionService:
    """Service for reading plain-text (.txt) files"""

    def extract_text_from_txt(self, txt_path: str) -> Tuple[str, int, Optional[list]]:
        """Read a plain-text file. Returns (text, page_count=1, page_wise_text)."""
        try:
            logger.info(f"Reading text file: {txt_path}")
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return text, 1, [{"page": 1, "text": text}]

        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise


class ExtractionService:
    """Main extraction service that handles all document types"""
    
    def __init__(self):
        self.pdf_service = PDFExtractionService()
        self.ocr_service = OCRService()
        self.docx_service = DocxExtractionService()
        self.txt_service = TextExtractionService()
    
    def extract_text(self, file_path: str, file_type: str) -> Tuple[str, int, Optional[list]]:
        """
        Extract text from any supported document type.
        
        Args:
            file_path: Path to the file
            file_type: File extension (pdf, png, jpg, jpeg, docx, txt)
        
        Returns:
            Tuple of (extracted_text, page_count, page_wise_text)
        """
        file_type_lower = file_type.lower()
        
        if file_type_lower == "pdf":
            return self.pdf_service.extract_text_from_pdf(file_path)
        elif file_type_lower in ["png", "jpg", "jpeg"]:
            text = self.ocr_service.extract_text_from_image(file_path)
            return text, 1, [{"page": 1, "text": text}]
        elif file_type_lower == "docx":
            return self.docx_service.extract_text_from_docx(file_path)
        elif file_type_lower == "txt":
            return self.txt_service.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
