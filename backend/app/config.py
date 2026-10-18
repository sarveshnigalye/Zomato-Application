"""
Configuration management for AI-Powered Restaurant Recommendation System.
Loads environment variables and sets path constants and model hyper-parameters.
"""

from pathlib import Path
from typing import List, Optional, Any
from pydantic import field_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None

# Derive project root (assumes backend/app/config.py -> two levels up to backend, three levels up to project root)
CURRENT_FILE = Path(__file__).resolve()
APP_DIR = CURRENT_FILE.parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
CHROMA_DIR = EMBEDDINGS_DIR / "chroma"
SQLITE_DB_PATH = PROCESSED_DATA_DIR / "restaurants.db"


class Settings(BaseSettings):
    """Application settings backed by environment variables."""

    # Project metadata
    PROJECT_NAME: str = "AI-Powered Restaurant Recommendation System"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]

    # Hugging Face Dataset configuration
    HF_DATASET_NAME: str = "ManikaSaini/zomato-restaurant-recommendation"
    RAW_DATA_PATH: str = str(RAW_DATA_DIR / "zomato_hf.csv")

    # Relational Database Configuration
    DATABASE_URL: str = f"sqlite:///{SQLITE_DB_PATH.as_posix()}"
    ASYNC_DATABASE_URL: str = f"sqlite+aiosqlite:///{SQLITE_DB_PATH.as_posix()}"

    # Vector Database & Embeddings
    CHROMA_PERSIST_DIRECTORY: str = str(CHROMA_DIR)
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION_NAME: str = "restaurant_embeddings"

    # LLM Settings
    LLM_PROVIDER: str = "groq"  # "groq", "gemini", "openai", or "mock"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TIMEOUT_SECONDS: float = 3.0
    LLM_MAX_TOKENS: int = 1500  # Cap output tokens (1000-1500) for Groq LPU speed

    # Hybrid Pre-Ranking Weights
    WEIGHT_SEMANTIC: float = 0.5
    WEIGHT_RATING: float = 0.3
    WEIGHT_POPULARITY: float = 0.2

    # Budget Tier Cutoffs (INR for two people)
    BUDGET_LOW_MAX: int = 500
    BUDGET_MEDIUM_MAX: int = 1500

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            if "," in v:
                return [i.strip() for i in v.split(",") if i.strip()]
            return [v]
        return v

    # Pydantic Settings Config
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env")),
            env_file_encoding="utf-8",
            extra="ignore",
        )
    else:
        class Config:
            env_file = str(PROJECT_ROOT / ".env")
            extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        # Normalize paths to absolute paths rooted at PROJECT_ROOT
        if self.DATABASE_URL.startswith("sqlite:///") and not Path(self.DATABASE_URL.replace("sqlite:///", "")).is_absolute():
            rel_path = self.DATABASE_URL.replace("sqlite:///", "")
            self.DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / rel_path).resolve().as_posix()}"
            
        if self.ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite:///") and not Path(self.ASYNC_DATABASE_URL.replace("sqlite+aiosqlite:///", "")).is_absolute():
            rel_path = self.ASYNC_DATABASE_URL.replace("sqlite+aiosqlite:///", "")
            self.ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{(PROJECT_ROOT / rel_path).resolve().as_posix()}"

        if not Path(self.RAW_DATA_PATH).is_absolute():
            self.RAW_DATA_PATH = str((PROJECT_ROOT / self.RAW_DATA_PATH).resolve())

        if not Path(self.CHROMA_PERSIST_DIRECTORY).is_absolute():
            self.CHROMA_PERSIST_DIRECTORY = str((PROJECT_ROOT / self.CHROMA_PERSIST_DIRECTORY).resolve())

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_file = Path(self.DATABASE_URL.replace("sqlite:///", ""))
            db_file.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()


