from __future__ import annotations

import math
from collections import Counter


def calculate_entropy(text: str) -> float:
    """Calculate the Shannon entropy of a given text.

    H(X) = -sum(P(x_i) * log2(P(x_i)))
    A lower entropy indicates highly repetitive or boilerplate content.
    """
    if not text:
        return 0.0

    counts = Counter(text)
    length = len(text)

    entropy = 0.0
    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def filter_by_entropy(lines: list[str], threshold: float = 3.0) -> list[str]:
    """Filters out lines whose Shannon entropy is below the threshold.

    Blank lines or repetitive boilerplate (e.g. `// ##########`) will be pruned.
    """
    filtered_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if calculate_entropy(stripped) >= threshold:
            filtered_lines.append(line)

    return filtered_lines


def count_tokens(text: str) -> int:
    """Counts the number of tokens using tiktoken if available, else standard char heuristic."""
    if not text:
        return 0

    try:
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except Exception:
        # Standard heuristic: ~4 characters per token
        return max(1, len(text) // 4)
