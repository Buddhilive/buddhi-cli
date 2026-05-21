from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from fastapi.staticfiles import StaticFiles
import os

from server.api.routes import responses
from server.core.exceptions import OpenAIAPIError, openai_error_handler, validation_error_handler, global_exception_handler
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
    title="Buddhi AI Inference Server",
    description="An OpenAI Responses API compatible endpoint powered by LiteRT-LM edge inference.",
    version="2.0.0",
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
app.add_exception_handler(OpenAIAPIError, openai_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include API Routers
app.include_router(responses.router, prefix="/v1", tags=["Responses"])

@app.get("/health", tags=["System"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

# Mount Svelte UI static files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_dist_path = os.path.join(base_dir, "ui", "dist")

if os.path.exists(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
else:
    @app.get("/")
    def serve_fallback_ui():
        return {
            "status": "warning",
            "message": "Buddhi AI server is running, but Svelte UI static files are not compiled.",
            "instructions": "Run 'pnpm build' in the 'ui' directory to build the Svelte UI assets."
        }

