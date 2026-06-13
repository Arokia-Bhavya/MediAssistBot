# backend/hybrid_rag.py

from groq import Groq
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchAny,
    Prefetch,
    FusionQuery,
    Fusion,
    SparseVector,
    NamedVector,
    NamedSparseVector,
    QueryRequest,
)
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding
from qdrant_client_instance import client as qdrant

from config import (
    EMBED_MODEL,
    COLLECTION_NAME,
    QDRANT_PATH,
    GROQ_API_KEY,
    GROQ_MODEL,
    RETRIEVAL_TOP_K,
    RERANK_TOP_N,
    RERANK_MODEL,
)
from rbac import get_collections_for_role

# ── Models (loaded once) ───────────────────────────────────────────────
print("Loading RAG models...")
dense_model = SentenceTransformer(EMBED_MODEL)
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25", batch_size=32)
reranker = CrossEncoder(RERANK_MODEL)
print("✓ RAG models loaded")

# ── Clients ────────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)


def get_rbac_filter(role: str) -> Filter:
    """
    Build a Qdrant metadata filter that restricts results
    to only collections this role is allowed to access.
    Applied at the vector store level — not the app layer.
    """
    allowed_collections = get_collections_for_role(role)

    return Filter(
        must=[
            FieldCondition(
                key="collection",
                match=MatchAny(any=allowed_collections)
            )
        ]
    )


def hybrid_search(question: str, role: str) -> list[dict]:
    """
    Run hybrid search (dense + sparse) with RBAC filter.
    Returns top-K candidate chunks before reranking.
    """
    # 1. Embed the question
    dense_vector = dense_model.encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    sparse_output = list(sparse_model.embed([question]))[0]
    sparse_vector = SparseVector(
        indices=sparse_output.indices.tolist(),
        values=sparse_output.values.tolist(),
    )

    # 2. RBAC filter — enforced at retrieval layer
    rbac_filter = get_rbac_filter(role)

    # 3. Hybrid query — dense + sparse fused together
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            # Dense branch
            Prefetch(
                query=dense_vector,
                using="dense",
                limit=RETRIEVAL_TOP_K,
            ),
            # Sparse branch
            Prefetch(
                query=sparse_vector,
                using="sparse",
                limit=RETRIEVAL_TOP_K,
            ),
        ],
        # Reciprocal Rank Fusion merges both result lists
        query=FusionQuery(fusion=Fusion.RRF),
        query_filter=rbac_filter,   # 👈 RBAC applied HERE
        limit=RETRIEVAL_TOP_K,
        with_payload=True,
    )

    # 4. Extract chunks from results
    candidates = []
    for point in results.points:
        candidates.append({
            "text": point.payload.get("text", ""),
            "source_document": point.payload.get("source_document", ""),
            "collection": point.payload.get("collection", ""),
            "section_title": point.payload.get("section_title", ""),
            "chunk_type": point.payload.get("chunk_type", "text"),
            "score": point.score,
        })

    return candidates


def rerank(question: str, candidates: list[dict]) -> list[dict]:
    """
    Cross-encoder reranking — scores each candidate against
    the question jointly, then keeps only top N.
    """
    if not candidates:
        return []

    # Cross-encoder reads (question, chunk) pairs together
    pairs = [(question, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)

    # Attach reranker scores
    for i, candidate in enumerate(candidates):
        candidate["rerank_score"] = float(scores[i])

    # Sort by reranker score descending, keep top N
    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:RERANK_TOP_N]


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Build the LLM prompt with retrieved context."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source_document']} — {chunk['section_title']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return f"""You are MediBot, an intelligent assistant for MediAssist Health Network.
Answer the question using ONLY the provided context.
If the answer is not in the context, say "I could not find relevant information in the available documents."
Always cite the source document and section in your answer.

Context:
{context}

Question: {question}

Answer:"""


def rag_answer(question: str, role: str) -> dict:
    allowed_collections = get_collections_for_role(role)

    # Step 1 — Hybrid retrieval
    candidates = hybrid_search(question, role)

    # Step 2 — Hard RBAC filter — remove any chunk not in allowed collections
    safe_candidates = [
        c for c in candidates
        if c["collection"] in allowed_collections
    ]


    if not safe_candidates:
        return {
            "answer": (
                f"As a {role}, you do not have access to the requested information. "
                f"I can only answer questions from the "
                f"{', '.join(allowed_collections)} collections."
            ),
            "sources": [],          # 👈 empty sources — no leakage
            "retrieval_type": "hybrid_rag",
            "role": role,
        }

    # Step 3 — Rerank safe candidates only
    top_chunks = rerank(question, safe_candidates)

    # Step 4 — LLM answer
    prompt = build_prompt(question, top_chunks)
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    answer = response.choices[0].message.content.strip()

    # Step 5 — Sources only from safe chunks
    sources = [
        {
            "source_document": c["source_document"],
            "section_title": c["section_title"],
            "collection": c["collection"],
        }
        for c in top_chunks
        if c["collection"] in allowed_collections   # 👈 extra guard
    ]

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_type": "hybrid_rag",
        "role": role,
    }

def is_rbac_blocked(question: str, role: str) -> tuple[bool, str]:
    """
    Check if a question is trying to access restricted content.
    Returns (blocked: bool, message: str)
    """
    from rbac import ROLE_COLLECTIONS
    allowed = get_collections_for_role(role)
    all_collections = ["general", "clinical", "nursing", "billing", "equipment"]
    restricted = [c for c in all_collections if c not in allowed]

    # Check if question mentions restricted collection keywords
    question_lower = question.lower()
    blocked_keywords = {
        "billing": ["billing", "insurance", "claim", "invoice"],
        "clinical": ["drug formulary", "treatment protocol", "diagnostic"],
        "nursing": ["nursing", "icu procedure", "infection control"],
        "equipment": ["equipment", "calibration", "maintenance manual"],
    }

    for collection in restricted:
        keywords = blocked_keywords.get(collection, [])
        if any(kw in question_lower for kw in keywords):
            return True, (
                f"As a {role}, you do not have access to {collection} documents. "
                f"I can only answer questions from the "
                f"{', '.join(allowed)} collections."
            )

    return False, ""