from __future__ import annotations

import json
import shutil
from pathlib import Path

from cortex.setup.cortex_workspace import ensure_cortex_workspace


def get_opencode_config_path() -> Path:
    """Return the OpenCode config directory."""
    return Path.home() / ".config" / "opencode"


def _ensure_workspace_structure() -> None:
    workspace = Path.cwd()
    result = ensure_cortex_workspace(workspace)
    created = result["created"]
    if created:
        print(f"  [ok] Ensured Cortex workspace files ({len(created)} created).")


def install_opencode_profile() -> bool:
    """Install Cortex Release 2 profiles into OpenCode."""
    print("Installing Cortex profiles into OpenCode...")
    _ensure_workspace_structure()

    config_dir = get_opencode_config_path()
    if not config_dir.exists():
        print(f"  [!] OpenCode config directory not found at {config_dir}.")
        print("  [!] Please run OpenCode at least once or create the directory.")
        return False

    config_file = config_dir / "opencode.json"
    if not config_file.exists():
        config_data = {"agent": {}}
    else:
        try:
            config_data = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  [X] Error: Could not parse {config_file}. Is it valid JSON?")
            return False

    config_data.setdefault("agent", {})

    workspace = Path.cwd()
    sync_prompt = workspace / ".cortex" / "skills" / "cortex-sync.md"
    sddwork_prompt = workspace / ".cortex" / "skills" / "cortex-SDDwork.md"

    cortex_sync_agent = {
        "mode": "primary",
        "description": "Cortex Sync - Pre-flight, context and spec preparation.",
        "model": "anthropic/claude-3-5-sonnet-20241022",
        "prompt": f"{{file:{str(sync_prompt)}}}",
        "tools": {
            "read": True,
            "write": True,
            "edit": True,
            "bash": True,
            "delegate": True,
            "delegation_read": True,
            "delegation_list": True,
        },
    }

    cortex_sddwork_agent = {
        "mode": "primary",
        "description": "Cortex SDDwork - Orchestrated implementation with mandatory documentation.",
        "model": "anthropic/claude-3-5-sonnet-20241022",
        "prompt": f"{{file:{str(sddwork_prompt)}}}",
        "tools": {
            "read": True,
            "write": True,
            "edit": True,
            "bash": True,
            "delegate": True,
            "delegation_read": True,
            "delegation_list": True,
        },
    }

    for old_name in ["cortex-orchestrator", "cortex-init", "cortex-work"]:
        config_data["agent"].pop(old_name, None)

    config_data["agent"]["cortex-sync"] = cortex_sync_agent
    config_data["agent"]["cortex-SDDwork"] = cortex_sddwork_agent

    if config_file.exists():
        backup_file = config_file.with_suffix(".json.bak")
        shutil.copy2(config_file, backup_file)
        print(f"  [ok] Created backup of opencode.json at {backup_file}")

    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"  [ok] Installed 'cortex-sync' and 'cortex-SDDwork' into {config_file}.")
    print("  [ok] Profiles available in OpenCode:")
    print("       cortex-sync    -> pre-flight, memory, spec preparation")
    print("       cortex-SDDwork -> orchestrated implementation + mandatory documenter")
    return True


