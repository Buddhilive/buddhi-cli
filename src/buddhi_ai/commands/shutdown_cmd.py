import os
import sys
import psutil
import argparse

def handle_shutdown(args: argparse.Namespace) -> None:
    pid_file = os.path.expanduser("~/.buddhi/server.pid")
    
    if not os.path.exists(pid_file):
        print("Buddhi server does not appear to be running (no pid file found).")
        sys.exit(0)

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
    except ValueError:
        print("Invalid PID in server.pid file. Cleaning up the file.")
        os.remove(pid_file)
        sys.exit(1)

    print(f"Shutting down Buddhi server (PID: {pid})...")

    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=5)
        print("Server stopped successfully.")
    except psutil.NoSuchProcess:
        print("Process was not running. It may have been stopped already.")
    except psutil.TimeoutExpired:
        print("Process did not terminate cleanly. Force killing...")
        process.kill()
        print("Server force stopped.")
    except Exception as e:
        print(f"Error while stopping server: {e}")
        
    if os.path.exists(pid_file):
        os.remove(pid_file)
