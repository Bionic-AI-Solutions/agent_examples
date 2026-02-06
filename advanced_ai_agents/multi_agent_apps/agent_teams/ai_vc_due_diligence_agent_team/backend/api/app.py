"""FastAPI Application Setup - VC Due Diligence API"""

from pathlib import Path
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from services.db_service import initialize_db_pool, close_db_pool
from router.research import router as research_router


# Health check router
health_router = APIRouter(prefix="/api")


@health_router.get("/health", summary="API Health Check")
async def health_check():
    """Health check endpoint for liveness/readiness probes"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "vc-diligence-api",
    }


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting VC Due Diligence API server")

    # Initialize database connection pool
    logger.info("Initializing database connection pool")
    await initialize_db_pool()
    logger.info("Database connection pool initialized")

    yield

    # Shutdown
    logger.info("Shutting down VC Due Diligence API server")

    # Close database connection pool
    logger.info("Closing database connection pool")
    await close_db_pool()

    logger.info("Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="VC Due Diligence API",
    description="AI-powered startup investment analysis using Google ADK agents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production (specific domains)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(research_router)

# Static files directory (frontend/static served from backend)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# Root endpoint - serve Clerk auth page
@app.get("/", include_in_schema=False)
async def root():
    """Serve the Clerk authentication / chat interface page"""
    index_file = _static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "VC Due Diligence API",
        "docs": "/api/docs",
        "health": "/api/health",
    }
