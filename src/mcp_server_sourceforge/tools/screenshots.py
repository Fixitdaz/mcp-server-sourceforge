"""
Screenshot Management Tools for SourceForge MCP Server
======================================================
Tools to list, upload, edit captions, and delete project screenshots.
"""

from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..client import SourceForgeClient


def register_screenshot_tools(mcp: FastMCP):
    """Register screenshot management tools."""

    @mcp.tool()
    async def sourceforge_list_screenshots(
        project_name: str,
        session_cookie: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List all screenshots uploaded for a SourceForge project, including their IDs, URLs, and captions.

        Args:
            project_name: The UNIX slug of the project.
            session_cookie: Optional admin session cookie. If omitted, public screenshots are fetched.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.list_screenshots(project_name)

    @mcp.tool()
    async def sourceforge_upload_screenshot(
        project_name: str,
        local_image_path: str,
        caption: Optional[str] = None,
        session_cookie: Optional[str] = None,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """
        Upload a screenshot image to a SourceForge project (up to 6 total allowed per project).

        Requires admin session credentials (SOURCEFORGE_SESSION_COOKIE or session_cookie).

        Args:
            project_name: The UNIX slug of the project.
            local_image_path: Absolute or relative local path to the image (PNG/JPEG/WEBP).
            caption: Optional descriptive caption to display beneath the screenshot.
            session_cookie: Optional admin session cookie if not set in environment.
            use_browser: Whether to force browser automation (Playwright/CDP) to bypass Cloudflare challenges.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.upload_screenshot(
            project_name=project_name,
            local_image_path=local_image_path,
            caption=caption,
            use_browser=use_browser,
        )

    @mcp.tool()
    async def sourceforge_edit_screenshot(
        project_name: str,
        screenshot_id: str,
        caption: str,
        session_cookie: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the caption of an existing project screenshot.

        Args:
            project_name: The UNIX slug of the project.
            screenshot_id: The ID of the screenshot (obtained from sourceforge_list_screenshots).
            caption: The new caption text.
            session_cookie: Optional admin session cookie if not set in environment.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.edit_screenshot(
            project_name=project_name,
            screenshot_id=screenshot_id,
            caption=caption,
        )

    @mcp.tool()
    async def sourceforge_delete_screenshot(
        project_name: str,
        screenshot_id: str,
        session_cookie: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete a screenshot from the project's summary gallery.

        Args:
            project_name: The UNIX slug of the project.
            screenshot_id: The ID of the screenshot (obtained from sourceforge_list_screenshots).
            session_cookie: Optional admin session cookie if not set in environment.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.delete_screenshot(
            project_name=project_name,
            screenshot_id=screenshot_id,
        )
