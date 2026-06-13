from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from auth import authenticate_user, create_token, decode_token
from rbac import get_collections_for_role, can_use_sql_rag
from hybrid_rag import rag_answer
from sql_rag import sql_rag_chain

app = FastAPI(title="MediBot API", version="1.0.0")

# ── CORS — allow Next.js frontend ─────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    accessible_collections: list[str]


class ChatRequest(BaseModel):
    question: str
    role: Optional[str] = None   # fallback if not using token auth


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    retrieval_type: str          # "hybrid_rag" or "sql_rag"
    role: str
    sql: Optional[str] = None    # only for sql_rag responses


class CollectionsResponse(BaseModel):
    role: str
    collections: list[str]


# ── Auth dependency ────────────────────────────────────────────────────
def get_current_role(authorization: str = Header(...)) -> str:
    """Extract and validate role from Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload["role"]


# ── Keyword router — decides hybrid RAG vs SQL RAG ────────────────────
SQL_KEYWORDS = [
    "how many", "count", "total", "sum", "average", "which department",
    "how much", "list all", "show me all", "number of", "breakdown",
    "last month", "this month", "per department", "by department",
    "most", "least", "highest", "lowest", "escalated", "rejected",
    "open tickets", "maintenance tickets", "claims",
]

def is_analytical_question(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in SQL_KEYWORDS)


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "MediBot API"}


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user["username"], user["role"])
    collections = get_collections_for_role(user["role"])

    return LoginResponse(
        token=token,
        username=user["username"],
        role=user["role"],
        accessible_collections=collections,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, role: str = Depends(get_current_role)):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Route: SQL RAG or Hybrid RAG
    if is_analytical_question(question) and can_use_sql_rag(role):
        # SQL RAG — for analytical questions (billing_executive, admin only)
        result = sql_rag_chain(question)
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            retrieval_type="sql_rag",
            role=role,
            sql=result.get("sql"),
        )
    else:
        # Hybrid RAG — for document questions (all roles)
        result = rag_answer(question, role)
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            retrieval_type="hybrid_rag",
            role=role,
        )


@app.get("/collections/{role}", response_model=CollectionsResponse)
def get_collections(role: str):
    valid_roles = ["doctor", "nurse", "billing_executive", "technician", "admin"]
    if role not in valid_roles:
        raise HTTPException(status_code=404, detail=f"Role '{role}' not found")

    return CollectionsResponse(
        role=role,
        collections=get_collections_for_role(role),
    )