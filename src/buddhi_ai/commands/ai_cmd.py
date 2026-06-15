import argparse
import sys
import json
import urllib.request
import urllib.error
from buddhi_ai.tui.app import BuddhiChatApp

def verify_server_ready(host: str, port: int) -> tuple[bool, str]:
    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                status = data.get("status")
                if status == "ok":
                    return True, "ready"
                elif status == "loading":
                    return False, "loading"
            return False, "unexpected"
    except urllib.error.URLError:
        return False, "offline"
    except Exception as e:
        return False, f"error: {str(e)}"

def handle_ai(args: argparse.Namespace) -> None:
    """Launch the interactive Terminal User Interface (TUI) Chat."""
    host = args.host
    port = args.port
    
    is_ready, status = verify_server_ready(host, port)
    if not is_ready:
        if status == "offline":
            print(f"[Error] The Buddhi API inferencing server is not running at http://{host}:{port}.")
            print("Please start the server first by running:")
            print("    buddhi server\n")
            print("If you need to download and setup the model first, please run:")
            print("    buddhi setup")
        elif status == "loading":
            print("[Error] The Buddhi API inferencing server is running but the model is still loading.")
            print("Please wait a moment and try launching the chat again.")
        else:
            print(f"[Error] Unexpected server status: {status}")
        sys.exit(1)
        
    app = BuddhiChatApp(host=host, port=port)
    app.run()
