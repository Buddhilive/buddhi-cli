import os
import sys

def get_token_counter():
    """Returns a function that counts tokens in a string.
    Tries to use litert_lm if available, otherwise falls back to tiktoken."""
    try:
        # Check if litert_lm exposes a tokenizer
        import litert_lm
        # Assuming litert_lm has some tokenizer logic exposed
        if hasattr(litert_lm, 'count_tokens'):
            return litert_lm.count_tokens
        elif hasattr(litert_lm, 'Tokenizer'):
            # Hypothetical API
            def litert_count(text):
                tokenizer = litert_lm.Tokenizer()
                return len(tokenizer.encode(text))
            return litert_count
    except ImportError:
        pass
    
    # Fallback to tiktoken
    try:
        import tiktoken
        def tiktoken_count(text):
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        return tiktoken_count
    except ImportError:
        print("Warning: Neither litert_lm nor tiktoken is available. Token counts will be estimated by character count (char / 4).")
        def rough_count(text):
            return len(text) // 4
        return rough_count

def run_benchmark():
    """Runs the benchmark suite over the current workspace."""
    count_tokens = get_token_counter()
    
    cwd = os.getcwd()
    print(f"Running Buddhi Benchmark on workspace: {cwd}")
    
    # 1. Benchmark indexer payload (Graph nodes vs Raw files)
    print("\n--- Phase 1: Codebase Indexing Metrics ---")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mcp_dir = os.path.join(base_dir, "mcp")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
        
    try:
        from server import get_codebase_summary_impl
        from indexer import CodeIndexer
        
        # We need a db_path inside .buddhi
        buddhi_dir = os.path.join(cwd, ".buddhi")
        db_path = os.path.join(buddhi_dir, "graph.db")
        
        if not os.path.exists(db_path):
            print("Graph database not found. Please run 'buddhi update' first.")
            return
            
        summary = get_codebase_summary_impl(db_path)
        summary_tokens = count_tokens(summary)
        print(f"Optimized Codebase Summary (Graph Community approach): {summary_tokens} tokens")
        
    except Exception as e:
        print(f"Failed to benchmark indexing: {e}")
    
    # Placeholder for CLI Execution Token Savings
    print("\n--- Phase 2: CLI Command Optimization ---")
    print("Simulated 'git log' vs 'buddhi execute git log':")
    # This would ideally run real commands and compare raw stdout with the JSON output
    print("Feature coming soon: Offline simulation of shell executions.")
    
    print("\nBenchmark completed.")
