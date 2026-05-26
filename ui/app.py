import os
import sys
import json
import time
import sqlite3
import pandas as pd
import httpx
import streamlit as st
import asyncio

# ------------------------------------------------------------------------------
# Config & Environment
# ------------------------------------------------------------------------------
BACKEND_HOST = os.getenv("BUDDHI_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BUDDHI_BACKEND_PORT", "58421")
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FAVICON_PATH = os.path.join(ASSETS_DIR, "favicon.ico")
LOGO_PATH = os.path.join(ASSETS_DIR, "logos", "icon-128x128.png")

# Streamlit Page Config
st.set_page_config(
    page_title="Buddhi AI — Observability & Chat",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------------------
# Premium Theme Styling (Primary: #da6243)
# ------------------------------------------------------------------------------
custom_css = """
<style>
    /* Premium Font Styling */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Global Dark Theme Overrides */
    .stApp {
        background-color: #0E0B0A;
        background-image: radial-gradient(circle at 10% 20%, rgba(218, 98, 67, 0.05) 0%, transparent 40%),
                          radial-gradient(circle at 90% 80%, rgba(30, 20, 18, 0.2) 0%, transparent 50%);
        background-attachment: fixed;
    }
    
    /* Sleek Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(14, 11, 10, 0.5);
    }
    ::-webkit-scrollbar-thumb {
        background: #da6243;
        border-radius: 2px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #f08265;
    }

    /* Sharp, High-Contrast Premium Card Layouts */
    div[data-testid="stSidebar"] {
        background-color: #16110F !important;
        border-right: 1px solid rgba(218, 98, 67, 0.15) !important;
    }

    /* Header Styling */
    .buddhi-header {
        margin-top: -50px;
        padding-bottom: 20px;
        border-bottom: 1px solid rgba(218, 98, 67, 0.2);
        margin-bottom: 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .buddhi-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFF 60%, #da6243 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .buddhi-badge {
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        padding: 3px 8px;
        background-color: rgba(218, 98, 67, 0.15);
        color: #da6243;
        border: 1px solid rgba(218, 98, 67, 0.4);
        border-radius: 2px;
        font-weight: bold;
    }

    /* Micro-Animations & Glow-Pulse Effects */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(218, 98, 67, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(218, 98, 67, 0); }
        100% { box-shadow: 0 0 0 0 rgba(218, 98, 67, 0); }
    }
    
    .pulse-btn {
        animation: pulse 2s infinite;
        border-radius: 2px;
    }

    /* Chat bubble enhancements for sharp, architectural look */
    div[data-testid="chatAvatarIconUser"], div[data-testid="chatAvatarIconAssistant"] {
        background-color: #da6243 !important;
    }
    
    .stChatMessage {
        border-radius: 2px !important;
        border: 1px solid rgba(218, 98, 67, 0.08) !important;
        margin-bottom: 12px !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    .stChatMessage:hover {
        border-color: rgba(218, 98, 67, 0.2) !important;
        transform: translateY(-1px);
    }

    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: rgba(30, 20, 18, 0.4) !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: rgba(14, 11, 10, 0.6) !important;
        border-left: 3px solid #da6243 !important;
    }

    /* Override Streamlit chat input border/focus colors */
    textarea[data-testid="stChatInputTextArea"] {
        border-radius: 2px !important;
        border: none !important;
        background-color: #16110F !important;
        color: #ececec !important;
    }
    textarea[data-testid="stChatInputTextArea"]:focus {
        border-color: #da6243 !important;
        box-shadow: 0 0 0 1px #da6243 !important;
    }

    /* Sidebar info text styles */
    .sidebar-section-title {
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        color: rgba(236, 236, 236, 0.6);
        letter-spacing: 1px;
        margin-top: 25px;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(218, 98, 67, 0.15);
        padding-bottom: 5px;
    }

    /* Premium styled hoverable metric cards for Dashboard */
    div[data-testid="stMetric"] {
        background-color: #16110F !important;
        border: 1px solid rgba(218, 98, 67, 0.15) !important;
        border-radius: 4px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
        transition: transform 0.2s ease-in-out, border-color 0.2s ease-in-out !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(218, 98, 67, 0.4) !important;
    }
    div[data-testid="stMetric"] label {
        color: rgba(236, 236, 236, 0.6) !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFF !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Backend Connectivity Check
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=5)
def check_backend_health():
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=1.5)
        if response.status_code == 200:
            return True, response.json().get("status", "ok")
    except Exception:
        pass
    return False, "offline"

backend_ok, backend_status = check_backend_health()

# ------------------------------------------------------------------------------
# Telemetry Database Integration
# ------------------------------------------------------------------------------
def get_telemetry_db_path():
    user_folder = os.path.expanduser("~")
    return os.path.join(user_folder, ".buddhi", "data", "telemetry.db")

def get_telemetry_metrics():
    db_path = get_telemetry_db_path()
    default_metrics = {"total": 0, "success": 0, "error": 0, "avg_latency": 0.0, "success_rate": 100.0}
    if not os.path.exists(db_path):
        return default_metrics
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        
        # Ensure table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if not cursor.fetchone():
            conn.close()
            return default_metrics
            
        cursor.execute("SELECT COUNT(*) FROM tool_usage")
        total = cursor.fetchone()[0]
        if total == 0:
            conn.close()
            return default_metrics
            
        cursor.execute("SELECT COUNT(*) FROM tool_usage WHERE status = 'success'")
        success = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tool_usage WHERE status = 'error'")
        error = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration_ms) FROM tool_usage")
        avg_latency = cursor.fetchone()[0] or 0.0
        
        success_rate = (success / total) * 100.0 if total > 0 else 100.0
        
        conn.close()
        return {
            "total": total,
            "success": success,
            "error": error,
            "avg_latency": round(avg_latency, 1),
            "success_rate": round(success_rate, 1)
        }
    except Exception:
        return default_metrics

def get_tool_usage_df():
    db_path = get_telemetry_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame(columns=["Tool Name", "Invocation Count"])
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame(columns=["Tool Name", "Invocation Count"])
            
        df = pd.read_sql_query("""
            SELECT tool_name as 'Tool Name', COUNT(*) as 'Invocation Count'
            FROM tool_usage
            GROUP BY tool_name
            ORDER BY 'Invocation Count' DESC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["Tool Name", "Invocation Count"])

