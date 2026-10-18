"""
SQLAlchemy ORM models and database connection utilities for SQLite metadata storage.
Includes Write-Ahead Logging (WAL) pragmas to prevent concurrency deadlocks.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.config import settings

Base = declarative_base()


class Restaurant(Base):
    """
    Sanitized restaurant entity populated from the Hugging Face Zomato dataset.
    """
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    location = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, default="Bangalore", index=True)
    
    # Cuisines stored as JSON array string, e.g., '["North Indian", "Mughlai"]'
    cuisines = Column(Text, nullable=False, default="[]")
    primary_cuisine = Column(String(100), nullable=True, index=True)
    
    # Numerical cost and derived budget tier ('low', 'medium', 'high')
    average_cost_for_two = Column(Integer, nullable=False, index=True)
    budget_tier = Column(String(50), nullable=False, index=True)
    
    # Rating metrics
    aggregate_rating = Column(Float, nullable=False, default=0.0, index=True)
    is_rated = Column(Boolean, nullable=False, default=True, index=True)
    votes = Column(Integer, nullable=False, default=0, index=True)
    
    # Operational flags
    has_online_delivery = Column(Boolean, nullable=False, default=False)
    has_table_booking = Column(Boolean, nullable=False, default=False)
    
    # Features & synthesized reviews
    # Highlights stored as JSON array string, e.g., '["Casual Dining", "Pasta"]'
    highlights = Column(Text, nullable=False, default="[]")
    reviews_summary = Column(Text, nullable=True)
    synthetic_profile = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_location_budget", "location", "budget_tier"),
        Index("idx_city_budget", "city", "budget_tier"),
        Index("idx_budget_rating", "budget_tier", "aggregate_rating"),
        Index("idx_cost_rating", "average_cost_for_two", "aggregate_rating"),
    )

    def get_cuisines_list(self) -> List[str]:
        """Deserialize cuisines JSON string into Python list."""
        if not self.cuisines:
            return []
        try:
            return json.loads(self.cuisines)
        except (json.JSONDecodeError, TypeError):
            return [c.strip() for c in self.cuisines.split(",") if c.strip()]

    def get_highlights_list(self) -> List[str]:
        """Deserialize highlights JSON string into Python list."""
        if not self.highlights:
            return []
        try:
            return json.loads(self.highlights)
        except (json.JSONDecodeError, TypeError):
            return [h.strip() for h in self.highlights.split(",") if h.strip()]

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "location": self.location,
            "city": self.city,
            "cuisines": self.get_cuisines_list(),
            "primary_cuisine": self.primary_cuisine,
            "average_cost_for_two": self.average_cost_for_two,
            "budget_tier": self.budget_tier,
            "aggregate_rating": self.aggregate_rating,
            "is_rated": self.is_rated,
            "votes": self.votes,
            "has_online_delivery": self.has_online_delivery,
            "has_table_booking": self.has_table_booking,
            "highlights": self.get_highlights_list(),
            "reviews_summary": self.reviews_summary,
            "synthetic_profile": self.synthetic_profile,
        }


class QueryFeedback(Base):
    """
    Telemetry and user feedback logging for recommendation outputs.
    """
    __tablename__ = "query_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    recommendation_id = Column(String(100), nullable=True, index=True)
    restaurant_id = Column(Integer, nullable=True, index=True)
    user_query = Column(Text, nullable=True)
    rating_score = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Initialize SQLite Engine with WAL configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable Write-Ahead Logging (WAL) and normal synchronous modes
    to avoid 'database is locked' errors during concurrent reads and writes.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize SQLite database tables."""
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency generator for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
