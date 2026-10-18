"""
Hybrid Candidate Scorer and Pre-Ranker.
Combines semantic vector similarity, star rating, and log-scaled popularity.
"""

import math
from typing import Any, Dict, List
from backend.app.config import settings


class HybridScorer:
    """Computes weighted multi-factor ranking scores for restaurant candidates."""

    def __init__(
        self,
        weight_semantic: float = settings.WEIGHT_SEMANTIC,
        weight_rating: float = settings.WEIGHT_RATING,
        weight_popularity: float = settings.WEIGHT_POPULARITY,
    ):
        self.w_sem = weight_semantic
        self.w_rat = weight_rating
        self.w_pop = weight_popularity

    def calculate_score(
        self,
        semantic_similarity: float,
        rating: float,
        votes: int,
        max_votes: int = 15000,
    ) -> float:
        """
        Calculates hybrid score:
        S = w_sem * S_semantic + w_rat * (Rating / 5.0) + w_pop * (log(1 + Votes) / log(1 + MaxVotes))
        """
        # Ensure semantic similarity bounded [0, 1]
        sem_score = max(0.0, min(1.0, float(semantic_similarity)))

        # Rating score normalized [0, 1]
        rat_score = max(0.0, min(1.0, float(rating) / 5.0))

        # Log-scaled vote popularity normalized [0, 1]
        votes_clamped = max(0, votes)
        max_votes_effective = max(100, max_votes)
        pop_score = math.log1p(votes_clamped) / math.log1p(max_votes_effective)
        pop_score = max(0.0, min(1.0, pop_score))

        final_score = (self.w_sem * sem_score) + (self.w_rat * rat_score) + (self.w_pop * pop_score)
        return round(final_score, 4)

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        top_k: int = 6,
    ) -> List[Dict[str, Any]]:
        """Ranks candidates by calculated match_score descending."""
        if not candidates:
            return []

        # Find max votes among candidates for dynamic normalization
        max_votes = max([c.get("votes", 0) for c in candidates] or [1000])
        max_votes = max(max_votes, 100)

        scored = []
        for c in candidates:
            sem_sim = c.get("semantic_similarity", 0.7)
            score = self.calculate_score(
                semantic_similarity=sem_sim,
                rating=c.get("aggregate_rating", 0.0),
                votes=c.get("votes", 0),
                max_votes=max_votes,
            )
            c_copy = dict(c)
            c_copy["match_score"] = score
            scored.append(c_copy)

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:top_k]


hybrid_scorer = HybridScorer()
