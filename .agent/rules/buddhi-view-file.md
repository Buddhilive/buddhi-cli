---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in tool `view_file` is deprecated and disabled in this environment.
2. For all file reading, file viewing, and content inspection, you MUST exclusively call the MCP tool `buddhi_view_file`.
3. When calling `buddhi_view_file`, inspect its schema parameters carefully:
   - Pass the file path into the `path` parameter.
   - Pass the query/intent details into the `task` parameter to dynamically optimize token usage.
   - Specify `mode` (e.g. `auto`, `full`, `signatures`, `map`, `lines:1-100`) as appropriate to save context window tokens.