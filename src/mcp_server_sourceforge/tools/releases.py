"""
Release & File Management Tools for SourceForge MCP Server
==========================================================
Tools to upload release packages via SFTP, list directories, create folders,
and configure default platform downloads via the SourceForge Release API.
"""

from typing import Optional, Dict, Any, List
import httpx
from mcp.server.fastmcp import FastMCP
from ..sftp import SourceForgeSFTP
from ..client import SourceForgeClient, SF_STATS_BASE


def register_release_tools(mcp: FastMCP):
    """Register file release and FRS management tools."""

    @mcp.tool()
    def sourceforge_upload_file(
        username: str,
        project_name: str,
        local_file_path: str,
        remote_folder: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload an ISO, binary, installer, or release archive to SourceForge File Release System (FRS) via SFTP.

        Uses auto-discovered SSH keys (~/.ssh/id_ed25519, id_rsa) or an explicit key path.

        Args:
            username: Your SourceForge username.
            project_name: The UNIX project name (e.g. 'revenant-os').
            local_file_path: Absolute or relative path to the local file to upload.
            remote_folder: Optional release subfolder (e.g. 'v1.0.0' or 'latest').
            ssh_key_path: Optional path to SSH private key.
        """
        sftp_mgr = SourceForgeSFTP(username=username, ssh_key_path=ssh_key_path)
        return sftp_mgr.upload_file(
            project_name=project_name,
            local_file_path=local_file_path,
            remote_folder=remote_folder,
        )

    @mcp.tool()
    def sourceforge_create_release_folder(
        username: str,
        project_name: str,
        folder_path: str,
        ssh_key_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a directory or nested release folder structure in the SourceForge FRS file system.

        Args:
            username: Your SourceForge username.
            project_name: The UNIX project name.
            folder_path: Folder name or nested path to create (e.g. 'v2.0/packages').
            ssh_key_path: Optional path to SSH private key.
        """
        sftp_mgr = SourceForgeSFTP(username=username, ssh_key_path=ssh_key_path)
        return sftp_mgr.create_folder(
            project_name=project_name,
            folder_path=folder_path,
        )

    @mcp.tool()
    async def sourceforge_list_files(project_name: str) -> Dict[str, Any]:
        """
        Retrieve released files, total downloads, and directory listings for a SourceForge project.

        Args:
            project_name: The UNIX slug of the project.
        """
        client = SourceForgeClient()
        data = await client.get_download_stats(project_name)
        if "error" in data:
            return data

        downloads = data.get("downloads", [])
        return {
            "project": project_name,
            "total_downloads": data.get("total", 0),
            "releases": [item[0] for item in downloads if len(item) > 0],
        }

    @mcp.tool()
    async def sourceforge_set_default_release(
        project_name: str,
        file_path: str,
        default_platforms: List[str],
        download_label: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set a file as the default download for specific platforms using the official SourceForge Release API.

        Requires your SourceForge Releases API Key (set SOURCEFORGE_API_KEY environment variable
        or pass api_key parameter).

        Args:
            project_name: The UNIX slug of the project.
            file_path: Path of the file relative to the project files root (e.g. 'v1.0.0/app-installer.exe').
            default_platforms: Target OS list. Allowed items: 'windows', 'mac', 'linux', 'bsd', 'solaris', 'others'.
            download_label: Optional custom text on the green Download button (e.g. 'Download for Windows').
            api_key: Optional SourceForge Releases API Key if not set in environment.
        """
        client = SourceForgeClient(api_key=api_key)
        return await client.set_default_release(
            project_name=project_name,
            file_path=file_path,
            default_platforms=default_platforms,
            download_label=download_label,
            api_key=api_key,
        )
