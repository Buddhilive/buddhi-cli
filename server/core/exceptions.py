from fastapi import Request
from fastapi.responses import JSONResponse

class InferenceError(Exception):
    """Custom exception for LiteRT-LM inference failures."""
    def __init__(self, detail: str):
        self.detail = detail

async def inference_error_handler(request: Request, exc: InferenceError):
    """
    Handles InferenceError and returns an OpenAI-compliant error response.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": exc.detail,
                "type": "server_error",
                "param": None,
                "code": "inference_failed"
            }
        }
    )

# You can add more exception handlers here if needed
