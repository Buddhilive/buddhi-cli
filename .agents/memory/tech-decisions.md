# Tech Decisions

- **Custom Skills Registry & Template Isolation (`buddhi skills`)**: `buddhi skills` uses an extensible registry structure mapping CLI flags (`--repo-to-skill`, etc.) to selective skill templates. Selective skills are packaged in a dedicated location (`buddhi.templates.custom_skills`) strictly separate from the default harness (`buddhi.templates.agents`) so that `buddhi init` does not eagerly copy them.
- **Python-Native Skill Scripts & CLI Runner (`buddhi skills run`)**: All custom skill helper scripts are authored as pure Python 3.10+ instead of bash scripts, ensuring 100% Windows/macOS/Linux compatibility. Execution is supported both directly via `python <script>` and through `buddhi skills run <skill-name> <args>` inside the CLI runtime.