def get_tool_latency_df():
    db_path = get_telemetry_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame(columns=["Tool Name", "Avg Latency (ms)"])
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame(columns=["Tool Name", "Avg Latency (ms)"])
            
        df = pd.read_sql_query("""
            SELECT tool_name as 'Tool Name', AVG(duration_ms) as 'Avg Latency (ms)'
            FROM tool_usage
            GROUP BY tool_name
            ORDER BY 'Avg Latency (ms)' DESC
        """, conn)
        df['Avg Latency (ms)'] = df['Avg Latency (ms)'].round(1)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["Tool Name", "Avg Latency (ms)"])

def get_usage_timeline_df():
    db_path = get_telemetry_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame(columns=["Time", "Triggers"])
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame(columns=["Time", "Triggers"])
            
        # Group by UTC hour using standard sqlite formatting
        df = pd.read_sql_query("""
            SELECT strftime('%m-%d %H:00', timestamp) as Time, COUNT(*) as Triggers
            FROM tool_usage
            GROUP BY Time
            ORDER BY Time ASC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["Time", "Triggers"])

def get_raw_logs_df(limit=100):
    db_path = get_telemetry_db_path()
    default_df = pd.DataFrame(columns=["ID", "Timestamp", "Tool Name", "Status", "Latency (ms)", "Arguments"])
    if not os.path.exists(db_path):
        return default_df
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if not cursor.fetchone():
            conn.close()
            return default_df
            
        df = pd.read_sql_query(f"""
            SELECT id as 'ID', timestamp as 'Timestamp', tool_name as 'Tool Name',
                   status as 'Status', duration_ms as 'Latency (ms)', arguments as 'Arguments'
            FROM tool_usage
            ORDER BY timestamp DESC
            LIMIT {limit}
        """, conn)
        df['Latency (ms)'] = df['Latency (ms)'].round(1)
        conn.close()
        return df
    except Exception:
        return default_df

def clear_telemetry_data():
    db_path = get_telemetry_db_path()
    if not os.path.exists(db_path):
        return True
        
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_usage'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM tool_usage")
            conn.commit()
        conn.close()
        return True
    except Exception:
        return False

# ------------------------------------------------------------------------------
# Initialize Page Routing & Navigation
# ------------------------------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ------------------------------------------------------------------------------
# Sidebar - Settings & Navigation
# ------------------------------------------------------------------------------
with st.sidebar:
    st.image(LOGO_PATH, width=64)
    st.markdown("<div style='font-size: 1.6rem; font-weight: 800; color: #FFF; margin-bottom: 5px;'>Buddhi AI</div>", unsafe_allow_html=True)
    
    # Connection status indicator
    if backend_ok:
        st.markdown('<span class="buddhi-badge" style="background-color: rgba(40, 167, 69, 0.1); color: #28a745; border-color: rgba(40, 167, 69, 0.4);">● Inference Server Online</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="buddhi-badge" style="background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border-color: rgba(220, 53, 69, 0.4);">● Connection Failed</span>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">Navigation</div>', unsafe_allow_html=True)
    
    # Vertical navigation buttons
    if st.button("📊 Dashboard", use_container_width=True, type="primary" if st.session_state.current_page == "Dashboard" else "secondary"):
        st.session_state.current_page = "Dashboard"
        st.rerun()
        
    if st.button("💬 Chat UI", use_container_width=True, type="primary" if st.session_state.current_page == "Chat UI" else "secondary"):
        st.session_state.current_page = "Chat UI"
        st.rerun()

    _workspace_path = os.getcwd().replace("\\", "/")
    _project_name = os.path.basename(_workspace_path)
    if not _project_name:
        _project_name = "active_workspace"
        
    _default_system_prompt = (
        f"You are Buddhi AI, a powerful local AI coding and thinking assistant.\n"
        f"You are actively assisting with the following project:\n"
        f"  - Project: {_project_name}\n"
        f"  - Workspace: {_workspace_path}\n"
        f"Answer concisely, provide high-quality code blocks, and think critically.\n\n"
        f"CRITICAL RULES:\n"
        f"1. You have access to CodeGraph codebase tools (like `get_codebase_summary`, `find_relevant_symbols`, etc.). You MUST use these tools to inspect and understand the active codebase before answering questions about this project's code, structure, or files.\n"
        f"2. DO NOT make assumptions or hallucinate details about this project based on the assistant name 'Buddhi' or any other general knowledge. If the codebase tools are not loaded, or if they return an empty response indicating that the codebase has not been indexed, you MUST explicitly inform the user: 'I cannot find the CodeGraph for this project. Please ensure you have initialized the project by running `buddhi init` in your terminal to index the codebase first, then restart the session.' Do not guess or hallucinate."
    )
    system_instruction = _default_system_prompt

    if st.session_state.current_page == "Chat UI":
        st.markdown('<div class="sidebar-section-title">Controls</div>', unsafe_allow_html=True)
        
        # Clear conversation history (for Chat page)
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.success("Chat history cleared!")
            time.sleep(0.8)
            st.rerun()

    st.markdown('<div class="sidebar-section-title">Backend Metadata</div>', unsafe_allow_html=True)
    st.markdown(f"**API Endpoint:** `{BACKEND_URL}`")
    st.markdown("**Model Type:** `gemma-4-E4B-it.litertlm` (Edge)")

# ------------------------------------------------------------------------------
# MCP Integration & Tool Execution
# ------------------------------------------------------------------------------
from ui.mcp_client import get_mcp_config, list_mcp_tools, call_mcp_tool

def get_system_instruction_with_tools(base_instruction, tools):
    if not tools:
        return base_instruction
    
    tools_json = []
    for t in tools:
        tools_json.append({
            "name": t.name,
            "description": t.description,
            "parameters": t.inputSchema
        })
    
    tools_str = json.dumps(tools_json, indent=2)
    
    instruction = base_instruction + "\n\n"
    instruction += "You have access to the following tools:\n\n"
    instruction += "```xml\n<tools>\n" + tools_str + "\n</tools>\n```\n\n"
    instruction += "To call a tool, use the exact following format:\n"
    instruction += "```xml\n<tool_call>\n"
    instruction += '{"name": "tool_name", "arguments": {"arg_name": "arg_value"}}\n'
    instruction += "</tool_call>\n```\n"
    instruction += "Once you receive the tool's output in the next turn, formulate your final response."
    
    return instruction

# ------------------------------------------------------------------------------
# API Streaming Function (Chat UI Page helper)
# ------------------------------------------------------------------------------
def stream_model_response(messages, system_instruction, thinking_placeholder=None):
    import asyncio
    import queue as queue_module
    import threading

    from ui.agent import get_react_agent
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    # Initialize the agent once per Streamlit session (synchronously, outside async scope)
    # This avoids re-spawning MCP stdio subprocesses on every message.
    if "_buddhi_react_agent" not in st.session_state:
        st.session_state["_buddhi_react_agent"] = get_react_agent()
    agent = st.session_state["_buddhi_react_agent"]

    # Build the message list synchronously before handing off to the thread
    langchain_messages = []
    if system_instruction:
        # Dynamically inject active CodeGraph configuration/database statuses to guarantee robust fallback
        from ui.mcp_client import get_mcp_config
        mcp_conf = get_mcp_config()
        mcp_status = "ACTIVE" if mcp_conf else "MISSING_CONFIG"
        
        db_exists = False
        try:
            from mcp.db import get_db_path
            db_exists = os.path.exists(get_db_path())
        except Exception:
            db_exists = os.path.exists(os.path.join(os.getcwd(), ".buddhi", "graph.db"))
            
        db_status = "INITIALIZED" if db_exists else "NOT_FOUND"
        
        extra_prompt = (
            f"\n\n[SYSTEM CODEGRAPH STATUS]\n"
            f"- MCP Server Config: {mcp_status}\n"
            f"- CodeGraph SQLite DB: {db_status}\n"
        )
        if mcp_status != "ACTIVE":
            extra_prompt += (
                "- CRITICAL INFO: The workspace `.agent/mcp_config.json` configuration is missing or invalid. CodeGraph tools are NOT available. You MUST tell the user that you cannot access their codebase because Buddhi is not initialized, and guide them to run `buddhi init` to start.\n"
            )
        elif db_status != "INITIALIZED":
            extra_prompt += (
                "- CRITICAL INFO: The CodeGraph SQLite database `.buddhi/graph.db` does not exist. The codebase has not been indexed yet. Even if tools are listed, calling them will yield no symbols. You MUST tell the user that you cannot find the CodeGraph for this project and ask them to run `buddhi init` or `buddhi update` in their terminal to index the codebase.\n"
            )
            
        langchain_messages.append(SystemMessage(content=system_instruction + extra_prompt))
    for msg in messages:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))

    inputs = {"messages": langchain_messages}

    # Thread-safe queue: events are put by the background thread, consumed here
    result_queue = queue_module.Queue()
    _SENTINEL = object()  # signals end of stream

    async def _run_agent():
        """Runs the LangGraph ReAct agent and pushes events onto the queue."""
        try:
            async for event in agent.astream_events(inputs, version="v2"):
                kind = event.get("event")
                name = event.get("name")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and chunk.content:
                        result_queue.put(("token", chunk.content))
                elif kind == "on_tool_start":
                    tool_input = event.get("data", {}).get("input", {})
                    result_queue.put(("tool_start", (name, tool_input)))
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output", "")
                    result_queue.put(("tool_end", (name, tool_output)))
        except Exception as e:
            result_queue.put(("error", str(e)))
        finally:
            result_queue.put((_SENTINEL, None))

    def _thread_worker():
        """Runs the async event consumer in a dedicated event loop on a background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_agent())
        finally:
            loop.close()

    thread = threading.Thread(target=_thread_worker, daemon=True)
    thread.start()

    # Premium collapsible status block for agent thoughts & tool triggers
    status = None
    if thinking_placeholder:
        status = thinking_placeholder.status("🧠 **Buddhi AI Thinking...**", expanded=True)

    # Drain the queue in Streamlit's sync context
    try:
        while True:
            item_type, val = result_queue.get()
            if item_type is _SENTINEL:
                break
            if item_type == "token":
                yield val
            elif item_type == "tool_start" and status:
                tool_name, tool_input = val
                status.write(f"🛠️ **Invoking MCP Tool:** `{tool_name}`")
                status.write(f"📥 **Parameters:** `{tool_input}`")
            elif item_type == "tool_end" and status:
                tool_name, tool_output = val
                preview = str(tool_output)[:400] + "..." if len(str(tool_output)) > 400 else str(tool_output)
                status.write(f"📤 **Tool Result (`{tool_name}`):**\n```\n{preview}\n```")
            elif item_type == "error":
                yield f"\n\n**Error during ReAct execution:** {val}"
    finally:
        thread.join(timeout=30)
        if status:
            status.update(label="🧠 **Thinking Complete**", state="complete", expanded=False)


