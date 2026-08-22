"""
Stage 2 & 3: Vector Embedding Generation + Vector Database Storage
- Uses a free, local sentence-transformers model to embed text (no API key needed)
- Stores vectors + original text in ChromaDB (local, persistent, file-based)
"""
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from app.config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL_NAME, TOP_K

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME
)

_client = PersistentClient(path=CHROMA_PATH)

_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=_embedding_fn,
    metadata={"hnsw:space": "cosine"},  # cosine similarity search
)


def add_chunks(chunks: list[dict]) -> int:
    """
    Add ingested chunks to the vector DB.
    chunks: [{"text": ..., "source": ..., "chunk_id": ...}, ...]
    Embeddings are generated automatically by the collection's embedding function.
    """
    if not chunks:
        return 0

    ids = [f"{c['source']}::{c['chunk_id']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks]

    _collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed the query and run cosine-similarity search against the vector DB.
    Returns the top_k most relevant chunks with their source metadata.
    """
    results = _collection.query(query_texts=[query], n_results=top_k)

    if not results["documents"] or not results["documents"][0]:
        return []

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": doc, "source": meta.get("source"), "score": 1 - dist})
    return hits


def collection_count() -> int:
    return _collection.count()
