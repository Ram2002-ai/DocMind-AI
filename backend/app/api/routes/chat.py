"""Chat endpoints for durable, threaded RAG conversations."""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from schemas import ChatRequest, ChatResponse, ConversationUpdate
from api.deps import get_db, get_current_user
from models.user import User
from models.conversation import Conversation, Message
from services.rag_service import RAGService
from core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/chat")


def _conversation_for_request(request: ChatRequest, user: User, db: Session) -> Conversation:
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id, Conversation.user_id == user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation
    conversation = Conversation(user_id=user.id, title=request.question.strip()[:80] or "New conversation")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message and get RAG response"""
    try:
        conversation = _conversation_for_request(request, current_user, db)
        
        # Store user message
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.question
        )
        db.add(user_message)
        db.commit()
        
        # Get RAG response
        rag_service = RAGService()
        result = rag_service.answer_question(
            question=request.question,
            user_id=current_user.id,
            document_ids=request.document_ids if request.document_ids else None
        )
        
        # Store assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"]
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        logger.info(f"Chat message processed for conversation {conversation.id}")
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=conversation.id,
            message_id=assistant_message.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request"
        )


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream an answer as SSE and persist the completed threaded turn."""
    conversation = _conversation_for_request(request, current_user, db)
    history = [{"role": item.role, "content": item.content} for item in conversation.messages[-12:]]
    db.add(Message(conversation_id=conversation.id, role="user", content=request.question))
    db.commit()

    def event(name: str, payload: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(payload)}\n\n"

    async def generate_events():
        answer_parts = []
        try:
            chunks, sources = RAGService().answer_question_stream(
                request.question, current_user.id, request.document_ids or None, history
            )
            yield event("meta", {"conversation_id": conversation.id})
            yield event("sources", {"sources": sources})
            for chunk in chunks:
                answer_parts.append(chunk)
                yield event("delta", {"content": chunk})

            message = Message(conversation_id=conversation.id, role="assistant", content="".join(answer_parts))
            db.add(message)
            conversation.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(message)
            yield event("done", {"message_id": message.id})
        except Exception as exc:
            db.rollback()
            logger.error(f"Streaming chat error: {exc}")
            yield event("error", {"detail": "Failed to process chat request"})

    return StreamingResponse(
        generate_events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's conversations"""
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == current_user.id
        ).order_by(Conversation.updated_at.desc(), Conversation.created_at.desc()).all()
        
        return {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "message_count": len(c.messages)
                }
                for c in conversations
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversations"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at
                }
                for m in conversation.messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename a conversation's title"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        title = payload.title.strip()[:80]
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")

        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        db.commit()

        return {"id": conversation.id, "title": conversation.title}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error renaming conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename conversation"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        db.delete(conversation)
        db.commit()
        
        logger.info(f"Conversation {conversation_id} deleted")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )
