"""
Relationship weight definitions.
"""

WEIGHTS = {
    "inherit": 10.0,
    "extension": 10.0,
    "compose": 5.0,
    "instantiation": 5.0,
    "call": 3.0,
    "import": 1.0,
    "reference": 1.0,
}

def get_weight(relationship_type: str) -> float:
    """Return the edge weight based on the relationship type string."""
    rel = relationship_type.lower()
    
    # Try direct match
    if rel in WEIGHTS:
        return WEIGHTS[rel]
        
    # Try substring match for common patterns
    if "inherit" in rel or "extend" in rel or "extension" in rel:
        return 10.0
    if "compose" in rel or "instantiat" in rel:
        return 5.0
    if "call" in rel or "function" in rel:
        return 3.0
    if "import" in rel or "reference" in rel or "include" in rel:
        return 1.0
        
    # Default to weakly coupled
    return 1.0
