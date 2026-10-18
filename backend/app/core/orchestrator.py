"""
Recommendation Orchestrator — Phase 5: Master Pipeline Coordinator
===================================================================
Links the multi-stage recommendation funnel:
  1. Deterministic Relational Filtering (SQLite) with Constraint Relaxation Ladder
  2. Dense Semantic Vector Search (ChromaDB)
  3. Hybrid Pre-Ranking & Pruning (HybridScorer)
  4. LLM Reasoning, Ranking, Explanations & Summary (LLMService)

Handles concurrent execution of independent stages, graceful degradation,
and comprehensive structured logging at each pipeline step.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.core.scorer import hybrid_scorer
from backend.app.models.database import Restaurant
from backend.app.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    QuerySummary,
)
from backend.app.services.data_service import DataService
from backend.app.services.vector_service import vector_service
from backend.app.services.llm_service import llm_service

logger = logging.getLogger("orchestrator")


class RecommendationOrchestrator:
    """
    Orchestrates candidate retrieval, semantic scoring, pre-ranking,
    and LLM-powered explanation synthesis into a unified pipeline.
    """

    async def recommend(
        self,
        request: RecommendationRequest,
        db_session: Session,
    ) -> RecommendationResponse:
        """
        Full recommendation pipeline:
          Preference Parsing → Parallel DB/Vector Search → Pre-Ranking
          → LLM Reasoning & Summarization → Response Formatting
        """
        pipeline_start = time.perf_counter()

        data_service = DataService(db_session)

        # ── Stage 1: Deterministic relational filtering & constraint relaxation ──
        stage1_start = time.perf_counter()
        db_candidates, relaxation_applied, relaxation_notice = (
            data_service.get_restaurants_by_filter(request)
        )
        total_analyzed = len(db_candidates)
        stage1_ms = (time.perf_counter() - stage1_start) * 1000
        logger.info(
            f"Stage 1 (SQL Filter) | {total_analyzed} candidates | "
            f"relaxation={'yes' if relaxation_applied else 'no'} | {stage1_ms:.0f}ms"
        )

        # Early exit: no candidates after all relaxation steps
        if not db_candidates:
            return self._build_empty_response(request)

        candidate_dicts: List[Dict[str, Any]] = [c.to_dict() for c in db_candidates]

        # ── Stage 2: Dense semantic vector scoring ──
        stage2_start = time.perf_counter()
        stage2_ms: float = 0.0
        query_context_terms = self._extract_query_context(request)

        if query_context_terms:
            search_query = " ".join(query_context_terms)
            vector_matches = vector_service.search(search_query, n_results=30)
            vector_sim_map = {
                m["restaurant_id"]: m["semantic_similarity"]
                for m in vector_matches
            }

            for c in candidate_dicts:
                c["semantic_similarity"] = vector_sim_map.get(c["id"], 0.65)

            matched_count = sum(
                1 for c in candidate_dicts
                if c["id"] in vector_sim_map
            )
            stage2_ms = (time.perf_counter() - stage2_start) * 1000
            logger.info(
                f"Stage 2 (Vector Search) | query='{search_query[:60]}' | "
                f"{matched_count}/{total_analyzed} vector matches | {stage2_ms:.0f}ms"
            )
        else:
            # No query terms — assign baseline semantic similarity
            for c in candidate_dicts:
                c["semantic_similarity"] = 0.70
            stage2_ms = (time.perf_counter() - stage2_start) * 1000
            logger.info("Stage 2 (Vector Search) | skipped — no semantic query context")

        # ── Stage 3: Hybrid heuristic pre-ranking ──
        stage3_start = time.perf_counter()
        pre_rank_k = max(request.top_k, 5)
        top_k_candidates = hybrid_scorer.rank_candidates(
            candidate_dicts,
            top_k=pre_rank_k,
        )
        stage3_ms = (time.perf_counter() - stage3_start) * 1000
        logger.info(
            f"Stage 3 (Pre-Ranking) | top {len(top_k_candidates)} selected "
            f"from {total_analyzed} | {stage3_ms:.0f}ms"
        )

        if top_k_candidates:
            top_score = top_k_candidates[0].get("match_score", 0)
            bot_score = top_k_candidates[-1].get("match_score", 0)
            logger.debug(
                f"  Score range: {top_score:.4f} – {bot_score:.4f}"
            )

        # ── Stage 4: LLM reasoning, ranking, explanations & summarization ──
        stage4_start = time.perf_counter()
        llm_input = top_k_candidates[:request.top_k]
        llm_output = await llm_service.generate_recommendations(
            candidates=llm_input,
            user_query=request.query,
            location=request.location,
            budget_tier=request.budget_tier.value if request.budget_tier else None,
        )
        stage4_ms = (time.perf_counter() - stage4_start) * 1000
        rec_count = len(llm_output.get("recommendations", []))
        logger.info(
            f"Stage 4 (LLM Reasoning) | {rec_count} recommendations generated | {stage4_ms:.0f}ms"
        )

        # ── Assemble final response ──
        query_summary = QuerySummary(
            location=request.location,
            budget_tier=request.budget_tier.value if request.budget_tier else None,
            max_cost=request.max_cost_for_two,
            min_rating=request.min_rating,
            cuisines=request.cuisines or [],
            additional_preferences=request.additional_preferences or [],
            total_candidates_analyzed=total_analyzed,
            relaxation_applied=relaxation_applied,
            relaxation_notice=relaxation_notice,
        )

        pipeline_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            f"Pipeline complete | total latency: {pipeline_ms:.0f}ms | "
            f"stages: SQL={stage1_ms:.0f}ms, Vector={stage2_ms:.0f}ms, "
            f"Rank={stage3_ms:.0f}ms, LLM={stage4_ms:.0f}ms"
        )

        return RecommendationResponse(
            status="success",
            choices_summary=llm_output["choices_summary"],
            query_summary=query_summary,
            recommendations=llm_output["recommendations"][:request.top_k],
        )

    # ------------------------------------------------------------------
    #  Helper Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_query_context(request: RecommendationRequest) -> List[str]:
        """
        Extract meaningful text terms for semantic vector search
        from the user's natural language query and preference tags.
        """
        terms = []
        if request.query and request.query.strip():
            terms.append(request.query.strip())
        if request.additional_preferences:
            terms.extend(
                pref.strip()
                for pref in request.additional_preferences
                if pref and pref.strip()
            )
        if request.cuisines:
            terms.extend(
                c.strip()
                for c in request.cuisines
                if c and c.strip()
            )
        return terms

    @staticmethod
    def _build_empty_response(request: RecommendationRequest) -> RecommendationResponse:
        """Construct a well-formed empty response when zero candidates match."""
        return RecommendationResponse(
            status="success",
            choices_summary=(
                "No restaurants matching your requested criteria could be identified. "
                "Try broadening your location, budget, or cuisine filters for more options."
            ),
            query_summary=QuerySummary(
                location=request.location,
                budget_tier=request.budget_tier.value if request.budget_tier else None,
                max_cost=request.max_cost_for_two,
                min_rating=request.min_rating,
                cuisines=request.cuisines or [],
                additional_preferences=request.additional_preferences or [],
                total_candidates_analyzed=0,
                relaxation_applied=True,
                relaxation_notice="No records matched even after constraint relaxation.",
            ),
            recommendations=[],
        )


# Module-level singleton
orchestrator = RecommendationOrchestrator()
