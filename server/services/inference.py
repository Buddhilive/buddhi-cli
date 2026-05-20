import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any

try:
    import litert_lm
except ImportError:
    litert_lm = None

from server.core.config import settings
from server.api.models.response_api import ResponseRequest, ResponseOutput, Item, TextContent, TokenUsage

class InferenceService:
    def __init__(self):
        self.model_path = settings.model_path
        self._engine = None

    def initialize_engine(self):
        if not litert_lm:
            print("WARNING: litert_lm not installed. Inference will fail.")
            return
        
        try:
            self._engine = litert_lm.Engine(self.model_path)
            self._engine.__enter__()
            print(f"Engine initialized with model: {self.model_path}")
        except Exception as e:
            print(f"Failed to initialize engine: {e}")

    def convert_messages(self, req: ResponseRequest):
        messages = []
        if req.instructions:
            messages.append({"role": "system", "content": [{"type": "text", "text": req.instructions}]})
        
        for item in req.input:
            messages.append({
                "role": item.role,
                "content": [{"type": "text", "text": c.text} for c in item.content]
            })
        return messages

    def _extract_user_input(self, messages: list) -> str:
        if messages and messages[-1]["role"] == "user":
            return messages[-1]["content"][0]["text"]
        return ""

    def _parse_chunk(self, chunk: Any) -> str:
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, dict):
            c = chunk.get("content", "")
            if isinstance(c, list) and len(c) > 0:
                return c[0].get("text", "") if isinstance(c[0], dict) else str(c[0])
            elif isinstance(c, str):
                return c
            else:
                return ""
        else:
            return getattr(chunk, "text", str(chunk))

    def generate_response(self, req: ResponseRequest) -> ResponseOutput:
        if not self._engine:
            raise Exception("Engine not initialized. Ensure litert-lm is installed and model exists.")
        
        messages = self.convert_messages(req)
        user_input = self._extract_user_input(messages)
        
        response_text = ""
        with self._engine.create_conversation(messages=messages[:-1] if user_input else messages) as conversation:
            response_obj = conversation.send_message(user_input) if hasattr(conversation, 'send_message') else conversation.send_message_async(user_input)
            
            # If response_obj is an iterable generator (and not just a dict/string), iterate through it
            if hasattr(response_obj, '__iter__') and not isinstance(response_obj, (dict, str)):
                for chunk in response_obj:
                    response_text += self._parse_chunk(chunk)
            elif hasattr(response_obj, '__aiter__'):
                raise Exception("Sync generate_response cannot process an async generator directly. Use stream=True.")
            else:
                # It returned a single complete object (like a dict)
                response_text = self._parse_chunk(response_obj)

        response_id = f"res-{uuid.uuid4().hex[:12]}"
        return ResponseOutput(
            id=response_id,
            output=[
                Item(role="assistant", content=[TextContent(text=response_text)])
            ],
            usage=TokenUsage() # Dummy usage
        )

    async def generate_response_stream(self, req: ResponseRequest) -> AsyncGenerator[Dict[str, Any], None]:
        if not self._engine:
            raise Exception("Engine not initialized. Ensure litert-lm is installed and model exists.")
        
        messages = self.convert_messages(req)
        user_input = self._extract_user_input(messages)
        response_id = f"res-{uuid.uuid4().hex[:12]}"
        
        with self._engine.create_conversation(messages=messages[:-1] if user_input else messages) as conversation:
            response_obj = conversation.send_message_async(user_input) if hasattr(conversation, 'send_message_async') else conversation.send_message(user_input)
            
            if hasattr(response_obj, "__aiter__"):
                async for chunk in response_obj:
                    text_chunk = self._parse_chunk(chunk)
                    yield {
                        "id": response_id,
                        "object": "response.chunk",
                        "delta": {"content": [{"type": "text", "text": text_chunk}]}
                    }
            elif hasattr(response_obj, "__iter__") and not isinstance(response_obj, (dict, str)):
                for chunk in response_obj:
                    text_chunk = self._parse_chunk(chunk)
                    yield {
                        "id": response_id,
                        "object": "response.chunk",
                        "delta": {"content": [{"type": "text", "text": text_chunk}]}
                    }
                    await asyncio.sleep(0) # yield control
            else:
                # It returned a single complete object
                text_chunk = self._parse_chunk(response_obj)
                yield {
                    "id": response_id,
                    "object": "response.chunk",
                    "delta": {"content": [{"type": "text", "text": text_chunk}]}
                }

inference_service = InferenceService()
