"""BuddhiAI Server API — FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import DATABASE_PATH, HF_TOKEN, MODELS_CACHE_DIR
from src.database import ModelRepository
from src.exceptions import BuddhiAPIError
from src.routers import model_download, model_library, model_search
from src.services.download_service import DownloadService
from src.services.huggingface_service import HuggingFaceService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup; clean up on shutdown."""
    # Ensure required directories exist
    MODELS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database (creates tables if needed)
    model_repo = ModelRepository(DATABASE_PATH)
    await model_repo.initialize()

    # Create shared service instances
    hf_service = HuggingFaceService(token=HF_TOKEN)
    download_service = DownloadService(
        hf_service=hf_service,
        model_repo=model_repo,
        cache_dir=MODELS_CACHE_DIR,
    )

    # Attach to app.state for dependency injection in routers
    app.state.model_repo = model_repo
    app.state.hf_service = hf_service
    app.state.download_service = download_service

    logger.info("BuddhiAI Server started — models cache: %s", MODELS_CACHE_DIR)
    yield

    # Shutdown: cancel any in-flight downloads
    await download_service.shutdown()
    logger.info("BuddhiAI Server shut down")


app = FastAPI(title="BuddhiAI Server API", lifespan=lifespan)

# CORS configuration for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────── Global exception handler ──────────────────────


@app.exception_handler(BuddhiAPIError)
async def buddhi_error_handler(request: Request, exc: BuddhiAPIError):
    """Convert BuddhiAPIError exceptions into structured JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


# ──────────────────── Include routers ───────────────────────────

app.include_router(model_search.router, prefix="/api/models", tags=["Model Search"])
app.include_router(model_download.router, prefix="/api/models", tags=["Model Download"])
app.include_router(model_library.router, prefix="/api/models", tags=["Model Library"])


# ──────────────────── Root routes ───────────────────────────────


@app.get("/")
def read_root():
    return {"message": "Hello from BuddhiAI Server API!"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=True,
    )