def install_claude_code() -> bool:
    """Set up CLAUDE.md for the current workspace."""
    print("\nSetting up Cortex instructions for Claude Code in current workspace...")
    _ensure_workspace_structure()

    current_dir = Path.cwd()
    claude_md = current_dir / "CLAUDE.md"
    instruction_block = (
        "\n\n<!-- CORTEX INTEGRATION START -->\n"
        "# Cortex Release 2 Checklist\n"
        "You are working in a Cortex-governed repository.\n"
        "1. Start with `cortex-sync` for pre-flight and context preparation.\n"
        "2. After context/spec preparation, continue with `cortex-SDDwork`.\n"
        "3. Never use external memory tools such as `engram_*`, `mem_*`, `save_memory`, or `session_summary`.\n"
        "4. The task is not complete until Cortex documentation has been written and synced.\n"
        "5. Finish through the Cortex documenter flow, not through generic session tools.\n"
        "<!-- CORTEX INTEGRATION END -->\n"
    )

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "<!-- CORTEX INTEGRATION START -->" in content:
            start_idx = content.find("<!-- CORTEX INTEGRATION START -->")
            end_marker = "<!-- CORTEX INTEGRATION END -->"
            end_idx = content.find(end_marker)
            if end_idx != -1:
                end_idx += len(end_marker)
                new_content = content[:start_idx] + instruction_block.strip("\n") + content[end_idx:]
                claude_md.write_text(new_content, encoding="utf-8")
                print("  [ok] Updated existing Cortex block in CLAUDE.md.")
            else:
                claude_md.write_text(content + instruction_block, encoding="utf-8")
                print("  [ok] Repaired Cortex block in CLAUDE.md.")
        else:
            claude_md.write_text(content + instruction_block, encoding="utf-8")
            print("  [ok] Appended Cortex Release 2 instructions to CLAUDE.md.")
    else:
        claude_md.write_text("# Project Instructions\n" + instruction_block, encoding="utf-8")
        print("  [ok] Created CLAUDE.md with Cortex Release 2 instructions.")

    print("\n  [!] To complete Claude Code setup, register the MCP server:")
    print("      claude mcp add cortex-memory \"cortex\" \"mcp-server\"")
    return True


def uninstall_opencode_profile() -> bool:
    """Remove Cortex profiles from OpenCode."""
    print("Uninstalling Cortex profiles from OpenCode...")
    config_file = get_opencode_config_path() / "opencode.json"
    if not config_file.exists():
        print(f"  [ok] OpenCode config not found at {config_file}. Nothing to do.")
        return True

    try:
        config_data = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"  [X] Error: Could not parse {config_file}.")
        return False

    removed: list[str] = []
    if "agent" in config_data:
        for profile in ["cortex-sync", "cortex-SDDwork", "cortex-work", "cortex-init", "cortex-orchestrator"]:
            if profile in config_data["agent"]:
                del config_data["agent"][profile]
                removed.append(profile)

    if removed:
        backup_file = config_file.with_suffix(".json.bak.uninstall")
        shutil.copy2(config_file, backup_file)
        config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        print(f"  [ok] Removed profiles: {', '.join(removed)} from OpenCode.")
    else:
        print("  [ok] No Cortex profiles found in OpenCode config. Nothing to do.")
    return True


def uninstall_claude_code() -> bool:
    """Remove Cortex setup from CLAUDE.md in the current workspace."""
    print("\nRemoving Cortex instructions from Claude Code in current workspace...")
    claude_md = Path.cwd() / "CLAUDE.md"
    if not claude_md.exists():
        print("  [ok] CLAUDE.md not found. Nothing to do.")
        return True

    content = claude_md.read_text(encoding="utf-8")
    start_marker = "<!-- CORTEX INTEGRATION START -->"
    end_marker = "<!-- CORTEX INTEGRATION END -->"
    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker) + len(end_marker)
        new_content = content[:start_idx] + content[end_idx:]
        if new_content.strip() == "# Project Instructions" or not new_content.strip():
            claude_md.unlink()
            print("  [ok] Removed empty CLAUDE.md file.")
        else:
            claude_md.write_text(new_content, encoding="utf-8")
            print("  [ok] Removed Cortex instructions from CLAUDE.md.")
    else:
        print("  [ok] Cortex instructions not found in CLAUDE.md. Nothing to do.")

    print("\n  [!] To complete Claude Code uninstallation, run:")
    print("      claude mcp remove cortex-memory")
    return True


def install() -> None:
    """Main entrypoint for installing IDE profiles."""
    print("=== Cortex IDE Installer ===")
    install_opencode_profile()
    install_claude_code()
    print("============================")
    print("Installation complete.")


def uninstall() -> None:
    """Main entrypoint for uninstalling IDE profiles."""
    print("=== Cortex IDE Uninstaller ===")
    uninstall_opencode_profile()
    uninstall_claude_code()
    print("==============================")
    print("Uninstallation complete.")


if __name__ == "__main__":
    install()
