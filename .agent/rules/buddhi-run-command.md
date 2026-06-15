---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in shell execution tool `run_command` are deprecated and disabled in this environment.
2. For all shell command execution, terminal commands, compilation, building, running tests, or diagnostics, you MUST exclusively call the MCP tool `buddhi_run_command`.
3. When calling `buddhi_run_command`, inspect its schema parameters carefully:
   - Pass the shell command into the `command` parameter.
   - Adjust `timeout_seconds` if you expect a long-running command.