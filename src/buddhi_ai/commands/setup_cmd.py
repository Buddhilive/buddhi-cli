import os
import sys
import shutil
import argparse

def get_drive_path(path: str) -> str:
    """Finds the nearest existing directory to check disk usage."""
    current = os.path.abspath(path)
    while not os.path.exists(current):
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return current

def handle_setup(args: argparse.Namespace) -> None:
    model_dir = os.path.expanduser("~/.buddhi/models")
    model_filename = "gemma-4-E4B-it.litertlm"
    model_path = os.path.join(model_dir, model_filename)

    # 1. Check if model already exists
    if os.path.exists(model_path):
        print(f"[OK] Gemma 4 E4B model is already available at {model_path}. Skipping download.")
        return

    # 2. Check disk space
    check_dir = get_drive_path(model_dir)
    try:
        usage = shutil.disk_usage(check_dir)
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 6.0:
            print(f"[Error] Insufficient disk space. Minimum 6.0 GB is required, but only {free_gb:.2f} GB is available.")
            print("Please free up some disk space and try again.")
            sys.exit(1)
    except Exception as e:
        print(f"[Warning] Could not verify disk space: {e}")

    # 3. Patch tqdm for rich progress UI
    try:
        import tqdm.auto
        from tqdm.rich import tqdm as rich_tqdm
        tqdm.auto.tqdm = rich_tqdm
    except ImportError:
        pass  # Fallback to standard tqdm if rich is somehow missing

    os.makedirs(model_dir, exist_ok=True)
    print(f"[INFO] Initializing Gemma 4 E4B model download ({model_filename}) from litert-community/gemma-4-E4B-it-litert-lm...")

    try:
        from huggingface_hub import hf_hub_download
        hf_hub_download(
            repo_id="litert-community/gemma-4-E4B-it-litert-lm",
            filename=model_filename,
            local_dir=model_dir,
            local_dir_use_symlinks=False
        )
        print(f"[OK] Model downloaded successfully to {model_path}")
    except KeyboardInterrupt:
        print("\n[Warning] Setup interrupted. You can re-run 'buddhi setup' anytime to resume the download.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Error] Download failed due to: {e}")
        print("You can re-run 'buddhi setup' to retry and resume the download.")
        sys.exit(1)
