#!/usr/bin/env python3
"""
SourceForge MCP Server
======================
Model Context Protocol server for interacting with SourceForge:
- Inspect project details and metadata via Allura REST API
- Query download statistics and geographic analytics
- Upload releases and files via SFTP to the File Release System (FRS)
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
import httpx
import paramiko
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-server-sourceforge")

# Initialize FastMCP Server
mcp = FastMCP("sourceforge")

SF_API_BASE = "https://sourceforge.net/rest/p"
SF_STATS_BASE = "https://sourceforge.net/projects"
SF_FRS_HOST = "frs.sourceforge.net"
SF_FRS_PORT = 22


@mcp.tool()
async def sourceforge_get_project(project_name: str) -> Dict[str, Any]:
    """
    Fetch public metadata, description, summary, and tools for a SourceForge project.

    Args:
        project_name: The UNIX name / slug of the project (e.g. 'revenant-os').
    """
    url = f"{SF_API_BASE}/{project_name}"
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            return {"error": f"Project '{project_name}' not found on SourceForge."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def sourceforge_get_download_stats(
    project_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve real-time download statistics and geographic breakdown for a project.

    Args:
        project_name: The UNIX name / slug of the project (e.g. 'revenant-os').
        start_date: Optional ISO start date (YYYY-MM-DD). Defaults to the past 7 days.
        end_date: Optional ISO end date (YYYY-MM-DD). Defaults to today.
    """
    url = f"{SF_STATS_BASE}/{project_name}/files/stats/json"
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, params=params)
        if response.status_code == 404:
            return {"error": f"Stats not found or unavailable for '{project_name}'."}
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def sourceforge_list_files(project_name: str) -> Dict[str, Any]:
    """
    Retrieve file releases and folder trees for a SourceForge project.

    Args:
        project_name: The UNIX name / slug of the project (e.g. 'revenant-os').
    """
    url = f"{SF_STATS_BASE}/{project_name}/files/stats/json"
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            return {"error": f"Files list not available for '{project_name}'."}
        response.raise_for_status()
        data = response.json()
        downloads = data.get("downloads", [])
        return {
            "project": project_name,
            "total_downloads": data.get("total", 0),
            "releases": [item[0] for item in downloads if len(item) > 0]
        }


@mcp.tool()
def sourceforge_upload_file(
    username: str,
    project_name: str,
    local_file_path: str,
    remote_folder: Optional[str] = None,
    ssh_key_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload an ISO, binary, or release artifact to SourceForge File Release System (FRS) via SFTP.

    Args:
        username: Your SourceForge username.
        project_name: The UNIX project name (e.g. 'revenant-os').
        local_file_path: Absolute or relative path to the local file to upload.
        remote_folder: Optional subfolder on SourceForge (e.g. 'v1.1-Build18.3').
        ssh_key_path: Optional path to an SSH private key (defaults to ~/.ssh/id_ed25519 or id_rsa).
    """
    if not os.path.isfile(local_file_path):
        return {"error": f"Local file not found: {local_file_path}"}

    filename = os.path.basename(local_file_path)
    file_size = os.path.getsize(local_file_path)

    base_remote_path = f"/home/frs/project/{project_name}"
    target_dir = f"{base_remote_path}/{remote_folder}" if remote_folder else base_remote_path
    target_file = f"{target_dir}/{filename}"

    # Auto-discover SSH key if not specified
    if not ssh_key_path:
        home = os.path.expanduser("~")
        for candidate in [
            os.path.join(home, ".ssh", "id_ed25519"),
            os.path.join(home, ".ssh", "id_rsa")
        ]:
            if os.path.isfile(candidate):
                ssh_key_path = candidate
                break

    try:
        transport = paramiko.Transport((SF_FRS_HOST, SF_FRS_PORT))
        if ssh_key_path:
            try:
                pkey = paramiko.Ed25519Key.from_private_key_file(ssh_key_path)
            except Exception:
                pkey = paramiko.RSAKey.from_private_key_file(ssh_key_path)
            transport.connect(username=username, pkey=pkey)
        else:
            transport.connect(username=username)

        sftp = paramiko.SFTPClient.from_transport(transport)

        # Ensure target directory exists
        if remote_folder:
            try:
                sftp.stat(target_dir)
            except IOError:
                sftp.mkdir(target_dir)

        # Upload with progress logging
        logger.info(f"Uploading {local_file_path} ({file_size} bytes) -> {target_file}")
        sftp.put(local_file_path, target_file)
        sftp.close()
        transport.close()

        download_url = f"https://sourceforge.net/projects/{project_name}/files/{remote_folder + '/' if remote_folder else ''}{filename}/download"
        return {
            "success": True,
            "project": project_name,
            "filename": filename,
            "bytes_uploaded": file_size,
            "destination": target_file,
            "download_url": download_url
        }
    except Exception as exc:
        logger.exception("Upload failed")
        return {"success": False, "error": str(exc)}


def main():
    """Run the SourceForge MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
