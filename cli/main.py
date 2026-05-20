import os
import sys

def get_model_target_dir():
    # The 'server' folder is adjacent to the 'cli' folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "server", "static", "model")

def setup_model():
    """
    Downloads the model required for inference.
    """
    from huggingface_hub import hf_hub_download
    
    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")
    
    if os.path.exists(model_path):
        print("Model already exists at:", model_path)
        return

    print("Downloading model from HuggingFace...", flush=True)
    os.makedirs(target_dir, exist_ok=True)
    hf_hub_download(
        repo_id="litert-community/gemma-4-E4B-it-litert-lm", 
        filename="gemma-4-E4B-it.litertlm", 
        local_dir=target_dir
    )
    print("Model downloaded successfully!", flush=True)

def start():
    """
    Starts the server.
    """
    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")
    
    if not os.path.exists(model_path):
        print("Warning: Model not found. You may need to run 'buddhi setup' first.")

    import uvicorn
    uvicorn.run("server.main:app", host="127.0.0.1", port=58421)

def cli():
    """
    CLI entry point.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_model()
    else:
        start()

if __name__ == "__main__":
    cli()
