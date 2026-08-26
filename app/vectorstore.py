"""
Stage 2 & 3: Vector Embedding Generation + Vector Database Storage
- Uses a free, local sentence-transformers model to embed text (no API key needed)
- Stores vectors + original text in ChromaDB (local, persistent, file-based)
"""
import threading
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from app.config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL_NAME, TOP_K

# ---------------------------------------------------------------------------
# Lazy-initialize the embedding function and the ChromaDB client / collection.
# Loading sentence-transformers can take 30–120 s on first run (model download).
# Deferring to first use means the server starts instantly and the cost is paid
# only when the first /ingest or /query request arrives.
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_embedding_fn = None
_client = None
_collection = None


def _get_collection():
    """Return the ChromaDB collection, initializing on first call (thread-safe)."""
    global _embedding_fn, _client, _collection
    if _collection is not None:
        return _collection

    with _lock:
        # Double-checked locking: re-check after acquiring the lock.
        if _collection is not None:
            return _collection

        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )
        _client = PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"},  # cosine similarity search
        )
    return _collection


def add_chunks(chunks: list[dict]) -> int:
    """
    Add ingested chunks to the vector DB.
    chunks: [{"text": ..., "source": ..., "chunk_id": ...}, ...]
    Embeddings are generated automatically by the collection's embedding function.
    """
    if not chunks:
        return 0

    col = _get_collection()
    ids = [f"{c['source']}::{c['chunk_id']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "chunk_id": str(c["chunk_id"])} for c in chunks]

    col.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed the query and run cosine-similarity search against the vector DB.
    Returns the top_k most relevant chunks with their source metadata.
    """
    col = _get_collection()
    count = col.count()
    if count == 0:
        return []
    # ChromaDB raises if n_results > number of stored items
    n = min(top_k, count)
    results = col.query(query_texts=[query], n_results=n)

    if not results["documents"] or not results["documents"][0]:
        return []

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": doc, "source": meta.get("source"), "score": 1 - dist})
    return hits


def collection_count() -> int:
    """
    Return the number of chunks stored.

    This is intentionally non-blocking: if the collection has not been
    initialized yet (i.e., no ingest or query has been made), we return 0
    immediately so the /status health-check endpoint stays fast.
    """
    if _collection is None:
        return 0
    try:
        return _collection.count()
    except Exception:
        return 0
