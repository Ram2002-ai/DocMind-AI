"""Local chat API consumed by the React chat workspace.

This route deliberately has a small, stable API contract for the UI.  It uses
one local workspace user; the authenticated /api/v1 routes remain available
for the production account-based API.
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

from db.session import SessionLocal, get_db
from models.conversation import Conversation, Message
from models.document import Document  # Registers the relationship mapper used by Message.
from models.summary import Summary  # Registers the relationship mapper used by Document.
from models.user import User
from services.llm_service import LLMService

router = APIRouter(prefix="/api/threads", tags=["Workspace chat"])

LOCAL_USER_EMAIL = "local-workspace@documind.ai"
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "data" / "uploads"


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


def _attachments(db: Session) -> list[dict]:
    documents = db.query(Document).filter(Document.user_id == _local_user(db).id).order_by(Document.created_at.desc()).all()
    return [{
        "id": str(document.id), "name": document.original_filename,
        "kind": "pdf" if document.file_type == "pdf" else "text" if document.file_type in {"txt", "md", "csv"} else "image",
        "sizeBytes": document.file_size, "status": "ready" if document.status == "COMPLETED" else "error",
        "pages": document.page_count, "errorMessage": document.error_message,
    } for document in documents]


def _thread_payload(conversation: Conversation, db: Session) -> dict:
    latest = conversation.messages[-1].content if conversation.messages else None
    return {
        "id": str(conversation.id),
        "title": conversation.title or "New chat",
        "createdAt": conversation.created_at.isoformat(),
        "updatedAt": conversation.updated_at.isoformat(),
        "attachments": _attachments(db),
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
    if not title or title.lower().startswith(("openrouter", "error", "failed", "the language")):
        return _fallback_title(question)
    return re.sub(r"[\r\n\"']+", " ", title).strip()[:80] or _fallback_title(question)


def _document_context(db: Session) -> str:
    documents = db.query(Document).filter(
        Document.user_id == _local_user(db).id,
        Document.status == "COMPLETED",
    ).all()
    return "\n\n".join(
        f"Document: {item.original_filename}\n{(item.extracted_text or '')[:12000]}"
        for item in documents
    )


def _answer_prompt(history: list[dict], question: str, document_context: str) -> str:
    previous = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history[-10:]
    )
    return f"""You are DocuMind, a helpful document and research assistant.
Answer the user's actual question directly and accurately. Do not invent a role,
scenario, or topic that the user did not ask for. If prior messages are useful,
use them for context. Format with Markdown when it improves readability.

Conversation history:
{previous or '(No earlier messages)'}

Uploaded document context:
{document_context or '(No uploaded document text)'}

User question: {question}
"""


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


@router.get("/{thread_id}/messages")
def get_messages(thread_id: str, db: Session = Depends(get_db)):
    conversation = _get_thread(thread_id, db)
    return [
        {"id": str(item.id), "role": item.role, "content": item.content, "createdAt": item.created_at.isoformat()}
        for item in conversation.messages
    ]


@router.post("/{thread_id}/files", status_code=status.HTTP_201_CREATED)
def upload_file(thread_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _get_thread(thread_id, db)
    if not file.filename:
        raise HTTPException(status_code=422, detail="A file is required")
    suffix = Path(file.filename).suffix.lower().lstrip(".")
    if suffix not in {"pdf", "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "gif"}:
        raise HTTPException(status_code=415, detail="Unsupported file type")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.utcnow().timestamp():.0f}_{Path(file.filename).name}"
    destination = UPLOAD_DIR / safe_name
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    text, pages, error = "", None, None
    try:
        if suffix in {"txt", "md", "csv"}:
            text = destination.read_text(encoding="utf-8", errors="replace")
        elif suffix == "pdf":
            import fitz
            pdf = fitz.open(destination)
            pages = len(pdf)
            text = "\n".join(page.get_text() for page in pdf)
    except Exception as exc:
        error = f"Could not extract text: {exc}"
    document = Document(user_id=_local_user(db).id, filename=file.filename, original_filename=file.filename,
                        file_type=suffix, file_size=destination.stat().st_size, file_path=str(destination),
                        status="COMPLETED" if not error else "FAILED", extracted_text=text, page_count=pages,
                        word_count=len(text.split()) if text else 0, error_message=error)
    db.add(document)
    db.commit()
    db.refresh(document)
    return _attachments(db)[0]


@router.delete("/{thread_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(thread_id: str, file_id: str, db: Session = Depends(get_db)):
    _get_thread(thread_id, db)
    document = db.query(Document).filter(Document.id == int(file_id), Document.user_id == _local_user(db).id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        Path(document.file_path).unlink(missing_ok=True)
    finally:
        db.delete(document)
        db.commit()


@router.post("/{thread_id}/chat/stream")
def stream_chat(thread_id: str, payload: ChatPayload, db: Session = Depends(get_db)):
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="A message is required")
    conversation = _get_thread(thread_id, db)
    history = [{"role": item.role, "content": item.content} for item in conversation.messages]
    is_first_message = not history
    conversation_id = conversation.id
    prompt = _answer_prompt(history, question, _document_context(db))
    db.add(Message(conversation_id=conversation_id, role="user", content=question))
    conversation.updated_at = datetime.utcnow()
    db.commit()

    def event(name: str, body: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(body)}\n\n"

    def generate() -> Iterator[str]:
        answer_parts = []
        stream_db = SessionLocal()
        try:
            if is_first_message:
                title = _generate_title(question)
                thread = stream_db.query(Conversation).filter(Conversation.id == conversation_id).first()
                if thread:
                    thread.title = title
                    stream_db.commit()
                yield event("thread_title", {"title": title})
            for chunk in LLMService().generate_stream(prompt):
                answer_parts.append(chunk)
                yield event("token", {"text": chunk})
            stream_db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="".join(answer_parts),
                )
            )
            thread = stream_db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if thread:
                thread.updated_at = datetime.utcnow()
            stream_db.commit()
            yield event("message_done", {})
        except Exception as exc:
            stream_db.rollback()
            yield event("error", {"message": str(exc) or "Unable to generate a response."})
        finally:
            stream_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