# ------------------------------------------------------------------------------
# Observability Dashboard Page Render
# ------------------------------------------------------------------------------
def render_dashboard_page():

    metrics = get_telemetry_metrics()
    
    # 4 Column metrics display with premium styling overrides
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(label="Total Invocations", value=f"{metrics['total']} runs")
    with col_m2:
        st.metric(label="Success Executions", value=f"{metrics['success']} runs")
    with col_m3:
        st.metric(label="System Health (Success %)", value=f"{metrics['success_rate']}%")
    with col_m4:
        st.metric(label="Average Latency", value=f"{metrics['avg_latency']} ms")

    st.write("")

    if metrics['total'] == 0:
        st.info("No tool execution logs found in the local telemetry database. Go to the 'Chat UI' tab and run prompts to invoke MCP codebase tools, then check back!", icon="ℹ️")
        return

    # Visualizations Row
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("<div style='font-size: 1.2rem; font-weight: 600; color: #FFF; margin-bottom: 10px;'>Tool Invocation Frequency</div>", unsafe_allow_html=True)
        usage_df = get_tool_usage_df()
        if not usage_df.empty:
            st.bar_chart(data=usage_df, x="Tool Name", y="Invocation Count")
        else:
            st.info("No frequency data available.")

    with col_chart2:
        st.markdown("<div style='font-size: 1.2rem; font-weight: 600; color: #FFF; margin-bottom: 10px;'>Tool Latency Profiler (ms)</div>", unsafe_allow_html=True)
        latency_df = get_tool_latency_df()
        if not latency_df.empty:
            st.bar_chart(data=latency_df, x="Tool Name", y="Avg Latency (ms)")
        else:
            st.info("No latency profile data available.")

    # Timeline / Trend Row
    st.write("")
    st.markdown("<div style='font-size: 1.2rem; font-weight: 600; color: #FFF; margin-bottom: 10px;'>Usage Timeline (Triggers / Hour)</div>", unsafe_allow_html=True)
    timeline_df = get_usage_timeline_df()
    if not timeline_df.empty:
        st.line_chart(data=timeline_df, x="Time", y="Triggers")
    else:
        st.info("No timeline trend data available yet.")

    # Raw Logs Table
    st.write("")
    st.markdown("<div style='font-size: 1.2rem; font-weight: 600; color: #FFF; margin-bottom: 10px;'>Recent Telemetry Invocations Log</div>", unsafe_allow_html=True)
    raw_df = get_raw_logs_df(limit=100)
    
    # Simple search search query filter
    search_query = st.text_input("🔍 Filter logs by tool name or status...", value="")
    if search_query:
        filtered_df = raw_df[
            raw_df["Tool Name"].str.contains(search_query, case=False, na=False) |
            raw_df["Status"].str.contains(search_query, case=False, na=False)
        ]
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(raw_df, use_container_width=True, hide_index=True)

    # Actions panel
    st.markdown('<div class="sidebar-section-title">Database Operations</div>', unsafe_allow_html=True)
    col_act1, col_act2 = st.columns([1, 4])
    with col_act1:
        if st.button("Flush Telemetry Database", type="secondary", use_container_width=True):
            if clear_telemetry_data():
                st.success("Telemetry cleared!")
                time.sleep(0.8)
                st.rerun()
            else:
                st.error("Failed to clear database.")

