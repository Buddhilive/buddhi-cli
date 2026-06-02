import os
import time
import json
import uuid
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager
from buddhi_ai.server.engine import LiteRTEngine

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Determine the model path
    model_path = os.path.expanduser("~/.buddhi/models/gemma-4-E4B-it.litertlm")
    logger.info("Initializing LiteRTEngine...")
    app.state.engine = LiteRTEngine(model_path)
    yield
    logger.info("Shutting down LiteRTEngine...")
    app.state.engine = None

app = FastAPI(title="Buddhi AI Local Engine (Gemma 4 E4B LiteRT)", lifespan=lifespan)

class ChatMessage(BaseModel):
    role: str
    content: Any  # Can be string or list of dicts for multi-modal

class ChatCompletionRequest(BaseModel):
    model: str = "gemma-4-E4B-it.litertlm"
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    top_p: Optional[float] = 1.0

def _format_message(msg: ChatMessage) -> Dict[str, Any]:
    # Pass through to the engine. If it's multi-modal, the engine will process it.
    return {"role": msg.role, "content": msg.content}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    engine = getattr(app.state, "engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="Model engine is not initialized.")
        
    messages = [_format_message(m) for m in request.messages]
    
    kwargs = {
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "top_p": request.top_p
    }

    req_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if request.stream:
        async def stream_generator():
            try:
                for chunk in engine.generate(messages, stream=True, **kwargs):
                    response_chunk = {
                        "id": req_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(response_chunk)}\n\n"
                    
                # Send final chunk
                final_chunk = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Synchronous generation
    try:
        response_text = engine.generate(messages, stream=False, **kwargs)
        
        return {
            "id": req_id,
            "object": "chat.completion",
            "created": created,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,  # Tokenizer not strictly implemented in this mock wrapper
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    engine = getattr(app.state, "engine", None)
    return {
        "status": "ok" if engine else "loading",
        "model": "gemma-4-E4B-it.litertlm"
    }
