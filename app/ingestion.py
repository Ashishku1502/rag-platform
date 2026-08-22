"""
Stage 1: Data Ingestion & Chunking
- Extracts raw text from PDFs / .txt documents
- Splits text into overlapping chunks so context isn't lost at chunk boundaries
"""
import os
from pypdf import PdfReader
from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def load_document(file_path: str) -> str:
    """Extract raw text from a PDF or plain text file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text

    elif ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .pdf, .txt, or .md")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks (character-based).
    Overlap preserves context across chunk boundaries so a sentence
    split across two chunks doesn't lose meaning.
    """
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap  # step forward, but overlap with previous chunk

    return chunks


def ingest_file(file_path: str) -> list[dict]:
    """
    Full ingestion for one file: load -> chunk -> attach metadata.
    Returns a list of dicts: {"text": chunk, "source": filename, "chunk_id": int}
    """
    raw_text = load_document(file_path)
    chunks = chunk_text(raw_text)
    filename = os.path.basename(file_path)

    return [
        {"text": chunk, "source": filename, "chunk_id": i}
        for i, chunk in enumerate(chunks)
    ]
