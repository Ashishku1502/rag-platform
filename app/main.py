"""
FastAPI backend for the RAG system.

Endpoints:
  GET  /                -> serves the chat UI
  POST /ingest           -> upload a .pdf/.txt/.md file, chunk + embed + store it
  POST /query             -> user query -> guardrail -> retrieve -> LLM -> guardrail -> answer
  GET  /status            -> quick health check (how many chunks are stored)
"""
import os
import shutil
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ingestion import ingest_file
from app.vectorstore import add_chunks, retrieve, collection_count
from app.guardrails import check_input, check_output
from app.rag_chain import generate_answer

app = FastAPI(title="RAG System API")

# React dev server runs on :5173 (Vite default) and calls this API directly.
# allow_origins=["*"] keeps this simple for local dev; lock this down to your
# actual frontend origin before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root():
    return {"service": "RAG System API", "docs": "/docs", "status": "/status"}


@app.get("/status")
def status():
    return {"chunks_stored": collection_count()}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """Upload -> extract text -> chunk -> embed -> store in vector DB."""
    allowed_ext = (".pdf", ".txt", ".md")
    if not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(400, f"Unsupported file type. Use one of: {allowed_ext}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        chunks = ingest_file(tmp_path)
        # keep filename (not the temp path) in the metadata
        for c in chunks:
            c["source"] = file.filename
        count = add_chunks(chunks)
    finally:
        os.remove(tmp_path)

    return {"filename": file.filename, "chunks_added": count}


@app.post("/query")
def query(req: QueryRequest):
    # 1. Input guardrail
    is_safe, reason = check_input(req.query)
    if not is_safe:
        raise HTTPException(400, f"Blocked by input guardrail: {reason}")

    # 2. Retrieval from vector DB
    chunks = retrieve(req.query)

    # 3 & 4. Prompt construction + LLM synthesis
    try:
        answer = generate_answer(req.query, chunks)
    except Exception as e:
        raise HTTPException(500, f"LLM call failed: {e}")

    # 5. Output guardrail
    safe_answer = check_output(answer)

    return {
        "answer": safe_answer,
        "sources": [{"source": c["source"], "score": round(c["score"], 3)} for c in chunks],
    }
