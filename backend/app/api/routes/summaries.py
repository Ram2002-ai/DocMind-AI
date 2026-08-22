"""Summary endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import SummaryResponse
from api.deps import get_db, get_current_user
from models.user import User
from models.document import Document
from services.document_service import DocumentService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/{document_id}/summary", response_model=SummaryResponse)
async def generate_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate or retrieve summary for a document"""
    try:
        # Verify document ownership
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document must be fully processed before generating summary"
            )
        
        # Generate summary
        doc_service = DocumentService(db)
        summary = doc_service.generate_summary(document_id)
        
        logger.info(f"Summary generated for document {document_id}")
        
        return SummaryResponse.model_validate(summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary"
        )


@router.get("/{document_id}/summary", response_model=SummaryResponse)
async def get_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get existing summary for a document"""
    try:
        # Verify document ownership
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get summary
        summary = document.summary
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No summary available for this document"
            )
        
        return SummaryResponse.model_validate(summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve summary"
        )
