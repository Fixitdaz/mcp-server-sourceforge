# 🚀 SourceForge MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Standard-green.svg)](https://modelcontextprotocol.io)

A comprehensive **Model Context Protocol (MCP)** server providing AI coding agents (AntiGravity, Claude Desktop, Cursor, Continue) with full end-to-end lifecycle capabilities to manage, brand, document, release, and monitor projects on **SourceForge**.

---

## 🌟 Full Capabilities

### 1. 📋 Project Setup & Metadata
- **`sourceforge_get_project`**: Fetch project metadata, taglines, long descriptions, registered tools, and maintainers via the Allura REST API.
- **`sourceforge_update_project_metadata`**: Update project display title, short summary (<= 70 characters for directory search results), full Markdown description, homepages, support URLs, and social media handles.
- **`sourceforge_upload_icon`**: Upload a project logo / avatar (PNG, JPG, SVG) for project headers and directory listings.
- **`sourceforge_delete_icon`**: Remove custom project icon and restore default.
- **`sourceforge_create_project_guide`**: Get automated checklists and structured configurations to bootstrap a new project.

### 2. 🖼️ Screenshot Gallery
- **`sourceforge_list_screenshots`**: Inspect all screenshots uploaded to a project, including IDs, image URLs, and captions.
- **`sourceforge_upload_screenshot`**: Upload screenshots (up to 6 per project) with descriptive captions for the project summary page.
- **`sourceforge_edit_screenshot`**: Update the caption of any uploaded screenshot.
- **`sourceforge_delete_screenshot`**: Remove a screenshot by its ID.

### 3. 📦 Releases & File Release System (FRS)
- **`sourceforge_upload_file`**: Upload large binaries, ISOs, zip archives, or release packages directly to `frs.sourceforge.net` via authenticated SFTP without hitting 2GB web limits.
- **`sourceforge_create_release_folder`**: Create subfolders and directory trees on FRS (e.g. `v1.0.0/builds`).
- **`sourceforge_list_files`**: View releases, total downloads, and folder trees.
- **`sourceforge_set_default_release`**: Use the official SourceForge Release REST API to designate default downloads for specific operating systems (`windows`, `mac`, `linux`, `bsd`, `solaris`, `others`) and customize the download button label.

### 4. 📝 Documentation & Wiki
- **`sourceforge_get_wiki_page`**: Read any project documentation or wiki page in Markdown.
- **`sourceforge_update_wiki_page`**: Create or edit documentation pages with Markdown formatting and tags.

### 5. 📊 Analytics & Download Metrics
- **`sourceforge_get_download_stats`**: Query download counts, date ranges, and geographic breakdown by country and OS.

### 6. 🌐 Browser Automation & Cloudflare Bypass (New!)
SourceForge web admin forms (`/admin/overview`, `/admin/screenshots`) are protected by **Cloudflare Turnstile**.
- **Autonomous Fallback**: When an HTTP POST receives a Cloudflare 403 challenge, the client automatically switches to **Playwright** stealth browser automation.
- **CDP Support**: Attach to an existing authenticated browser (Vivaldi, Chrome, Edge) via `SOURCEFORGE_CDP_URL` (e.g. `http://localhost:9222`) to reuse active sessions without solving challenges.
- **Headless / Headful**: Runs headless by default or launches a visible window if interactive clearance is required.

---

## 🔐 Authentication Guide

SourceForge uses four authentication methods depending on the operation:

| Feature | Method | Environment Variable | Tool Parameter |
|---|---|---|---|
| **File Releases (SFTP)** | SSH Key (`~/.ssh/id_ed25519` or `id_rsa`) | `SOURCEFORGE_USERNAME`, `SOURCEFORGE_SSH_KEY_PATH` | `username`, `ssh_key_path` |
| **Default Downloads & Labels** | Releases API Key | `SOURCEFORGE_API_KEY` | `api_key` |
| **Metadata, Icons & Screenshots** | Admin Session Cookie | `SOURCEFORGE_SESSION_COOKIE` | `session_cookie` |
| **Browser CDP (Cloudflare Bypass)** | Chrome DevTools Protocol | `SOURCEFORGE_CDP_URL` | N/A |
| **Wiki REST API** | Bearer Token / OAuth | `SOURCEFORGE_BEARER_TOKEN` | `bearer_token` |

### How to get your credentials:
1. **SSH Key for Uploads**: Add your public SSH key in [Account Preferences > SSH Keys](https://sourceforge.net/auth/preferences/).
2. **Releases API Key**: Generate your key on your [SourceForge Account Page](https://sourceforge.net/auth/preferences/) under the **Releases API Key** section.
3. **Session Cookie**: Log in to SourceForge in your browser and copy your `session` cookie (found under Developer Tools > Storage / Application > Cookies for `sourceforge.net`).
4. **Bearer Token**: Generate an OAuth token under the **OAuth tab** in your Account settings.

---

## 📦 Installation

### Core (SFTP, REST APIs, Analytics):
```bash
git clone https://github.com/Fixitdaz/mcp-server-sourceforge.git
cd mcp-server-sourceforge
pip install -e .
```

### With Autonomous Browser Automation (Playwright):
```bash
pip install -e ".[browser]"
playwright install chromium
```

---

## ⚙️ MCP Client Configuration

### In AntiGravity or Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sourceforge": {
      "command": "python",
      "args": ["-m", "mcp_server_sourceforge.server"],
      "env": {
        "SOURCEFORGE_USERNAME": "your_username",
        "SOURCEFORGE_API_KEY": "your_release_api_key",
        "SOURCEFORGE_SESSION_COOKIE": "your_session_cookie",
        "SOURCEFORGE_BEARER_TOKEN": "your_bearer_token"
      }
    }
  }
}
```

Or using `uvx`:
```json
{
  "mcpServers": {
    "sourceforge": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Fixitdaz/mcp-server-sourceforge", "mcp-server-sourceforge"],
      "env": {
        "SOURCEFORGE_USERNAME": "your_username",
        "SOURCEFORGE_API_KEY": "your_release_api_key"
      }
    }
  }
}
```

---

## 🛠️ Step-by-Step New Project Workflow

When bootstrapping a project from scratch:

1. **Plan & Guide**:
   Call `sourceforge_create_project_guide` with your UNIX name, description, and license.
2. **Brand & Describe**:
   - `sourceforge_upload_icon`: Set your high-res project logo.
   - `sourceforge_update_project_metadata`: Set your 70-character summary and full Markdown description.
   - `sourceforge_upload_screenshot`: Upload preview screenshots with captions.
3. **Release Files**:
   - `sourceforge_create_release_folder`: Create `v1.0.0/`.
   - `sourceforge_upload_file`: Upload installer or ISO artifacts.
   - `sourceforge_set_default_release`: Designate the default file for Windows / Mac / Linux and set a button label like "Download for Windows".
4. **Document**:
   - `sourceforge_update_wiki_page`: Publish `Home` and `Installation` guides.
5. **Monitor**:
   - `sourceforge_get_download_stats`: Track daily download traction across countries!

---

## 📄 License

MIT License — Copyright (c) 2026 Fixitdaz
