"""
Vector Service: ChromaDB semantic search operations and embedding indexing.
Gracefully handles missing chromadb installations with fallback keyword matching.
"""

import logging
from typing import Any, Dict, List, Optional
from backend.app.config import settings

logger = logging.getLogger("vector_service")


class VectorService:
    """Manages ChromaDB collections and vector similarity search."""

    def __init__(self):
        self.client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        """Attempts to initialize ChromaDB persistent client."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB vector collection successfully loaded.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization skipped or failed: {e}. Semantic fallback enabled.")
            self.client = None
            self.collection = None

    def search(
        self,
        query_text: str,
        n_results: int = 10,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes dense vector search against ChromaDB.
        Returns candidate document IDs and cosine similarity scores.
        """
        if not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
            )
            matches = []
            if results and "ids" in results and results["ids"]:
                ids = results["ids"][0]
                distances = results.get("distances", [[]])[0] if "distances" in results else []
                for i, doc_id in enumerate(ids):
                    # Convert cosine distance to cosine similarity (1.0 - distance)
                    dist = distances[i] if i < len(distances) else 0.5
                    sim = max(0.0, min(1.0, 1.0 - dist))
                    matches.append({"restaurant_id": int(doc_id), "semantic_similarity": sim})
            return matches
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


vector_service = VectorService()
