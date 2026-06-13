# backend/debug_qdrant.py

from qdrant_client import QdrantClient
from config import QDRANT_PATH, COLLECTION_NAME

client = QdrantClient(path=QDRANT_PATH)

# Fetch 5 random points and print their payload
results = client.scroll(
    collection_name=COLLECTION_NAME,
    limit=5,
    with_payload=True,
)

for point in results[0]:
    print("─" * 40)
    print("ID:", point.id)
    print("Payload keys:", list(point.payload.keys()))
    print("collection:", point.payload.get("collection"))
    print("access_roles:", point.payload.get("access_roles"))
    print("source_document:", point.payload.get("source_document"))