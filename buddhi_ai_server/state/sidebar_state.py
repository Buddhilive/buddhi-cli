"""
Sidebar state management for Buddhi AI Server.

Tracks whether the sidebar is collapsed or expanded, and whether the
viewport is in mobile mode. Mobile detection uses ``rx.call_script`` to
read ``window.innerWidth`` from the browser and call ``set_mobile`` with
the result.
"""

import reflex as rx


# Width constants exposed as module-level vars for use in components.
SIDEBAR_EXPANDED_WIDTH = "240px"
SIDEBAR_COLLAPSED_WIDTH = "68px"
MOBILE_BREAKPOINT = 768  # pixels


class SidebarState(rx.State):
    """Global sidebar UI state shared across all pages."""

    # Whether the sidebar is currently collapsed to icon-only rail.
    is_collapsed: bool = False

    # Whether the current viewport is considered mobile width.
    # Set by check_mobile which reads window.innerWidth via rx.call_script.
    is_mobile: bool = False

    def toggle_sidebar(self) -> None:
        """Toggle between expanded and collapsed sidebar."""
        self.is_collapsed = not self.is_collapsed

    def set_mobile(self, is_mobile: bool) -> None:
        """
        Update mobile state from the client-side JS measurement.

        Args:
            is_mobile: True when viewport width is below MOBILE_BREAKPOINT.
        """
        self.is_mobile = is_mobile
        # On mobile, always collapse sidebar to avoid covering main content.
        if is_mobile:
            self.is_collapsed = True

    def check_mobile(self) -> rx.Component:  # type: ignore[return]
        """
        Fire a JS expression that reads ``window.innerWidth`` and calls
        ``SidebarState.set_mobile`` with the result.

        This is triggered via ``on_mount`` in the layout template and also
        wired to a ``window.onresize`` listener (see layout.py).
        """
        return rx.call_script(
            f"window.innerWidth < {MOBILE_BREAKPOINT}",
            callback=SidebarState.set_mobile,
        )

    def collapse_on_navigate(self) -> None:
        """Collapse sidebar when a nav item is clicked on mobile."""
        if self.is_mobile:
            self.is_collapsed = True

    @rx.var
    def sidebar_width(self) -> str:
        """Return the current pixel width of the sidebar."""
        return (
            SIDEBAR_COLLAPSED_WIDTH
            if self.is_collapsed
            else SIDEBAR_EXPANDED_WIDTH
        )
