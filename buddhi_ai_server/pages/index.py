"""
Home page for Buddhi AI Server.

Demonstrates the shared layout with a simple welcome card.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.templates.layout import layout


def _stat_card(icon: str, label: str, value: str, accent: str) -> rx.Component:
    """A small metric/stat card for the dashboard demo."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=18, color=accent),
                rx.text(label, font_size="0.8125rem", color="var(--gray-10)"),
                spacing="2",
                align="center",
            ),
            rx.text(
                value,
                font_size="1.75rem",
                font_weight="700",
                color="var(--gray-12)",
            ),
            spacing="1",
            align="start",
        ),
        padding="20px 24px",
        border_radius="12px",
        background="var(--color-panel-solid)",
        border="1px solid var(--gray-4)",
        flex="1",
        min_width="160px",
        transition="box-shadow 0.2s, transform 0.2s",
        _hover={
            "box_shadow": "0 4px 20px rgba(0,0,0,0.10)",
            "transform": "translateY(-2px)",
        },
    )


def _welcome_hero() -> rx.Component:
    """Hero welcome section."""
    return rx.vstack(
        rx.hstack(
            rx.box(
                rx.icon("brain-circuit", size=32, color="var(--accent-9)"),
                padding="12px",
                border_radius="12px",
                background="var(--accent-3)",
            ),
            rx.vstack(
                rx.heading(
                    "Welcome to Buddhi AI",
                    size="7",
                    color="var(--gray-12)",
                    font_weight="700",
                ),
                rx.text(
                    "Your intelligent assistant — private, local, and always ready.",
                    font_size="0.9375rem",
                    color="var(--gray-10)",
                ),
                spacing="1",
                align="start",
            ),
            spacing="4",
            align="center",
        ),
        rx.divider(border_color="var(--gray-4)"),
        rx.hstack(
            _stat_card("zap", "Models loaded", "0", "var(--amber-9)"),
            _stat_card("message-square", "Sessions", "0", "var(--blue-9)"),
            _stat_card("hard-drive", "Storage used", "0 MB", "var(--green-9)"),
            spacing="4",
            width="100%",
            flex_wrap="wrap",
        ),
        rx.box(
            rx.vstack(
                rx.text(
                    "Getting started",
                    font_size="0.9375rem",
                    font_weight="600",
                    color="var(--gray-12)",
                ),
                rx.text(
                    "Use the navigation on the left to explore the app. "
                    "Click the chevron icon at the top of the sidebar to "
                    "collapse it to an icon-only rail — giving you more "
                    "space for your work.",
                    font_size="0.875rem",
                    color="var(--gray-10)",
                    line_height="1.6",
                ),
                rx.link(
                    rx.button(
                        rx.icon("book-open", size=16),
                        "Read the docs",
                        variant="soft",
                        size="2",
                    ),
                    href="https://reflex.dev/docs/",
                    is_external=True,
                ),
                spacing="3",
                align="start",
            ),
            padding="24px",
            border_radius="12px",
            background="var(--accent-2)",
            border="1px solid var(--accent-4)",
            width="100%",
        ),
        spacing="6",
        align="start",
        width="100%",
    )


def _index_content() -> rx.Component:
    """The inner page content (without the layout wrapper)."""
    return rx.box(
        _welcome_hero(),
        padding="32px",
        max_width="900px",
        margin="0 auto",
        width="100%",
    )


def index() -> rx.Component:
    """Home page wrapped with the shared application layout."""
    return layout(_index_content())
