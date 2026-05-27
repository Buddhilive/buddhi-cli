import os
import re
import json

def get_mcp_config():
    config_path = os.path.join(os.getcwd(), ".agent", "mcp_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                # Remove possible comments from json
                raw = f.read()
                clean = re.sub(r"//.*", "", raw)
                data = json.loads(clean)
                server = data.get("mcpServers", {}).get("buddhi-mcp")
                if server:
                    return server
        except Exception:
            pass
    return None

async def list_mcp_tools(server_config):
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config.get("args", []),
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools

async def call_mcp_tool(server_config, tool_name, tool_args):
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config.get("args", []),
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=tool_args)
            return result.content
