"""
Unit and integration tests for Phase 1 Data Ingestion and Sanitization.
Verifies edge cases DATA-01 through DATA-07 from Docs/edge-case.md.
"""

import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.database import Base, Restaurant
from backend.app.scripts.ingest_data import (
    parse_rating,
    parse_cost,
    assign_budget_tier,
    parse_cuisines,
    synthesize_highlights,
    sanitize_row,
    generate_restaurant_profile,
)


class TestRatingParsing:
    """Tests for DATA-02: Slash-Rating & Unrated Formatting."""

    def test_slash_rating(self):
        rating, is_rated = parse_rating("4.1/5")
        assert rating == 4.1
        assert is_rated is True

    def test_float_string_rating(self):
        rating, is_rated = parse_rating("3.8")
        assert rating == 3.8
        assert is_rated is True

    def test_new_restaurant(self):
        rating, is_rated = parse_rating("NEW")
        assert rating == 0.0
        assert is_rated is False

    def test_hyphen_unrated(self):
        rating, is_rated = parse_rating("-")
        assert rating == 0.0
        assert is_rated is False

    def test_none_or_empty(self):
        rating, is_rated = parse_rating(None)
        assert rating == 0.0
        assert is_rated is False


class TestCostParsing:
    """Tests for DATA-03: Localized Currency & Comma Cost Formatting."""

    def test_comma_cost(self):
        assert parse_cost("1,200") == 1200
        assert parse_cost("2,500") == 2500

    def test_currency_symbol(self):
        assert parse_cost("₹800") == 800

    def test_empty_or_none_defaults(self):
        assert parse_cost(None, default_cost=500) == 500
        assert parse_cost("", default_cost=500) == 500


class TestBudgetTierAssignment:
    """Tests for DATA-04: Strict budget tier classification boundaries."""

    def test_low_tier_boundary(self):
        assert assign_budget_tier(150) == "low"
        assert assign_budget_tier(500) == "low"

    def test_medium_tier_boundary(self):
        assert assign_budget_tier(501) == "medium"
        assert assign_budget_tier(1000) == "medium"
        assert assign_budget_tier(1500) == "medium"

    def test_high_tier_boundary(self):
        assert assign_budget_tier(1501) == "high"
        assert assign_budget_tier(3000) == "high"


class TestCuisineNormalization:
    """Tests for DATA-05: Dirty & Inconsistent Cuisine Representations."""

    def test_casing_and_whitespace(self):
        cuisines, primary = parse_cuisines(" north indian , mughlai , fast food ")
        assert "North Indian" in cuisines
        assert "Mughlai" in cuisines
        assert "Fast Food" in cuisines
        assert primary == "North Indian"

    def test_deduplication(self):
        cuisines, primary = parse_cuisines("Italian, Pizza, italian")
        assert len(cuisines) == 2
        assert cuisines == ["Italian", "Pizza"]

    def test_empty_cuisine(self):
        cuisines, primary = parse_cuisines(None)
        assert cuisines == ["Multi-Cuisine"]
        assert primary == "Multi-Cuisine"


class TestHighlightsSynthesis:
    """Tests for DATA-06: High Sparsity in dish_liked and rest_type."""

    def test_full_attributes(self):
        tags = synthesize_highlights("Casual Dining", "Pasta, Pizza", ["Italian"])
        assert "Casual Dining" in tags
        assert "Pasta" in tags
        assert "Pizza" in tags

    def test_sparse_fallback(self):
        tags = synthesize_highlights(None, None, ["South Indian"])
        assert len(tags) > 0
        assert any("South Indian" in t for t in tags) or "Casual Dining" in tags


class TestSanitizeRow:
    """Tests comprehensive sanitization and synthetic profile generation."""

    def test_valid_row(self):
        raw = {
            "name": "Toit",
            "location": "Indiranagar",
            "address": "100 Feet Road, Indiranagar",
            "cuisines": "Italian, American, Craft Beer",
            "rate": "4.7/5",
            "votes": "12000",
            "approx_cost(for two people)": "1,500",
            "online_order": "Yes",
            "book_table": "Yes",
            "rest_type": "Microbrewery",
            "dish_liked": "Pizza, Stout",
            "reviews_list": "Energetic brewery with artisan food.",
        }
        sanitized = sanitize_row(raw)
        assert sanitized is not None
        assert sanitized["name"] == "Toit"
        assert sanitized["budget_tier"] == "medium"
        assert sanitized["average_cost_for_two"] == 1500
        assert sanitized["aggregate_rating"] == 4.7
        assert sanitized["is_rated"] is True
        assert sanitized["has_online_delivery"] is True
        assert sanitized["has_table_booking"] is True
        assert "Toit" in sanitized["synthetic_profile"]
