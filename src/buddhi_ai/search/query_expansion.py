"""
Query expansion for zero-hit fallback.

Splits camelCase, PascalCase, and snake_case identifiers into component
tokens and builds FTS5-compatible OR queries.
"""
import re
from typing import List


def expand_query(query: str) -> List[str]:
    """Split a query string into component tokens.

    Handles camelCase, PascalCase, snake_case, and space-separated terms.
    Filters out tokens shorter than 2 characters.

    Examples:
        >>> expand_query("getUserData")
        ['get', 'User', 'Data']
        >>> expand_query("parse_file")
        ['parse', 'file']
        >>> expand_query("XMLParser")
        ['XML', 'Parser']
    """
    tokens: List[str] = []

    for word in query.split():
        # Split snake_case first
        parts = word.split("_")
        for part in parts:
            if not part:
                continue
            # Split camelCase / PascalCase using lookahead/lookbehind
            # Handles: "getUserData" -> ["get", "User", "Data"]
            # Handles: "XMLParser"   -> ["XML", "Parser"]
            camel_parts = re.sub(
                r"([a-z])([A-Z])", r"\1 \2", part
            )
            camel_parts = re.sub(
                r"([A-Z]+)([A-Z][a-z])", r"\1 \2", camel_parts
            )
            tokens.extend(camel_parts.split())

    # Filter trivially short tokens
    return [t for t in tokens if len(t) >= 2]


def build_fts_query(terms: List[str]) -> str:
    """Join expanded terms with OR for FTS5 MATCH syntax.

    FTS5 uses implicit AND between tokens, so we explicitly
    use OR to broaden the search on expanded terms.

    Examples:
        >>> build_fts_query(["get", "User", "Data"])
        'get OR User OR Data'
        >>> build_fts_query(["parse"])
        'parse'
    """
    if not terms:
        return ""

    # Escape FTS5 special characters by wrapping each term in double quotes
    # if it contains special chars, otherwise use raw
    safe_terms: List[str] = []
    for term in terms:
        if re.search(r'[^\w]', term):
            safe_terms.append(f'"{term}"')
        else:
            safe_terms.append(term)

    return " OR ".join(safe_terms)
