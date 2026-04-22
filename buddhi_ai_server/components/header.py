"""
Header component for Buddhi AI Server.

A sticky, full-width top bar with no visible borders. Uses a frosted-glass
(backdrop-blur) effect to stay legible over any background. Contains:
  - Left:   Sidebar toggle button (hamburger), visible on all viewports.
  - Center: App title / current page breadcrumb area.
  - Right:  Color mode toggle.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.state.sidebar_state import SidebarState


HEADER_HEIGHT = "60px"


def _mobile_menu_button() -> rx.Component:
    """Hamburger button — shown on all viewports alongside the sidebar toggle."""
    return rx.box(
        rx.icon(
            "menu",
            size=20,
            color="var(--gray-11)",
        ),
        on_click=SidebarState.toggle_sidebar,
        padding="8px",
        border_radius="8px",
        cursor="pointer",
        display=rx.cond(SidebarState.is_mobile, "flex", "none"),
        align_items="center",
        justify_content="center",
        _hover={"background": "var(--gray-3)"},
        transition="background 0.15s ease-in-out",
        title="Toggle navigation",
        flex_shrink="0",
    )


def _breadcrumb() -> rx.Component:
    """Dynamic page title derived from the current route path."""
    # Map path → human-readable title.
    page_title = rx.match(
        rx.State.router.page.path,
        ("/", "Home"),
        ("/settings", "Settings"),
        ("/about", "About"),
        "Buddhi AI",  # default fallback
    )

    return rx.hstack(
        rx.text(
            "Buddhi AI",
            font_size="1rem",
            font_weight="700",
            color="var(--gray-12)",
            display=rx.cond(SidebarState.is_mobile, "block", "none"),
        ),
        rx.text(
            "/",
            font_size="0.875rem",
            color="var(--gray-8)",
            display=rx.cond(SidebarState.is_mobile, "block", "none"),
        ),
        rx.text(
            page_title,
            font_size="0.9375rem",
            font_weight="500",
            color="var(--gray-11)",
        ),
        spacing="2",
        align="center",
    )


def header() -> rx.Component:
    """
    Sticky borderless header bar.

    No border or box-shadow is applied. A subtle backdrop-blur gives it
    depth without a hard dividing line.
    """
    return rx.box(
        rx.hstack(
            # Left: mobile hamburger (only on small viewports)
            _mobile_menu_button(),

            # Center: breadcrumb / page title
            _breadcrumb(),

            rx.spacer(),

            # Right: color-mode toggle
            rx.color_mode.button(
                padding="8px",
                border_radius="8px",
                color="var(--gray-11)",
                _hover={"background": "var(--gray-3)"},
                transition="background 0.15s ease-in-out",
                cursor="pointer",
            ),

            spacing="3",
            align="center",
            width="100%",
            height=HEADER_HEIGHT,
            padding_x="20px",
        ),

        # --- Container styles ---
        position="sticky",
        top="0",
        z_index="20",
        width="100%",
        height=HEADER_HEIGHT,

        # Frosted-glass — no hard border.
        background="color-mix(in srgb, var(--color-background) 80%, transparent)",
        backdrop_filter="blur(12px)",
        border="none",
        box_shadow="none",

        # Smooth background repaints on theme toggle.
        transition="background 0.2s ease-in-out",
    )
