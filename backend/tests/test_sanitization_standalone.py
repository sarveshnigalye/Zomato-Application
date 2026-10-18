"""
Standalone unit test suite using standard library unittest.
Executes test assertions for Phase 1 data ingestion and sanitization without third-party dependencies.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.scripts.ingest_data import (
    parse_rating,
    parse_cost,
    assign_budget_tier,
    parse_cuisines,
    synthesize_highlights,
    sanitize_row,
    generate_restaurant_profile,
)


class TestDataSanitizationStandalone(unittest.TestCase):
    """Test suite covering Phase 1 edge cases (DATA-01 to DATA-07)."""

    def test_data_02_rating_parsing(self):
        """DATA-02: Rating parsing with slash, float, NEW, and null."""
        r1, is_rated1 = parse_rating("4.1/5")
        self.assertEqual(r1, 4.1)
        self.assertTrue(is_rated1)

        r2, is_rated2 = parse_rating("3.9")
        self.assertEqual(r2, 3.9)
        self.assertTrue(is_rated2)

        r3, is_rated3 = parse_rating("NEW")
        self.assertEqual(r3, 0.0)
        self.assertFalse(is_rated3)

        r4, is_rated4 = parse_rating("-")
        self.assertEqual(r4, 0.0)
        self.assertFalse(is_rated4)

        r5, is_rated5 = parse_rating(None)
        self.assertEqual(r5, 0.0)
        self.assertFalse(is_rated5)

    def test_data_03_cost_parsing(self):
        """DATA-03: Localized comma currency strings parsed to int."""
        self.assertEqual(parse_cost("1,200"), 1200)
        self.assertEqual(parse_cost("₹2,500"), 2500)
        self.assertEqual(parse_cost("600"), 600)
        self.assertEqual(parse_cost(None, default_cost=500), 500)
        self.assertEqual(parse_cost("", default_cost=500), 500)

    def test_data_04_budget_tier_boundaries(self):
        """DATA-04: Strict budget tier classification intervals."""
        # Low: <= 500
        self.assertEqual(assign_budget_tier(150), "low")
        self.assertEqual(assign_budget_tier(500), "low")

        # Medium: 501 - 1500
        self.assertEqual(assign_budget_tier(501), "medium")
        self.assertEqual(assign_budget_tier(1200), "medium")
        self.assertEqual(assign_budget_tier(1500), "medium")

        # High: > 1500
        self.assertEqual(assign_budget_tier(1501), "high")
        self.assertEqual(assign_budget_tier(3000), "high")

    def test_data_05_cuisine_normalization(self):
        """DATA-05: Clean whitespace, title-case, and deduplicate cuisines."""
        cuisines, primary = parse_cuisines(" north indian , chinese , north indian ")
        self.assertEqual(cuisines, ["North Indian", "Chinese"])
        self.assertEqual(primary, "North Indian")

        cuisines_empty, primary_empty = parse_cuisines(None)
        self.assertEqual(cuisines_empty, ["Multi-Cuisine"])
        self.assertEqual(primary_empty, "Multi-Cuisine")

    def test_data_06_highlights_synthesis(self):
        """DATA-06: Ensure highlights are synthesized and never empty."""
        tags = synthesize_highlights("Casual Dining, Wine Bar", "Pasta, Pizza", ["Italian"])
        self.assertIn("Casual Dining", tags)
        self.assertIn("Pasta", tags)
        self.assertGreater(len(tags), 0)

        # Fallback when sparse
        fallback_tags = synthesize_highlights(None, None, ["South Indian"])
        self.assertGreater(len(fallback_tags), 0)

    def test_row_sanitization_and_profile(self):
        """Complete row sanitization with synthetic profile generation."""
        raw = {
            "name": "Chianti Italian Restaurant",
            "location": "Indiranagar",
            "address": "12th Main Rd, Indiranagar",
            "cuisines": "Italian, Pizza, Pasta",
            "rate": "4.5/5",
            "votes": "2840",
            "approx_cost(for two people)": "1,200",
            "online_order": "Yes",
            "book_table": "Yes",
            "rest_type": "Casual Dining",
            "dish_liked": "Wood-Fired Pizza, Tiramisu",
            "reviews_list": "Authentic wood-fired pizza and great atmosphere.",
        }
        cleaned = sanitize_row(raw)
        self.assertIsNotNone(cleaned)
        self.assertEqual(cleaned["name"], "Chianti Italian Restaurant")
        self.assertEqual(cleaned["city"], "Bangalore")
        self.assertEqual(cleaned["budget_tier"], "medium")
        self.assertEqual(cleaned["average_cost_for_two"], 1200)
        self.assertEqual(cleaned["aggregate_rating"], 4.5)
        self.assertTrue(cleaned["is_rated"])
        self.assertTrue(cleaned["has_online_delivery"])
        self.assertTrue(cleaned["has_table_booking"])
        self.assertIn("Chianti Italian Restaurant", cleaned["synthetic_profile"])


if __name__ == "__main__":
    unittest.main()
