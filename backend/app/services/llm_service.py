"""
LLM Service — Phase 4: LLM Reasoning, Ranking, Explanations & Summarization (Groq)
====================================================================================
Integrates the Groq LPU™ inference engine for ultra-low-latency restaurant ranking,
personalized AI explanations, and executive choices summaries.

Supports:
  • Official Groq SDK  (groq.AsyncGroq)  — preferred path
  • Async HTTP fallback (httpx.AsyncClient) — automatic when SDK unavailable
  • Deterministic heuristic fallback       — zero-downtime when API unreachable

Anti-hallucination: Every returned restaurant_id is validated against the candidate pool.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

import httpx

from backend.app.config import settings
from backend.app.models.schemas import AIExplanation, RecommendationItem

logger = logging.getLogger("llm_service")

# ---------------------------------------------------------------------------
# Attempt to import the official Groq SDK; fall back gracefully
# ---------------------------------------------------------------------------
try:
    from groq import AsyncGroq  # type: ignore[import-untyped]

    _GROQ_SDK_AVAILABLE = True
    logger.info("Groq SDK detected — will use groq.AsyncGroq for LLM calls.")
except ImportError:
    _GROQ_SDK_AVAILABLE = False
    logger.info("Groq SDK not installed — will use httpx.AsyncClient as HTTP fallback.")


# ============================================================================
#  Prompt Templates
# ============================================================================

SYSTEM_PROMPT = """\
You are an impartial, world-class culinary recommendation expert.

STRICT GROUNDING RULES — read carefully:
1. You may ONLY select and rank restaurants from the provided candidate list.
2. NEVER invent, fabricate, or hallucinate restaurant names, prices, dishes, \
   ratings, locations, or any other data not explicitly present in the candidates.
3. Your output MUST be strictly valid JSON conforming to the schema below.
4. Do NOT include markdown fences, commentary, or any text outside the JSON object.

REQUIRED JSON SCHEMA:
{
  "choices_summary": "<string: 2-4 sentence executive overview comparing the top \
picks and highlighting trade-offs such as best budget vs. highest rated>",
  "recommendations": [
    {
      "restaurant_id": <int: must match a candidate id>,
      "name": "<string: exact name from candidate>",
      "cuisine": "<string: comma-separated cuisines from candidate>",
      "rating": <float: aggregate_rating from candidate>,
      "votes": <int: votes from candidate>,
      "estimated_cost": <int: average_cost_for_two from candidate>,
      "location": "<string: location from candidate>",
      "match_score": <float 0-1: your confidence this fits the user>,
      "ai_explanation": {
        "summary": "<string: 1-sentence punchy rationale>",
        "why_recommended": "<string: detailed justification citing specific user \
criteria such as budget, cuisine, location, and implicit preferences>",
        "highlighted_features": ["<feature1>", "<feature2>", "..."]
      }
    }
  ]
}

RANKING DIRECTIVES:
• Re-rank the candidates (top 3-5) to best match the user's explicit criteria \
  (budget tier, cuisine preference, location) AND implicit preferences \
  (e.g. romantic, family-friendly, quick service, outdoor seating, late night).
• For each restaurant, generate a personalized ai_explanation with:
   – summary: one sentence, punchy
   – why_recommended: cite specific user criteria that this restaurant satisfies
   – highlighted_features: list 2-5 distinguishing features from highlights/reviews
• Synthesize a choices_summary comparing recommendations and noting trade-offs \
  (e.g. "best for budget-conscious diners" vs. "highest-rated splurge").
