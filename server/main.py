from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

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

def start():
    """
    CLI entry point to start the server.
    """
    import os
    from huggingface_hub import hf_hub_download
    
    # Path to the model directory relative to this file
    # __file__ is server/main.py, so we want server/static/model
    server_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(server_dir, "static", "model")
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")
    
    if not os.path.exists(model_path):
        print("Model not found. Downloading from HuggingFace...", flush=True)
        os.makedirs(target_dir, exist_ok=True)
        hf_hub_download(
            repo_id="litert-community/gemma-4-E4B-it-litert-lm", 
            filename="gemma-4-E4B-it.litertlm", 
            local_dir=target_dir
        )
        print("Model downloaded successfully!", flush=True)

    import uvicorn
    uvicorn.run("server.main:app", host="127.0.0.1", port=58421)
