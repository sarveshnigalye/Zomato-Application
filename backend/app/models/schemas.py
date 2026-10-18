"""
Pydantic schemas and Data Transfer Objects (DTOs) for the Recommendation API.
Enforces validation rules, bounds, and structured JSON output serialization.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BudgetTier(str, Enum):
    """Categorical budget tiers based on average cost for two."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RestaurantBase(BaseModel):
    name: str = Field(..., description="Restaurant name")
    address: Optional[str] = Field(None, description="Physical street address")
    location: str = Field(..., description="Neighborhood or locality")
    city: str = Field("Bangalore", description="Canonical city")
    cuisines: List[str] = Field(default_factory=list, description="List of cuisines")
    primary_cuisine: Optional[str] = Field(None, description="Primary dominant cuisine")
    average_cost_for_two: int = Field(..., ge=0, description="Estimated cost for two people in INR")
    budget_tier: BudgetTier = Field(..., description="Categorical budget tier (low, medium, high)")
    aggregate_rating: float = Field(0.0, ge=0.0, le=5.0, description="Rating between 0.0 and 5.0")
    is_rated: bool = Field(True, description="False if newly opened or unrated")
    votes: int = Field(0, ge=0, description="Total vote count")
    has_online_delivery: bool = Field(False, description="Whether online ordering is available")
    has_table_booking: bool = Field(False, description="Whether table reservations are supported")
    highlights: List[str] = Field(default_factory=list, description="Synthesized restaurant features")
    reviews_summary: Optional[str] = Field(None, description="Extracted customer reviews text")


class RestaurantCreate(RestaurantBase):
    synthetic_profile: Optional[str] = None


class RestaurantRead(RestaurantBase):
    id: int
    synthetic_profile: Optional[str] = None

    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    """Request payload submitted by the user or client interface."""
    query: Optional[str] = Field(
        None,
        description="Natural language preference query (e.g. 'romantic pasta with outdoor seating')",
        max_length=500,
    )
    location: Optional[str] = Field(
        None,
        description="Target city or neighborhood (e.g., 'Bangalore', 'Indiranagar', 'Delhi')",
    )
    budget_tier: Optional[BudgetTier] = Field(
        None,
        description="Categorical budget preference: 'low' (<=₹500), 'medium' (₹500-1500), 'high' (>₹1500)",
    )
    max_cost_for_two: Optional[int] = Field(
        None,
        ge=0,
        le=20000,
        description="Explicit numerical budget ceiling for two diners",
    )
    min_rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="Minimum acceptable star rating threshold",
    )
    cuisines: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred cuisine types (e.g. ['Italian', 'Continental'])",
    )
    additional_preferences: Optional[List[str]] = Field(
        default_factory=list,
        description="Qualitative feature tags (e.g. ['quick service', 'family-friendly', 'romantic'])",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of final recommendations to return",
    )

    @field_validator("cuisines", "additional_preferences", mode="before")
    def clean_string_lists(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []


class AIExplanation(BaseModel):
    """Structured LLM explanation for an individual restaurant recommendation."""
    summary: str = Field(..., description="1-sentence punchy rationale")
    why_recommended: str = Field(..., description="Detailed justification mapping to user desires")
    highlighted_features: List[str] = Field(
        default_factory=list,
        description="Key bulleted features (e.g. ['Wood-Fired Pizza', 'Fast Kitchen'])",
    )


class RecommendationItem(BaseModel):
    """Single recommended restaurant item with full metadata and AI reasoning."""
    restaurant_id: int
    name: str
    cuisine: str
    rating: float
    votes: int
    estimated_cost: int
    location: str
    address: Optional[str] = None
    match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_explanation: AIExplanation


class QuerySummary(BaseModel):
    """Summary of parameters used during the multi-stage candidate retrieval."""
    location: Optional[str] = None
    budget_tier: Optional[str] = None
    max_cost: Optional[int] = None
    min_rating: Optional[float] = None
    cuisines: List[str] = Field(default_factory=list)
    additional_preferences: List[str] = Field(default_factory=list)
    total_candidates_analyzed: int = 0
    relaxation_applied: bool = False
    relaxation_notice: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Complete response returned to the frontend or API caller."""
    status: str = "success"
    choices_summary: str = Field(..., description="High-level executive summary contrasting top picks")
    query_summary: QuerySummary
    recommendations: List[RecommendationItem] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    """User feedback payload for recommendation engagement telemetry."""
    recommendation_id: Optional[str] = None
    restaurant_id: Optional[int] = None
    user_query: Optional[str] = None
    rating_score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str = "success"
    message: str = "Feedback logged successfully"
