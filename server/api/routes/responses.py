import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from server.api.models.response_api import ResponseRequest, ResponseOutput
from server.services.inference import inference_service
from server.core.exceptions import InferenceError

router = APIRouter()

@router.post("/responses", response_model=ResponseOutput, response_model_exclude_none=True)
async def create_response(req: ResponseRequest, request: Request):
    """
    OpenAI Responses API endpoint.
    Creates a response to the user's input.
    If stream=True is specified in the request, it streams back Server-Sent Events (SSE).
    """
    try:
        if req.stream:
            async def event_generator():
                async for chunk in inference_service.generate_response_stream(req):
                    yield {
                        "event": "message",
                        "data": json.dumps(chunk)
                    }
                yield {"event": "message", "data": "[DONE]"}
            
            return EventSourceResponse(event_generator())
        else:
            return inference_service.generate_response(req)
    except Exception as e:
        raise InferenceError(str(e))
