"""
Data Service: Structured SQL retrieval and hard filtering over SQLite metadata.
Implements the Constraint Relaxation Ladder (RET-01) for strict filter starvation.
"""

import json
from typing import List, Optional, Tuple
from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import Session

from backend.app.models.database import Restaurant
from backend.app.models.schemas import BudgetTier, RecommendationRequest


class DataService:
    """Handles structured SQL queries, filtering, and constraint relaxation."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_restaurants_by_filter(
        self,
        request: RecommendationRequest,
    ) -> Tuple[List[Restaurant], bool, Optional[str]]:
        """
        Executes deterministic multi-criteria SQL query.
        If results < 3, triggers the Constraint Relaxation Ladder (RET-01).
        Returns: (candidate_list, relaxation_applied, relaxation_notice)
        """
        candidates, applied, notice = self._execute_query(
            location=request.location,
            budget_tier=request.budget_tier.value if request.budget_tier else None,
            max_cost=request.max_cost_for_two,
            min_rating=request.min_rating,
            cuisines=request.cuisines,
        )

        # Trigger Constraint Relaxation Ladder if candidate count is too low (< 3)
        if len(candidates) < 3:
            # Step 1: Relax min_rating by 0.5
            relaxed_rating = max(0.0, (request.min_rating - 0.5)) if request.min_rating else None
            candidates, _, _ = self._execute_query(
                location=request.location,
                budget_tier=request.budget_tier.value if request.budget_tier else None,
                max_cost=request.max_cost_for_two,
                min_rating=relaxed_rating,
                cuisines=request.cuisines,
            )

            if len(candidates) >= 3:
                return (
                    candidates,
                    True,
                    f"Notice: Broadened minimum rating threshold to {relaxed_rating:.1f} stars to provide top options.",
                )

            # Step 2: Expand budget bounds
            expanded_cost = (request.max_cost_for_two * 1.3) if request.max_cost_for_two else None
            candidates, _, _ = self._execute_query(
                location=request.location,
                budget_tier=None,  # Expand all budget tiers
                max_cost=int(expanded_cost) if expanded_cost else None,
                min_rating=relaxed_rating,
                cuisines=request.cuisines,
            )

            if len(candidates) >= 3:
                return (
                    candidates,
                    True,
                    "Notice: Expanded budget criteria to nearby tiers to provide relevant recommendations.",
                )

            # Step 3: Expand locality to entire city
            candidates, _, _ = self._execute_query(
                location=None,  # Expand locality
                budget_tier=None,
                max_cost=None,
                min_rating=relaxed_rating,
                cuisines=request.cuisines,
            )

            return (
                candidates,
                True,
                "Notice: Broadened search area across the city to find the best matching dining experiences.",
            )

        return candidates, False, None

    def _execute_query(
        self,
        location: Optional[str] = None,
        budget_tier: Optional[str] = None,
        max_cost: Optional[int] = None,
        min_rating: Optional[float] = None,
        cuisines: Optional[List[str]] = None,
    ) -> Tuple[List[Restaurant], bool, Optional[str]]:
        """Core SQL filter builder."""
        query = self.db.query(Restaurant)

        # Location filter (case-insensitive substring match)
        if location and location.strip():
            loc_term = f"%{location.strip()}%"
            query = query.filter(
                or_(
                    Restaurant.location.ilike(loc_term),
                    Restaurant.city.ilike(loc_term),
                    Restaurant.address.ilike(loc_term),
                )
            )

        # Budget tier categorical filter
        if budget_tier:
            query = query.filter(Restaurant.budget_tier == budget_tier)

        # Numerical cost ceiling filter (RET-02 conflict resolution: prioritize ceiling)
        if max_cost is not None and max_cost > 0:
            query = query.filter(Restaurant.average_cost_for_two <= max_cost)

        # Minimum rating filter
        if min_rating is not None and min_rating > 0:
            query = query.filter(Restaurant.aggregate_rating >= min_rating)

        # Cuisine matching
        if cuisines and len(cuisines) > 0:
            cuisine_conditions = [
                Restaurant.cuisines.ilike(f"%{c.strip()}%") for c in cuisines if c.strip()
            ]
            if cuisine_conditions:
                query = query.filter(or_(*cuisine_conditions))

        # Order by rating and votes desc
        results = (
            query.order_by(desc(Restaurant.aggregate_rating), desc(Restaurant.votes))
            .limit(50)
            .all()
        )
        return results, False, None

    def get_restaurant_by_id(self, restaurant_id: int) -> Optional[Restaurant]:
        """Fetch single restaurant by primary key ID."""
        return self.db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    def get_distinct_cuisines(self) -> List[str]:
        """Fetch unique list of standardized cuisines across dataset."""
        rows = self.db.query(Restaurant.cuisines).all()
        cuisine_set = set()
        for (c_json,) in rows:
            if not c_json:
                continue
            try:
                for c in json.loads(c_json):
                    if c:
                        cuisine_set.add(c.strip())
            except Exception:
                pass
        return sorted(list(cuisine_set))

    def get_distinct_locations(self) -> List[str]:
        """Fetch unique list of locations/neighborhoods and cities."""
        loc_rows = self.db.query(Restaurant.location).distinct().all()
        city_rows = self.db.query(Restaurant.city).distinct().all()

        seen = set()
        result = []
        # Add cities first (e.g. Bangalore, Delhi)
        for (c,) in city_rows:
            if c and c.strip() and c.strip() not in seen:
                seen.add(c.strip())
                result.append(c.strip())
        result.sort()

        # Add localities/neighborhoods
        localities = []
        for (l,) in loc_rows:
            if l and l.strip() and l.strip() not in seen:
                seen.add(l.strip())
                localities.append(l.strip())
        localities.sort()

        return sorted(result + localities)
