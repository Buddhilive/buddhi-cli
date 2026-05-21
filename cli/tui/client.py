"""Async HTTP/SSE client for the Buddhi FastAPI backend."""
from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

BASE_URL = "http://127.0.0.1:58421"
TIMEOUT = 60.0


class BuddhiClient:
    """Streams chat completions from the /v1/responses SSE endpoint."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url

    async def health_check(self) -> bool:
        """Returns True if the backend is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return False

    async def stream_chat(
        self, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """
        Yields text delta strings from the streaming SSE response.

        Args:
            messages: List of {"role": str, "content": str} dicts.

        Yields:
            Incremental text chunks from the assistant.

        Raises:
            ConnectionError: If the backend is not reachable.
            httpx.HTTPStatusError: On non-2xx responses.
        """
        # The server's ResponseRequest model requires each message's `content`
        # to be a list of content parts: [{type: "text", text: "..."}].
        # Convert flat {role, content: str} dicts to that structure.
        formatted_input = [
            {
                "role": m["role"],
                "content": [{"type": "text", "text": m["content"]}],
            }
            for m in messages
        ]
        payload = {
            "model": "gemma-4-E4B",
            "input": formatted_input,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/responses",
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[len("data:"):].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            # Extract delta text from the response structure
                            delta = _extract_delta(chunk)
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            continue

        except httpx.ConnectError as exc:
            raise ConnectionError(
                "Cannot reach Buddhi server. Is it running?"
            ) from exc


def _extract_delta(chunk: dict) -> str:
    """
    Pull incremental text from the SSE chunk produced by the inference service.

    Server yields chunks shaped as:
        {"id": "...", "object": "response.chunk",
         "delta": {"content": [{"type": "text", "text": "..."}]}}

    Also handles the legacy / fallback structures just in case.
    """
    # Primary: delta.content[].text  (actual server format)
    delta = chunk.get("delta", {})
    if isinstance(delta, dict):
        content = delta.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text", "")
                    if text:
                        return text
        # Fallback: delta.text (flat string)
        text = delta.get("text", "")
        if text:
            return text

    # Legacy: output[].content[].text  (Responses API non-stream format)
    for output in chunk.get("output", []):
        for part in output.get("content", []):
            text = part.get("text", "")
            if text:
                return text

    return ""
