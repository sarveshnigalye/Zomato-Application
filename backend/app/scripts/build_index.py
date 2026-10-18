"""
Vector Store & Profile Indexing Script (Phase 2).
Builds persistent ChromaDB embeddings from SQLite restaurants metadata.
"""

import logging
import sys
from pathlib import Path
from typing import List, Any

CURRENT_FILE = Path(__file__).resolve()
SCRIPTS_DIR = CURRENT_FILE.parent
APP_DIR = SCRIPTS_DIR.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.models.database import Restaurant, SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_index")


def generate_restaurant_profile(restaurant: Any) -> str:
    """Generate a synthetic textual profile for a restaurant.
    Uses key attributes to create a descriptive paragraph.
    """
    # Ensure we have list forms for cuisines and highlights
    cuisines = restaurant.cuisines
    if isinstance(cuisines, str):
        try:
            import json
            cuisines_list = json.loads(cuisines)
        except Exception:
            cuisines_list = [c.strip() for c in cuisines.split(',') if c.strip()]
    else:
        cuisines_list = list(cuisines)
    cuisine_str = ", ".join(cuisines_list)
    highlights = restaurant.highlights
    if isinstance(highlights, str):
        try:
            import json
            highlights_list = json.loads(highlights)
        except Exception:
            highlights_list = [h.strip() for h in highlights.split(',') if h.strip()]
    else:
        highlights_list = list(highlights)
    highlights_str = ", ".join(highlights_list)
    profile = (
        f"{restaurant.name} is a {cuisine_str} dining place located in {restaurant.location}. "
        f"Budget tier: {restaurant.budget_tier} (average cost for two: ₹{restaurant.average_cost_for_two}). "
        f"Rating: {restaurant.aggregate_rating} stars with {restaurant.votes} reviews. "
        f"Popular features: {highlights_str}. "
    )
    # Append a short snippet of reviews if available
    if getattr(restaurant, 'reviews_summary', None):
        profile += f"Atmosphere & highlights: {restaurant.reviews_summary[:200]}."
    return profile

def build_chroma_index():
    """Reads all restaurants from SQLite and indexes them into ChromaDB."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        logger.error("ChromaDB is not installed. Please run: pip install chromadb sentence-transformers")
        return

    session = SessionLocal()
    restaurants = session.query(Restaurant).all()
    session.close()

    if not restaurants:
        logger.warning("No restaurants found in database. Run ingest_data.py first!")
        return

    logger.info(f"Loaded {len(restaurants)} restaurants from SQLite. Initializing ChromaDB...")

    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
    
    # Try sentence transformer embedding function or fallback to default
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
    except Exception as e:
        logger.warning(f"Could not load SentenceTransformer ({e}). Using default Chroma embedding function.")
        ef = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[dict] = []

    for r in restaurants:
        # Generate synthetic profile if not present
        profile_text = r.synthetic_profile
        if not profile_text:
            profile_text = generate_restaurant_profile(r)
            # Update the ORM object (no commit needed for indexing)
            r.synthetic_profile = profile_text
        ids.append(str(r.id))
        documents.append(profile_text[:512])  # VEC-01 token budget compliance
        metadatas.append({
            "location": r.location,
            "city": r.city,
            "budget_tier": r.budget_tier,
            "aggregate_rating": float(r.aggregate_rating),
            "primary_cuisine": r.primary_cuisine or "Multi-Cuisine",
            "average_cost_for_two": int(r.average_cost_for_two),
        })

    # Batch upsert in chunks of 200
    batch_size = 200
    for i in range(0, len(ids), batch_size):
        end = i + batch_size
        collection.upsert(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )
        logger.info(f"Indexed batch {min(end, len(ids))}/{len(ids)}")

    logger.info("ChromaDB indexing completed successfully.")


if __name__ == "__main__":
    build_chroma_index()
