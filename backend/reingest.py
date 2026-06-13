# backend/reingest.py

from qdrant_client import QdrantClient
from config import QDRANT_PATH, COLLECTION_NAME
from ingest import run_ingestion

client = QdrantClient(path=QDRANT_PATH)

# Delete old collection
if COLLECTION_NAME in [c.name for c in client.get_collections().collections]:
    client.delete_collection(COLLECTION_NAME)
    print(f"✓ Deleted old collection '{COLLECTION_NAME}'")

# Re-ingest with new chunking strategy
run_ingestion()