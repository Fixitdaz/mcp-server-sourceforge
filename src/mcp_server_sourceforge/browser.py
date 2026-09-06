"""
SourceForge Browser Automation Engine
======================================
Provides autonomous browser automation (via Playwright and CDP) to handle
Cloudflare Turnstile challenges on SourceForge web admin forms (/admin/overview, /admin/screenshots).
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("mcp-server-sourceforge.browser")

def is_playwright_available() -> bool:
    """Check if Playwright is installed and importable."""
    try:
        import playwright.async_api  # noqa: F401
        return True
    except ImportError:
        return False


class SourceForgeBrowser:
    """
    Automates SourceForge web interactions using Playwright or CDP (Chrome DevTools Protocol).
    Bypasses Cloudflare Turnstile challenges and automates admin form updates.
    """

    def __init__(
        self,
        session_cookie: Optional[str] = None,
        cdp_url: Optional[str] = None,
        headless: bool = True,
        timeout: float = 30000.0,
    ):
        self.session_cookie = session_cookie or os.environ.get("SOURCEFORGE_SESSION_COOKIE")
        self.cdp_url = cdp_url or os.environ.get("SOURCEFORGE_CDP_URL")
        self.headless = headless
        self.timeout = timeout

    def _parse_cookies(self) -> List[Dict[str, Any]]:
        """Parse cookie string into Playwright cookie objects."""
        cookies = []
        if not self.session_cookie:
            return cookies

        raw_parts = self.session_cookie.split(";") if ";" in self.session_cookie else [self.session_cookie]
        for part in raw_parts:
            part = part.strip()
            if "=" in part:
                name, val = part.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": val.strip(),
                    "domain": ".sourceforge.net",
                    "path": "/",
                })
            else:
                cookies.append({
                    "name": "session",
                    "value": part,
                    "domain": ".sourceforge.net",
                    "path": "/",
                })
        return cookies

    async def _handle_cloudflare(self, page, max_wait: float = 25.0) -> bool:
        """
        Detect Cloudflare Turnstile challenge and wait for clearance or user solve.
        Returns True when cleared, False on timeout.
        """
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < max_wait:
            title = await page.title()
            if "just a moment" not in title.lower():
                # Challenge passed
                logger.info(f"Cloudflare clearance verified: '{title}'")
                return True

            logger.info("Cloudflare challenge detected, waiting for clearance...")
            
            # Check for turnstile iframe
            frames = page.frames
            for f in frames:
                if "challenges.cloudflare.com" in f.url or "turnstile" in f.url:
                    try:
                        box = await f.query_selector("input[type=checkbox]")
                        if box:
                            await box.click(timeout=2000)
                            logger.info("Clicked Cloudflare Turnstile checkbox.")
                    except Exception as e:
                        logger.debug(f"Checkbox click attempt: {e}")

            await asyncio.sleep(2.0)

        title = await page.title()
        return "just a moment" not in title.lower()

    async def update_project_overview(
        self,
        project_name: str,
        name: Optional[str] = None,
        summary: Optional[str] = None,
        short_description: Optional[str] = None,
        external_homepage: Optional[str] = None,
        icon_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update project metadata and icon via authenticated browser session on /admin/overview.
        """
        if not is_playwright_available():
            return {
                "success": False,
                "error": "Playwright is not installed. Install optional browser dependencies via: pip install \"mcp-server-sourceforge[browser]\" && playwright install chromium",
            }

        from playwright.async_api import async_playwright

        url = f"https://sourceforge.net/p/{project_name}/admin/overview"
        logger.info(f"Opening browser to update overview at {url}...")

        async with async_playwright() as p:
            browser = None
            context = None
            try:
                if self.cdp_url:
                    logger.info(f"Connecting to running browser via CDP at {self.cdp_url}...")
                    browser = await p.chromium.connect_over_cdp(self.cdp_url)
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                else:
                    args = [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-infobars",
                    ]
                    browser = await p.chromium.launch(
                        headless=self.headless,
                        args=args,
                    )
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                        viewport={"width": 1280, "height": 800},
                    )

                # Add stealth if available
                try:
                    from playwright_stealth import stealth_async
                    has_stealth = True
                except ImportError:
                    has_stealth = False

                # Inject cookies
                cookies = self._parse_cookies()
                if cookies:
                    await context.add_cookies(cookies)

                page = await context.new_page()
                if has_stealth:
                    await stealth_async(page)

                # Navigate
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                # Check Cloudflare
                cleared = await self._handle_cloudflare(page)
                if not cleared:
                    return {
                        "success": False,
                        "error": "Could not clear Cloudflare Turnstile challenge. Set SOURCEFORGE_CDP_URL or run non-headless.",
                    }

                # Check if we were redirected to login (session invalid)
                if "/auth/" in page.url:
                    return {
                        "success": False,
                        "error": "Session cookie is invalid or expired. Redirected to login page.",
                    }

                # Fill metadata fields
                if name:
                    name_input = await page.query_selector('input[name="name"]')
                    if name_input:
                        await name_input.fill(name)

                if summary:
                    summary_input = await page.query_selector('input[name="summary"]')
                    if summary_input:
                        await summary_input.fill(summary)

                if external_homepage:
                    home_input = await page.query_selector('input[name="external_homepage"]')
                    if home_input:
                        await home_input.fill(external_homepage)

                if short_description:
                    desc_input = await page.query_selector('textarea[name="short_description"]')
                    if desc_input:
                        await desc_input.fill(short_description)

                if icon_path and os.path.exists(icon_path):
                    icon_input = await page.query_selector('input[name="icon"]')
                    if icon_input:
                        await icon_input.set_input_files(icon_path)
                        logger.info(f"Attached icon from {icon_path}")

                # Submit form
                save_btn = await page.query_selector('input[type="submit"][value="Save"]')
                if not save_btn:
                    save_btn = await page.query_selector('button[type="submit"]')
                if not save_btn:
                    save_btn = await page.query_selector('form input[type="submit"]')

                if save_btn:
                    await save_btn.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    logger.info("Clicked save button and form submitted.")
                    return {
                        "success": True,
                        "message": f"Successfully updated project metadata for '{project_name}' via browser automation.",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Could not find Save button on /admin/overview form.",
                    }

            except Exception as e:
                logger.error(f"Browser update error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }
            finally:
                if browser and not self.cdp_url:
                    await browser.close()

    async def upload_screenshot(
        self,
        project_name: str,
        screenshot_path: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a project screenshot via authenticated browser session on /admin/screenshots.
        """
        if not is_playwright_available():
            return {
                "success": False,
                "error": "Playwright is not installed. Install optional browser dependencies via: pip install \"mcp-server-sourceforge[browser]\" && playwright install chromium",
            }

        if not os.path.exists(screenshot_path):
            return {
                "success": False,
                "error": f"Screenshot file does not exist: {screenshot_path}",
            }

        from playwright.async_api import async_playwright

        url = f"https://sourceforge.net/p/{project_name}/admin/screenshots"
        logger.info(f"Opening browser to upload screenshot at {url}...")

        async with async_playwright() as p:
            browser = None
            try:
                if self.cdp_url:
                    browser = await p.chromium.connect_over_cdp(self.cdp_url)
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                else:
                    args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                    browser = await p.chromium.launch(headless=self.headless, args=args)
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    )

                cookies = self._parse_cookies()
                if cookies:
                    await context.add_cookies(cookies)

                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                cleared = await self._handle_cloudflare(page)
                if not cleared:
                    return {
                        "success": False,
                        "error": "Could not clear Cloudflare Turnstile challenge on screenshots page.",
                    }

                file_input = await page.query_selector('input[type="file"][name="screenshot"]')
                if not file_input:
                    file_input = await page.query_selector('input[type="file"]')

                if not file_input:
                    return {
                        "success": False,
                        "error": "File input element for screenshot upload not found.",
                    }

                await file_input.set_input_files(screenshot_path)

                if caption:
                    caption_input = await page.query_selector('input[name="caption"]')
                    if caption_input:
                        await caption_input.fill(caption)

                save_btn = await page.query_selector('input[type="submit"][value="Upload"]')
                if not save_btn:
                    save_btn = await page.query_selector('input[type="submit"][value="Save"]')
                if not save_btn:
                    save_btn = await page.query_selector('button[type="submit"]')

                if save_btn:
                    await save_btn.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return {
                        "success": True,
                        "message": f"Successfully uploaded screenshot '{os.path.basename(screenshot_path)}' for '{project_name}' via browser automation.",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Could not find Upload/Save button on /admin/screenshots form.",
                    }

            except Exception as e:
                logger.error(f"Browser screenshot upload error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                }
            finally:
                if browser and not self.cdp_url:
                    await browser.close()
