"""LangGraph RAG backend with OCR document ingestion and tool-calling chat.

Adapted from the LangGraph PDF chatbot reference to integrate with DocuMind AI:
- Per-thread FAISS vector stores for document retrieval
- OCR-backed extraction for scanned PDFs and images (via ExtractionService)
- Tool-calling agent: RAG, web search, calculator, stock lookup
- SQLite checkpointer for durable conversation memory
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Any, Dict, Iterator, Optional, TypedDict

import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LCDocument
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import settings
from app.core.logging import get_logger
from app.services.extraction_service import ExtractionService

logger = get_logger(__name__)

_APP_DIR = Path(__file__).resolve().parents[1]
_CHECKPOINT_PATH = (_APP_DIR / settings.LANGGRAPH_CHECKPOINT_PATH).resolve()
_CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Per-thread vector stores and metadata
_THREAD_VECTOR_STORES: Dict[str, FAISS] = {}
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}

_TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    separators=["\n\n", "\n", " ", ""],
)

# -------------------
# LLM + embeddings
# -------------------
llm = ChatOpenAI(
    model=settings.GROQ_MODEL,
    base_url=settings.GROQ_BASE_URL,
    api_key=settings.GROQ_API_KEY,
    temperature=settings.LLM_TEMPERATURE,
)

def _load_embeddings() -> HuggingFaceEmbeddings:
    """Load the local embedding model without hard-depending on network
    access every single startup/hot-reload. sentence-transformers/HF Hub
    normally does a freshness-check HEAD request even when the model is
    already cached on disk; if that check fails (DNS hiccup, no internet,
    firewall), fall back to the local cache instead of crashing the whole app.
    """
    model_name = f"sentence-transformers/{settings.EMBEDDING_MODEL}"
    try:
        return HuggingFaceEmbeddings(model_name=model_name)
    except Exception as exc:
        logger.warning(
            "Embedding model load hit a network error (%s); retrying from local cache only.",
            exc,
        )
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        return HuggingFaceEmbeddings(model_name=model_name)


_embeddings: Optional[HuggingFaceEmbeddings] = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Load the embedding model only when a document is indexed."""
    global _embeddings
    if _embeddings is None:
        _embeddings = _load_embeddings()
    return _embeddings


def _get_retriever(thread_id: Optional[str]):
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None


def _update_thread_store(thread_id: str, chunks: list[LCDocument]) -> None:
    thread_key = str(thread_id)
    existing = _THREAD_VECTOR_STORES.get(thread_key)
    if existing and chunks:
        existing.add_documents(chunks)
        vector_store = existing
    elif chunks:
        vector_store = FAISS.from_documents(chunks, _get_embeddings())
    else:
        return

    _THREAD_VECTOR_STORES[thread_key] = vector_store
    _THREAD_RETRIEVERS[thread_key] = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.TOP_K},
    )


def ingest_document(
    file_path: str,
    thread_id: str,
    filename: str,
    file_type: str,
) -> dict:
    """Extract text (with OCR when needed), chunk, and index into the thread FAISS store."""
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")

    extraction = ExtractionService()
    raw_text, page_count, page_wise_text = extraction.extract_text(file_path, file_type)

    if not raw_text.strip():
        raise ValueError("No content could be extracted from the document (vision description and OCR both returned empty).")

    if page_wise_text:
        docs = [
            LCDocument(
                page_content=page["text"],
                metadata={"page": page["page"], "source": filename},
            )
            for page in page_wise_text
            if page.get("text", "").strip()
        ]
    else:
        docs = [LCDocument(page_content=raw_text, metadata={"source": filename})]

    chunks = _TEXT_SPLITTER.split_documents(docs)
    if not chunks:
        raise ValueError("Document produced no indexable chunks after splitting.")

    thread_key = str(thread_id)
    _update_thread_store(thread_key, chunks)

    meta = _THREAD_METADATA.setdefault(
        thread_key,
        {"files": [], "documents": 0, "chunks": 0, "filename": filename},
    )
    meta["files"].append(
        {"filename": filename, "pages": page_count, "chunks": len(chunks)}
    )
    meta["documents"] = meta.get("documents", 0) + (page_count or 1)
    meta["chunks"] = meta.get("chunks", 0) + len(chunks)
    meta["filename"] = filename

    logger.info(
        "Indexed %s for thread %s (%s pages, %s chunks)",
        filename,
        thread_key,
        page_count,
        len(chunks),
    )

    return {
        "filename": filename,
        "documents": page_count or 1,
        "chunks": len(chunks),
        "used_ocr": not page_wise_text or any(
            not page.get("text", "").strip() for page in (page_wise_text or [])
        ),
    }


