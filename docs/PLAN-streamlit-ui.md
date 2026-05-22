# Plan: Streamlit Chat UI Migration

This plan details the implementation to remove the Svelte project in the `ui` folder, replace it with a premium Streamlit chat UI that calls the FastAPI Responses API, and connect it with the CLI command `buddhi live` so both servers run concurrently.

## Overview
Currently, the `buddhi live` command serves a Svelte frontend compiled to `ui/dist` via FastAPI static files. We will replace this setup by:
1. Deleting all Svelte-related files in the `ui` folder.
2. Creating a premium, interactive Streamlit application in the `ui` directory (e.g. `ui/app.py`) that utilizes Streamlit's built-in chat interface elements (`st.chat_input`, `st.chat_message`, `st.write_stream`) and styles.
3. Adding `streamlit` to the project's dependencies in `pyproject.toml`.
4. Updating `cli/main.py` so the `buddhi live` command runs both the FastAPI server (as a daemon thread or concurrent subprocess) and the Streamlit app (using the current python executable), respect `--no-browser` flags, and automatically open the Streamlit UI in the system's default browser window.
5. Updating `server/main.py` to remove Svelte static file mounting and redirect `/` to a helpful status page or the Streamlit app.

---

## Success Criteria
- **Clean UI Folder**: Svelte files are completely removed; only the Streamlit application and its configuration remain.
- **Concurrent Execution**: Running `buddhi live` starts both the FastAPI backend and Streamlit frontend concurrently.
- **Premium Chat Experience**: Streamlit chat interface works smoothly, streams inference outputs token-by-token using FastAPI Responses API's streaming mode, and maintains conversation context.
- **Robust CLI Flags**: `--host`, `--port`, and `--no-browser` are respected by both FastAPI and Streamlit processes.

---

## Tech Stack
- **Backend API**: FastAPI (existing), Uvicorn (existing)
- **Frontend UI**: Streamlit
- **HTTP Client**: `httpx` (existing, supports async/sync streaming)
- **CLI Framework**: Python `argparse`, `subprocess`, `threading`

---

## Open Questions

> [!IMPORTANT]
> ### 1. Streamlit Styling & Layout
> We plan to implement a sleek dark mode custom theme with modern typography and styled chat bubbles to match the premium aesthetics of Buddhi AI. Do you have any specific color palettes or UI layouts you'd like to see for the Streamlit dashboard?
>
> ### 2. Streamlit Port Configuration
> Streamlit defaults to port `8501`. Should we allow users to customize the Streamlit port via a CLI argument (e.g., `--frontend-port` or `--ui-port` in `buddhi live`), or is hardcoding a default port like `8501` acceptable?
>
> ### 3. Concurrent Runner Preference
> We propose starting the FastAPI server in a background thread within the CLI process using Python's `threading` and running Streamlit as a subprocess using `sys.executable -m streamlit run ...`. This makes process signals (like Ctrl+C) clean and ensures that the servers share the exact same runtime environment. Does this architecture suit your deployment model?

---

## Proposed Changes

### [cli]
#### [MODIFY] [main.py](file:///c:/DevDojo/Buddhi/buddhi-ai/cli/main.py)
- Modify the `start()` function to:
  - Run the FastAPI server (`server.main:app`) in a background thread using `uvicorn.Server(config)`.
  - Launch the Streamlit application in `ui/app.py` via `subprocess.Popen` using the current Python environment (`sys.executable -m streamlit run`).
  - Pass the host, FastAPI port, and `--server.headless` options (`true` if `--no-browser` is set, `false` otherwise) to Streamlit.
  - Monitor the subprocesses and handle graceful shutdowns (Ctrl+C).

### [server]
#### [MODIFY] [main.py](file:///c:/DevDojo/Buddhi/buddhi-ai/server/main.py)
- Remove Svelte `ui_dist_path` static files mounting.
- Replace `/` path handler with a descriptive JSON landing page or health check status to guide API consumers.

### [ui]
#### [DELETE] Svelte Project files
- Delete Svelte folders/files: `ui/src`, `ui/public`, `ui/package.json`, `ui/pnpm-lock.yaml`, `ui/index.html`, `ui/vite.config.ts`, `ui/tsconfig.json`, `ui/svelte.config.js`, etc.
#### [NEW] [app.py](file:///c:/DevDojo/Buddhi/buddhi-ai/ui/app.py)
- Create a premium Streamlit application:
  - Modern, responsive chat bubbles using `st.chat_message` and `st.chat_input`.
  - Handle conversation state using `st.session_state` to store messages.
  - Implement full streaming response support using FastAPI's `/v1/responses` SSE stream and Streamlit's `st.write_stream`.
  - Connect to the FastAPI backend dynamically using host and port (or default configured endpoint).

### [root]
#### [MODIFY] [pyproject.toml](file:///c:/DevDojo/Buddhi/buddhi-ai/pyproject.toml)
- Add `streamlit>=1.35.0` to the `dependencies` block.

---

## Task Breakdown

### Phase 1: Dependency & Cleanup
- [ ] **Task 1**: Add `streamlit` to `pyproject.toml` dependencies.
  - *Verify*: Run `pip install -e .` or `uv pip install -e .` and check that Streamlit is successfully installed.
- [ ] **Task 2**: Delete Svelte boilerplate files inside the `ui` directory.
  - *Verify*: Verify `ui` contains no Svelte config, source files, or `package.json`.

### Phase 2: Streamlit Application
- [ ] **Task 3**: Implement the Streamlit chat interface in `ui/app.py`.
  - *Verify*: Run `streamlit run ui/app.py` manually, verify page loads in browser and shows chat components.
- [ ] **Task 4**: Add HTTP API integration with FastAPI responses endpoint (non-streaming and streaming SSE support).
  - *Verify*: With local FastAPI server running, post a chat message in Streamlit and see the streaming model response appear token-by-token.

### Phase 3: CLI Runner Integration
- [ ] **Task 5**: Update `cli/main.py` command handling.
  - *Verify*: Run `buddhi live --help` and verify options are present.
- [ ] **Task 6**: Implement double-runner (Uvicorn thread + Streamlit subprocess) in `cli/main.py`'s `start()` function.
  - *Verify*: Run `buddhi live`, check terminal outputs for both server startup and Streamlit opening in the browser automatically. Test graceful shutdown (Ctrl+C).

### Phase 4: Server Route Cleanup
- [ ] **Task 7**: Clean up static mounting in `server/main.py`.
  - *Verify*: Accessing `http://127.0.0.1:58421/` returns JSON status response rather than trying to serve Svelte.

---

## Verification Plan

### Automated Tests
- Run code formatters and lint checks:
  ```powershell
  ruff check cli server ui/app.py
  ```
- Run general vulnerability scanners:
  ```powershell
  python .agent/skills/vulnerability-scanner/scripts/security_scan.py .
  ```

### Manual Verification
1. Run `buddhi live` in PowerShell.
2. Confirm the system default browser opens Streamlit app on `http://localhost:8501`.
3. Type a message in the chat input, press enter, and verify the model streams back responses smoothly.
4. Stop the CLI using `Ctrl+C` and verify both the backend server and frontend Streamlit processes exit cleanly.
5. Run `buddhi live --no-browser` and verify the browser does not open automatically, but both servers still start successfully.
