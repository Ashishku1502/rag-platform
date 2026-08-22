# RAG System — Full Working Project

A complete Retrieval-Augmented Generation pipeline, matching the architecture:

`PDF/Docs → Chunking → Embeddings → Vector DB (Chroma) → FastAPI → Guardrails → Claude → Guardrails → UI`

- **Vector DB**: ChromaDB, local + persistent (no external account needed)
- **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers` — runs locally, free, downloads once (~80MB)
- **LLM**: Claude, via the Anthropic API (you provide your own key)
- **Guardrails**: rule-based input (prompt-injection detection) and output (secret/PII redaction) filters
- **Frontend**: React (Vite) console UI — a live "pipeline trace" that lights up as each stage runs

## 1. Backend setup

```bash
cd rag-project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# open .env and paste your ANTHROPIC_API_KEY
```

Get an API key at https://console.anthropic.com if you don't have one.

Run it:
```bash
uvicorn app.main:app --reload
```
The API is now live at `http://127.0.0.1:8000` (docs at `/docs`).

## 2. Frontend setup (in a second terminal)

```bash
cd rag-project/frontend
npm install
npm run dev
```
Open **http://localhost:5173** — that's the console UI. Vite proxies `/query`, `/ingest`, and `/status` to the FastAPI backend on :8000 (see `frontend/vite.config.js`), so both need to be running.

To ship a static build instead of the dev server: `npm run build` outputs to `frontend/dist/` — serve that with any static host, or point FastAPI's `StaticFiles` at it.

> Note: an earlier plain HTML/JS version of this UI is kept at `static/index.html` for reference — it's no longer wired up now that the React app is the primary frontend.

## 3. Try it end-to-end

A sample doc is included at `sample_docs/hr_policy.txt` so you can test immediately:

1. In the UI, upload `sample_docs/hr_policy.txt` under "Ingest a document".
2. Ask: *"What is our company's paternity leave policy?"*
3. You should get an answer synthesized from the doc, with a source citation.

Try uploading your own PDFs too (`.pdf`, `.txt`, `.md` supported).

## 4. API reference (for testing with curl/Postman)

**Ingest a file:**
```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -F "file=@sample_docs/hr_policy.txt"
```

**Query:**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our paternity leave policy?"}'
```

**Status (how many chunks are indexed):**
```bash
curl http://127.0.0.1:8000/status
```

## 5. Project structure

```
rag-project/
├── app/
│   ├── config.py       # env vars: API key, chunk size, top_k, model name
│   ├── ingestion.py     # Stage 1: load PDF/txt, chunk with overlap
│   ├── vectorstore.py   # Stage 2+3: embed + store/retrieve in ChromaDB
│   ├── guardrails.py    # Input (prompt injection) + output (secret redaction) checks
│   ├── rag_chain.py     # Stage 5: prompt construction + Claude call
│   └── main.py          # FastAPI app tying it all together
├── frontend/             # React (Vite) console UI
│   ├── src/App.jsx       # Pipeline tracker + ingest panel + chat
│   ├── src/index.css     # Blueprint-schematic design system
│   └── vite.config.js    # Dev-server proxy to the FastAPI backend
├── static/
│   └── index.html       # Legacy plain HTML/JS UI (kept for reference, not served)
├── sample_docs/
│   └── hr_policy.txt    # Sample doc to test with immediately
├── chroma_db/            # Persisted vector DB (created on first run)
├── requirements.txt
├── .env.example
└── README.md
```

## 6. How each guardrail works

- **Input guardrail** (`check_input`): rejects empty/oversized queries and blocks common prompt-injection phrasing (e.g. "ignore previous instructions") before retrieval even runs.
- **Output guardrail** (`check_output`): regex-scrubs the LLM's response for things that look like API keys, bearer tokens, or emails before it reaches the user — a safety net in case the LLM echoes something from context it shouldn't.

These are intentionally lightweight/dependency-free so the project runs with zero external guardrail services. For production, swap in something like NeMo Guardrails or a dedicated moderation API for stronger coverage.

## 7. Known limitations / next steps (good talking points for interviews)

- Chunking is character-based, not sentence/token-aware — swapping to a tokenizer-based splitter (e.g. `tiktoken`) would be more precise.
- No auth on the API — add an API key or JWT middleware before deploying publicly.
- ChromaDB here is local/single-node — for production scale, swap the `vectorstore.py` backend for Pinecone/Weaviate (the interface is already isolated so this is a small change).
- No conversation memory — each `/query` is stateless; adding a session/history param would let it handle follow-up questions.
