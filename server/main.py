from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import responses
from server.core.exceptions import InferenceError, inference_error_handler
from server.services.inference import inference_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown events.
    """
    # Startup
    inference_service.initialize_engine()
    yield
    # Shutdown
    # Additional cleanup if needed
    pass

app = FastAPI(
    title="LiteRT-LM Responses API",
    description="An OpenAI Responses API compatible endpoint powered by LiteRT-LM edge inference.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for standard setups
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(InferenceError, inference_error_handler)

# Include API Routers
app.include_router(responses.router, prefix="/v1", tags=["Responses"])

@app.get("/health", tags=["System"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}
