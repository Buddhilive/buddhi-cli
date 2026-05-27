from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class OpenAIAPIError(Exception):
    """Base class for all OpenAI-compliant API errors."""
    def __init__(self, message: str, type: str, code: str, status_code: int, param: str = None):
        self.message = message
        self.type = type
        self.code = code
        self.status_code = status_code
        self.param = param

class InvalidRequestError(OpenAIAPIError):
    def __init__(self, message: str, code: str = "invalid_request_error", param: str = None):
        super().__init__(message=message, type="invalid_request_error", code=code, status_code=400, param=param)

class AuthenticationError(OpenAIAPIError):
    def __init__(self, message: str, code: str = "authentication_error"):
        super().__init__(message=message, type="authentication_error", code=code, status_code=401)

class RateLimitError(OpenAIAPIError):
    def __init__(self, message: str, code: str = "rate_limit_exceeded"):
        super().__init__(message=message, type="rate_limit_error", code=code, status_code=429)

class InferenceError(OpenAIAPIError):
    """Custom exception for LiteRT-LM inference failures."""
    def __init__(self, message: str):
        super().__init__(message=message, type="server_error", code="inference_failed", status_code=500)

async def openai_error_handler(request: Request, exc: OpenAIAPIError):
    """Handles OpenAIAPIError and returns an OpenAI-compliant error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": exc.type,
                "param": exc.param,
                "code": exc.code
            }
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Intercepts FastAPI RequestValidationError and returns a 400 OpenAI-compliant response."""
    errors = exc.errors()
    if errors:
        loc = " -> ".join([str(l) for l in errors[0].get("loc", [])])
        msg = f"Invalid request parameter: {loc}. {errors[0].get('msg', '')}."
        param = str(errors[0].get("loc", [-1])[-1])
    else:
        msg = "Invalid request."
        param = None

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "message": msg,
                "type": "invalid_request_error",
                "param": param,
                "code": "invalid_type"
            }
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions (500)."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An internal server error occurred.",
                "type": "server_error",
                "param": None,
                "code": "internal_error"
            }
        }
    )
