# backend/ingest.py

import os
import uuid
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    Distance,
    PointStruct,
    SparseVector,
)
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client_instance import client


from config import (
    EMBED_MODEL,
    EMBED_DIM,
    COLLECTION_NAME,
    QDRANT_PATH,
)
from rbac import ROLE_COLLECTIONS

# ── Models (loaded once at startup) ───────────────────────────────────
print("Loading embedding models...")
dense_model = SentenceTransformer(EMBED_MODEL)
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25", batch_size=32)
print(f"✓ Dense model loaded: {EMBED_MODEL}")
print(f"✓ Sparse model loaded: Qdrant/bm25")

# ── Invert ROLE_COLLECTIONS → COLLECTION_ROLES ────────────────────────
# rbac.py defines role → [collections]
# We need collection → [roles] for metadata
COLLECTION_ROLES: dict[str, list[str]] = {}
for role, collections in ROLE_COLLECTIONS.items():
    for col in collections:
        COLLECTION_ROLES.setdefault(col, [])
        if role not in COLLECTION_ROLES[col]:
            COLLECTION_ROLES[col].append(role)


def create_qdrant_collection():
    """Create Qdrant collection with dense + sparse vector config."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' already exists, skipping.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(
                size=EMBED_DIM,
                distance=Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        },
    )
    print(f"✓ Created collection '{COLLECTION_NAME}'")


def chunk_document(file_path: str, collection: str) -> list[dict]:
    """
    Parse a PDF/Markdown file with Docling and chunk hierarchically.
    Each chunk carries its parent section heading as context.
    """
    converter = DocumentConverter()
    result = converter.convert(file_path)
    doc = result.document

    chunker = HybridChunker(
        tokenizer=EMBED_MODEL,
        max_tokens=512,
        merge_peers=True,
    )

    chunks = []
    for chunk in chunker.chunk(doc):

        # Skip chunks that are too small to be meaningful
        word_count = len(chunk.text.split())
        if word_count < 20:            # 👈 drop anything under 20 words
            continue
        # Extract the nearest parent heading for context
        headings = chunk.meta.headings if chunk.meta else []
        section_title = headings[-1] if headings else "General"

        # Prepend heading so chunk is self-contained
        # e.g. "Drug Dosage\n\n25mg twice daily" instead of just "25mg twice daily"
        chunk_text = (
            f"{section_title}\n\n{chunk.text}"
            if section_title != "General"
            else chunk.text
        )

        # Detect chunk type from Docling label
        chunk_type = "text"
        if hasattr(chunk, "label"):
            label = str(chunk.label).lower()
            if "table" in label:
                chunk_type = "table"
            elif "heading" in label:
                chunk_type = "heading"
            elif "code" in label:
                chunk_type = "code"

        chunks.append({
            "text": chunk_text,
            "metadata": {
                "source_document": Path(file_path).name,
                "collection": collection,
                "access_roles": COLLECTION_ROLES.get(collection, []),
                "section_title": section_title,
                "chunk_type": chunk_type,
            }
        })

    print(f"    → {len(chunks)} chunks from {Path(file_path).name}")
    return chunks


def embed_and_upload(chunks: list[dict], batch_size: int = 32):
    """Generate dense + sparse vectors and upload to Qdrant."""
    texts = [c["text"] for c in chunks]
    total = len(texts)

    # Dense vectors — semantic similarity
    print(f"    Generating dense vectors for {total} chunks...")
    dense_vectors = dense_model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    # Sparse vectors — BM25 keyword matching
    print(f"    Generating sparse vectors for {total} chunks...")
    sparse_outputs = list(sparse_model.embed(texts))

    # Build Qdrant points
    points = []
    for i, chunk in enumerate(chunks):
        sv = sparse_outputs[i]
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vectors[i].tolist(),
                    "sparse": SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                },
                # Store full metadata + text in payload
                payload=chunk["metadata"] | {"text": chunk["text"]},
            )
        )

    client.upload_points(
        collection_name=COLLECTION_NAME,
        points=points,
        batch_size=batch_size,
    )
    print(f"    ✓ Uploaded {len(points)} points to Qdrant")


def ingest_collection(collection: str, data_dir: str = "data"):
    """Ingest all PDFs and Markdown files in a collection folder."""
    folder = Path(data_dir) / collection
    if not folder.exists():
        print(f"  Folder '{folder}' not found, skipping.")
        return

    files = list(folder.glob("**/*.pdf")) + list(folder.glob("**/*.md"))
    if not files:
        print(f"  No files found in '{folder}', skipping.")
        return

    print(f"\n── Collection: '{collection}' ({len(files)} files) ──")
    all_chunks = []
    for file_path in files:
        print(f"  Parsing: {file_path.name}")
        chunks = chunk_document(str(file_path), collection)
        all_chunks.extend(chunks)

    if all_chunks:
        embed_and_upload(all_chunks)
    else:
        print(f"  No chunks extracted from '{collection}'")


def run_ingestion():
    """Main entry point — ingest all 5 collections into Qdrant."""
    print("=" * 50)
    print("  MediBot Ingestion Pipeline")
    print("=" * 50)

    create_qdrant_collection()

    for collection in ["general", "clinical", "nursing", "billing", "equipment"]:
        ingest_collection(collection)

    total = client.count(collection_name=COLLECTION_NAME).count
    print("\n" + "=" * 50)
    print(f"  ✅ Ingestion complete!")
    print(f"  Total chunks in Qdrant: {total}")
    print("=" * 50)


if __name__ == "__main__":
    run_ingestion()