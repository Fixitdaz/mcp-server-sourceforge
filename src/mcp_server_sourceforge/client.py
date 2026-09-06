"""
SourceForge HTTP Client
=======================
Handles communications with:
- Allura REST APIs (Wiki, Tickets, Project details)
- SourceForge Admin Web endpoints (Metadata, Screenshots, Icon uploads)
- Release REST API (Setting default downloads, labels)
- Statistics API
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
import httpx
from bs4 import BeautifulSoup

from mcp_server_sourceforge.browser import SourceForgeBrowser, is_playwright_available

logger = logging.getLogger("mcp-server-sourceforge.client")

SF_BASE_URL = "https://sourceforge.net"
SF_API_BASE = f"{SF_BASE_URL}/rest/p"
SF_STATS_BASE = f"{SF_BASE_URL}/projects"


class SourceForgeClient:
    """HTTP Client for SourceForge with API & Web Admin session capabilities."""

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        session_cookie: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.bearer_token = bearer_token or os.environ.get("SOURCEFORGE_BEARER_TOKEN")
        self.session_cookie = session_cookie or os.environ.get("SOURCEFORGE_SESSION_COOKIE")
        self.api_key = api_key or os.environ.get("SOURCEFORGE_API_KEY")
        self.timeout = timeout

    def _get_headers(self, auth_type: str = "bearer") -> Dict[str, str]:
        headers = {
            "User-Agent": "mcp-server-sourceforge/0.1.0",
            "Accept": "application/json",
        }
        if auth_type == "bearer" and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def _get_cookies(self) -> Dict[str, str]:
        cookies = {}
        if self.session_cookie:
            # Handle either raw cookie string (key=val; key2=val2) or single session value
            if "=" in self.session_cookie:
                for part in self.session_cookie.split(";"):
                    if "=" in part:
                        k, v = part.strip().split("=", 1)
                        cookies[k] = v
            else:
                cookies["session"] = self.session_cookie
        return cookies

    async def get_project_rest(self, project_name: str) -> Dict[str, Any]:
        """Fetch project details via Allura REST API."""
        url = f"{SF_API_BASE}/{project_name}"
        headers = self._get_headers()
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return {"error": f"Project '{project_name}' not found on SourceForge."}
            resp.raise_for_status()
            return resp.json()

    async def get_csrf_token(self, client: httpx.AsyncClient, page_url: str) -> Tuple[Optional[str], str]:
        """
        Request a page and extract the Allura _csrf_token from cookies or HTML form input.
        Returns (csrf_token, page_html).
        """
        resp = await client.get(page_url)
        if resp.status_code == 404:
            raise ValueError(f"Page not found: {page_url}")
        if resp.status_code == 403:
            raise PermissionError(
                f"Access denied to {page_url}. Please ensure your SOURCEFORGE_SESSION_COOKIE has admin rights."
            )
        resp.raise_for_status()

        # Try cookie first
        csrf = client.cookies.get("_csrf_token")
        if not csrf:
            soup = BeautifulSoup(resp.text, "html.parser")
            csrf_input = soup.find("input", {"name": "_csrf_token"})
            if csrf_input and csrf_input.get("value"):
                csrf = csrf_input["value"]

        return csrf, resp.text

    async def update_project_metadata(
        self,
        project_name: str,
        name: Optional[str] = None,
        summary: Optional[str] = None,
        short_description: Optional[str] = None,
        external_homepage: Optional[str] = None,
        support_page: Optional[str] = None,
        video_url: Optional[str] = None,
        twitter_handle: Optional[str] = None,
        facebook_page: Optional[str] = None,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """
        Update project metadata (name, summary, markdown description, links) via Admin overview.
        Supports automatic Playwright/CDP browser fallback when Cloudflare Turnstile challenge is encountered.
        Requires session cookie.
        """
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Updating project metadata requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }

        if use_browser:
            browser = SourceForgeBrowser(session_cookie=self.session_cookie)
            return await browser.update_project_overview(
                project_name=project_name,
                name=name,
                summary=summary,
                short_description=short_description,
                external_homepage=external_homepage,
            )

        overview_url = f"{SF_BASE_URL}/p/{project_name}/admin/overview"
        update_url = f"{SF_BASE_URL}/p/{project_name}/admin/update"
        cookies = self._get_cookies()

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, html = await self.get_csrf_token(client, overview_url)
            except Exception as e:
                # Cloudflare 403 or PermissionError fallback to browser
                if "403" in str(e) or "Access denied" in str(e) or "Cloudflare" in str(e):
                    logger.info("Direct HTTP encountered Cloudflare challenge. Falling back to browser automation...")
                    if is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL"):
                        browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                        return await browser.update_project_overview(
                            project_name=project_name,
                            name=name,
                            summary=summary,
                            short_description=short_description,
                            external_homepage=external_homepage,
                        )
                    return {
                        "success": False,
                        "error": (
                            "Cloudflare Turnstile challenge detected on SourceForge web admin form. "
                            "To enable automatic browser bypass, install optional browser dependencies: "
                            'pip install "mcp-server-sourceforge[browser]" && playwright install chromium '
                            "or configure SOURCEFORGE_CDP_URL to connect to your running browser."
                        ),
                        "details": str(e),
                    }
                return {"success": False, "error": str(e)}

            soup = BeautifulSoup(html, "html.parser")
            # Populate existing form values so we don't accidentally blank out unspecified fields
            form = soup.find("form")
            data = {}
            if form:
                for inp in form.find_all(["input", "textarea"]):
                    inp_name = inp.get("name")
                    if inp_name and inp_name not in ["icon", "delete_icon"]:
                        data[inp_name] = inp.get("value", "") or inp.text or ""

            if csrf:
                data["_csrf_token"] = csrf

            # Overwrite with provided arguments
            if name is not None:
                data["name"] = name
            if summary is not None:
                data["summary"] = summary
            if short_description is not None:
                data["short_description"] = short_description
            if external_homepage is not None:
                data["external_homepage"] = external_homepage
            if support_page is not None:
                data["support_page"] = support_page
            if video_url is not None:
                data["video_url"] = video_url
            if twitter_handle is not None:
                data["twitter_handle"] = twitter_handle
            if facebook_page is not None:
                data["facebook_page"] = facebook_page

            headers = {"Referer": overview_url}
            resp = await client.post(update_url, data=data, headers=headers)
            if resp.status_code in [200, 302]:
                return {
                    "success": True,
                    "project": project_name,
                    "message": "Project metadata updated successfully.",
                    "overview_url": overview_url,
                }
            if resp.status_code == 403 and (is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL")):
                logger.info("POST returned 403. Attempting browser fallback...")
                browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                return await browser.update_project_overview(
                    project_name=project_name,
                    name=name,
                    summary=summary,
                    short_description=short_description,
                    external_homepage=external_homepage,
                )
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Failed to update metadata. Server responded with {resp.status_code}: {resp.text[:300]}",
            }

    async def upload_icon(
        self,
        project_name: str,
        local_icon_path: str,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """Upload a logo/icon image to a SourceForge project."""
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Uploading an icon requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }
        if not os.path.isfile(local_icon_path):
            return {"success": False, "error": f"Icon file not found at {local_icon_path}"}

        if use_browser:
            browser = SourceForgeBrowser(session_cookie=self.session_cookie)
            return await browser.update_project_overview(
                project_name=project_name,
                icon_path=local_icon_path,
            )

        overview_url = f"{SF_BASE_URL}/p/{project_name}/admin/overview"
        update_url = f"{SF_BASE_URL}/p/{project_name}/admin/update"
        cookies = self._get_cookies()

        filename = os.path.basename(local_icon_path)
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, _ = await self.get_csrf_token(client, overview_url)
            except Exception as e:
                if "403" in str(e) or "Access denied" in str(e) or "Cloudflare" in str(e):
                    if is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL"):
                        browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                        return await browser.update_project_overview(
                            project_name=project_name,
                            icon_path=local_icon_path,
                        )
                    return {
                        "success": False,
                        "error": (
                            "Cloudflare challenge detected when uploading icon. "
                            'Install browser dependencies via: pip install "mcp-server-sourceforge[browser]" '
                            "or configure SOURCEFORGE_CDP_URL."
                        ),
                        "details": str(e),
                    }
                return {"success": False, "error": str(e)}

            data = {}
            if csrf:
                data["_csrf_token"] = csrf

            with open(local_icon_path, "rb") as f:
                files = {"icon": (filename, f.read(), content_type)}

            headers = {"Referer": overview_url}
            resp = await client.post(update_url, data=data, files=files, headers=headers)
            if resp.status_code in [200, 302]:
                return {
                    "success": True,
                    "project": project_name,
                    "message": f"Icon '{filename}' uploaded successfully.",
                }
            if resp.status_code == 403 and (is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL")):
                browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                return await browser.update_project_overview(
                    project_name=project_name,
                    icon_path=local_icon_path,
                )
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Failed to upload icon. HTTP {resp.status_code}: {resp.text[:300]}",
            }

    async def delete_icon(self, project_name: str) -> Dict[str, Any]:
        """Remove the custom icon from a SourceForge project."""
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Deleting an icon requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }

        overview_url = f"{SF_BASE_URL}/p/{project_name}/admin/overview"
        update_url = f"{SF_BASE_URL}/p/{project_name}/admin/update"
        cookies = self._get_cookies()

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, _ = await self.get_csrf_token(client, overview_url)
            except Exception as e:
                return {"success": False, "error": str(e)}

            data = {"delete_icon": "on"}
            if csrf:
                data["_csrf_token"] = csrf

            headers = {"Referer": overview_url}
            resp = await client.post(update_url, data=data, headers=headers)
            if resp.status_code in [200, 302]:
                return {"success": True, "project": project_name, "message": "Custom icon deleted."}
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Failed to delete icon. HTTP {resp.status_code}",
            }

    async def list_screenshots(self, project_name: str) -> Dict[str, Any]:
        """Fetch all screenshots currently uploaded for a project."""
        screenshots_url = f"{SF_BASE_URL}/p/{project_name}/admin/screenshots"
        cookies = self._get_cookies()

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(screenshots_url)
            if resp.status_code == 404:
                return {"error": f"Screenshots page not found for project '{project_name}'."}
            if resp.status_code == 403:
                # Fall back to public project page to parse public screenshots
                public_url = f"{SF_BASE_URL}/projects/{project_name}/"
                pub_resp = await client.get(public_url)
                if pub_resp.status_code != 200:
                    return {"error": f"Cannot view project '{project_name}' (status {pub_resp.status_code})."}
                soup = BeautifulSoup(pub_resp.text, "html.parser")
                items = []
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if "screenshot" in src:
                        items.append({"url": src, "caption": img.get("alt", "")})
                return {"project": project_name, "screenshots": items, "read_only": True}

            soup = BeautifulSoup(resp.text, "html.parser")
            screenshots = []
            for row in soup.select("ul#sortable li, div.screenshot-item, tr.screenshot"):
                img_tag = row.find("img")
                img_url = img_tag["src"] if img_tag and img_tag.get("src") else None

                screenshot_id = row.get("data-id") or row.get("id")
                caption_elem = row.find("input", {"name": re.compile(r"caption")}) or row.find("span", {"class": "caption"})
                caption = caption_elem.get("value", "") if hasattr(caption_elem, "get") else (caption_elem.text.strip() if caption_elem else "")

                del_link = row.find("a", href=re.compile(r"delete_screenshot"))
                if del_link and not screenshot_id:
                    m = re.search(r"id=([a-f0-9]+)", del_link.get("href", ""))
                    if m:
                        screenshot_id = m.group(1)

                screenshots.append({
                    "id": screenshot_id,
                    "url": img_url,
                    "caption": caption
                })

            return {"project": project_name, "total": len(screenshots), "screenshots": screenshots}

    async def upload_screenshot(
        self,
        project_name: str,
        local_image_path: str,
        caption: Optional[str] = None,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        """Upload a project screenshot image with an optional caption."""
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Uploading a screenshot requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }
        if not os.path.isfile(local_image_path):
            return {"success": False, "error": f"Image file not found at {local_image_path}"}

        if use_browser:
            browser = SourceForgeBrowser(session_cookie=self.session_cookie)
            return await browser.upload_screenshot(
                project_name=project_name,
                screenshot_path=local_image_path,
                caption=caption,
            )

        admin_url = f"{SF_BASE_URL}/p/{project_name}/admin/screenshots"
        add_url = f"{SF_BASE_URL}/p/{project_name}/admin/add_screenshot"
        cookies = self._get_cookies()

        filename = os.path.basename(local_image_path)
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, _ = await self.get_csrf_token(client, admin_url)
            except Exception as e:
                if "403" in str(e) or "Access denied" in str(e) or "Cloudflare" in str(e):
                    if is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL"):
                        browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                        return await browser.upload_screenshot(
                            project_name=project_name,
                            screenshot_path=local_image_path,
                            caption=caption,
                        )
                    return {
                        "success": False,
                        "error": (
                            "Cloudflare challenge detected when uploading screenshot. "
                            'Install browser dependencies via: pip install "mcp-server-sourceforge[browser]" '
                            "or configure SOURCEFORGE_CDP_URL."
                        ),
                        "details": str(e),
                    }
                return {"success": False, "error": str(e)}

            data = {}
            if csrf:
                data["_csrf_token"] = csrf
            if caption:
                data["caption"] = caption

            with open(local_image_path, "rb") as f:
                files = {"screenshot": (filename, f.read(), content_type)}

            headers = {"Referer": admin_url}
            resp = await client.post(add_url, data=data, files=files, headers=headers)
            if resp.status_code in [200, 302]:
                return {
                    "success": True,
                    "project": project_name,
                    "filename": filename,
                    "caption": caption or "",
                    "message": f"Screenshot '{filename}' uploaded successfully.",
                }
            if resp.status_code == 403 and (is_playwright_available() or os.environ.get("SOURCEFORGE_CDP_URL")):
                browser = SourceForgeBrowser(session_cookie=self.session_cookie)
                return await browser.upload_screenshot(
                    project_name=project_name,
                    screenshot_path=local_image_path,
                    caption=caption,
                )
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Failed to upload screenshot. HTTP {resp.status_code}: {resp.text[:300]}",
            }

    async def delete_screenshot(self, project_name: str, screenshot_id: str) -> Dict[str, Any]:
        """Delete a screenshot by its ObjectId."""
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Deleting a screenshot requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }

        admin_url = f"{SF_BASE_URL}/p/{project_name}/admin/screenshots"
        delete_url = f"{SF_BASE_URL}/p/{project_name}/admin/delete_screenshot"
        cookies = self._get_cookies()

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, _ = await self.get_csrf_token(client, admin_url)
            except Exception as e:
                return {"success": False, "error": str(e)}

            data = {"id": screenshot_id}
            if csrf:
                data["_csrf_token"] = csrf

            headers = {"Referer": admin_url}
            resp = await client.post(delete_url, data=data, headers=headers)
            if resp.status_code in [200, 302]:
                return {"success": True, "project": project_name, "screenshot_id": screenshot_id, "message": "Screenshot deleted."}
            return {"success": False, "status_code": resp.status_code, "error": f"Failed to delete screenshot: HTTP {resp.status_code}"}

    async def edit_screenshot(self, project_name: str, screenshot_id: str, caption: str) -> Dict[str, Any]:
        """Edit caption of an existing screenshot."""
        if not self.session_cookie:
            return {
                "success": False,
                "error": "Editing a screenshot requires SOURCEFORGE_SESSION_COOKIE with admin privileges.",
            }

        admin_url = f"{SF_BASE_URL}/p/{project_name}/admin/screenshots"
        edit_url = f"{SF_BASE_URL}/p/{project_name}/admin/edit_screenshot"
        cookies = self._get_cookies()

        async with httpx.AsyncClient(cookies=cookies, timeout=self.timeout, follow_redirects=True) as client:
            try:
                csrf, _ = await self.get_csrf_token(client, admin_url)
            except Exception as e:
                return {"success": False, "error": str(e)}

            data = {"id": screenshot_id, "caption": caption}
            if csrf:
                data["_csrf_token"] = csrf

            headers = {"Referer": admin_url}
            resp = await client.post(edit_url, data=data, headers=headers)
            if resp.status_code in [200, 302]:
                return {"success": True, "project": project_name, "screenshot_id": screenshot_id, "caption": caption}
            return {"success": False, "status_code": resp.status_code, "error": f"Failed to edit screenshot: HTTP {resp.status_code}"}

    async def set_default_release(
        self,
        project_name: str,
        file_path: str,
        default_platforms: List[str],
        download_label: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Configure default release downloads and download label using SourceForge Release API.
        Default platforms: list of strings from ('windows', 'mac', 'linux', 'bsd', 'solaris', 'others').
        """
        key = api_key or self.api_key
        if not key:
            return {
                "success": False,
                "error": "Setting default release requires a Releases API Key. Provide api_key or set SOURCEFORGE_API_KEY.",
            }

        clean_path = file_path.strip("/")
        if clean_path.endswith("/download"):
            clean_path = clean_path[:-9]

        url = f"{SF_BASE_URL}/projects/{project_name}/files/{clean_path}"

        params = [("api_key", key)]
        for plat in default_platforms:
            params.append(("default", plat.lower()))
        if download_label:
            params.append(("download_label", download_label))

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.put(url, data=params, headers=headers)
            if resp.status_code in [200, 204]:
                try:
                    result_json = resp.json()
                except Exception:
                    result_json = {"status": "ok"}
                return {
                    "success": True,
                    "project": project_name,
                    "file_path": clean_path,
                    "defaults": default_platforms,
                    "download_label": download_label,
                    "response": result_json,
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Release API request failed: HTTP {resp.status_code} - {resp.text[:300]}",
            }

    async def get_wiki_page(self, project_name: str, page_name: str = "Home", wiki_mount: str = "wiki") -> Dict[str, Any]:
        """Retrieve a wiki page content via Allura REST API."""
        url = f"{SF_API_BASE}/{project_name}/{wiki_mount}/{page_name}"
        headers = self._get_headers()
        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return {"error": f"Wiki page '{page_name}' not found under mount '{wiki_mount}'."}
            resp.raise_for_status()
            return resp.json()

    async def update_wiki_page(
        self,
        project_name: str,
        page_name: str,
        text: str,
        labels: Optional[str] = None,
        wiki_mount: str = "wiki",
    ) -> Dict[str, Any]:
        """Create or update a wiki page with markdown content via Allura REST API."""
        url = f"{SF_API_BASE}/{project_name}/{wiki_mount}/{page_name}"
        headers = self._get_headers()
        data = {"text": text}
        if labels:
            data["labels"] = labels

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.post(url, data=data)
            if resp.status_code in [200, 201]:
                return {"success": True, "project": project_name, "page": page_name, "data": resp.json()}
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Failed to update wiki page: HTTP {resp.status_code} - {resp.text[:300]}",
            }

    async def get_download_stats(
        self,
        project_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch download counts and geography stats."""
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now.strftime("%Y-%m-%d")
        if not start_date:
            start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        url = f"{SF_STATS_BASE}/{project_name}/files/stats/json"
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return {"error": f"Download stats not found for project '{project_name}'."}
            resp.raise_for_status()
            return resp.json()
