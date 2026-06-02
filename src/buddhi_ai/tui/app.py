import asyncio
import os
import json
import httpx
import tiktoken
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal, Container
from textual.widgets import Header, Footer, TextArea, Button, Static, Markdown
from textual import work
from textual.binding import Binding

class UserMessage(Static):
    """A widget to display a User message in the chat thread."""
    def __init__(self, text: str):
        super().__init__(text)
        self.border_title = "👤 You"

class AssistantMessage(Static):
    """A widget to display an Assistant message with Markdown in the chat thread."""
    def __init__(self, markdown_text: str = ""):
        super().__init__()
        self.markdown_text = markdown_text
        self.border_title = "🤖 Buddhi AI"
        
    def compose(self) -> ComposeResult:
        self.md = Markdown(self.markdown_text)
        yield self.md
        
    def update_message(self, text: str):
        self.markdown_text = text
        self.md.update(self.markdown_text)

class BuddhiChatApp(App):
    """The main Buddhi AI TUI Chat Application."""
    
    TITLE = "Buddhi AI - Interactive Chat CLI"
    SUB_TITLE = "Codebase mapping & boilerplate filter agent"
    
    BINDINGS = [
        Binding("ctrl+s", "send", "Send Message", show=True),
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+x", "clear_thread", "Clear Chat", show=True),
    ]

    CSS = """
    Screen {
        background: $background;
    }

    #chat-container {
        width: 100%;
        height: 100%;
        layout: vertical;
    }

    #chat-thread {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        background: $boost;
        padding: 1 2;
    }

    #input-container {
        width: 100%;
        height: 7;
        layout: horizontal;
        border-top: solid $primary;
        background: $panel;
        padding: 1 2;
    }

    #chat-input {
        width: 1fr;
        height: 5;
        border: round $primary-muted;
    }

    #send-button {
        width: 14;
        height: 3;
        margin-top: 1;
        margin-left: 2;
    }

    UserMessage {
        background: $primary-muted;
        color: $text;
        margin: 1 0;
        padding: 1 2;
        border: round $primary;
        height: auto;
        width: 100%;
    }

    AssistantMessage {
        background: $surface;
        color: $text;
        margin: 1 0;
        padding: 1 2;
        border: round $success;
        height: auto;
        width: 100%;
    }
    
    AssistantMessage Markdown {
        background: transparent;
        margin: 0;
        padding: 0;
    }
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 54321, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.conversation_history = []
        self.system_prompt = (
            "You are Buddhi AI, an intelligent codebase explorer and expert software engineer. "
            "You help developers navigate, audit, and refactor workspaces, map structural entities "
            "(functions, classes, imports), and filter boilerplate code using Shannon entropy and "
            "Tree-sitter parsers. Be concise, helpful, and provide high-quality markdown formatted responses."
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="chat-container"):
            with VerticalScroll(id="chat-thread"):
                # Placeholder for initial message, injected in on_mount
                pass
            with Horizontal(id="input-container"):
                yield TextArea(placeholder="Type your message here... (Ctrl+S to Send, Ctrl+X to Clear)", id="chat-input")
                yield Button("Send", variant="primary", id="send-button")
        yield Footer()

    def on_mount(self) -> None:
        # Check custom config for system prompt
        config_path = os.path.expanduser("~/.buddhi/config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    if "system_prompt" in config:
                        self.system_prompt = config["system_prompt"]
            except Exception:
                pass

        self.conversation_history = []
        
        intro_text = (
            "Hello! I am **Buddhi AI**, your intelligent codebase explorer.\n\n"
            "I'm fully connected to the local LiteRT-LM API. How can I assist you with your codebase today?"
        )
        
        thread = self.query_one("#chat-thread", VerticalScroll)
        intro_msg = AssistantMessage(intro_text)
        thread.mount(intro_msg)

        self.query_one("#chat-input").focus()
        
    def action_send(self) -> None:
        """Handle sending the message from input area."""
        textarea = self.query_one("#chat-input", TextArea)
        prompt = textarea.text.strip()
        if not prompt:
            return
            
        thread = self.query_one("#chat-thread", VerticalScroll)
        user_msg = UserMessage(prompt)
        thread.mount(user_msg)
        
        textarea.text = ""
        
        assistant_msg = AssistantMessage("")
        thread.mount(assistant_msg)
        thread.scroll_end(animate=False)
        
        self.stream_response(assistant_msg, prompt)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button":
            self.action_send()

    def action_clear_thread(self) -> None:
        """Clear all chat messages and remount initial message."""
        thread = self.query_one("#chat-thread", VerticalScroll)
        for child in list(thread.children):
            child.remove()
        
        self.conversation_history = []
        intro_text = "Chat history cleared. How can I assist you next?"
        intro_msg = AssistantMessage(intro_text)
        thread.mount(intro_msg)
        thread.scroll_end(animate=False)

    @work(exclusive=True)
    async def stream_response(self, assistant_msg: AssistantMessage, prompt: str):
        """Connect to the local LiteRT-LM API and stream the actual LLM response."""
        textarea = self.query_one("#chat-input", TextArea)
        send_btn = self.query_one("#send-button", Button)
        thread = self.query_one("#chat-thread", VerticalScroll)
        
        textarea.disabled = True
        send_btn.disabled = True
        
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Buffer and Summarize Logic (120k token limit)
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            total_tokens = sum(len(enc.encode(msg["content"])) for msg in self.conversation_history)
            if self.system_prompt:
                total_tokens += len(enc.encode(self.system_prompt))
                
            if total_tokens > 120000 and len(self.conversation_history) > 6:
                middle_msgs = self.conversation_history[2:-4]
                if middle_msgs:
                    summary_prompt = "Summarize the following chat history concisely while preserving key details and entity mappings:\n\n"
                    for m in middle_msgs:
                        summary_prompt += f"{m['role'].upper()}: {m['content']}\n"
                        
                    try:
                        async with httpx.AsyncClient() as client:
                            summary_resp = await client.post(
                                f"http://{self.host}:{self.port}/v1/chat/completions",
                                json={
                                    "model": "gemma-4-E4B-it.litertlm",
                                    "messages": [{"role": "user", "content": summary_prompt}],
                                    "stream": False,
                                },
                                timeout=30.0
                            )
                            if summary_resp.status_code == 200:
                                summary_data = summary_resp.json()
                                summary_content = summary_data["choices"][0]["message"]["content"]
                                new_history = self.conversation_history[:2]
                                new_history.append({"role": "system", "content": f"[System Note: Summary of previous discussion: {summary_content}]"})
                                new_history.extend(self.conversation_history[-4:])
                                self.conversation_history = new_history
                    except Exception:
                        pass # Proceed without summarization if it fails
        except Exception:
            pass # Fallback if tiktoken encoding fails
            
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
            
        messages.extend(self.conversation_history)
        
        current_text = ""
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"http://{self.host}:{self.port}/v1/chat/completions",
                    json={
                        "model": "gemma-4-E4B-it.litertlm",
                        "messages": messages,
                        "stream": True,
                        "temperature": 0.7,
                        "max_tokens": 1024,
                    },
                    timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        error_detail = await response.aread()
                        assistant_msg.update_message(f"⚠️ **Error from API server ({response.status_code}):** {error_detail.decode('utf-8')}")
                        return
                        
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    assistant_msg.update_message(f"⚠️ **Streaming Error:** {data['error']}")
                                    return
                                    
                                content = data["choices"][0]["delta"].get("content", "")
                                if content:
                                    current_text += content
                                    assistant_msg.update_message(current_text)
                                    thread.scroll_end(animate=False)
                            except Exception:
                                pass
                                
            if current_text:
                self.conversation_history.append({"role": "assistant", "content": current_text})
                
        except Exception as e:
            assistant_msg.update_message(f"⚠️ **Failed to communicate with inferencing server:** {str(e)}")
        finally:
            textarea.disabled = False
            send_btn.disabled = False
            textarea.focus()
            thread.scroll_end(animate=False)

if __name__ == "__main__":
    BuddhiChatApp().run()
