"""Entity extraction endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import EntityResponse
from api.deps import get_db, get_current_user
from models.user import User
from models.document import Document
from services.document_service import DocumentService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/{document_id}/entities", response_model=EntityResponse)
async def extract_entities(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract entities from a document"""
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
                detail="Document must be fully processed before extracting entities"
            )
        
        # Extract entities
        doc_service = DocumentService(db)
        entities = doc_service.get_entities(document_id)
        
        logger.info(f"Entities extracted from document {document_id}")
        
        return EntityResponse(
            document_id=document_id,
            emails=entities.get("emails", []),
            phone_numbers=entities.get("phone_numbers", []),
            dates=entities.get("dates", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity extraction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract entities"
        )
