# Implementation Choices: Polished CLI Output, 1.0.0 Release

**Branch**: `014-polished-cli-output` | **Date**: 2026-10-30

### Choices Ledger

#### C001: 66-Column Pure ASCII Block Art
- **Context**: The spec requested an ASCII art style title saying "BuddhiAI CLI" with the tool version.
- **Choice**: Hand-crafted 66-column block font (`| __ ) ...`) containing 100% 7-bit ASCII characters (codes 32-126) with zero external dependency (avoided adding `pyfiglet`).
- **Classification**: `sound`
- **Rationale**: 66 columns cleanly fit inside standard 80-column terminal viewports without line wrapping. 7-bit ASCII prevents Unicode encoding errors on legacy Windows consoles (cp1252/cp437).

#### C002: Dynamic Narrow Viewport Fallback (< 70 Columns)
- **Context**: Terminals narrower than 70 columns would wrap multi-line ASCII art, ruining visual presentation.
- **Choice**: Inspect `console.width` and degrade automatically to a single-line styled header: `BuddhiAI CLI v1.0.0 - Tree-Sitter Code Graph & Agent Harness`.
- **Classification**: `sound`
- **Rationale**: Preserves readability across compact split-panes, mobile terminal emulators, and nested IDE consoles.

#### C003: Windows Legacy Console Encoding Auto-Detection
- **Context**: Windows command prompts running in `cp1252` charmap crash when attempting to print Unicode glyphs like `✓` (`\u2713`), `•` (`\u2022`), or `→` (`\u2192`).
- **Choice**: Implemented `_can_encode()` probe in `src/buddhi/ui/formatters.py` that dynamically falls back to safe ASCII equivalents (`[done]`, `*`, `->`, `[!]`, `[error]`) when the console stream cannot encode Unicode.
- **Classification**: `sound`
- **Rationale**: Eliminates `UnicodeEncodeError` across all legacy Windows environments while preserving rich Unicode on modern UTF-8 terminals.

