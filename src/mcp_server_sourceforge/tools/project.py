"""
Project Management Tools for SourceForge MCP Server
===================================================
Tools to inspect, configure, and manage project metadata, descriptions, and icons.
"""

from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..client import SourceForgeClient


def register_project_tools(mcp: FastMCP):
    """Register project metadata, overview, and icon tools."""

    @mcp.tool()
    async def sourceforge_get_project(project_name: str) -> Dict[str, Any]:
        """
        Fetch public metadata, summary, description, and registered tools for a SourceForge project.

        Args:
            project_name: The UNIX slug of the project (e.g. 'revenant-os').
        """
        client = SourceForgeClient()
        return await client.get_project_rest(project_name)

    @mcp.tool()
    async def sourceforge_update_project_metadata(
        project_name: str,
        name: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        external_homepage: Optional[str] = None,
        support_page: Optional[str] = None,
        video_url: Optional[str] = None,
        twitter_handle: Optional[str] = None,
        facebook_page: Optional[str] = None,
        session_cookie: Optional[str] = None,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """
        Update project overview, short summary, full markdown description, and links.

        Requires admin session credentials (set SOURCEFORGE_SESSION_COOKIE environment variable
        or pass session_cookie).

        Args:
            project_name: The UNIX name of the project.
            name: Optional new display title for the project.
            summary: Short summary statement (70 characters or less recommended by SourceForge for search previews).
            description: Detailed project description (supports Markdown).
            external_homepage: Optional URL to external project website.
            support_page: Optional URL or tool name for community support.
            video_url: Optional YouTube/video demo URL.
            twitter_handle: Optional X/Twitter handle.
            facebook_page: Optional Facebook page URL.
            session_cookie: Optional admin session cookie if not set in environment.
            use_browser: Whether to force browser automation (Playwright/CDP) to bypass Cloudflare challenges.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.update_project_metadata(
            project_name=project_name,
            name=name,
            summary=summary,
            short_description=description,
            external_homepage=external_homepage,
            support_page=support_page,
            video_url=video_url,
            twitter_handle=twitter_handle,
            facebook_page=facebook_page,
            use_browser=use_browser,
        )

    @mcp.tool()
    async def sourceforge_upload_icon(
        project_name: str,
        local_icon_path: str,
        session_cookie: Optional[str] = None,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """
        Upload a custom logo or icon for the SourceForge project (displayed in directories and headers).

        Args:
            project_name: The UNIX project name.
            local_icon_path: Local filesystem path to the icon image (PNG, JPG, SVG).
            session_cookie: Optional admin session cookie if not set in environment.
            use_browser: Whether to force browser automation (Playwright/CDP) to bypass Cloudflare challenges.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.upload_icon(project_name, local_icon_path, use_browser=use_browser)

    @mcp.tool()
    async def sourceforge_delete_icon(
        project_name: str,
        session_cookie: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove the custom logo/icon from a SourceForge project, reverting to default.

        Args:
            project_name: The UNIX project name.
            session_cookie: Optional admin session cookie if not set in environment.
        """
        client = SourceForgeClient(session_cookie=session_cookie)
        return await client.delete_icon(project_name)

    @mcp.tool()
    async def sourceforge_create_project_guide(
        unix_name: str,
        display_name: str,
        summary: str,
        description: str,
        license_name: str = "MIT",
    ) -> Dict[str, Any]:
        """
        Provide structured configuration, registration link, and automated checklist
        for launching a new project on SourceForge.

        Args:
            unix_name: The desired unique UNIX slug (e.g. 'my-awesome-tool').
            display_name: Full human-readable project title.
            summary: Short tagline (<= 70 characters).
            description: Full markdown description of the project.
            license_name: Open source license (e.g. 'MIT', 'GPLv3', 'Apache 2.0').
        """
        return {
            "registration_url": "https://sourceforge.net/p/add_project",
            "suggested_config": {
                "unix_name": unix_name,
                "display_name": display_name,
                "summary": summary[:70],
                "description": description,
                "license": license_name,
                "default_tools": ["files", "wiki", "git", "discussion", "tickets"],
            },
            "next_steps": [
                f"1. Register '{unix_name}' on https://sourceforge.net/p/add_project using your SourceForge account.",
                "2. Upload your project logo using `sourceforge_upload_icon`.",
                "3. Upload screenshots of your application using `sourceforge_upload_screenshot`.",
                "4. Upload release binaries/ISOs using `sourceforge_upload_file`.",
                "5. Set default platform downloads using `sourceforge_set_default_release`.",
                "6. Publish initial documentation with `sourceforge_update_wiki_page`."
            ]
        }
