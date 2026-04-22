"""
Shared page layout template for Buddhi AI Server.

All pages import and call ``layout(content)`` to receive the sidebar +
header shell wrapped around their content. This is the single source of
truth for the application chrome.

Mobile detection:
  SidebarState exposes ``check_mobile`` which calls ``rx.call_script`` to
  read ``window.innerWidth`` and update the state. This event is fired:
    1. On layout mount via ``on_mount``.
    2. On window resize via an ``rx.script`` that attaches a debounced
       listener calling the same event through Reflex's event system.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.components.header import HEADER_HEIGHT, header
from buddhi_ai_server.components.sidebar import sidebar
from buddhi_ai_server.state.sidebar_state import SidebarState


def layout(page_content: rx.Component) -> rx.Component:
    """
    Wrap *page_content* with the shared sidebar + header application shell.

    Usage::

        def my_page() -> rx.Component:
            return layout(rx.text("Hello, world!"))

    Args:
        page_content: The component tree representing the current page body.

    Returns:
        A full-viewport component with sidebar, sticky header, and the
        page content in a scrollable main area.
    """
    return rx.box(
        # --- Main flex row: sidebar | content column ---
        rx.hstack(
            # Left: collapsible sidebar
            sidebar(),

            # Right: header + scrollable page body
            rx.box(
                # Sticky header
                header(),

                # Scrollable page body
                rx.box(
                    page_content,
                    flex="1",
                    overflow_y="auto",
                    width="100%",
                    min_height=f"calc(100dvh - {HEADER_HEIGHT})",
                ),

                display="flex",
                flex_direction="column",
                flex="1",
                overflow="hidden",
                min_width="0",  # prevents flex children from overflowing
            ),

            spacing="0",
            align="start",
            width="100%",
            height="100dvh",
            overflow="hidden",
        ),

        # Root container
        width="100%",
        height="100dvh",
        overflow="hidden",
        position="relative",

        # Trigger mobile detection on every page mount.
        on_mount=SidebarState.check_mobile,
    )