"""


def _build_user_prompt(
    candidates: List[Dict[str, Any]],
    user_query: Optional[str],
    location: Optional[str],
    budget_tier: Optional[str],
) -> str:
    """Construct the user prompt with compact candidate serialization."""
    # Serialize top-K candidate pool (≤ 5) with only fields the LLM needs
    compact_candidates = []
    for c in candidates[:5]:
        compact_candidates.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "cuisines": c.get("cuisines", []),
            "average_cost_for_two": c.get("average_cost_for_two"),
            "aggregate_rating": c.get("aggregate_rating"),
            "votes": c.get("votes", 0),
            "location": c.get("location"),
            "budget_tier": c.get("budget_tier"),
            "highlights": c.get("highlights", [])[:6],
            "reviews_summary": (c.get("reviews_summary") or "")[:200],
        })

    candidates_json = json.dumps(compact_candidates, ensure_ascii=False, indent=None)

    parts = [
        f"User query: {user_query or 'General dining recommendation'}",
        f"Location preference: {location or 'any'}",
        f"Budget tier: {budget_tier or 'any'}",
        f"\nCandidate restaurants (JSON):\n{candidates_json}",
        "\nProduce the required JSON output following the schema in your instructions. "
        "Remember: only use restaurant data from the candidates above.",
    ]
    return "\n".join(parts)


# ============================================================================
#  LLM Service
# ============================================================================

class LLMService:
    """
    Manages LLM reasoning via Groq, structured validation, and resilient
    deterministic fallback generation.
    """

    def __init__(self) -> None:
        self.provider: str = settings.LLM_PROVIDER.lower()
        self.timeout: float = settings.LLM_TIMEOUT_SECONDS
        self.max_tokens: int = getattr(settings, "LLM_MAX_TOKENS", 1500)

        # Select model based on provider
        if self.provider == "groq":
            self.model: str = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        else:
            self.model = settings.LLM_MODEL

        # Pre-initialize Groq SDK client (lazy, lightweight)
        self._groq_client: Optional[Any] = None
        if self.provider == "groq" and _GROQ_SDK_AVAILABLE and settings.GROQ_API_KEY:
            try:
                self._groq_client = AsyncGroq(
                    api_key=settings.GROQ_API_KEY,
                    timeout=self.timeout,
                )
            except Exception as exc:
                logger.warning(f"Groq SDK client init failed: {exc}. Will use httpx fallback.")

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    async def generate_recommendations(
        self,
        candidates: List[Dict[str, Any]],
        user_query: Optional[str] = None,
        location: Optional[str] = None,
        budget_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Coordinate LLM reasoning or seamlessly default to heuristic fallback.

        Flow:
          1. Check API key availability
          2. Call Groq (SDK → httpx fallback)
          3. Validate & parse response (Pydantic + ID integrity)
          4. On any failure → deterministic heuristic fallback
        """
        if not candidates:
            return {
                "choices_summary": "No matching restaurants found for your filter combination.",
                "recommendations": [],
            }

        # Gate: check API key for selected provider
        if not self._has_api_key():
            logger.info(
                f"No API key configured for provider '{self.provider}'. "
                "Activating deterministic heuristic reasoning engine."
            )
            return self.generate_heuristic_fallback(candidates, user_query, location, budget_tier)

        try:
            raw_response = await self._call_llm(candidates, user_query, location, budget_tier)
            return self._parse_and_validate(raw_response, candidates)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning(
                    "Groq API rate-limited (HTTP 429). "
                    "Falling back to deterministic heuristic engine."
                )
            else:
                logger.error(
                    f"Groq API HTTP error {exc.response.status_code}: {exc}. "
                    "Falling back to heuristic generator."
                )
            return self.generate_heuristic_fallback(candidates, user_query, location, budget_tier)
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.warning(
                f"Groq API call timed out ({self.timeout}s ceiling): {exc}. "
                "Falling back to heuristic generator."
            )
            return self.generate_heuristic_fallback(candidates, user_query, location, budget_tier)
        except (httpx.ConnectError, httpx.NetworkError, ConnectionError, OSError) as exc:
            logger.warning(
                f"Groq API connection failure: {exc}. "
                "Falling back to heuristic generator."
            )
            return self.generate_heuristic_fallback(candidates, user_query, location, budget_tier)
        except Exception as exc:
            logger.error(
                f"LLM generation failed unexpectedly: {type(exc).__name__}: {exc}. "
                "Falling back to heuristic generator."
            )
            return self.generate_heuristic_fallback(candidates, user_query, location, budget_tier)

    # ------------------------------------------------------------------
    #  LLM Call Dispatch
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        candidates: List[Dict[str, Any]],
        user_query: Optional[str],
        location: Optional[str],
        budget_tier: Optional[str],
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate LLM backend. Currently supports Groq only."""
        if self.provider == "groq":
            return await self._call_groq(candidates, user_query, location, budget_tier)
        # Future: elif self.provider == "gemini" / "openai" ...
        raise ValueError(f"Unsupported LLM provider for live calls: {self.provider}")

    async def _call_groq(
        self,
        candidates: List[Dict[str, Any]],
        user_query: Optional[str],
        location: Optional[str],
        budget_tier: Optional[str],
    ) -> Dict[str, Any]:
        """
        Call Groq LLM with grounded prompt and JSON Mode enforcement.

        Attempts the official SDK first; falls back to httpx if unavailable.
        Logs latency, token consumption, and fallback trigger events.
        """
        user_prompt = _build_user_prompt(candidates, user_query, location, budget_tier)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        start_time = time.perf_counter()

        # --- Path A: Official Groq SDK ---
        if self._groq_client is not None:
            try:
                response = await self._groq_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=self.max_tokens,
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                content = response.choices[0].message.content or ""

                # Log token usage & latency
                usage = getattr(response, "usage", None)
                if usage:
                    logger.info(
                        f"Groq SDK response | model={self.model} | "
                        f"latency={elapsed_ms:.0f}ms | "
                        f"prompt_tokens={usage.prompt_tokens} | "
                        f"completion_tokens={usage.completion_tokens} | "
                        f"total_tokens={usage.total_tokens}"
                    )
                else:
                    logger.info(
                        f"Groq SDK response | model={self.model} | latency={elapsed_ms:.0f}ms"
                    )

                return self._safe_json_parse(content)

            except Exception as sdk_exc:
                logger.warning(
                    f"Groq SDK call failed ({type(sdk_exc).__name__}: {sdk_exc}). "
                    "Retrying via httpx HTTP fallback."
                )
                # Fall through to httpx path

        # --- Path B: httpx HTTP Client Fallback ---
        return await self._call_groq_httpx(messages, start_time)

    async def _call_groq_httpx(
        self,
        messages: List[Dict[str, str]],
        start_time: float,
    ) -> Dict[str, Any]:
        """Direct HTTP call to Groq OpenAI-compatible endpoint via httpx."""
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Extract content
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        # Log token usage & latency
        usage = data.get("usage", {})
        if usage:
            logger.info(
                f"Groq httpx response | model={self.model} | "
                f"latency={elapsed_ms:.0f}ms | "
                f"prompt_tokens={usage.get('prompt_tokens', '?')} | "
                f"completion_tokens={usage.get('completion_tokens', '?')} | "
                f"total_tokens={usage.get('total_tokens', '?')}"
            )
        else:
            logger.info(
                f"Groq httpx response | model={self.model} | latency={elapsed_ms:.0f}ms"
            )

        return self._safe_json_parse(content)

    # ------------------------------------------------------------------
    #  Response Parsing & Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_json_parse(content: str) -> Dict[str, Any]:
        """Parse JSON content from LLM output, stripping markdown fences if present."""
        text = content.strip()
        # Strip markdown code fences (```json ... ```)
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse JSON from LLM response: {exc}")
            raise ValueError(f"Malformed JSON from LLM: {exc}") from exc

    def _parse_and_validate(
        self,
        data: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate LLM JSON output against Pydantic schemas and enforce
        candidate ID integrity (anti-hallucination guard).
        """
        # --- Structural validation ---
        if not isinstance(data, dict):
            logger.error("LLM response is not a dict; falling back.")
            return self.generate_heuristic_fallback(candidates, None, None, None)

        choices_summary = data.get("choices_summary", "")
        raw_recs = data.get("recommendations", [])

        if not choices_summary or not isinstance(raw_recs, list):
            logger.error(
                "LLM response missing 'choices_summary' or 'recommendations'; falling back."
            )
            return self.generate_heuristic_fallback(candidates, None, None, None)

        # --- Build valid candidate ID set for anti-hallucination ---
        valid_ids: Set[int] = {c.get("id") for c in candidates if c.get("id") is not None}

        # Also build a name→id lookup for remapping attempts
        name_to_candidate: Dict[str, Dict[str, Any]] = {
            c.get("name", "").strip().lower(): c
            for c in candidates
            if c.get("name")
        }

        parsed_recs: List[RecommendationItem] = []
        hallucinated_count = 0

        for rec in raw_recs:
            if not isinstance(rec, dict):
                continue

            rid = rec.get("restaurant_id")

            # --- Candidate ID integrity check ---
            if rid not in valid_ids:
                # Attempt remap by name match
                rec_name = (rec.get("name") or "").strip().lower()
                matched_candidate = name_to_candidate.get(rec_name)

                if matched_candidate:
                    remapped_id = matched_candidate.get("id")
                    logger.warning(
                        f"Remapped hallucinated restaurant_id={rid} to {remapped_id} "
                        f"via name match '{rec.get('name')}'."
                    )
                    rid = remapped_id
                else:
                    hallucinated_count += 1
                    logger.warning(
                        f"Discarding hallucinated recommendation: restaurant_id={rid}, "
                        f"name='{rec.get('name')}' — not in candidate pool."
                    )
                    continue

            # --- Parse AI explanation via Pydantic ---
            ai_exp_data = rec.get("ai_explanation", {})
            if not isinstance(ai_exp_data, dict):
                ai_exp_data = {}

            try:
                ai_exp = AIExplanation(
                    summary=ai_exp_data.get("summary", "Recommended based on your preferences."),
                    why_recommended=ai_exp_data.get(
                        "why_recommended",
                        "This restaurant matches your stated dining criteria.",
                    ),
                    highlighted_features=ai_exp_data.get("highlighted_features", []),
                )
            except Exception as val_exc:
                logger.warning(f"AIExplanation validation failed for ID {rid}: {val_exc}")
                ai_exp = AIExplanation(
                    summary="Recommended based on your preferences.",
                    why_recommended="This restaurant matches your stated dining criteria.",
                    highlighted_features=[],
                )

            # --- Build RecommendationItem via Pydantic ---
            try:
                item = RecommendationItem(
                    restaurant_id=rid,
                    name=rec.get("name", ""),
                    cuisine=rec.get("cuisine", ""),
                    rating=float(rec.get("rating", 0.0)),
                    votes=int(rec.get("votes", 0)),
                    estimated_cost=int(rec.get("estimated_cost", 0)),
                    location=rec.get("location", ""),
                    address=rec.get("address"),
                    match_score=self._clamp_score(rec.get("match_score")),
                    ai_explanation=ai_exp,
                )
                parsed_recs.append(item)
            except Exception as val_exc:
                logger.warning(
                    f"RecommendationItem validation failed for ID {rid}: {val_exc}. Skipping."
                )

        if hallucinated_count > 0:
            logger.info(
                f"Anti-hallucination guard: discarded {hallucinated_count} ungrounded "
                f"recommendation(s) from LLM output."
            )

        # If all recommendations were hallucinated, fall back
        if not parsed_recs:
            logger.error("All LLM recommendations failed validation. Falling back to heuristic.")
            return self.generate_heuristic_fallback(candidates, None, None, None)

        return {
            "choices_summary": choices_summary,
            "recommendations": parsed_recs,
        }

    @staticmethod
    def _clamp_score(value: Any) -> Optional[float]:
        """Clamp match_score to [0.0, 1.0] or return None."""
        if value is None:
            return None
        try:
            v = float(value)
            return max(0.0, min(1.0, v))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    #  Deterministic Heuristic Fallback (Task 4.5 / FALLBACK-01)
    # ------------------------------------------------------------------

    def generate_heuristic_fallback(
        self,
        candidates: List[Dict[str, Any]],
        user_query: Optional[str] = None,
        location: Optional[str] = None,
        budget_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Zero-latency deterministic fallback that constructs template-driven
        explanations and an executive summary purely from SQLite metadata.

        Designed to respond in <15ms with zero unhandled exceptions.
        """
        fallback_start = time.perf_counter()
        logger.info("Heuristic fallback engine activated.")

        recs: List[RecommendationItem] = []
        names: List[str] = []

        for c in candidates:
            name = c.get("name", "Restaurant")
            names.append(name)

            cuisines_raw = c.get("cuisines", [])
            if isinstance(cuisines_raw, list):
                cuisine_str = ", ".join(cuisines_raw) if cuisines_raw else "Multi-Cuisine"
                primary_cuisine = cuisines_raw[0] if cuisines_raw else "Multi-Cuisine"
            else:
                cuisine_str = str(cuisines_raw)
                primary_cuisine = cuisine_str.split(",")[0].strip() if cuisine_str else "Dining"

            rating = c.get("aggregate_rating", 0.0)
            cost = c.get("average_cost_for_two", 500)
            votes = c.get("votes", 0)
            highlights = c.get("highlights", [])
            highlights_str = ", ".join(highlights[:3]) if highlights else "popular dishes"
            loc = c.get("location", "the area")
            tier = c.get("budget_tier", "selected")

            explanation = AIExplanation(
                summary=(
                    f"Top-rated {primary_cuisine} recommendation in {loc} "
                    f"for your {tier} budget."
                ),
                why_recommended=(
                    f"{name} fits your dining criteria with an impressive "
                    f"{rating:.1f}-star rating and an estimated cost of ₹{cost} for two. "
                    f"Celebrated for {highlights_str}, it provides consistent quality "
                    f"and quick, reliable hospitality."
                    + (f" Perfectly suited for: {user_query}." if user_query else "")
                ),
                highlighted_features=(
                    highlights[:4]
                    or [f"{primary_cuisine} Specials", f"{tier.capitalize()} Fit"]
                ),
            )

            rec_item = RecommendationItem(
                restaurant_id=c.get("id", 0),
                name=name,
                cuisine=cuisine_str,
                rating=rating,
                votes=votes,
                estimated_cost=cost,
                location=f"{loc}, {c.get('city', 'Bangalore')}",
                address=c.get("address"),
                match_score=c.get("match_score", 0.85),
                ai_explanation=explanation,
            )
            recs.append(rec_item)

        # Executive choices summary
        loc_text = f" in {location}" if location else ""
        budget_text = f" within your {budget_tier} budget" if budget_tier else ""

        if len(names) >= 2:
            choices_summary = (
                f"Here are {len(recs)} highly recommended dining destinations"
                f"{loc_text}{budget_text}. "
                f"Leading the options, {names[0]} excels in customer satisfaction "
                f"and quality, while {names[1]} offers a compelling alternative with "
                f"its own culinary strengths. "
                f"Each option has been selected for consistent ratings and verified "
                f"dining atmosphere."
            )
        elif names:
            choices_summary = (
                f"We found a top dining recommendation{loc_text}{budget_text}: "
                f"{names[0]}. This venue stands out for its consistent quality and "
                f"verified customer satisfaction."
            )
        else:
            choices_summary = (
                "No restaurants matched your exact criteria. "
                "Try broadening your filters for more options."
            )

        elapsed_ms = (time.perf_counter() - fallback_start) * 1000
        logger.info(f"Heuristic fallback completed in {elapsed_ms:.1f}ms — {len(recs)} items.")

        return {
            "choices_summary": choices_summary,
            "recommendations": recs,
        }

    # ------------------------------------------------------------------
    #  Utility
    # ------------------------------------------------------------------

    def _has_api_key(self) -> bool:
        """Check if the configured provider has a valid API key."""
        if self.provider == "groq":
            return bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here")
        if self.provider == "gemini":
            return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
        if self.provider == "openai":
            return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here")
        return False


# Module-level singleton
llm_service = LLMService()
