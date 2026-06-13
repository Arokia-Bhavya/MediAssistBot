import os
from dotenv import load_dotenv

load_dotenv()

# LLM & Embeddings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EMBED_DIM = 384  # all-MiniLM-L6-v2 outputs 384-dim vectors


# Qdrant
COLLECTION_NAME = "medibot"  # single Qdrant collection, RBAC via metadata
# Qdrant - local path mode
QDRANT_PATH = "./qdrant_storage"
QDRANT_URL = None

# Auth
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
TOKEN_EXPIRE_HOURS = 8

# RAG settings
RETRIEVAL_TOP_K = 10   # fetch this many candidates initially
RERANK_TOP_N = 3       # keep only top N after reranking

# Demo users: username -> {password, role}
DEMO_USERS = {
    "dr.mehta":     {"password": "doctor",           "role": "doctor"},
    "nurse.priya":  {"password": "nurse",            "role": "nurse"},
    "billing.ravi": {"password": "billing_executive","role": "billing_executive"},
    "tech.anand":   {"password": "technician",       "role": "technician"},
    "admin.sys":    {"password": "admin",            "role": "admin"},
}