def rebuild_thread_index(thread_id: str, documents: list[dict]) -> None:
    """Rebuild a thread's FAISS index from remaining on-disk documents."""
    thread_key = str(thread_id)
    clear_thread_index(thread_key)

    total_chunks = 0
    total_pages = 0
    files_meta = []

    for doc in documents:
        try:
            summary = ingest_document(
                file_path=doc["file_path"],
                thread_id=thread_key,
                filename=doc["filename"],
                file_type=doc["file_type"],
            )
            total_chunks += summary["chunks"]
            total_pages += summary["documents"]
            files_meta.append(
                {"filename": doc["filename"], "pages": summary["documents"], "chunks": summary["chunks"]}
            )
        except Exception as exc:
            logger.warning("Skipping document %s during rebuild: %s", doc.get("filename"), exc)

    if files_meta:
        _THREAD_METADATA[thread_key] = {
            "files": files_meta,
            "documents": total_pages,
            "chunks": total_chunks,
            "filename": files_meta[-1]["filename"],
        }


def clear_thread_index(thread_id: str) -> None:
    thread_key = str(thread_id)
    _THREAD_VECTOR_STORES.pop(thread_key, None)
    _THREAD_RETRIEVERS.pop(thread_key, None)
    _THREAD_METADATA.pop(thread_key, None)


# -------------------
# Tools
# -------------------
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """Perform basic arithmetic: add, sub, mul, div."""
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as exc:
        return {"error": str(exc)}


@tool
def get_stock_price(symbol: str) -> dict:
    """Fetch the latest stock quote for a ticker symbol (e.g. AAPL, TSLA)."""
    api_key = settings.ALPHA_VANTAGE_API_KEY or "demo"
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "symbol": symbol}


@tool
def rag_tool(query: str, config: RunnableConfig) -> dict:
    """Retrieve relevant passages from documents uploaded to this chat thread.

    thread_id is NOT an argument the model provides — LangGraph injects the
    real RunnableConfig (which carries the actual conversation's thread_id)
    automatically when this tool is invoked, since models are unreliable at
    echoing IDs back correctly (or skip the argument) when asked to supply
    them as free text.
    """
    thread_id = (config or {}).get("configurable", {}).get("thread_id")
    retriever = _get_retriever(thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF or image first.",
            "query": query,
        }

    result = retriever.invoke(query)
    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        "query": query,
        "context": context,
        "metadata": metadata,
        "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }


tools = [search_tool, get_stock_price, calculator, rag_tool]
llm_with_tools = llm.bind_tools(tools)


