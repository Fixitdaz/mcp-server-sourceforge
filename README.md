# 🚀 SourceForge MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Standard-green.svg)](https://modelcontextprotocol.io)

An official **Model Context Protocol (MCP)** server providing AI coding agents (Claude Desktop, AntiGravity, Cursor, Continue) with native capabilities to manage, inspect, and upload release artifacts to **SourceForge**.

---

## 🌟 Capabilities

- **`sourceforge_get_project`**: Fetch project metadata, overview, description, and registered tools via the SourceForge Allura REST API.
- **`sourceforge_get_download_stats`**: Pull real-time download counts, country metrics, and historical timeline statistics.
- **`sourceforge_list_files`**: Browse released binaries, ISO images, and directory structures.
- **`sourceforge_upload_file`**: Seamlessly upload large ISOs, binaries, or release packages directly to the SourceForge File Release System (`frs.sourceforge.net`) via authenticated SFTP without hitting 2GB API caps.

---

## 📦 Installation

### Using `uv` / `pip`:
```bash
git clone https://github.com/Fixitdaz/mcp-server-sourceforge.git
cd mcp-server-sourceforge
pip install -e .
```

---

## ⚙️ Configuration

Add to your MCP Client configuration (e.g. `claude_desktop_config.json` or AntiGravity settings):

```json
{
  "mcpServers": {
    "sourceforge": {
      "command": "python",
      "args": ["-m", "mcp_server_sourceforge.server"]
    }
  }
}
```

Or run directly with `uvx`:
```json
{
  "mcpServers": {
    "sourceforge": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Fixitdaz/mcp-server-sourceforge", "mcp-server-sourceforge"]
    }
  }
}
```

---

## 🔐 Authentication for Uploads

Uploading files to SourceForge requires an SSH Key registered in your [SourceForge Account Preferences](https://sourceforge.net/auth/preferences/).

The server automatically looks for:
- `~/.ssh/id_ed25519`
- `~/.ssh/id_rsa`

Or you can pass a custom `ssh_key_path` when invoking `sourceforge_upload_file`.

---

## 📄 License

MIT License — Copyright (c) 2026 Fixitdaz
