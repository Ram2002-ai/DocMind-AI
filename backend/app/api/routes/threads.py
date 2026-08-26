"""Local chat API consumed by the React chat workspace.

This route deliberately has a small, stable API contract for the UI.  It uses
one local workspace user; the authenticated /api/v1 routes remain available
for the production account-based API.

Chat is answered by the LangGraph agent in services/langgraph_rag_service.py
(tool-calling: per-thread FAISS document retrieval, web search, calculator,
stock lookup). Uploaded files are extracted (with OCR fallback) and indexed
into that thread's FAISS store so the agent's rag_tool can retrieve them.
"""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from models.conversation import Conversation, Message
from models.document import Document  # Registers the relationship mapper used by Message.
from models.summary import Summary  # Registers the relationship mapper used by Document.
from models.user import User
from services import langgraph_rag_service as agent
from services.extraction_service import ExtractionService
from services.llm_service import LLMService

router = APIRouter(prefix="/api/threads", tags=["Workspace chat"])

LOCAL_USER_EMAIL = "local-workspace@documind.ai"
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "data" / "uploads"
ACCEPTED_SUFFIXES = {"pdf", "docx", "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "gif"}


class ChatPayload(BaseModel):
    message: str


def _local_user(db: Session) -> User:
    user = db.query(User).filter(User.email == LOCAL_USER_EMAIL).first()
    if user:
        return user
    user = User(email=LOCAL_USER_EMAIL, password_hash="local-workspace-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _thread_documents(db: Session, conversation_id: int) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.conversation_id == conversation_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def _attachments(db: Session, conversation_id: int) -> list[dict]:
    return [{
        "id": str(document.id), "name": document.original_filename,
        "kind": "pdf" if document.file_type == "pdf" else "text" if document.file_type in {"txt", "md", "csv", "docx"} else "image",
        "sizeBytes": document.file_size, "status": "ready" if document.status == "COMPLETED" else "error",
        "pages": document.page_count, "errorMessage": document.error_message,
    } for document in _thread_documents(db, conversation_id)]


def _thread_payload(conversation: Conversation, db: Session) -> dict:
    latest = conversation.messages[-1].content if conversation.messages else None
    return {
        "id": str(conversation.id),
        "title": conversation.title or "New chat",
        "createdAt": conversation.created_at.isoformat(),
        "updatedAt": conversation.updated_at.isoformat(),
        "attachments": _attachments(db, conversation.id),
        "messagePreview": latest,
    }


def _get_thread(thread_id: str, db: Session) -> Conversation:
    try:
        conversation_id = int(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == _local_user(db).id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _fallback_title(question: str) -> str:
    normalized = " ".join(question.split())
    return normalized[:60] + ("…" if len(normalized) > 60 else "") or "New chat"


def _generate_title(question: str) -> str:
    prompt = (
        "Write a concise 3 to 7 word chat title for this user request. "
        "Return only the title, with no quotation marks or punctuation at the end.\n\n"
        f"User request: {question}"
    )
    title = LLMService().generate(prompt, retries=0).strip()
    # Do not show provider errors as a conversation title.
    if not title or title.lower().startswith(("groq", "error", "failed", "the language")):
        return _fallback_title(question)
    return re.sub(r"[\r\n\"']+", " ", title).strip()[:80] or _fallback_title(question)


def _index_document(document: Document, thread_id: str) -> None:
    """Extract + index a single document into the thread's FAISS store.
    Updates the Document row in place with the extraction result.
    """
    try:
        summary = agent.ingest_document(
            file_path=document.file_path,
            thread_id=thread_id,
            filename=document.original_filename,
            file_type=document.file_type,
        )
        document.status = "COMPLETED"
        document.page_count = summary["documents"]
        document.word_count = None
        document.error_message = None
    except Exception as exc:
        document.status = "FAILED"
        document.error_message = f"Could not index document: {exc}"


def _reindex_thread(db: Session, thread_id: str) -> None:
    """Rebuild the thread's FAISS index from whatever documents remain
    COMPLETED in the database (used after a delete)."""
    conversation_id = int(thread_id)
    remaining = [
        {"file_path": d.file_path, "filename": d.original_filename, "file_type": d.file_type}
        for d in _thread_documents(db, conversation_id)
        if d.status == "COMPLETED"
    ]
    if remaining:
        agent.rebuild_thread_index(thread_id, remaining)
    else:
        agent.clear_thread_index(thread_id)


@router.get("")
def list_threads(db: Session = Depends(get_db)):
    user = _local_user(db)
    conversations = db.query(Conversation).filter(Conversation.user_id == user.id).order_by(
        Conversation.updated_at.desc(), Conversation.created_at.desc()
    ).all()
    return [_thread_payload(item, db) for item in conversations]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_thread(db: Session = Depends(get_db)):
    conversation = Conversation(user_id=_local_user(db).id, title="New chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _thread_payload(conversation, db)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: str, db: Session = Depends(get_db)):
    db.delete(_get_thread(thread_id, db))
    db.commit()
    agent.clear_thread_index(thread_id)


@router.get("/{thread_id}/messages")
def get_messages(thread_id: str, db: Session = Depends(get_db)):
    conversation = _get_thread(thread_id, db)
    return [
        {"id": str(item.id), "role": item.role, "content": item.content, "createdAt": item.created_at.isoformat()}
        for item in conversation.messages
    ]


@router.post("/{thread_id}/files", status_code=status.HTTP_201_CREATED)
def upload_file(thread_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    conversation = _get_thread(thread_id, db)
    if not file.filename:
        raise HTTPException(status_code=422, detail="A file is required")
    suffix = Path(file.filename).suffix.lower().lstrip(".")
    if suffix not in ACCEPTED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.utcnow().timestamp():.0f}_{Path(file.filename).name}"
    destination = UPLOAD_DIR / safe_name
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    document = Document(
        user_id=_local_user(db).id, conversation_id=conversation.id,
        filename=file.filename, original_filename=file.filename,
        file_type=suffix, file_size=destination.stat().st_size, file_path=str(destination),
        status="PROCESSING",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _index_document(document, thread_id)
    db.commit()
    db.refresh(document)
    return _attachments(db, conversation.id)[0]


@router.delete("/{thread_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(thread_id: str, file_id: str, db: Session = Depends(get_db)):
    conversation = _get_thread(thread_id, db)
    document = db.query(Document).filter(
        Document.id == int(file_id), Document.conversation_id == conversation.id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        Path(document.file_path).unlink(missing_ok=True)
    finally:
        db.delete(document)
        db.commit()
    _reindex_thread(db, thread_id)


def _ensure_indexed(db: Session, thread_id: str) -> None:
    """The FAISS index lives only in memory, not the database, so it's lost
    on every backend restart even though the Document rows (and their
    "ready" status in the UI) persist. Rebuild it on demand before chatting
    so a restart can't silently make document context disappear.
    """
    if agent.thread_has_document(thread_id):
        return
    conversation_id = int(thread_id)
    completed = [d for d in _thread_documents(db, conversation_id) if d.status == "COMPLETED"]
    if completed:
        agent.rebuild_thread_index(thread_id, [
            {"file_path": d.file_path, "filename": d.original_filename, "file_type": d.file_type}
            for d in completed
        ])


def _sse(name: str, body: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(body)}\n\n"


@router.post("/{thread_id}/chat/stream")
def stream_chat(thread_id: str, payload: ChatPayload, db: Session = Depends(get_db)):
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="A message is required")
    conversation = _get_thread(thread_id, db)
    is_first_message = not conversation.messages
    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    conversation.updated_at = datetime.utcnow()
    db.commit()
    _ensure_indexed(db, thread_id)

    def generate() -> Iterator[str]:
        answer_parts = []
        try:
            if is_first_message:
                title = _generate_title(question)
                conversation.title = title
                db.commit()
                yield _sse("thread_title", {"title": title})

            for event_type, body in agent.stream_chat_response(thread_id, question):
                if event_type == "token":
                    answer_parts.append(body.get("text", ""))
                yield _sse(event_type, body)

            db.add(Message(conversation_id=conversation.id, role="assistant", content="".join(answer_parts)))
            conversation.updated_at = datetime.utcnow()
            db.commit()
            yield _sse("message_done", {})
        except Exception as exc:
            db.rollback()
            yield _sse("error", {"message": str(exc) or "Unable to generate a response."})

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/{thread_id}/chat")
def chat_once(thread_id: str, payload: ChatPayload, db: Session = Depends(get_db)):
    """Non-streaming fallback used by the frontend if the SSE connection fails."""
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="A message is required")
    conversation = _get_thread(thread_id, db)
    is_first_message = not conversation.messages
    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    conversation.updated_at = datetime.utcnow()
    db.commit()
    _ensure_indexed(db, thread_id)

    if is_first_message:
        conversation.title = _generate_title(question)

    try:
        answer = agent.invoke_chat_response(thread_id, question)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Unable to generate a response: {exc}") from exc

    assistant_message = Message(conversation_id=conversation.id, role="assistant", content=answer)
    db.add(assistant_message)
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_message)
    return {
        "id": str(assistant_message.id),
        "role": "assistant",
        "content": assistant_message.content,
        "createdAt": assistant_message.created_at.isoformat(),
    }
