# backend/debug_chunks.py

from qdrant_client import QdrantClient
from config import QDRANT_PATH, COLLECTION_NAME

client = QdrantClient(path=QDRANT_PATH)

results = client.scroll(
    collection_name=COLLECTION_NAME,
    limit=20,
    with_payload=True,
)

lengths = []
for point in results[0]:
    text = point.payload.get("text", "")
    lengths.append(len(text.split()))
    print("─" * 40)
    print(f"Collection : {point.payload.get('collection')}")
    print(f"Section    : {point.payload.get('section_title')}")
    print(f"Type       : {point.payload.get('chunk_type')}")
    print(f"Word count : {len(text.split())}")
    print(f"Preview    : {text[:150]}...")

print("\n" + "=" * 40)
print(f"Avg chunk size : {sum(lengths)//len(lengths)} words")
print(f"Min chunk size : {min(lengths)} words")
print(f"Max chunk size : {max(lengths)} words")