"""
Phase 5 Integration Tests: FastAPI Backend & Orchestration
============================================================
Tests cover:
  - Health check endpoint
  - POST /api/v1/recommend (full pipeline, edge cases, validation)
  - GET /api/v1/restaurants/{id} (found and not found)
  - GET /api/v1/cuisines (distinct cuisine listing)
  - GET /api/v1/locations (distinct location listing)
  - POST /api/v1/feedback (valid submission and validation errors)
  - Uniform exception handlers (validation, 404, 500)
  - Security headers presence
  - CORS header presence
  - Request validation error formatting

Note: The `client` fixture and in-memory test DB are provided by conftest.py.
"""

import pytest


# ===========================================================================
#  System Endpoints
# ===========================================================================

class TestHealthCheck:
    """Verify the /health endpoint returns correct liveness data."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "version" in data

    def test_health_includes_llm_provider(self, client):
        response = client.get("/health")
        data = response.json()
        assert "llm_provider" in data


# ===========================================================================
#  Recommendation Endpoint
# ===========================================================================

class TestRecommendEndpoint:
    """Integration tests for POST /api/v1/recommend."""

    def test_recommend_basic_request(self, client):
        """A minimal valid request should return a structured response."""
        payload = {
            "query": "Italian food",
            "location": "Bangalore",
            "top_k": 3,
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "choices_summary" in data
        assert "query_summary" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_recommend_with_budget_tier(self, client):
        """Request with budget_tier filter."""
        payload = {
            "query": "cheap eats",
            "budget_tier": "low",
            "top_k": 3,
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_recommend_with_cuisine_filter(self, client):
        """Request with cuisine preference."""
        payload = {
            "cuisines": ["North Indian", "Chinese"],
            "top_k": 3,
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_recommend_with_all_filters(self, client):
        """Request with all possible filter parameters."""
        payload = {
            "query": "romantic dinner",
            "location": "Koramangala",
            "budget_tier": "medium",
            "max_cost_for_two": 1200,
            "min_rating": 3.5,
            "cuisines": ["Italian"],
            "additional_preferences": ["romantic", "outdoor seating"],
            "top_k": 5,
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "query_summary" in data

        # Verify query_summary echoes request parameters
        qs = data["query_summary"]
        assert qs["location"] == "Koramangala"
        assert qs["budget_tier"] == "medium"

    def test_recommend_empty_query_returns_results(self, client):
        """Request with no query or filters should still work (broadest search)."""
        payload = {"top_k": 3}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_recommend_response_has_choices_summary(self, client):
        """Every successful response must include a choices_summary string."""
        payload = {"query": "quick lunch", "top_k": 2}
        response = client.post("/api/v1/recommend", json=payload)
        data = response.json()
        assert isinstance(data.get("choices_summary"), str)
        assert len(data["choices_summary"]) > 0

    def test_recommend_recommendations_structure(self, client):
        """Verify each recommendation item has required fields."""
        payload = {"query": "biryani", "top_k": 3}
        response = client.post("/api/v1/recommend", json=payload)
        data = response.json()

        for rec in data.get("recommendations", []):
            assert "restaurant_id" in rec
            assert "name" in rec
            assert "cuisine" in rec
            assert "rating" in rec
            assert "votes" in rec
            assert "estimated_cost" in rec
            assert "location" in rec
            assert "ai_explanation" in rec

            # AI explanation sub-structure
            ai_exp = rec["ai_explanation"]
            assert "summary" in ai_exp
            assert "why_recommended" in ai_exp
            assert "highlighted_features" in ai_exp
            assert isinstance(ai_exp["highlighted_features"], list)

    def test_recommend_top_k_respected(self, client):
        """Response should not exceed requested top_k count."""
        payload = {"query": "pizza", "top_k": 2}
        response = client.post("/api/v1/recommend", json=payload)
        data = response.json()
        assert len(data.get("recommendations", [])) <= 2

    def test_recommend_total_latency_under_threshold(self, client):
        """End-to-end recommendation call should complete within 5 seconds."""
        import time

        payload = {"query": "South Indian food", "location": "Bangalore", "top_k": 3}

        start = time.perf_counter()
        response = client.post("/api/v1/recommend", json=payload)
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        # Allow generous timeout (5s) accounting for LLM calls or cold start
        assert elapsed < 5.0, f"Recommendation took {elapsed:.2f}s — exceeds 5s threshold"


# ===========================================================================
#  Request Validation
# ===========================================================================

class TestRequestValidation:
    """Verify Pydantic validation errors produce structured responses."""

    def test_invalid_budget_tier_rejected(self, client):
        """Invalid budget_tier enum value should trigger validation error."""
        payload = {
            "budget_tier": "ultra_expensive",  # Not a valid BudgetTier
            "top_k": 3,
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data.get("status") == "error" or "detail" in data

    def test_negative_top_k_rejected(self, client):
        """top_k < 1 should be rejected."""
        payload = {"top_k": 0}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422

    def test_top_k_exceeds_max_rejected(self, client):
        """top_k > 20 should be rejected."""
        payload = {"top_k": 50}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422

    def test_min_rating_out_of_bounds_rejected(self, client):
        """min_rating > 5.0 should be rejected."""
        payload = {"min_rating": 6.0, "top_k": 3}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422

    def test_max_cost_negative_rejected(self, client):
        """max_cost_for_two < 0 is invalid."""
        payload = {"max_cost_for_two": -100, "top_k": 3}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422

    def test_cuisines_as_comma_string_accepted(self, client):
        """Cuisines passed as comma-separated string should auto-parse."""
        payload = {
            "cuisines": "Italian, Chinese, North Indian",
            "top_k": 3,
        }
        response = client.post("/api/v1/recommend", json=payload)
        # Should auto-parse via field_validator — either 200 or valid response
        assert response.status_code == 200


# ===========================================================================
#  Restaurant Detail Endpoint
# ===========================================================================

class TestRestaurantDetailEndpoint:
    """Integration tests for GET /api/v1/restaurants/{id}."""

    def test_get_nonexistent_restaurant_returns_404(self, client):
        """Requesting a non-existent restaurant ID should return 404."""
        response = client.get("/api/v1/restaurants/999999")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data.get("status", "") or "detail" in data

    def test_get_restaurant_with_invalid_id_type(self, client):
        """Non-integer restaurant ID should return 422."""
        response = client.get("/api/v1/restaurants/abc")
        assert response.status_code == 422


# ===========================================================================
#  Cuisines & Locations Endpoints
# ===========================================================================

class TestCatalogEndpoints:
    """Integration tests for catalog metadata endpoints."""

    def test_get_cuisines_returns_list(self, client):
        """GET /api/v1/cuisines should return a list of strings."""
        response = client.get("/api/v1/cuisines")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All items should be strings
        for item in data:
            assert isinstance(item, str)

    def test_get_locations_returns_list(self, client):
        """GET /api/v1/locations should return a list of strings."""
        response = client.get("/api/v1/locations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, str)

    def test_cuisines_are_sorted(self, client):
        """Cuisines list should be alphabetically sorted."""
        response = client.get("/api/v1/cuisines")
        data = response.json()
        if len(data) > 1:
            assert data == sorted(data), "Cuisines list should be sorted alphabetically"

    def test_locations_are_sorted(self, client):
        """Locations list should be alphabetically sorted."""
        response = client.get("/api/v1/locations")
        data = response.json()
        if len(data) > 1:
            assert data == sorted(data), "Locations list should be sorted alphabetically"


# ===========================================================================
#  Feedback Endpoint
# ===========================================================================

class TestFeedbackEndpoint:
    """Integration tests for POST /api/v1/feedback."""

    def test_submit_valid_feedback(self, client):
        """Valid feedback should be accepted."""
        payload = {
            "recommendation_id": "test-rec-001",
            "restaurant_id": 1,
            "user_query": "Italian restaurants",
            "rating_score": 4,
            "comment": "Great recommendations!",
        }
        response = client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "feedback" in data["message"].lower() or "thank" in data["message"].lower()

    def test_submit_minimal_feedback(self, client):
        """Feedback with only required fields should be accepted."""
        payload = {"rating_score": 3}
        response = client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 200

    def test_feedback_invalid_rating_rejected(self, client):
        """rating_score outside 1-5 should be rejected."""
        payload = {"rating_score": 0}
        response = client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 422

    def test_feedback_rating_too_high_rejected(self, client):
        """rating_score > 5 should be rejected."""
        payload = {"rating_score": 10}
        response = client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 422

    def test_feedback_missing_rating_rejected(self, client):
        """rating_score is required."""
        payload = {"comment": "No rating provided"}
        response = client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 422


# ===========================================================================
#  Security Headers
# ===========================================================================

class TestSecurityHeaders:
    """Verify security response headers are present on all endpoints."""

    def test_security_headers_on_health(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "same-origin"

    def test_request_id_header_present(self, client):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_security_headers_on_api_endpoint(self, client):
        response = client.get("/api/v1/cuisines")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


# ===========================================================================
#  CORS Headers
# ===========================================================================

class TestCORSHeaders:
    """Verify CORS headers are properly set for cross-origin requests."""

    def test_cors_preflight_allowed(self, client):
        """OPTIONS preflight request should return appropriate CORS headers."""
        response = client.options(
            "/api/v1/recommend",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        # Should not be 405 Method Not Allowed
        assert response.status_code in (200, 204)
        assert "access-control-allow-origin" in response.headers


# ===========================================================================
#  Error Response Uniformity
# ===========================================================================

class TestUniformErrorResponses:
    """Verify all error responses follow the uniform JSON error schema."""

    def test_404_error_format(self, client):
        """404 responses should follow the uniform error schema."""
        response = client.get("/api/v1/restaurants/999999")
        assert response.status_code == 404
        data = response.json()
        # Should have structured error fields
        assert "message" in data or "detail" in data

    def test_422_error_contains_details(self, client):
        """422 validation errors should include field-level details."""
        payload = {"top_k": -5, "min_rating": 99.0}
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 422
        data = response.json()
        # Should contain error information
        assert (
            "details" in data
            or "detail" in data
        ), "422 response should include validation details"

    def test_nonexistent_route_returns_404(self, client):
        """Requests to undefined routes should return 404, not 500."""
        response = client.get("/api/v1/nonexistent_endpoint")
        assert response.status_code in (404, 405)


# ===========================================================================
#  Swagger Documentation
# ===========================================================================

class TestDocumentation:
    """Verify API documentation endpoints are accessible."""

    def test_swagger_docs_accessible(self, client):
        """Swagger UI should be accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_accessible(self, client):
        """ReDoc should be accessible at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self, client):
        """OpenAPI JSON schema should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/api/v1/recommend" in schema["paths"]
        assert "/api/v1/cuisines" in schema["paths"]
        assert "/api/v1/locations" in schema["paths"]
        assert "/api/v1/feedback" in schema["paths"]


# ---------------------------------------------------------------------------
#  Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
