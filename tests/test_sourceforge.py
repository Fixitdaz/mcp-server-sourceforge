"""
Unit & Integration Tests for SourceForge MCP Server
"""

import os
import unittest
from unittest.mock import patch

from mcp_server_sourceforge.client import SourceForgeClient
from mcp_server_sourceforge.sftp import SourceForgeSFTP
from mcp_server_sourceforge.tools.project import register_project_tools
from mcp_server_sourceforge.tools.releases import register_release_tools
from mcp.server.fastmcp import FastMCP


class TestSourceForgeClient(unittest.IsolatedAsyncioTestCase):
    def test_client_init_and_headers(self):
        client = SourceForgeClient(
            bearer_token="test_bearer_123",
            session_cookie="session=testcookie123",
            api_key="test_api_key_456"
        )
        self.assertEqual(client.bearer_token, "test_bearer_123")
        self.assertEqual(client.api_key, "test_api_key_456")

        headers = client._get_headers(auth_type="bearer")
        self.assertEqual(headers["Authorization"], "Bearer test_bearer_123")
        self.assertEqual(headers["Accept"], "application/json")

        cookies = client._get_cookies()
        self.assertEqual(cookies.get("session"), "testcookie123")

    def test_cookie_string_parsing(self):
        client = SourceForgeClient(session_cookie="foo=bar; baz=qux; session=my_session")
        cookies = client._get_cookies()
        self.assertEqual(cookies["foo"], "bar")
        self.assertEqual(cookies["baz"], "qux")
        self.assertEqual(cookies["session"], "my_session")

    async def test_set_default_release_missing_key(self):
        client = SourceForgeClient(api_key=None)
        res = await client.set_default_release("myproj", "v1/app.exe", ["windows"])
        self.assertFalse(res["success"])
        self.assertIn("requires a Releases API Key", res["error"])

    async def test_update_metadata_missing_session(self):
        client = SourceForgeClient(session_cookie=None)
        res = await client.update_project_metadata("myproj", name="New Name")
        self.assertFalse(res["success"])
        self.assertIn("requires SOURCEFORGE_SESSION_COOKIE", res["error"])

    async def test_upload_icon_missing_file(self):
        client = SourceForgeClient(session_cookie="dummy")
        res = await client.upload_icon("myproj", "non_existent_file_12345.png")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])


class TestSourceForgeSFTP(unittest.TestCase):
    def test_sftp_missing_username(self):
        sftp = SourceForgeSFTP(username=None)
        with patch.dict(os.environ, {}, clear=True):
            # Pass __file__ so local file check passes, triggering connection attempt
            res = sftp.upload_file("myproj", __file__)
            self.assertFalse(res["success"])
            self.assertIn("SFTP connection failed", res["error"])

    def test_sftp_nonexistent_local_file(self):
        sftp = SourceForgeSFTP(username="testuser")
        res = sftp.upload_file("myproj", "does_not_exist.tar.gz")
        self.assertFalse(res["success"])
        self.assertIn("Local file not found", res["error"])


class TestToolsRegistration(unittest.TestCase):
    def test_fastmcp_registration(self):
        mcp = FastMCP("test_sf")
        register_project_tools(mcp)
        register_release_tools(mcp)

        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        self.assertIn("sourceforge_get_project", tool_names)
        self.assertIn("sourceforge_update_project_metadata", tool_names)
        self.assertIn("sourceforge_upload_icon", tool_names)
        self.assertIn("sourceforge_create_project_guide", tool_names)
        self.assertIn("sourceforge_upload_file", tool_names)
        self.assertIn("sourceforge_set_default_release", tool_names)


if __name__ == "__main__":
    unittest.main()
