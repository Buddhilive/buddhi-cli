"""
Settings page stub for Buddhi AI Server.

Demonstrates that the shared layout persists across routes.
"""

from __future__ import annotations

import reflex as rx

from buddhi_ai_server.templates.layout import layout


def _settings_section(
    icon: str,
    title: str,
    description: str,
    control: rx.Component,
) -> rx.Component:
    """A single settings row with label and a control on the right."""
    return rx.hstack(
        rx.hstack(
            rx.icon(icon, size=18, color="var(--gray-10)", flex_shrink="0"),
            rx.vstack(
                rx.text(title, font_size="0.9rem", font_weight="500", color="var(--gray-12)"),
                rx.text(description, font_size="0.8125rem", color="var(--gray-10)"),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="start",
        ),
        rx.spacer(),
        control,
        align="center",
        width="100%",
        padding_y="16px",
    )


def _settings_content() -> rx.Component:
    """Inner content for the Settings page."""
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.heading("Settings", size="7", font_weight="700", color="var(--gray-12)"),
                rx.text(
                    "Manage your application preferences.",
                    font_size="0.9375rem",
                    color="var(--gray-10)",
                ),
                spacing="1",
                align="start",
            ),
            rx.divider(border_color="var(--gray-4)"),

            # Appearance section
            rx.box(
                rx.text(
                    "Appearance",
                    font_size="0.8125rem",
                    font_weight="600",
                    color="var(--gray-9)",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                    padding_bottom="8px",
                ),
                rx.box(
                    _settings_section(
                        "sun-moon",
                        "Theme",
                        "Switch between light and dark interface.",
                        rx.color_mode.button(
                            variant="soft",
                            size="2",
                            cursor="pointer",
                        ),
                    ),
                    rx.divider(border_color="var(--gray-3)"),
                    _settings_section(
                        "layout-panel-left",
                        "Sidebar default",
                        "Choose whether the sidebar starts expanded or collapsed.",
                        rx.select(
                            ["Expanded", "Collapsed"],
                            default_value="Expanded",
                            size="2",
                        ),
                    ),
                    padding_x="20px",
                    border_radius="12px",
                    background="var(--color-panel-solid)",
                    border="1px solid var(--gray-4)",
                ),
                width="100%",
            ),

            rx.box(
                rx.text(
                    "About",
                    font_size="0.8125rem",
                    font_weight="600",
                    color="var(--gray-9)",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                    padding_bottom="8px",
                ),
                rx.box(
                    _settings_section(
                        "tag",
                        "Version",
                        "Current application version.",
                        rx.badge("0.1.0", variant="soft", color_scheme="blue"),
                    ),
                    rx.divider(border_color="var(--gray-3)"),
                    _settings_section(
                        "github",
                        "Source code",
                        "View and contribute on GitHub.",
                        rx.link(
                            rx.button(
                                rx.icon("external-link", size=14),
                                "GitHub",
                                variant="ghost",
                                size="2",
                            ),
                            href="https://github.com/Buddhilive/buddhi-ai-server",
                            is_external=True,
                        ),
                    ),
                    padding_x="20px",
                    border_radius="12px",
                    background="var(--color-panel-solid)",
                    border="1px solid var(--gray-4)",
                ),
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


def settings() -> rx.Component:
    """Settings page wrapped with the shared application layout."""
    return layout(_settings_content())
