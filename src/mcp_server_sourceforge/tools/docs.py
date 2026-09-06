"""
Documentation & Wiki Tools for SourceForge MCP Server
=====================================================
Tools to inspect, create, and update wiki documentation pages with Markdown.
"""

from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..client import SourceForgeClient


def register_doc_tools(mcp: FastMCP):
    """Register wiki documentation tools."""

    @mcp.tool()
    async def sourceforge_get_wiki_page(
        project_name: str,
        page_name: str = "Home",
        wiki_mount: str = "wiki",
        bearer_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch the markdown content and metadata of a project wiki or documentation page.

        Args:
            project_name: The UNIX slug of the project.
            page_name: Name/slug of the wiki page (defaults to 'Home').
            wiki_mount: Tool mount point for the wiki (defaults to 'wiki').
            bearer_token: Optional OAuth/Bearer token for private pages.
        """
        client = SourceForgeClient(bearer_token=bearer_token)
        return await client.get_wiki_page(
            project_name=project_name,
            page_name=page_name,
            wiki_mount=wiki_mount,
        )

    @mcp.tool()
    async def sourceforge_update_wiki_page(
        project_name: str,
        page_name: str,
        text: str,
        labels: Optional[str] = None,
        wiki_mount: str = "wiki",
        bearer_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a wiki documentation page with Markdown text.

        Requires an Allura Bearer token (set SOURCEFORGE_BEARER_TOKEN or pass bearer_token).

        Args:
            project_name: The UNIX slug of the project.
            page_name: Name of the wiki page to create/edit (e.g. 'Home' or 'Installation').
            text: Full Markdown content of the page.
            labels: Optional comma-separated tags or labels.
            wiki_mount: Tool mount point for the wiki (defaults to 'wiki').
            bearer_token: Optional OAuth/Bearer token if not set in environment.
        """
        client = SourceForgeClient(bearer_token=bearer_token)
        return await client.update_wiki_page(
            project_name=project_name,
            page_name=page_name,
            text=text,
            labels=labels,
            wiki_mount=wiki_mount,
        )