# -------------------
# LangGraph state + nodes
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState, config=None):
    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")

    thread_key = str(thread_id) if thread_id else ""
    doc_meta = thread_document_metadata(thread_key)
    doc_hint = (
        f"A document `{doc_meta.get('filename')}` is indexed "
        f"({doc_meta.get('chunks', 0)} chunks, {doc_meta.get('documents', 0)} pages)."
        if doc_meta
        else "No document is indexed for this chat yet."
    )

    # Safety net: retrieve relevant chunks for the latest user message up front
    # and hand them to the model directly, rather than relying entirely on the
    # model choosing to call rag_tool — not every model reliably makes that
    # call even when instructed to, especially smaller/faster ones.
    context_block = ""
    retriever = _get_retriever(thread_key)
    if retriever is not None:
        last_human = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        if isinstance(last_human, str) and last_human.strip():
            try:
                hits = retriever.invoke(last_human)
                if hits:
                    excerpts = "\n\n".join(
                        f"[{doc.metadata.get('source', doc_meta.get('filename', 'document'))}"
                        f"{', page ' + str(doc.metadata['page']) if doc.metadata.get('page') else ''}]\n"
                        f"{doc.page_content}"
                        for doc in hits
                    )
                    context_block = (
                        "\n\nRelevant excerpts already retrieved from the indexed document "
                        f"for the user's latest message:\n{excerpts}\n"
                        "Use these if they answer the question. Call `rag_tool` again only "
                        "if you need a different or more specific search."
                    )
            except Exception as exc:
                logger.warning("Proactive retrieval failed for thread %s: %s", thread_key, exc)

    system_message = SystemMessage(
        content=(
            "You are DocuMind, a helpful document and research assistant. "
            f"{doc_hint}{context_block} "
            "For ANY question that could relate to an uploaded document, call "
            "`rag_tool` with the user's query if the excerpts above aren't enough "
            "before answering — you do not need to supply a thread id, it is handled "
            "automatically. You may also use web search, stock prices, and the "
            "calculator when helpful. Answer clearly using Markdown when it improves "
            "readability. If no document is available, ask the user to upload one."
        )
    )

    messages = [system_message, *state["messages"]]
    response = llm_with_tools.invoke(messages, config=config)
    return {"messages": [response]}


tool_node = ToolNode(tools)

conn = sqlite3.connect(database=str(_CHECKPOINT_PATH), check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)


# -------------------
# Public helpers
# -------------------
def retrieve_all_threads() -> list[str]:
    all_threads: set[str] = set()
    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
        if thread_id:
            all_threads.add(str(thread_id))
    return list(all_threads)


def thread_has_document(thread_id: str) -> bool:
    return str(thread_id) in _THREAD_RETRIEVERS


def thread_document_metadata(thread_id: str) -> dict:
    return _THREAD_METADATA.get(str(thread_id), {})


def stream_chat_response(
    thread_id: str,
    user_input: str,
) -> Iterator[tuple[str, dict]]:
    """Yield (event_type, payload) tuples for SSE streaming."""
    config = {
        "configurable": {"thread_id": str(thread_id)},
        "metadata": {"thread_id": str(thread_id)},
        "run_name": "chat_turn",
    }

    seen_tool_calls: set[str] = set()

    for message_chunk, _ in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="messages",
    ):
        if isinstance(message_chunk, AIMessage):
            if message_chunk.tool_calls:
                for tool_call in message_chunk.tool_calls:
                    call_id = tool_call.get("id") or str(uuid.uuid4())
                    if call_id in seen_tool_calls:
                        continue
                    seen_tool_calls.add(call_id)
                    yield "tool_call", {
                        "id": call_id,
                        "name": tool_call.get("name", "tool"),
                        "input": tool_call.get("args", {}),
                        "status": "running",
                    }

            content = message_chunk.content
            if isinstance(content, str) and content:
                yield "token", {"text": content}
            elif isinstance(content, list):
                for block in content:
                    text = block.get("text", "") if isinstance(block, dict) else ""
                    if text:
                        yield "token", {"text": text}

        elif isinstance(message_chunk, ToolMessage):
            yield "tool_call", {
                "id": message_chunk.tool_call_id or str(uuid.uuid4()),
                "name": message_chunk.name or "tool",
                "status": "done",
                "output": str(message_chunk.content)[:500],
            }


def invoke_chat_response(thread_id: str, user_input: str) -> str:
    """Non-streaming chat turn; returns the final assistant text."""
    config = {"configurable": {"thread_id": str(thread_id)}}
    result = chatbot.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    block.get("text", "") for block in content if isinstance(block, dict)
                )
    return "I couldn't generate a response."
