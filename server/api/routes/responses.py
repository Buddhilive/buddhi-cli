import json
import time
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from server.api.models.response_api import ResponseRequest, ResponseOutput, Item, TextContent
from server.api.models.chat_api import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionResponseChoice, ChatMessage, ChatCompletionUsage
from server.services.inference import inference_service

router = APIRouter()

@router.post("/responses", response_model=ResponseOutput, response_model_exclude_none=True)
async def create_response(req: ResponseRequest, request: Request):
    """
    OpenAI Responses API endpoint.
    Creates a response to the user's input.
    If stream=True is specified in the request, it streams back Server-Sent Events (SSE).
    """
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

@router.post("/chat/completions", response_model=ChatCompletionResponse, response_model_exclude_none=True)
async def create_chat_completion(req: ChatCompletionRequest, request: Request):
    """
    OpenAI-compatible Chat Completions API endpoint.
    Maps ChatCompletionRequest payload to local Inference Engine and returns OpenAI formatted responses.
    """
    instructions = None
    input_items = []
    
    for msg in req.messages:
        if msg.role == "system":
            instructions = msg.content
        elif msg.role == "tool":
            # Pass tool results back as user messages indicating it is a tool response
            # Truncate to prevent context window overflow on large tool outputs (4096 tokens max for edge model)
            content_str = msg.content or ""
            if len(content_str) > 4000:
                content_str = content_str[:4000] + "\n...[TRUNCATED FOR LENGTH]..."
                
            input_items.append(
                Item(
                    role="user",
                    content=[TextContent(text=f"Tool result for {msg.name}:\n{content_str}")]
                )
            )
        elif msg.role == "assistant" and getattr(msg, "tool_calls", None):
            tool_call_texts = []
            if msg.content:
                tool_call_texts.append(msg.content)
            for tc in msg.tool_calls:
                func = tc.get("function", {})
                # Ensure arguments are valid JSON string
                args_str = func.get("arguments", "{}")
                if not args_str.strip():
                    args_str = "{}"
                tool_call_texts.append(f'<|tool_call>call:{func.get("name")}{args_str}<tool_call|>')
            
            input_items.append(
                Item(
                    role="assistant",
                    content=[TextContent(text="\n".join(tool_call_texts))]
                )
            )
        else:
            input_items.append(
                Item(
                    role=msg.role,
                    content=[TextContent(text=msg.content or "")]
                )
            )

    # Inject tool definitions into instructions if tools are provided
    if req.tools:
        tool_instructions = "You have access to the following tools:\n\n"
        tools_list = []
        for t in req.tools:
            if t.get("type") == "function":
                func = t.get("function", {})
                tools_list.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {})
                })
        
        tool_instructions += json.dumps(tools_list, indent=2) + "\n\n"
        tool_instructions += "To call a tool, use the exact following native format (output nothing else in that block):\n"
        tool_instructions += "<|tool_call>call:tool_name{\"arg_name\": \"arg_value\"}<tool_call|>\n"
        tool_instructions += "Once you receive the tool's output in the next turn, formulate your final response."
        
        if instructions:
            instructions += "\n\n" + tool_instructions
        else:
            instructions = tool_instructions
            
    response_req = ResponseRequest(
        instructions=instructions,
        input=input_items,
        stream=req.stream
    )
    
    if req.stream:
        async def event_generator():
            resp_id = None
            buffer = ""
            in_tool_call = False
            
            async for chunk in inference_service.generate_response_stream(response_req):
                resp_id = chunk.get("id") or resp_id
                text_chunk = chunk.get("delta", {}).get("content", [{}])[0].get("text", "")
                
                if not text_chunk:
                    continue
                    
                buffer += text_chunk
                
                if not in_tool_call and "<|tool_call>" in buffer:
                    pre_text, rest = buffer.split("<|tool_call>", 1)
                    if pre_text:
                        openai_chunk = {
                            "id": resp_id or "chatcmpl-stream",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": req.model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": pre_text, "role": "assistant"},
                                "finish_reason": None
                            }]
                        }
                        yield {"event": "message", "data": json.dumps(openai_chunk)}
                    
                    buffer = "<|tool_call>" + rest
                    in_tool_call = True
                    
                if in_tool_call:
                    if "<tool_call|>" in buffer:
                        import re
                        match = re.search(r'<\|tool_call\>(.*?)<tool_call\|>', buffer, re.DOTALL)
                        if match:
                            try:
                                import uuid
                                raw_call = match.group(1).strip()
                                # Parse 'call:function_name{...}' or 'call:function_name'
                                func_name = ""
                                arguments_str = "{}"
                                
                                if raw_call.startswith("call:"):
                                    raw_call = raw_call[5:]
                                    if "{" in raw_call:
                                        func_name, args_part = raw_call.split("{", 1)
                                        arguments_str = "{" + args_part
                                    else:
                                        func_name = raw_call
                                        
                                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                                
                                tool_chunk = {
                                    "id": resp_id or "chatcmpl-stream",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": req.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {
                                            "role": "assistant",
                                            "content": None,
                                            "tool_calls": [{
                                                "index": 0,
                                                "id": tool_call_id,
                                                "type": "function",
                                                "function": {
                                                    "name": func_name.strip(),
                                                    "arguments": arguments_str
                                                }
                                            }]
                                        },
                                        "finish_reason": None
                                    }]
                                }
                                yield {"event": "message", "data": json.dumps(tool_chunk)}
                                
                                finish_chunk = {
                                    "id": resp_id or "chatcmpl-stream",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": req.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "tool_calls"
                                    }]
                                }
                                yield {"event": "message", "data": json.dumps(finish_chunk)}
                                yield {"event": "message", "data": "[DONE]"}
                                return
                            except Exception as e:
                                print(f"Error parsing tool call: {e}")
                                pass
                                
                        buffer = ""
                        in_tool_call = False
                else:
                    if "<" not in buffer:
                        openai_chunk = {
                            "id": resp_id or "chatcmpl-stream",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": req.model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": buffer, "role": "assistant"},
                                "finish_reason": None
                            }]
                        }
                        yield {"event": "message", "data": json.dumps(openai_chunk)}
                        buffer = ""
                    else:
                        last_lt = buffer.rfind("<")
                        if last_lt > 0:
                            emit_text = buffer[:last_lt]
                            buffer = buffer[last_lt:]
                            openai_chunk = {
                                "id": resp_id or "chatcmpl-stream",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": req.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": emit_text, "role": "assistant"},
                                    "finish_reason": None
                                }]
                            }
                            yield {"event": "message", "data": json.dumps(openai_chunk)}
                            
            if buffer:
                openai_chunk = {
                    "id": resp_id or "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": req.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": buffer, "role": "assistant"},
                        "finish_reason": None
                    }]
                }
                yield {"event": "message", "data": json.dumps(openai_chunk)}
            
            final_chunk = {
                "id": resp_id or "chatcmpl-stream",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield {"event": "message", "data": json.dumps(final_chunk)}
            yield {"event": "message", "data": "[DONE]"}
            
        return EventSourceResponse(event_generator())
    else:
        resp = inference_service.generate_response(response_req)
        content_text = resp.output[0].content[0].text if resp.output else ""
        
        import re
        tool_calls = []
        
        # Check for <|tool_call> tags
        tool_call_match = re.search(r'<\|tool_call\>(.*?)<tool_call\|>', content_text, re.DOTALL)
        if tool_call_match:
            try:
                raw_call = tool_call_match.group(1).strip()
                func_name = ""
                arguments_str = "{}"
                
                if raw_call.startswith("call:"):
                    raw_call = raw_call[5:]
                    if "{" in raw_call:
                        func_name, args_part = raw_call.split("{", 1)
                        arguments_str = "{" + args_part
                    else:
                        func_name = raw_call
                        
                import uuid
                tool_calls.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": func_name.strip(),
                        "arguments": arguments_str
                    }
                })
                # Remove the tool call from content
                content_text = content_text[:tool_call_match.start()].strip()
            except Exception:
                pass
        
        return ChatCompletionResponse(
            id=resp.id,
            object="chat.completion",
            created=int(time.time()),
            model=req.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant", 
                        content=content_text if content_text else None,
                        tool_calls=tool_calls if tool_calls else None
                    ),
                    finish_reason="tool_calls" if tool_calls else "stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens
            )
        )

