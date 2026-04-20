from __future__ import annotations

import json
from pathlib import Path


def _is_wsl() -> bool:
    """Detect if we are running under WSL."""
    try:
        version_content = Path("/proc/version").read_text().lower()
        return "microsoft" in version_content or "wsl" in version_content
    except Exception:
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

exec 2>> "{log_file}"

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONWARNINGS=ignore
export PYTHONPATH="{workspace}"

set -m

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
                "enabled": True,
            }
        }

    return {
        "cortex": {
            "type": "local",
            "command": ["cortex", "mcp-server", "--stdio"],
            "enabled": True,
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
                "enabled": True,
            }
        }

    return {
        "cortex": {
            "command": "cortex",
            "args": ["mcp-server", "--stdio"],
            "env": {
                "PYTHONPATH": str(workspace),
                "PYTHONWARNINGS": "ignore",
            },
            "enabled": True,
        }
    }


def _find_cortex_project_root() -> Path:
    """Find the Cortex project root by looking for config.yaml."""
    current = Path.cwd()
    while current != current.parent:
        if (current / "config.yaml").exists():
            return current
        current = current.parent
    return Path.home()


def install_opencode_profile():
    """Adapter for OpenCode with tool-based governance profiles."""
    print("[Tool-Based Governance Injector] Target: OpenCode")
    config_dir = Path.home() / ".config" / "opencode"
    config_file = config_dir / "opencode.json"
    config_dir.mkdir(parents=True, exist_ok=True)

    project_root = _find_cortex_project_root()
    profiles = {
        "cortex-sync": {
            "mode": "primary",
            "description": "ANALISIS: Pre-flight con inyeccion obligatoria de contexto.",
            "prompt": f"{{file:{str(project_root / '.cortex' / 'skills' / 'cortex-sync.md')}}}",
            "tools": {
                "read": True,
                "write": False,
                "edit": False,
                "bash": False,
                "glob": True,
                "grep": True,
                "cortex_sync_ticket": True,
                "cortex_create_spec": True,
                "cortex_context": True,
                "cortex_search": True,
                "cortex_sync_vault": True,
            },
        },
        "cortex-SDDwork": {
            "mode": "primary",
            "description": "ORQUESTADOR: Delegacion obligatoria por rondas de subagentes.",
            "prompt": f"{{file:{str(project_root / '.cortex' / 'skills' / 'cortex-SDDwork.md')}}}",
            "tools": {
                "read": True,
                "write": False,
                "edit": False,
                "bash": False,
                "cortex_context": True,
                "cortex_search": True,
                "cortex_delegate_task": True,
                "cortex_delegate_batch": True,
                "cortex_get_task_result": True,
            },
        },
        "cortex-documenter": {
            "mode": "primary",
            "description": "DOCUMENTACION: Persistencia final en Vault.",
            "prompt": f"{{file:{str(project_root / '.cortex' / 'subagents' / 'cortex-documenter.md')}}}",
            "tools": {
                "read": True,
                "write": True,
                "edit": False,
                "bash": False,
                "cortex_save_session": True,
                "cortex_sync_vault": True,
            },
        },
    }

    config_data = {
        "agent": profiles,
        "mcp": get_opencode_mcp_definition(),
    }

    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"  [OK] Applied Tool-Based Governance to {config_file}")


def install_claude_desktop_profile():
    """Adapter for Claude Desktop."""
    print("[Hybrid Search Injector] Target: Claude Desktop")
    config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    data = {"mcpServers": {}}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    data.setdefault("mcpServers", {})
    data["mcpServers"].update(get_claude_mcp_definition())

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected MCP into {config_path}")


def install():
    install_opencode_profile()
    install_claude_desktop_profile()


def uninstall():
    print("[Uninstaller] Cleaning Configs")
    # ...


if __name__ == "__main__":
    install()
