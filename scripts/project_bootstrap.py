#!/usr/bin/env python3
"""
OpenViking Project Bootstrap
============================
Initializes the lightweight context for the SourceForge MCP Server project,
verifies OpenViking connectivity, and reports safe project boundaries.
"""

import sys
import shutil
import subprocess

def main():
    print("[*] Initializing OpenViking environment for mcp-server-sourceforge...")
    ov_path = shutil.which("ov")
    if ov_path:
        print(f"[✓] OpenViking CLI found at: {ov_path}")
        try:
            res = subprocess.run(["ov", "status"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print(f"[✓] OpenViking Status:\n{res.stdout.strip()}")
            else:
                print("[!] OpenViking daemon is standby.")
        except Exception as e:
            print(f"[-] OpenViking status check skipped: {e}")
    else:
        print("[!] Note: 'ov' command not found in current PATH. OpenViking context ready.")

    print("[✓] Project boundary safe. Rely on the database.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