# ------------------------------------------------------------------------------
# Chat UI Page Render
# ------------------------------------------------------------------------------
def render_chat_page(system_instruction):

    # Connection failure warning
    if not backend_ok:
        st.error(f"Cannot connect to Buddhi inference server at `{BACKEND_URL}`. "
                 f"Please verify that `buddhi live` is running properly on your system.", icon="⚠️")
        st.stop()

    # Initialize Chat State
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Message History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input & Streaming Execution
    if user_input := st.chat_input("Chat with your codebase..."):
        # Display and record user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Process assistant response with full streaming
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            response_placeholder = st.empty()
            
            # Indicate model is initiating before the heavy execution loop starts
            thinking_placeholder.status("⚙️ **Model Initiating...**", expanded=True)
            
            # We pass our list of messages and system instructions to the generator
            response_generator = stream_model_response(st.session_state.messages, system_instruction, thinking_placeholder=thinking_placeholder)
            
            # Render dynamic token-by-token streaming UI
            assistant_response = response_placeholder.write_stream(response_generator)
            
        # Append final full response to state
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})

# ------------------------------------------------------------------------------
# Main Window Routing Router
# ------------------------------------------------------------------------------
if st.session_state.current_page == "Dashboard":
    render_dashboard_page()
else:
    render_chat_page(system_instruction)
