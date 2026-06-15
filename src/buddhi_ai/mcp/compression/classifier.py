import os


def resolve_mode(filepath: str, task_intent: str | None = None) -> str:
    """
    Resolves 'auto' mode into a concrete compression profile based on task intent and file size.
    
    Rules:
    - Active Editing (fix, modify, etc) -> full
    - Mapping (architecture, dependencies, etc) -> map
    - Read-Only (understand, trace, etc) -> signatures
    - Fallback -> file scale (< 4KB = full, >= 4KB = signatures)
    """
    if task_intent:
        intent_lower = task_intent.lower()
        
        # Active Editing Actions
        editing_keywords = [
            "fix", "modify", "refactor", "change", "update", 
            "add", "implement", "edit", "write"
        ]
        if any(kw in intent_lower for kw in editing_keywords):
            return "full"
            
        # Read-Only / Mapping Actions
        map_keywords = [
            "architecture", "dependencies", "imports", 
            "exports", "linkages", "outline"
        ]
        if any(kw in intent_lower for kw in map_keywords):
            return "map"
            
        signature_keywords = [
            "find references", "understand", "trace", 
            "call flow", "signature", "interface", "overview", "read"
        ]
        if any(kw in intent_lower for kw in signature_keywords):
            return "signatures"
            
    # Fallback Standard: based on file scale
    try:
        size_bytes = os.path.getsize(filepath)
        # Small files (< 4KB) stay full, large files drop to signatures
        if size_bytes < 4096:
            return "full"
        else:
            return "signatures"
    except (OSError, FileNotFoundError):
        # If file doesn't exist yet or can't be read, default to signatures for safety
        return "signatures"
