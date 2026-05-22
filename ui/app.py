import os
import sys
import json
import httpx
import streamlit as st

# ------------------------------------------------------------------------------
# Config & Environment
# ------------------------------------------------------------------------------
BACKEND_HOST = os.getenv("BUDDHI_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BUDDHI_BACKEND_PORT", "58421")
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# Streamlit Page Config
st.set_page_config(
    page_title="Buddhi AI — Chat",
    page_icon="🤖",
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
        border: 1px solid rgba(218, 98, 67, 0.2) !important;
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
# Sidebar - Settings & Customization
# ------------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/artificial-intelligence.png", width=64)
    st.markdown("<div style='font-size: 1.6rem; font-weight: 800; color: #FFF; margin-bottom: 5px;'>Buddhi Live</div>", unsafe_allow_html=True)
    
    # Connection status indicator
    if backend_ok:
        st.markdown(f'<span class="buddhi-badge" style="background-color: rgba(40, 167, 69, 0.1); color: #28a745; border-color: rgba(40, 167, 69, 0.4);">● Inference Server Online</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="buddhi-badge" style="background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border-color: rgba(220, 53, 69, 0.4);">● Connection Failed</span>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">System Settings</div>', unsafe_allow_html=True)
    
    # System Instruction/Prompt editor
    system_instruction = st.text_area(
        "System Instruction (System Prompt)",
        value="You are Buddhi AI, a powerful, helpful local AI coding and thinking assistant. Answer concisely, provide high-quality code blocks, and think critically.",
        height=120,
        help="System instructions guide the model's tone, style, and rules."
    )

    st.markdown('<div class="sidebar-section-title">Controls</div>', unsafe_allow_html=True)
    
    # Clear conversation button
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown('<div class="sidebar-section-title">Backend Metadata</div>', unsafe_allow_html=True)
    st.markdown(f"**API Endpoint:** `{BACKEND_URL}`")
    st.markdown(f"**Model Type:** `gemma-4-E4B-it.litertlm` (Edge)")

# ------------------------------------------------------------------------------
# Main Window UI
# ------------------------------------------------------------------------------
# Premium Top Header
st.markdown(f"""
<div class="buddhi-header">
    <div class="buddhi-title">Buddhi AI <span style="font-size: 1.2rem; font-weight: 300; opacity: 0.7;">live chat</span></div>
    <div>
        <span class="buddhi-badge">v2.0.0</span>
        <span class="buddhi-badge">LiteRT-LM</span>
    </div>
</div>
""", unsafe_allow_html=True)

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

# ------------------------------------------------------------------------------
# API Streaming Function
# ------------------------------------------------------------------------------
def stream_model_response(messages, system_instruction):
    input_items = []
    for msg in messages:
        input_items.append({
            "role": msg["role"],
            "content": [{"type": "text", "text": msg["content"]}]
        })
        
    payload = {
        "input": input_items,
        "stream": True
    }
    if system_instruction:
        payload["instructions"] = system_instruction
        
    headers = {"Content-Type": "application/json"}
    
    try:
        with httpx.stream("POST", f"{BACKEND_URL}/v1/responses", json=payload, headers=headers, timeout=60.0) as r:
            if r.status_code != 200:
                error_detail = r.read().decode()
                yield f"**API Error ({r.status_code}):** {error_detail}"
                return
                
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("delta", {})
                        content_list = delta.get("content", [])
                        if content_list:
                            chunk_text = content_list[0].get("text", "")
                            yield chunk_text
                    except Exception:
                        pass
    except Exception as e:
        yield f"**Inference Connection Error:** {str(e)}"

# ------------------------------------------------------------------------------
# Chat Input & Streaming Execution
# ------------------------------------------------------------------------------
if user_input := st.chat_input("Message Buddhi AI..."):
    # Display and record user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process assistant response with full streaming
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # We pass our list of messages and the system instructions to the generator
        response_generator = stream_model_response(st.session_state.messages, system_instruction)
        
        # Render dynamic token-by-token streaming UI
        assistant_response = response_placeholder.write_stream(response_generator)
        
    # Append final full response to state
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
