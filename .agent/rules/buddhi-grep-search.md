---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in tool `grep_search` is deprecated and disabled in this environment.
2. For all text-matching, regex searches, or code querying tasks, you MUST exclusively call the MCP tool `buddhi_grep_search`.
3. When calling `buddhi_grep_search`, inspect its schema parameters carefully:
   - Pass the search string into the `query` parameter (do not use `pattern`).
   - Pass directory filters into the `globs` array parameter.