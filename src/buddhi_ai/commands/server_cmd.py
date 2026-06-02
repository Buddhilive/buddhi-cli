import os
import sys
import time
import subprocess
import argparse

def handle_server(args: argparse.Namespace) -> None:
    model_path = os.path.expanduser("~/.buddhi/models/gemma-4-E4B-it.litertlm")
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}.")
        print("Please ensure the model is downloaded and placed in the correct location.")
        sys.exit(1)

    port = 54321
    buddhi_dir = os.path.expanduser("~/.buddhi")
    os.makedirs(buddhi_dir, exist_ok=True)
    pid_file = os.path.join(buddhi_dir, "server.pid")

    if os.path.exists(pid_file):
        print(f"Server is already running or pid file exists ({pid_file}).")
        print("Run 'buddhi shutdown' to stop it first.")
        sys.exit(1)

    if args.verbose:
        print(f"Starting Buddhi API Server on port {port} in foreground...")
        # Run uvicorn programmatically or via subprocess
        import uvicorn
        uvicorn.run("buddhi_ai.server.api:app", host="127.0.0.1", port=port, log_level="debug")
    else:
        print(f"Starting Buddhi API Server on port {port} in background...")
        
        # Command to run uvicorn
        cmd = [sys.executable, "-m", "uvicorn", "buddhi_ai.server.api:app", "--host", "127.0.0.1", "--port", str(port)]
        
        kwargs = {}
        if os.name == 'nt':
            # Windows detached process
            kwargs.update(creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # Unix detached process
            kwargs.update(start_new_session=True)
            
        with open(os.path.join(buddhi_dir, "server.log"), "a") as log_out:
            process = subprocess.Popen(
                cmd,
                stdout=log_out,
                stderr=log_out,
                stdin=subprocess.DEVNULL,
                cwd=os.getcwd(),
                **kwargs
            )
            
        with open(pid_file, "w") as f:
            f.write(str(process.pid))
            
        print(f"Server started with PID {process.pid}.")
        print(f"Logs are being written to {os.path.join(buddhi_dir, 'server.log')}")
