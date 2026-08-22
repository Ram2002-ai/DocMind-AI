import chromadb
from utils.embeddings import get_embedding_model

client = chromadb.Client()

collection = client.get_or_create_collection(
    name="documents"
)

model = get_embedding_model()


def clear_all_documents():
    try:
        existing = collection.get()
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def remove_document(source):
    try:
        collection.delete(where={"source": source})
    except Exception:
        pass


def store_document(text, source):
    chunk_size = 500
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    if not chunks:
        return

    embeddings = model.encode(chunks).tolist()

    ids = [f"{source}_{i}" for i in range(len(chunks))]

    metadatas = [{"source": source} for _ in chunks]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )


def search_document(query, sources=None, n_results=3):
    embedding = model.encode(query).tolist()

    where_filter = None
    if sources:
        if len(sources) == 1:
            where_filter = {"source": sources[0]}
        else:
            where_filter = {"source": {"$in": sources}}

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=where_filter
    )

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    return [
        {"text": doc, "source": meta.get("source", "unknown")}
        for doc, meta in zip(documents, metadatas)
    ]
