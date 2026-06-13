from qdrant_client import QdrantClient
from config import QDRANT_PATH

# Single shared instance used across the entire app
client = QdrantClient(path=QDRANT_PATH)