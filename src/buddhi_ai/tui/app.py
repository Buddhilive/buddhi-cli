import asyncio
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

    MOCK_RESPONSES = {
        "intro": (
            "Hello! I am **Buddhi AI**, your intelligent codebase explorer.\n\n"
            "I can help you navigate, audit, and refactor your workspace:\n"
            "1. 🔍 **Map structural entities** (functions, classes, imports) using advanced Tree-sitter parsers.\n"
            "2. ⚡ **Boilerplate filtering** utilizing Shannon entropy to isolate unique logic.\n"
            "3. 📊 **Metrics tracking** to gauge token savings and productivity boosts.\n\n"
            "How can I assist you with your codebase today?"
        ),
        "code": (
            "Here is how you can use a custom Python script to interact with your codebase's AST using tree-sitter:\n\n"
            "```python\n"
            "from tree_sitter import Language, Parser\n\n"
            "# Initialize parser\n"
            "parser = Parser()\n"
            "parser.set_language(Language('build/my-languages.so', 'python'))\n\n"
            "tree = parser.parse(b\"\"\"\n"
            "def hello_world():\n"
            "    print('Hello, Buddhi!')\n"
            "\"\"\")\n"
            "print(tree.root_node.sexp())\n"
            "```\n\n"
            "Let me know if you would like me to write a parser hook for your specific language!"
        ),
        "repo": (
            "### 📁 Repository Intelligence Summary\n\n"
            "I analyzed your workspace structure:\n"
            "- **Active Languages:** Python (core CLI), TOML (project config), Markdown (documentation).\n"
            "- **Dependencies:** `tree-sitter` (P25+), `mcp`, `tiktoken`, and now `textual`!\n"
            "- **Target Entrypoint:** `src/buddhi_ai/cli.py` which delegates to hooks and CLI controllers.\n\n"
            "Let me know if you want me to analyze a specific file's structure or clean up boilerplate!"
        )
    }

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="chat-container"):
            with VerticalScroll(id="chat-thread"):
                # Initial system introduction
                yield AssistantMessage(self.MOCK_RESPONSES["intro"])
            with Horizontal(id="input-container"):
                yield TextArea(placeholder="Type your message here... (Ctrl+S to Send, Ctrl+X to Clear)", id="chat-input")
                yield Button("Send", variant="primary", id="send-button")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-input").focus()
        
    def action_send(self) -> None:
        """Handle sending the message from input area."""
        textarea = self.query_one("#chat-input", TextArea)
        prompt = textarea.text.strip()
        if not prompt:
            return
            
        # Mount User Message
        thread = self.query_one("#chat-thread", VerticalScroll)
        user_msg = UserMessage(prompt)
        thread.mount(user_msg)
        
        # Clear Input
        textarea.text = ""
        
        # Select response based on keywords
        response_text = self._get_mock_response(prompt)
        
        # Create Empty Assistant Message
        assistant_msg = AssistantMessage("")
        thread.mount(assistant_msg)
        
        # Scroll to bottom
        thread.scroll_end(animate=False)
        
        # Stream response
        self.stream_response(assistant_msg, response_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button":
            self.action_send()

    def action_clear_thread(self) -> None:
        """Clear all chat messages and remount initial message."""
        thread = self.query_one("#chat-thread", VerticalScroll)
        # Remove all children
        for child in list(thread.children):
            child.remove()
        
        # Mount intro
        intro_msg = AssistantMessage(self.MOCK_RESPONSES["intro"])
        thread.mount(intro_msg)
        thread.scroll_end(animate=False)

    @work(exclusive=True)
    async def stream_response(self, assistant_msg: AssistantMessage, response_text: str):
        """Simulate a streaming response from an LLM by appending word by word."""
        current_text = ""
        words = response_text.split(" ")
        thread = self.query_one("#chat-thread", VerticalScroll)
        
        for word in words:
            current_text += (word + " ")
            assistant_msg.update_message(current_text)
            thread.scroll_end(animate=False)
            await asyncio.sleep(0.04) # Simulate premium typing speed
            
        # Ensure scroll catches up fully at the end
        thread.scroll_end(animate=False)

    def _get_mock_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["help", "buddhi", "intro", "hello", "hi"]):
            return self.MOCK_RESPONSES["intro"]
        elif any(w in prompt_lower for w in ["code", "script", "example", "python", "tree-sitter"]):
            return self.MOCK_RESPONSES["code"]
        elif any(w in prompt_lower for w in ["repo", "structure", "folder", "project", "file"]):
            return self.MOCK_RESPONSES["repo"]
        else:
            return (
                f"I received your message: *\"{prompt}\"*\n\n"
                "As I am currently running in TUI UI mock mode, I don't have a live connection to an LLM. "
                "However, I successfully captured your prompt! Here is some markdown telemetry of your query:\n\n"
                "| Property | Value |\n"
                "| --- | --- |\n"
                "| **Prompt Length** | " + str(len(prompt)) + " chars |\n"
                "| **Word Count** | " + str(len(prompt.split())) + " words |\n"
                "| **UI Framework** | Textual 0.86+ |\n"
                "| **Mock Stream Status** | ✅ Streaming Active |\n\n"
                "Try asking me about **'code'** or **'repo'** to see predefined premium mock responses!"
            )

if __name__ == "__main__":
    BuddhiChatApp().run()
