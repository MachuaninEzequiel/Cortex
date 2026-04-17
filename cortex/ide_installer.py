from __future__ import annotations
import json
import shutil
import os
import sys
from pathlib import Path

# --- CORE INJECTOR LOGIC ---

def _is_wsl() -> bool:
    """Detect if we are running under WSL."""
    try:
        version_content = Path("/proc/version").read_text().lower()
        return "microsoft" in version_content or "wsl" in version_content
    except:
        return False

def _create_shielded_wrapper() -> Path:
    """Create a shielded bash wrapper to filter WSL and Python noise."""
    cortex_bin_dir = Path.home() / ".cortex" / "bin"
    cortex_log_dir = Path.home() / ".cortex" / "logs"
    cortex_bin_dir.mkdir(parents=True, exist_ok=True)
    cortex_log_dir.mkdir(parents=True, exist_ok=True)
    
    wrapper_path = cortex_bin_dir / "cortex-mcp-wrapper"
    log_file = cortex_log_dir / "mcp-shield.log"
    
    workspace = Path.cwd()
    
    wrapper_content = f"""#!/bin/bash
# Cortex Shielded Wrapper v2.19
# Intercepts WSL noise and redirects stderr to a dedicated log.

# 1. Redirect ALL stderr to the shield log
exec 2>> "{log_file}"

# 2. Pure Environment for JSON-RPC
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONWARNINGS=ignore
export PYTHONPATH="{workspace}"

# 3. Clean start - ensure no jobs report status
set -m

# 4. Exec replacement - replace shell with Python process
exec /usr/bin/python3 -m cortex.cli.main mcp-server --stdio
"""
    wrapper_path.write_text(wrapper_content, encoding="utf-8")
    wrapper_path.chmod(0o755)
    print(f"  [OK] Created Shielded Wrapper at {wrapper_path}")
    return wrapper_path

def get_opencode_mcp_definition() -> dict:
    """Return the MCP definition in OpenCode's specific format."""
    if _is_wsl():
        wrapper_path = _create_shielded_wrapper()
        return {
            "cortex": {
                "type": "local",
                "command": [str(wrapper_path)],
                "enabled": True
            }
        }
    else:
        return {
            "cortex": {
                "type": "local",
                "command": ["cortex", "mcp-server", "--stdio"],
                "enabled": True
            }
        }

def get_claude_mcp_definition() -> dict:
    """Return the MCP definition in Claude Desktop's standard format."""
    workspace = Path.cwd()
    if _is_wsl():
        wrapper_path = _create_shielded_wrapper()
        return {
            "cortex": {
                "command": str(wrapper_path),
                "args": [],
                "env": {},
                "enabled": True
            }
        }
    else:
        return {
            "cortex": {
                "command": "cortex",
                "args": ["mcp-server", "--stdio"],
                "env": {
                    "PYTHONPATH": str(workspace),
                    "PYTHONWARNINGS": "ignore"
                },
                "enabled": True
            }
        }

# --- ADAPTERS ---

def install_opencode_profile():
    """Adapter for OpenCode (Orchestration & Hybrid Search Schema v2.19)."""
    print("[Hybrid Search Injector] Target: OpenCode")
    config_dir = Path.home() / ".config" / "opencode"
    config_file = config_dir / "opencode.json"
    
    config_data = {"agent": {}, "mcp": {}}
    if config_file.exists():
        try: config_data = json.loads(config_file.read_text(encoding="utf-8"))
        except: pass
    
    # 1. Inject MCP Server
    config_data.pop("mcpServers", None)
    config_data.setdefault("mcp", {})
    config_data["mcp"].update(get_opencode_mcp_definition())
    
    workspace = Path.cwd()
    
    # 2. Inject Hybrid Governance Agents
    config_data.setdefault("agent", {})
    profiles = {
        "cortex-sync": {
            "mode": "primary",
            "description": "Cortex Analysis (Strict - Vector Enabled)",
            "prompt": f"{{file:{str(workspace / '.cortex' / 'skills' / 'cortex-sync.md')}}}",
            "tools": {
                "read": True, "glob": True, "grep": True,
                "write": False, "edit": False, "bash": False,
                "cortex_search_vector": True,
                "cortex_search": True,
                "cortex_context": True, 
                "cortex_create_spec": True, "cortex_sync_vault": True
            }
        },
        "cortex-SDDwork": {
            "mode": "primary",
            "description": "Cortex Orchestrator (Implementation - Bypass Enabled)",
            "prompt": f"{{file:{str(workspace / '.cortex' / 'skills' / 'cortex-SDDwork.md')}}}",
            "tools": {
                "read": True, "glob": True, "grep": True,
                "write": True, "edit": True, "bash": True,
                "cortex_search": True,
                "cortex_search_vector": False,
                "cortex_delegate_task": True, "cortex_get_task_result": True,
                "cortex_sync_vault": True
            }
        }
    }
    
    config_data["agent"].pop("cortex-documenter", None)
    config_data["agent"].update(profiles)
    
    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"  [OK] Applied Hybrid Search Governance to {config_file}")

def install_claude_desktop_profile():
    """Adapter for Claude Desktop."""
    print("[Hybrid Search Injector] Target: Claude Desktop")
    config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    data = {"mcpServers": {}}
    if config_path.exists():
        try: data = json.loads(config_path.read_text(encoding="utf-8"))
        except: pass
    
    data.setdefault("mcpServers", {})
    data["mcpServers"].update(get_claude_mcp_definition())
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected MCP into {config_path}")

# --- ENTRYPOINTS ---

def install():
    install_opencode_profile()
    install_claude_desktop_profile()

def uninstall():
    print("[Uninstaller] Cleaning Configs")
    # ...

if __name__ == "__main__":
    install()
