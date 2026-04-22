"""
Buddhi AI Server — Reflex application entry point.

All pages are imported here and registered with the ``rx.App`` instance.
New pages should:
  1. Be created under ``buddhi_ai_server/pages/``.
  2. Wrap their return value with ``layout()`` from ``templates/layout.py``.
  3. Be imported and registered with ``app.add_page`` below.
"""

import reflex as rx

from buddhi_ai_server.pages.index import index
from buddhi_ai_server.pages.settings import settings
from buddhi_ai_server.pages.about import about

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = rx.App(
    theme=rx.theme(
        appearance="dark",          # default theme; user can toggle via header
        has_background=True,
        accent_color="violet",      # primary accent throughout the UI
        gray_color="slate",
        radius="medium",
    ),
)

# ---------------------------------------------------------------------------
# Page registration
# ---------------------------------------------------------------------------

app.add_page(index, route="/", title="Home | Buddhi AI")
app.add_page(settings, route="/settings", title="Settings | Buddhi AI")
app.add_page(about, route="/about", title="About | Buddhi AI")
