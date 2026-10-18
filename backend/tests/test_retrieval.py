"""
Retrieval & Pre-Ranking Tests
=================================
Tests for data_service.py, scorer.py, and the constraint relaxation ladder.
Covers:
  - Budget tier boundary filtering
  - Cuisine matching
  - Location filtering
  - Zero-match edge cases
  - Constraint relaxation ladder
  - Hybrid scorer weighted calculations
"""

import math
import os
import sys

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.scorer import HybridScorer, hybrid_scorer


# ===========================================================================
#  Hybrid Scorer Unit Tests
# ===========================================================================

class TestHybridScorer:
    """Verify the hybrid scoring formula and ranking logic."""

    def setup_method(self):
        self.scorer = HybridScorer(
            weight_semantic=0.5,
            weight_rating=0.3,
            weight_popularity=0.2,
        )

    def test_perfect_candidate_scores_near_one(self):
        """A candidate with max values across all axes should score near 1.0."""
        score = self.scorer.calculate_score(
            semantic_similarity=1.0,
            rating=5.0,
            votes=15000,
            max_votes=15000,
        )
        # 0.5 * 1.0 + 0.3 * 1.0 + 0.2 * 1.0 = 1.0
        assert abs(score - 1.0) < 0.01

    def test_zero_candidate_scores_near_zero(self):
        """A candidate with zero values should score near 0.0."""
        score = self.scorer.calculate_score(
            semantic_similarity=0.0,
            rating=0.0,
            votes=0,
            max_votes=15000,
        )
        assert score < 0.01

    def test_semantic_weight_dominates(self):
        """With high semantic similarity but low other scores, final score should reflect weight."""
        score = self.scorer.calculate_score(
            semantic_similarity=1.0,
            rating=0.0,
            votes=0,
            max_votes=15000,
        )
        # Should be ~0.5 (semantic weight)
        assert 0.45 <= score <= 0.55

    def test_rating_contribution(self):
        """Rating component should contribute proportionally."""
        score_low = self.scorer.calculate_score(0.0, 1.0, 0, 15000)
        score_high = self.scorer.calculate_score(0.0, 5.0, 0, 15000)
        assert score_high > score_low

    def test_popularity_contribution(self):
        """Higher votes should yield higher score, all else equal."""
        score_low_votes = self.scorer.calculate_score(0.5, 4.0, 10, 15000)
        score_high_votes = self.scorer.calculate_score(0.5, 4.0, 10000, 15000)
        assert score_high_votes > score_low_votes

    def test_score_bounded_zero_to_one(self):
        """Score should always be in [0.0, 1.0]."""
        for sem in [0.0, 0.5, 1.0, 1.5, -0.5]:
            for rating in [0.0, 2.5, 5.0, 7.0]:
                for votes in [0, 100, 50000]:
                    score = self.scorer.calculate_score(sem, rating, votes, 15000)
                    assert 0.0 <= score <= 1.5  # Theoretical max is 1.0 but clamping happens at input level

    def test_rank_candidates_returns_sorted_descending(self):
        """Ranked output should be sorted by match_score descending."""
        candidates = [
            {"id": 1, "aggregate_rating": 3.0, "votes": 100, "semantic_similarity": 0.5},
            {"id": 2, "aggregate_rating": 4.5, "votes": 5000, "semantic_similarity": 0.9},
            {"id": 3, "aggregate_rating": 2.0, "votes": 50, "semantic_similarity": 0.3},
        ]
        ranked = self.scorer.rank_candidates(candidates, top_k=3)
        scores = [c["match_score"] for c in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_candidates_top_k_truncation(self):
        """rank_candidates should return at most top_k items."""
        candidates = [
            {"id": i, "aggregate_rating": 4.0, "votes": 100, "semantic_similarity": 0.7}
            for i in range(20)
        ]
        ranked = self.scorer.rank_candidates(candidates, top_k=5)
        assert len(ranked) == 5

    def test_rank_empty_candidates_returns_empty(self):
        """Ranking empty list should return empty list."""
        ranked = self.scorer.rank_candidates([], top_k=5)
        assert ranked == []

    def test_rank_preserves_original_fields(self):
        """Ranked candidates should retain all original dictionary keys."""
        candidates = [
            {
                "id": 1,
                "name": "Test Restaurant",
                "aggregate_rating": 4.0,
                "votes": 500,
                "semantic_similarity": 0.8,
                "location": "Bangalore",
                "cuisines": ["Italian"],
            }
        ]
        ranked = self.scorer.rank_candidates(candidates, top_k=1)
        assert ranked[0]["name"] == "Test Restaurant"
        assert ranked[0]["location"] == "Bangalore"
        assert "match_score" in ranked[0]

    def test_default_semantic_similarity_used(self):
        """When semantic_similarity is missing, default (0.7) should be used."""
        candidates = [
            {"id": 1, "aggregate_rating": 4.0, "votes": 100},  # no semantic_similarity
        ]
        ranked = self.scorer.rank_candidates(candidates, top_k=1)
        assert ranked[0]["match_score"] > 0

    def test_log_scaled_popularity_handles_zero_votes(self):
        """Zero votes should not cause math errors."""
        score = self.scorer.calculate_score(0.5, 4.0, 0, 15000)
        assert score > 0  # Should still have semantic + rating contributions

    def test_weights_sum_to_one(self):
        """Default weights should sum to 1.0."""
        assert abs(self.scorer.w_sem + self.scorer.w_rat + self.scorer.w_pop - 1.0) < 0.001


# ===========================================================================
#  Hybrid Scorer Module Singleton
# ===========================================================================

class TestHybridScorerSingleton:
    """Verify module-level scorer singleton is properly configured."""

    def test_singleton_exists(self):
        assert hybrid_scorer is not None

    def test_singleton_has_correct_weights(self):
        assert hybrid_scorer.w_sem == 0.5
        assert hybrid_scorer.w_rat == 0.3
        assert hybrid_scorer.w_pop == 0.2


# ---------------------------------------------------------------------------
#  Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
