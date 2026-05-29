import tiktoken
from buddhi_ai.parser.entropy import calculate_entropy


def filter_by_entropy(lines: list[str], threshold: float = 3.0) -> list[str]:
    """
    Filters out lines whose Shannon entropy is below the threshold.
    Blank lines or repetitive boilerplate (e.g. `// ##########`) will be pruned.
    """
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # Empty lines have 0.0 entropy and will be naturally dropped, which is desired
        if calculate_entropy(stripped) >= threshold:
            filtered_lines.append(line)
            
    return filtered_lines


def count_tokens(text: str) -> int:
    """Counts the exact number of BPE tokens using cl100k_base."""
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))
