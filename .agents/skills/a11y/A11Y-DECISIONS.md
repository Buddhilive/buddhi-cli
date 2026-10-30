# A11Y Decisions Log (Pattern Memory)

> Purpose: cross-turn memory of choices between equally conformant alternatives.

## Decisions

- **Documentation Search Combobox** -> `role="combobox"` on `#search-input` with `aria-controls="search-results-list"`, `aria-expanded`, and default `<li role="option">` hint - WAI-ARIA APG Combobox pattern for client-side search. (2026-10-27)
- **Interactive Graph Navigation** -> Dedicated accessible anchor in header with visible text and explanatory title - ensures direct navigation without modal trap. (2026-10-27)
- **High-Contrast Dark Theme** -> `#f1f5f9` text on `#0b0f19` background (17.48:1 ratio) with sky-400 focus ring (8.94:1 ratio) - passes WCAG 2.2 AA Standard Profile without relying on low-contrast glow. (2026-10-27)

