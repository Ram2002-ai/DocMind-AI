"""Semantic search endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import SearchRequest, SearchResponse, SearchResultItem
from api.deps import get_db, get_current_user
from models.user import User
from services.rag_service import RAGService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/search")


@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform semantic search across documents"""
    try:
        if not request.query or request.query.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty"
            )
        
        rag_service = RAGService()
        
        results = rag_service.search_documents(
            query=request.query,
            user_id=current_user.id,
            document_ids=request.document_ids if request.document_ids else None,
            top_k=request.top_k
        )
        
        # Convert to response format
        search_results = [
            SearchResultItem(
                document_id=r["document_id"],
                filename=r["filename"],
                page=r.get("page"),
                text=r["text"],
                similarity_score=r["similarity_score"]
            )
            for r in results
        ]
        
        logger.info(f"Search performed: '{request.query}' - {len(search_results)} results")
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )
