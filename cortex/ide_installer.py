import json
import os
import sys
import shutil
from pathlib import Path

def get_opencode_config_path():
    """Returns the path to the opencode config directory (~/.config/opencode)."""
    home_dir = Path.home()
    return home_dir / ".config" / "opencode"

def install_opencode_profile():
    """Injects the cortex-orchestrator into opencode.json"""
    print("Installing Cortex profile into OpenCode...")
    config_dir = get_opencode_config_path()
    
    if not config_dir.exists():
        print(f"  [!] OpenCode config directory not found at {config_dir}.")
        print("  [!] Please run OpenCode at least once or create the directory.")
        return False
        
    config_file = config_dir / "opencode.json"
    
    if not config_file.exists():
        # Create a new minimal config if it doesn't exist
        config_data = {"agent": {}}
    else:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            print(f"  [X] Error: Could not parse {config_file}. Is it valid JSON?")
            return False

    if "agent" not in config_data:
        config_data["agent"] = {}
        
    # Get the absolute path to our agent_guidelines.md
    base_dir = Path(__file__).resolve().parent
    guidelines_path = base_dir / "agent_guidelines.md"
    
    if not guidelines_path.exists():
        print(f"  [X] Error: Could not find {guidelines_path}. Cortex installation might be corrupt.")
        return False

    # Create the Cortex orchestrator definition
    # Using {file:...} syntax native to OpenCode if it supports it, 
    # but to be safe and compatible with standard OpenCode features, 
    # we inject `{file:ABSOLUTE_PATH}` which OpenCode expands.
    cortex_agent = {
        "mode": "primary",
        "description": "Cortex Orchestrator - Enterprise Governance Memory Enabled.",
        "model": "anthropic/claude-3-5-sonnet-20241022",
        "prompt": f"{{file:{str(guidelines_path)}}}",
        "permission": {
            "task": {
                "*": "deny",
                "sdd-*": "allow"
            }
        },
        "tools": {
            "read": True,
            "write": True,
            "edit": True,
            "bash": True,
            "delegate": True,
            "delegation_read": True,
            "delegation_list": True
        }
    }
    
    config_data["agent"]["cortex-orchestrator"] = cortex_agent
    
    # Backup original config
    if config_file.exists():
        backup_file = config_file.with_suffix(".json.bak")
        shutil.copy2(config_file, backup_file)
        print(f"  [ok] Created backup of opencode.json at {backup_file}")

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
        
    print(f"  [ok] Installed 'cortex-orchestrator' into {config_file}.")
    print("  [ok] You can now switch to Cortex by pressing Tab in OpenCode.")
    return True

def install_claude_code():
    """Sets up CLAUDE.md for Claude Code in the current workspace."""
    print("\nSetting up Cortex instructions for Claude Code in current workspace...")
    current_dir = Path.cwd()
    claude_md = current_dir / "CLAUDE.md"
    
    base_dir = Path(__file__).resolve().parent
    guidelines_path = base_dir / "agent_guidelines.md"
    
    instruction_block = (
        "\n\n<!-- CORTEX INTEGRATION START -->\n"
        "# 🧠 Cortex Context Checklist\n"
        "You are working in a Cortex-governed repository. Before fulfilling ANY task:\n"
        "1. Check for updates in the vault/ folder. Run `git fetch`.\n"
        "2. If remote commits exist that are not available locally, you MUST STOP and explicitly ask:\n"
        "   > \"Encontré actualizaciones en el repo de las memorias, ¿hago pull?\"\n"
        "3. Wait for the user's approval before running `git pull`.\n"
        "4. Only then, proceed to use MCP tools (like cortex_context or cortex_search) to enrich your context.\n"
        "<!-- CORTEX INTEGRATION END -->\n"
    )

    if claude_md.exists():
        with open(claude_md, "r", encoding="utf-8") as f:
            content = f.read()
        if "<!-- CORTEX INTEGRATION START -->" in content:
            print("  [ok] CLAUDE.md already has Cortex integration.")
        else:
            with open(claude_md, "a", encoding="utf-8") as f:
                f.write(instruction_block)
            print("  [ok] Appended Cortex instructions to CLAUDE.md.")
    else:
        with open(claude_md, "w", encoding="utf-8") as f:
            f.write("# Project Instructions\n")
            f.write(instruction_block)
        print("  [ok] Created CLAUDE.md with Cortex instructions.")
        
    print("\n  [!] To complete Claude Code setup, run the following command to register the MCP server:")
    print("      claude mcp add cortex-memory \"cortex\" \"mcp-server\"")
    return True

def uninstall_opencode_profile():
    """Removes the cortex-orchestrator from opencode.json"""
    print("Uninstalling Cortex profile from OpenCode...")
    config_dir = get_opencode_config_path()
    config_file = config_dir / "opencode.json"
    
    if not config_file.exists():
        print(f"  [ok] OpenCode config not found at {config_file}. Nothing to do.")
        return True
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except json.JSONDecodeError:
        print(f"  [X] Error: Could not parse {config_file}.")
        return False
        
    if "agent" in config_data and "cortex-orchestrator" in config_data["agent"]:
        # Backup before modifying
        backup_file = config_file.with_suffix(".json.bak.uninstall")
        shutil.copy2(config_file, backup_file)
        
        del config_data["agent"]["cortex-orchestrator"]
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        print("  [ok] Successfully removed 'cortex-orchestrator' from OpenCode.")
    else:
        print("  [ok] 'cortex-orchestrator' not found in OpenCode config. Nothing to do.")
    return True

def uninstall_claude_code():
    """Removes Cortex setup from Claude Code."""
    print("\nRemoving Cortex instructions from Claude Code in current workspace...")
    current_dir = Path.cwd()
    claude_md = current_dir / "CLAUDE.md"
    
    if claude_md.exists():
        with open(claude_md, "r", encoding="utf-8") as f:
            content = f.read()
            
        if "<!-- CORTEX INTEGRATION START -->" in content and "<!-- CORTEX INTEGRATION END -->" in content:
            # We remove the block including the markdown tags
            start_idx = content.find("<!-- CORTEX INTEGRATION START -->")
            end_idx = content.find("<!-- CORTEX INTEGRATION END -->") + len("<!-- CORTEX INTEGRATION END -->\n")
            
            new_content = content[:start_idx] + content[end_idx:]
            
            # If the file is basically empty now (just whitespace and maybe the header), we could delete it, but let's just write it
            if new_content.strip() == "# Project Instructions" or not new_content.strip():
                claude_md.unlink()
                print("  [ok] Removed empty CLAUDE.md file.")
            else:
                with open(claude_md, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print("  [ok] Removed Cortex instructions from CLAUDE.md.")
        else:
            print("  [ok] Cortex instructions not found in CLAUDE.md. Nothing to do.")
    else:
        print("  [ok] CLAUDE.md not found. Nothing to do.")
        
    print("\n  [!] To complete Claude Code uninstallation, run the following command to remove the MCP server:")
    print("      claude mcp remove cortex-memory")
    return True

def install():
    """Main entrypoint for installing IDE profiles."""
    print("=== Cortex IDE Installer ===")
    install_opencode_profile()
    install_claude_code()
    print("============================")
    print("Installation complete.")

def uninstall():
    """Main entrypoint for uninstalling IDE profiles."""
    print("=== Cortex IDE Uninstaller ===")
    uninstall_opencode_profile()
    uninstall_claude_code()
    print("==============================")
    print("Uninstallation complete.")

if __name__ == "__main__":
    install()
