"""
Tests for SourceForge Browser Automation and Cloudflare Fallback
"""

import os
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from mcp_server_sourceforge.browser import SourceForgeBrowser, is_playwright_available
from mcp_server_sourceforge.client import SourceForgeClient


class TestSourceForgeBrowser(unittest.IsolatedAsyncioTestCase):
    def test_browser_init(self):
        browser = SourceForgeBrowser(
            session_cookie="session=test_jwt_cookie_123",
            cdp_url="http://localhost:9222",
            headless=True,
        )
        self.assertEqual(browser.session_cookie, "session=test_jwt_cookie_123")
        self.assertEqual(browser.cdp_url, "http://localhost:9222")
        self.assertTrue(browser.headless)

    def test_cookie_parsing(self):
        browser = SourceForgeBrowser(
            session_cookie="foo=bar; session=my_token; _csrf_token=csrf123"
        )
        cookies = browser._parse_cookies()
        self.assertEqual(len(cookies), 3)
        names = [c["name"] for c in cookies]
        self.assertIn("foo", names)
        self.assertIn("session", names)
        self.assertIn("_csrf_token", names)
        for c in cookies:
            self.assertEqual(c["domain"], ".sourceforge.net")
            self.assertEqual(c["path"], "/")

    async def test_update_when_playwright_not_installed(self):
        browser = SourceForgeBrowser(session_cookie="test")
        with patch("mcp_server_sourceforge.browser.is_playwright_available", return_value=False):
            res = await browser.update_project_overview("test-proj", name="Test")
            self.assertFalse(res["success"])
            self.assertIn("Playwright is not installed", res["error"])

    async def test_upload_screenshot_missing_file(self):
        browser = SourceForgeBrowser(session_cookie="test")
        with patch("mcp_server_sourceforge.browser.is_playwright_available", return_value=True):
            res = await browser.upload_screenshot("test-proj", "non_existent_img.png")
            self.assertFalse(res["success"])
            self.assertIn("does not exist", res["error"])

    async def test_client_browser_fallback_on_403(self):
        client = SourceForgeClient(session_cookie="session=test_session")
        
        # Mock get_csrf_token to raise PermissionError (representing 403 Cloudflare challenge)
        with patch.object(
            client,
            "get_csrf_token",
            side_effect=PermissionError("Access denied to overview. 403 Forbidden")
        ):
            # When playwright is not installed
            with patch("mcp_server_sourceforge.client.is_playwright_available", return_value=False):
                res = await client.update_project_metadata("myproj", name="New Name")
                self.assertFalse(res["success"])
                self.assertIn("Cloudflare Turnstile challenge detected", res["error"])
                self.assertIn("mcp-server-sourceforge[browser]", res["error"])

            # When playwright is installed / browser fallback enabled
            with patch("mcp_server_sourceforge.client.is_playwright_available", return_value=True):
                mock_browser_instance = MagicMock()
                mock_browser_instance.update_project_overview = AsyncMock(
                    return_value={"success": True, "message": "Updated via browser automation"}
                )
                with patch(
                    "mcp_server_sourceforge.client.SourceForgeBrowser",
                    return_value=mock_browser_instance
                ):
                    res = await client.update_project_metadata("myproj", name="New Name")
                    self.assertTrue(res["success"])
                    self.assertEqual(res["message"], "Updated via browser automation")


if __name__ == "__main__":
    unittest.main()
