"""
SourceForge FRS SFTP Manager
============================
Handles authenticated SFTP connections to frs.sourceforge.net for:
- Uploading release binaries, packages, ISOs without file size limits
- Creating directory trees in the File Release System (FRS)
- Listing remote files and directories
"""

import os
import stat
import logging
from typing import Optional, Dict, Any, List, Tuple
import paramiko

logger = logging.getLogger("mcp-server-sourceforge.sftp")

SF_FRS_HOST = "frs.sourceforge.net"
SF_FRS_PORT = 22


def discover_ssh_key() -> Optional[str]:
    """Auto-discover user SSH private key in ~/.ssh."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".ssh", "id_ed25519"),
        os.path.join(home, ".ssh", "id_rsa"),
        os.path.join(home, ".ssh", "id_ecdsa"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def get_private_key(key_path: str):
    """Attempt to load private key using various Paramiko key classes."""
    for key_cls in [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey]:
        try:
            return key_cls.from_private_key_file(key_path)
        except Exception:
            continue
    raise ValueError(f"Could not load SSH private key from '{key_path}'. Ensure it is a valid format (Ed25519/RSA/ECDSA).")


class SourceForgeSFTP:
    """Manages SFTP interactions with SourceForge File Release System."""

    def __init__(
        self,
        username: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.username = username or os.environ.get("SOURCEFORGE_USERNAME")
        self.ssh_key_path = ssh_key_path or os.environ.get("SOURCEFORGE_SSH_KEY_PATH") or discover_ssh_key()
        self.password = password or os.environ.get("SOURCEFORGE_PASSWORD")

    def _connect(self) -> Tuple[paramiko.Transport, paramiko.SFTPClient]:
        if not self.username:
            raise ValueError("SourceForge username is required. Set SOURCEFORGE_USERNAME or pass 'username'.")

        transport = paramiko.Transport((SF_FRS_HOST, SF_FRS_PORT))
        if self.ssh_key_path and os.path.isfile(self.ssh_key_path):
            pkey = get_private_key(self.ssh_key_path)
            transport.connect(username=self.username, pkey=pkey)
        elif self.password:
            transport.connect(username=self.username, password=self.password)
        else:
            # Attempt agent / default connection
            transport.connect(username=self.username)

        sftp = paramiko.SFTPClient.from_transport(transport)
        return transport, sftp

    def ensure_remote_dir(self, sftp: paramiko.SFTPClient, remote_dir: str):
        """Recursively ensure a directory exists on the remote SFTP server."""
        dirs_to_create = []
        current = remote_dir.replace("\\", "/")
        while current and current != "/":
            try:
                sftp.stat(current)
                break
            except IOError:
                dirs_to_create.append(current)
                current = os.path.dirname(current)

        while dirs_to_create:
            target = dirs_to_create.pop()
            try:
                sftp.mkdir(target)
            except IOError as e:
                logger.debug(f"mkdir {target} ignored: {e}")

    def upload_file(
        self,
        project_name: str,
        local_file_path: str,
        remote_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to SourceForge File Release System (FRS)."""
        if not os.path.isfile(local_file_path):
            return {"success": False, "error": f"Local file not found: {local_file_path}"}

        filename = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)

        base_remote_path = f"/home/frs/project/{project_name}"
        clean_folder = remote_folder.strip("/\\") if remote_folder else ""
        target_dir = f"{base_remote_path}/{clean_folder}" if clean_folder else base_remote_path
        target_file = f"{target_dir}/{filename}"

        try:
            transport, sftp = self._connect()
        except Exception as e:
            return {"success": False, "error": f"SFTP connection failed: {str(e)}"}

        try:
            if clean_folder:
                self.ensure_remote_dir(sftp, target_dir)

            logger.info(f"Uploading {local_file_path} ({file_size} bytes) -> {target_file}")
            sftp.put(local_file_path, target_file)

            download_subpath = f"{clean_folder}/" if clean_folder else ""
            download_url = f"https://sourceforge.net/projects/{project_name}/files/{download_subpath}{filename}/download"

            return {
                "success": True,
                "project": project_name,
                "filename": filename,
                "bytes_uploaded": file_size,
                "destination": target_file,
                "download_url": download_url,
                "rel_path": f"{download_subpath}{filename}"
            }
        except Exception as exc:
            logger.exception("SFTP upload failed")
            return {"success": False, "error": str(exc)}
        finally:
            sftp.close()
            transport.close()

    def create_folder(self, project_name: str, folder_path: str) -> Dict[str, Any]:
        """Create a folder within the project's FRS directory."""
        clean_path = folder_path.strip("/\\")
        target_dir = f"/home/frs/project/{project_name}/{clean_path}"

        try:
            transport, sftp = self._connect()
        except Exception as e:
            return {"success": False, "error": f"SFTP connection failed: {str(e)}"}

        try:
            self.ensure_remote_dir(sftp, target_dir)
            return {
                "success": True,
                "project": project_name,
                "created_folder": clean_path,
                "remote_path": target_dir,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            sftp.close()
            transport.close()

    def list_remote_files(self, project_name: str, remote_folder: Optional[str] = None) -> Dict[str, Any]:
        """List files and directories in the project's FRS directory."""
        base_remote_path = f"/home/frs/project/{project_name}"
        clean_folder = remote_folder.strip("/\\") if remote_folder else ""
        target_dir = f"{base_remote_path}/{clean_folder}" if clean_folder else base_remote_path

        try:
            transport, sftp = self._connect()
        except Exception as e:
            return {"success": False, "error": f"SFTP connection failed: {str(e)}"}

        try:
            items = []
            for attr in sftp.listdir_attr(target_dir):
                is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                items.append({
                    "name": attr.filename,
                    "is_directory": is_dir,
                    "size": attr.st_size if not is_dir else 0,
                    "modified": attr.st_mtime,
                })
            return {
                "success": True,
                "project": project_name,
                "folder": clean_folder,
                "items": items
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            sftp.close()
            transport.close()
