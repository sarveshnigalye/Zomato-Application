"""
FastAPI Application Entry Point — Phase 5: Backend API & Orchestration
========================================================================
Provides RESTful endpoints for restaurant recommendations, metadata lookups,
and user feedback. Implements uniform exception handling, security headers,
request ID tracking, and startup/shutdown lifecycle events.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import settings
from backend.app.core.orchestrator import orchestrator
from backend.app.models.database import get_db, init_db, QueryFeedback
from backend.app.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RestaurantRead,
    FeedbackRequest,
    FeedbackResponse,
)
from backend.app.services.data_service import DataService

logger = logging.getLogger("api")

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(name)-16s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# =============================================================================
#  Application Lifecycle Events
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # --- Startup ---
    logger.info(f"Starting {settings.PROJECT_NAME} v0.1.0")
    init_db()
    logger.info("SQLite database schema initialized.")
    logger.info(f"LLM provider: {settings.LLM_PROVIDER} | Model: {settings.GROQ_MODEL}")
    logger.info(f"API documentation available at /docs")
    yield
    # --- Shutdown ---
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# =============================================================================
#  FastAPI Application Instance
# =============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AI-Powered Restaurant Recommendation API with hybrid RAG retrieval, "
        "Groq LLM reasoning, and personalized dining explanations."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# =============================================================================
#  Middleware Stack
# =============================================================================

# 1. CORS Middleware — enable frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects standard security response headers on every HTTP response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# 3. Request Logging & Timing Middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status code, and latency for every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({elapsed_ms:.0f}ms)"
        )
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestLoggingMiddleware)


# =============================================================================
#  Uniform Global Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic request validation errors with structured error response."""
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        })

    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed. Check the 'details' field for specifics.",
            "details": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Uniform handler for all HTTPException responses."""
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions — prevents raw stack traces from leaking."""
    logger.error(
        f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": (
                "An unexpected internal error occurred. "
                "Our recommendation engine encountered an issue processing your request."
            ),
        },
    )


# =============================================================================
#  API Endpoints
# =============================================================================

# --- System ---

@app.get("/health", tags=["System"], summary="Service liveness check")
def health_check():
    """Health check endpoint verifying API service liveness."""
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": "0.1.0",
        "llm_provider": settings.LLM_PROVIDER,
    }


# --- Recommendations ---

@app.post(
    f"{settings.API_V1_STR}/recommend",
    response_model=RecommendationResponse,
    tags=["Recommendations"],
    summary="Generate personalized restaurant recommendations",
    description=(
        "Main recommendation flow combining hard SQL filters, dense vector semantic search, "
        "hybrid scoring, and LLM reasoning to return ranked candidates with AI explanations."
    ),
)
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Orchestrates the full multi-stage recommendation pipeline:
    1. Deterministic SQL filtering (location, budget, rating, cuisine)
    2. Dense semantic vector search (ChromaDB)
    3. Hybrid pre-ranking (weighted scoring)
    4. LLM reasoning, ranking & explanation synthesis (Groq)
    """
    try:
        response = await orchestrator.recommend(request, db)
        return response
    except Exception as e:
        logger.error(f"Recommendation pipeline error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation engine error: {str(e)}",
        )


# --- Catalog ---

@app.get(
    f"{settings.API_V1_STR}/restaurants/{{restaurant_id}}",
    response_model=RestaurantRead,
    tags=["Catalog"],
    summary="Fetch full restaurant profile by ID",
)
def get_restaurant_by_id(
    restaurant_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves full restaurant details from SQLite catalog by primary key."""
    data_service = DataService(db)
    restaurant = data_service.get_restaurant_by_id(restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restaurant with ID {restaurant_id} not found.",
        )
    return restaurant.to_dict()


@app.get(
    f"{settings.API_V1_STR}/cuisines",
    response_model=List[str],
    tags=["Catalog"],
    summary="Get list of available distinct cuisines",
)
def get_cuisines(db: Session = Depends(get_db)):
    """Returns sorted distinct cuisines available in the dataset."""
    data_service = DataService(db)
    return data_service.get_distinct_cuisines()


@app.get(
    f"{settings.API_V1_STR}/locations",
    response_model=List[str],
    tags=["Catalog"],
    summary="Get list of available distinct locations",
)
def get_locations(db: Session = Depends(get_db)):
    """Returns sorted distinct neighborhoods and locations in the dataset."""
    data_service = DataService(db)
    return data_service.get_distinct_locations()


# --- Telemetry ---

@app.post(
    f"{settings.API_V1_STR}/feedback",
    response_model=FeedbackResponse,
    tags=["Telemetry"],
    summary="Submit user feedback on recommendation quality",
)
def submit_feedback(
    feedback: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """Logs recommendation feedback to SQLite query_feedback table."""
    try:
        record = QueryFeedback(
            recommendation_id=feedback.recommendation_id,
            restaurant_id=feedback.restaurant_id,
            user_query=feedback.user_query,
            rating_score=feedback.rating_score,
            comment=feedback.comment,
        )
        db.add(record)
        db.commit()
        return FeedbackResponse(status="success", message="Thank you for your feedback!")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback recording failed: {str(e)}",
        )


# =============================================================================
#  Static Frontend Mount (Serves UI at http://localhost:8000/)
# =============================================================================

from fastapi.staticfiles import StaticFiles
from backend.app.config import PROJECT_ROOT

frontend_path = PROJECT_ROOT / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


# =============================================================================
#  Development Server Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
