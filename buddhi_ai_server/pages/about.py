"""
About page stub for Buddhi AI Server.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.templates.layout import layout


def _about_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon("info", size=28, color="var(--accent-9)"),
                    padding="12px",
                    border_radius="12px",
                    background="var(--accent-3)",
                ),
                rx.vstack(
                    rx.heading("About Buddhi AI", size="7", font_weight="700", color="var(--gray-12)"),
                    rx.text(
                        "A private, local-first AI assistant server.",
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
            rx.box(
                rx.vstack(
                    rx.text(
                        "Buddhi AI Server is an open-source, local-first AI inference server "
                        "built with Reflex. All computation happens on your device — your data "
                        "never leaves your machine.",
                        font_size="0.9375rem",
                        color="var(--gray-11)",
                        line_height="1.7",
                    ),
                    rx.hstack(
                        rx.link(
                            rx.button(
                                rx.icon("github", size=16),
                                "GitHub",
                                variant="soft",
                                size="2",
                            ),
                            href="https://github.com/Buddhilive/buddhi-ai-server",
                            is_external=True,
                        ),
                        rx.link(
                            rx.button(
                                rx.icon("book-open", size=16),
                                "Reflex Docs",
                                variant="ghost",
                                size="2",
                            ),
                            href="https://reflex.dev/docs/",
                            is_external=True,
                        ),
                        spacing="3",
                    ),
                    spacing="4",
                    align="start",
                ),
                padding="24px",
                border_radius="12px",
                background="var(--color-panel-solid)",
                border="1px solid var(--gray-4)",
                width="100%",
            ),
            spacing="6",
            align="start",
            width="100%",
        ),
        padding="32px",
        max_width="720px",
        margin="0 auto",
        width="100%",
    )


def about() -> rx.Component:
    """About page wrapped with the shared application layout."""
    return layout(_about_content())
