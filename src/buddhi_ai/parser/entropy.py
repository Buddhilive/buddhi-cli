import math
from collections import Counter


def calculate_entropy(text: str) -> float:
    """
    Calculate the Shannon entropy of a given text.
    H(X) = -sum(P(x_i) * log2(P(x_i)))

    A lower entropy indicates highly repetitive or boilerplate content
    (e.g., long lines of `//////` or padded arrays).
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


def filter_boilerplate(text: str, threshold: float = 3.0) -> bool:
    """
    Returns True if the text is considered boilerplate (entropy < threshold).
    """
    return calculate_entropy(text) < threshold
