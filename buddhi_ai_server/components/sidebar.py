"""
Sidebar navigation component for Buddhi AI Server.

Renders a collapsible vertical navigation rail. When expanded (240 px) it shows
icon + label for each nav item. When collapsed (68 px) only the icon is shown.
The width transition is handled purely via CSS so the animation is smooth.

Mobile behaviour: on viewports narrower than 768 px the sidebar is absolutely
positioned and slides in over the main content, then dismisses on nav-item click.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.state.sidebar_state import (
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_EXPANDED_WIDTH,
    SidebarState,
)


# ---------------------------------------------------------------------------
# Nav item data
# ---------------------------------------------------------------------------

class NavItem:
    """Descriptor for a single navigation link."""

    def __init__(self, label: str, icon: str, href: str) -> None:
        self.label = label
        self.icon = icon
        self.href = href


NAV_ITEMS: list[NavItem] = [
    NavItem("Home", "home", "/"),
    NavItem("Settings", "settings", "/settings"),
    NavItem("About", "info", "/about"),
]


# ---------------------------------------------------------------------------
# Helper components
# ---------------------------------------------------------------------------

def _nav_item(item: NavItem) -> rx.Component:
    """Single navigation row with icon and animated label."""
    # Detect whether this item's route matches the current page path.
    is_active = rx.State.router.page.path == item.href

    return rx.link(
        rx.hstack(
            # Icon — always visible.
            rx.icon(
                item.icon,
                size=20,
                flex_shrink="0",
                color=rx.cond(
                    is_active,
                    "var(--accent-9)",
                    "var(--gray-11)",
                ),
            ),
            # Label — fades and shrinks to zero-width when collapsed.
            rx.text(
                item.label,
                font_size="0.875rem",
                font_weight="500",
                white_space="nowrap",
                overflow="hidden",
                max_width=rx.cond(SidebarState.is_collapsed, "0px", "160px"),
                opacity=rx.cond(SidebarState.is_collapsed, "0", "1"),
                transition="max-width 0.25s ease-in-out, opacity 0.2s ease-in-out",
                color=rx.cond(
                    is_active,
                    "var(--accent-9)",
                    "var(--gray-11)",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
            padding_x="12px",
            padding_y="10px",
            border_radius="8px",
            background=rx.cond(
                is_active,
                "var(--accent-3)",
                "transparent",
            ),
            _hover={
                "background": rx.cond(
                    is_active,
                    "var(--accent-4)",
                    "var(--gray-3)",
                ),
                "cursor": "pointer",
            },
            transition="background 0.15s ease-in-out",
        ),
        href=item.href,
        on_click=SidebarState.collapse_on_navigate,
        text_decoration="none",
        width="100%",
        display="block",
    )


def _toggle_button() -> rx.Component:
    """Chevron/hamburger button at the top of the sidebar to toggle it."""
    return rx.box(
        rx.icon(
            rx.cond(SidebarState.is_collapsed, "panel-left-open", "panel-left-close"),
            size=20,
            color="var(--gray-11)",
        ),
        on_click=SidebarState.toggle_sidebar,
        padding="10px",
        border_radius="8px",
        cursor="pointer",
        display="flex",
        align_items="center",
        justify_content="center",
        _hover={"background": "var(--gray-3)"},
        transition="background 0.15s ease-in-out",
        title=rx.cond(SidebarState.is_collapsed, "Expand sidebar", "Collapse sidebar"),
    )


def _logo_area() -> rx.Component:
    """App logo / name shown at the top of the expanded sidebar."""
    return rx.hstack(
        rx.image(
            src="/favicon.ico",
            width="28px",
            height="28px",
            border_radius="6px",
            flex_shrink="0",
            alt="Buddhi AI logo",
        ),
        rx.text(
            "Buddhi AI",
            font_size="1rem",
            font_weight="700",
            white_space="nowrap",
            overflow="hidden",
            max_width=rx.cond(SidebarState.is_collapsed, "0px", "160px"),
            opacity=rx.cond(SidebarState.is_collapsed, "0", "1"),
            transition="max-width 0.25s ease-in-out, opacity 0.2s ease-in-out",
            color="var(--gray-12)",
        ),
        spacing="3",
        align="center",
        padding_x="12px",
        padding_y="10px",
        width="100%",
    )


def _mobile_overlay() -> rx.Component:
    """
    Semi-transparent backdrop shown behind the sidebar on mobile when open.
    Clicking it collapses the sidebar.
    """
    return rx.box(
        on_click=SidebarState.toggle_sidebar,
        position="fixed",
        top="0",
        left="0",
        width="100vw",
        height="100vh",
        background="rgba(0,0,0,0.45)",
        z_index="99",
        display=rx.cond(
            SidebarState.is_mobile & ~SidebarState.is_collapsed,
            "block",
            "none",
        ),
    )


# ---------------------------------------------------------------------------
# Public component
# ---------------------------------------------------------------------------

def sidebar() -> rx.Component:
    """
    Collapsible sidebar navigation.

    - Desktop: persistent vertical rail, collapses to icon-only (68 px).
    - Mobile: absolute overlay that slides in from the left; closed by default.
    """
    sidebar_box = rx.box(
        # --- Top section: logo + toggle ---
        rx.vstack(
            rx.hstack(
                _logo_area(),
                rx.spacer(),
                _toggle_button(),
                align="center",
                width="100%",
                padding_right="8px",
            ),
            rx.divider(border_color="var(--gray-4)", margin_y="4px"),
            spacing="0",
            width="100%",
        ),

        # --- Nav items ---
        rx.vstack(
            *[_nav_item(item) for item in NAV_ITEMS],
            spacing="1",
            width="100%",
            padding_x="8px",
            padding_top="8px",
        ),

        # --- Sidebar container styles ---
        position=rx.cond(SidebarState.is_mobile, "fixed", "sticky"),
        top="0",
        left="0",
        z_index=rx.cond(SidebarState.is_mobile, "100", "10"),
        height="100dvh",
        width=rx.cond(
            SidebarState.is_collapsed,
            SIDEBAR_COLLAPSED_WIDTH,
            SIDEBAR_EXPANDED_WIDTH,
        ),
        min_width=rx.cond(
            SidebarState.is_collapsed,
            SIDEBAR_COLLAPSED_WIDTH,
            SIDEBAR_EXPANDED_WIDTH,
        ),
        overflow_x="hidden",
        overflow_y="auto",
        flex_shrink="0",
        display="flex",
        flex_direction="column",
        padding_top="12px",
        padding_bottom="24px",
        background="var(--color-panel-solid)",
        border_right="1px solid var(--gray-4)",
        transition="width 0.25s ease-in-out, min-width 0.25s ease-in-out",
        # Hide mobile sidebar behind the left edge when collapsed on mobile.
        transform=rx.cond(
            SidebarState.is_mobile & SidebarState.is_collapsed,
            f"translateX(-{SIDEBAR_EXPANDED_WIDTH})",
            "translateX(0)",
        ),
    )

    return rx.fragment(
        _mobile_overlay(),
        sidebar_box,
    )
