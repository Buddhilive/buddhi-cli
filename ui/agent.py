import asyncio
import threading
from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ui.mcp_client import call_mcp_tool, get_mcp_config, list_mcp_tools

def run_async_sync(coro):
    """
    Runs an asynchronous coroutine in a separate temporary thread with its own event loop,
    bypassing 'This event loop is already running' issues in Streamlit/Uvicorn threads.
    """
    result = None
    exception = None
    
    def worker():
        nonlocal result, exception
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            loop.close()
        except Exception as e:
            exception = e
            
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    return result

class MCPDynamicTool(BaseTool):
    """
    Dynamically wraps any MCP tool to be used inside LangGraph / LangChain ReAct agent.
    """
    name: str = ""
    description: str = ""
    mcp_config: dict = Field(default_factory=dict)
    
    def _run(self, **kwargs) -> str:
        """
        Synchronous tool execution. Delegates to the async call_mcp_tool function via run_async_sync.
        """
        try:
            result = run_async_sync(call_mcp_tool(self.mcp_config, self.name, kwargs))
            
            # Format and return tool results as clean text
            text_parts = []
            for item in result:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts)
        except Exception as e:
            return f"Error executing tool {self.name}: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        """
        Asynchronous tool execution.
        """
        try:
            result = await call_mcp_tool(self.mcp_config, self.name, kwargs)
            text_parts = []
            for item in result:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts)
        except Exception as e:
            return f"Error executing tool {self.name}: {str(e)}"

def get_react_agent():
    """
    Initializes standard ChatOpenAI client pointing to local compatible endpoint
    and compiles a stateful LangGraph ReAct agent with dynamic MCP tools.
    """
    mcp_config = get_mcp_config()
    langchain_tools = []
    
    if mcp_config:
        try:
            # Safely fetch MCP tools synchronously using the thread worker
            mcp_tools = run_async_sync(list_mcp_tools(mcp_config))
            
            for tool in mcp_tools:
                langchain_tools.append(
                    MCPDynamicTool(
                        name=tool.name,
                        description=tool.description,
                        mcp_config=mcp_config
                    )
                )
        except Exception as e:
            print(f"Warning: Failed to load MCP tools into agent: {e}")
            
    # Configure the ChatOpenAI client to hit local compatible endpoint
    llm = ChatOpenAI(
        model="gemma-4-E4B-it.litertlm",
        openai_api_base="http://localhost:58421/v1",
        openai_api_key="buddhi",
        temperature=0.2, # Lower temperature for more accurate reasoning
        streaming=True
    )
    
    # Compile the ReAct agent graph
    agent = create_react_agent(llm, tools=langchain_tools)
    return agent
