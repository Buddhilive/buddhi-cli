"""
Constants for the metrics module.
"""

# Approximate Claude Sonnet 4.5 pricing (USD per million tokens)
INPUT_PRICE_PER_MTOK = 3.00
OUTPUT_PRICE_PER_MTOK = 15.00
PRICING_LABEL = "Claude Sonnet (approximate)"

# Token encoding to use for counting (closest public approximation to Gemini)
TOKEN_ENCODING = "cl100k_base"
