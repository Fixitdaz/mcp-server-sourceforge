#!/usr/bin/env python3
"""
SourceForge MCP Server
======================
Model Context Protocol (MCP) server providing AI agents with full lifecycle
capabilities for SourceForge:
- Project metadata, taglines, and markdown descriptions
- Icon and logo uploading / removal
- Screenshot gallery management (upload, caption, delete)
- SFTP file uploads to the File Release System (FRS)
- Release API automation (default downloads per platform, download labels)
- Wiki and documentation authoring
- Download analytics and geographical statistics
"""

import logging
from mcp.server.fastmcp import FastMCP

from .tools.project import register_project_tools
from .tools.screenshots import register_screenshot_tools
from .tools.releases import register_release_tools
from .tools.docs import register_doc_tools
from .tools.stats import register_stats_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-server-sourceforge")

# Initialize FastMCP Server
mcp = FastMCP("sourceforge")

# Register modular toolsets
register_project_tools(mcp)
register_screenshot_tools(mcp)
register_release_tools(mcp)
register_doc_tools(mcp)
register_stats_tools(mcp)


def main():
    """Run the SourceForge MCP server."""
    logger.info("Starting SourceForge MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
