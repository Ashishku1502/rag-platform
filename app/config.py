import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the .env file relative to the project root (one level above this file)
# so the app always finds its config regardless of the working directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct:featherless-ai")

# Propagate the key as HF_TOKEN so the huggingface_hub SDK authenticates
# automatically — this suppresses the unauthenticated-requests warning and
# enables higher rate limits / faster downloads.
if HUGGINGFACE_API_KEY and not os.getenv("HF_TOKEN"):
    os.environ["HF_TOKEN"] = HUGGINGFACE_API_KEY

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "3"))

# Make CHROMA_PATH absolute so it resolves correctly regardless of CWD.
_chroma_path_raw = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_PATH = str(
    Path(_chroma_path_raw)
    if Path(_chroma_path_raw).is_absolute()
    else _PROJECT_ROOT / _chroma_path_raw
)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "company_docs")

# Free, local sentence-transformers embedding model (no API key needed for local dev)
# In production, the HuggingFace Inference API is used instead of a local model.
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# --- Chroma Cloud (required for Vercel / serverless deployments) -----------
# Sign up at https://www.trychroma.com/ to get these credentials.
# When all three are set, ChromaDB uses the cloud; otherwise falls back to
# a local PersistentClient (useful for local development).
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "")
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "")
