"""Lazy loading of tree-sitter grammars, one per supported language id."""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from functools import cache

import tree_sitter as ts

QUERIES_PACKAGE = "buddhi.languages.queries"

# language id -> (module name, attribute or callable name that returns the language pointer)
_GRAMMAR_SOURCES: dict[str, tuple[str, str]] = {
    "python": ("tree_sitter_python", "language"),
    "javascript": ("tree_sitter_javascript", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "tsx": ("tree_sitter_typescript", "language_tsx"),
    "go": ("tree_sitter_go", "language"),
    "rust": ("tree_sitter_rust", "language"),
    "csharp": ("tree_sitter_c_sharp", "language"),
    "java": ("tree_sitter_java", "language"),
    "kotlin": ("tree_sitter_kotlin", "language"),
    "swift": ("tree_sitter_swift", "language"),
}

# language id -> query filename (multiple language ids may share a .scm file)
_QUERY_FILES: dict[str, str] = {
    "python": "python.scm",
    "javascript": "javascript.scm",
    "typescript": "typescript.scm",
    "tsx": "typescript.scm",
    "go": "go.scm",
    "rust": "rust.scm",
    "csharp": "csharp.scm",
    "java": "java.scm",
    "kotlin": "kotlin.scm",
    "swift": "swift.scm",
}


@dataclass
class LanguageSpec:
    id: str
    language: ts.Language
    query: ts.Query


@cache
def available_languages() -> dict[str, str | None]:
    """Return {language_id: None} for loadable languages, {language_id: error} otherwise."""
    result: dict[str, str | None] = {}
    for lang_id in _GRAMMAR_SOURCES:
        try:
            _load_spec(lang_id)
            result[lang_id] = None
        except Exception as exc:  # noqa: BLE001 - want to record any load failure
            result[lang_id] = str(exc)
    return result


@cache
def _load_spec(lang_id: str) -> LanguageSpec:
    if lang_id not in _GRAMMAR_SOURCES:
        raise ValueError(f"Unknown language id: {lang_id}")

    module_name, attr_name = _GRAMMAR_SOURCES[lang_id]
    module = importlib.import_module(module_name)
    getter = getattr(module, attr_name)
    language = ts.Language(getter())

    query_filename = _QUERY_FILES[lang_id]
    query_text = (
        importlib.resources.files(QUERIES_PACKAGE).joinpath(query_filename).read_text(encoding="utf-8")
    )
    query = ts.Query(language, query_text)

    return LanguageSpec(id=lang_id, language=language, query=query)


def get_spec(lang_id: str) -> LanguageSpec | None:
    """Return the LanguageSpec for lang_id, or None if unavailable (missing grammar/query)."""
    try:
        return _load_spec(lang_id)
    except Exception:  # noqa: BLE001
        return None
