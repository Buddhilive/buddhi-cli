from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Request Models
# ------------------------------------------------------------------------------

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str = Field(..., description="The text content.")

class Item(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the item.")
    content: List[TextContent] = Field(..., description="Array of content parts.")

class ResponseRequest(BaseModel):
    """
    Request payload following the new OpenAI Responses API.
    """
    instructions: Optional[str] = Field(None, description="System instructions or prompt.")
    input: List[Item] = Field(..., description="The input items/messages to the model.")
    previous_response_id: Optional[str] = Field(None, description="ID of a previous response for stateful continuation.")
    stream: Optional[bool] = Field(False, description="If true, server-sent events will be streamed.")

# ------------------------------------------------------------------------------
# Response Models
# ------------------------------------------------------------------------------

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ResponseOutput(BaseModel):
    """
    Output payload for standard (non-streaming) response.
    """
    id: str = Field(..., description="Unique identifier for the response.")
    object: Literal["response"] = "response"
    status: str = Field("completed", description="Status of the response.")
    output: List[Item] = Field(..., description="The generated output items.")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage statistics.")

class ResponseStreamEvent(BaseModel):
    """
    Output payload for a Server-Sent Event (SSE) chunk.
    """
    id: str = Field(..., description="Unique identifier for the response.")
    object: Literal["response.chunk"] = "response.chunk"
    delta: Dict[str, Any] = Field(..., description="The delta/chunk content.")
