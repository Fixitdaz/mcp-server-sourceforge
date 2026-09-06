"""
Statistics & Analytics Tools for SourceForge MCP Server
=======================================================
Tools to retrieve project download metrics and geographic distributions.
"""

from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..client import SourceForgeClient


def register_stats_tools(mcp: FastMCP):
    """Register statistics tools."""

    @mcp.tool()
    async def sourceforge_get_download_stats(
        project_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve download statistics and country breakdowns for a SourceForge project.

        Args:
            project_name: The UNIX slug of the project (e.g. 'revenant-os').
            start_date: Optional start date in YYYY-MM-DD format (defaults to past 7 days).
            end_date: Optional end date in YYYY-MM-DD format (defaults to current date).
        """
        client = SourceForgeClient()
        return await client.get_download_stats(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
        )
