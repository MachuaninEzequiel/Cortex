"""
cortex.profile_injector
------------------------
Profile injection for Cortex Agents across different IDEs.

This module injects Cortex agent profiles (cortex-sync, cortex-SDDwork, etc.)
as configuration files in each IDE's native format. The profiles instruct the
IDE's native agent to use Cortex Engine tools for memory/search and IDE-native
delegation tools (Task, runSubagent, etc.) for subagent orchestration.
"""

from __future__ import annotations

import json
from pathlib import Path


def _find_cortex_project_root() -> Path:
    """Find the Cortex project root by looking for .cortex directory."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".cortex").exists():
            return parent
    raise FileNotFoundError("Could not find .cortex directory. Are you in a Cortex project?")


def _get_subagent_prompt(project_root: Path, subagent_name: str) -> str:
    """Read subagent prompt from .cortex/subagents/ directory."""
    subagent_path = project_root / ".cortex" / "subagents" / f"{subagent_name}.md"
    if subagent_path.exists():
        return subagent_path.read_text(encoding="utf-8")
    # Fallback: return basic prompt if file doesn't exist
    return f"# {subagent_name}\n\nYou are {subagent_name}, a Cortex subagent."


def _get_cortex_sync_prompt(project_root: Path) -> str:
    """Generate the cortex-sync profile prompt for IDEs."""
    return f"""# Cortex Sync - Pre-flight Analysis

You are Cortex-Sync, the pre-flight analysis agent. Your role is to prepare the ground for implementation by gathering context and creating technical specifications.

## ⚠️ MANDATORY FIRST STEP - NO EXCEPTIONS

**ANTES DE HACER CUALQUIER OTRA COSA, DEBES LLAMAR A `cortex_sync_ticket`**

This is a technical governance rule enforced by the Cortex Engine. If you attempt to call `cortex_create_spec` without first calling `cortex_sync_ticket`, the operation will be automatically rejected with a governance violation error.

## Your Mission

You are the **Pre-flight and Analysis Agent**. Your only goal is to prepare the ground for implementation.

### Strict Limits

1. **YOU CANNOT WRITE FILES**: You have write: false and edit: false
2. **YOU CANNOT EXECUTE COMMANDS**: You have bash: false
3. **YOU DO NOT IMPLEMENT**: Your final output is a persisted Spec and handoff to Cortex-SDDwork

## Mandatory Flow (DO NOT DEVIATE)

1. **⚠️ STEP 1 - MANDATORY CONTEXT INJECTION**: Your FIRST and MOST IMPORTANT step is to call `cortex_sync_ticket` with the current user request. This injects historical context via ONNX/hybrid retrieval.
2. **STEP 2 - EXPLORE**: Use glob and read to contrast the ticket with actual code.
3. **STEP 3 - SPECIFY**: Use `cortex_create_spec` to save the technical specification.
4. **STEP 4 - CLOSE**: Once the Spec is persisted, stop.

## Example of Correct Flow

User: "I need to change login.html to be more modern"

CORRECT:
1. cortex_sync_ticket(user_request="I need to change login.html to be more modern")
2. glob "**/*.html"
3. read login.html
4. cortex_create_spec(title="Modernize login.html", goal="Update styling...")
5. STOP and tell user: "✅ Spec completed. Switch to Cortex-SDDwork for implementation."

INCORRECT:
1. read login.html
2. cortex_create_spec(...) ← VIOLATION: cortex_sync_ticket not called first


## ⚠️ CRITICAL: STOP AFTER SPEC
NO reportar "implementation completed", NO marcar todos como completos

## Available Tools

- cortex_sync_ticket - MANDATORY first step
- cortex_search - Fast keyword search
- cortex_search_vector - Deep semantic search
- cortex_context - Enriched project context
- cortex_create_spec - Persist technical specification
- cortex_sync_vault - Sync vault

## Cortex Engine Integration

The Cortex Engine MCP server provides:
- cortex_sync_ticket: Injects historical context via ONNX/hybrid retrieval
- cortex_search: Fast keyword search (bypass AI)
- cortex_search_vector: Deep semantic search (requires ONNX model)
- cortex_context: Enriched project context with dependency graphs
- cortex_create_spec: Persist technical specifications in vault
- cortex_sync_vault: Sync and re-index vault documents

Use these tools to gather context before creating specifications.
"""


def _get_cortex_sddwork_prompt(project_root: Path) -> str:
    """Generate the cortex-SDDwork profile prompt for IDEs."""
    return f"""# Cortex SDDwork - Implementation Orchestrator

You are Cortex-SDDwork, the implementation orchestrator. Your role is to orchestrate subagents to implement specifications created by Cortex-Sync.

## ⚠️ STRICT GOVERNANCE RULES

1. **NEVER EDIT CODE DIRECTLY**: Your only function is to orchestrate subagents. You have write: false and edit: false.
2. **NEVER REPLACE SUBAGENTS WITH MANUAL WORK**: If a subagent fails, adjust the delegation and relaunch.
3. **USE IDE-NATIVE DELEGATION**: Use your IDE's native delegation tools (Task, runSubagent, @agent, delegate) to invoke subagents.
4. **ALWAYS END WITH DOCUMENTATION**: Every implementation must end by invoking cortex-documenter.

## Your Mission

You are the **Implementation Orchestrator**. Your only goal is to orchestrate subagents to implement the spec.

### Strict Limits

- **NO DIRECT EDITS**: You cannot write or edit files directly
- **NO MANUAL IMPLEMENTATION**: If a subagent fails, adjust the delegation and try again
- **NO SHORTCUTS**: Always follow the mandatory flow

## Mandatory Flow (DO NOT DEVIATE)

1. **STEP 1 - READ SPEC**: Read the technical specification created by Cortex-Sync.
2. **STEP 2 - DELEGATE**: Use your IDE's native delegation tools to invoke subagents with Cortex prompts:
   - For exploration: Use IDE's Explore subagent with cortex-code-explorer prompt
   - For implementation: Use IDE's General subagent with cortex-code-implementer prompt
   - For review: Use IDE's General subagent with cortex-code-reviewer prompt
   - For testing: Use IDE's General subagent with cortex-code-tester prompt
   - For documentation: Use IDE's General subagent with cortex-documenter prompt
3. **STEP 3 - CONSOLIDATE**: Gather results from all subagents and ensure spec compliance.
4. **STEP 4 - DOCUMENT**: Invoke cortex-documenter to persist the session in the vault.

## IDE-Native Delegation

Use your IDE's native delegation tools to invoke subagents:

- **OpenCode**: Use Task tool with subagent='General' or subagent='Explore', passing the Cortex subagent prompt
- **Cursor**: Use @general or @explore, then provide the Cortex subagent prompt
- **Claude Code**: Use Task with the Cortex subagent prompt
- **VS Code Copilot**: Use runSubagent with the Cortex subagent prompt
- **Zed**: Use delegate with the Cortex subagent prompt

The Cortex subagent prompts are defined in .cortex/subagents/*.md. Read them and pass them to the IDE's native subagents.

## Cortex Subagent Prompts

The Cortex subagent prompts are located in:
- .cortex/subagents/cortex-code-explorer.md
- .cortex/subagents/cortex-code-planner.md
- .cortex/subagents/cortex-code-implementer.md
- .cortex/subagents/cortex-code-reviewer.md
- .cortex/subagents/cortex-code-tester.md
- .cortex/subagents/cortex-documenter.md

Read these files to get the prompt for each Cortex subagent, then pass that prompt to the IDE's native subagent (General or Explore).

## Cortex Engine Integration

You have access to Cortex Engine tools for context gathering:

- `cortex_search`: Fast keyword search
- `cortex_context`: Enriched project context
- `cortex_search_vector`: Deep semantic search
- `cortex_save_session`: Document the session
- `cortex_sync_vault`: Sync the vault

Use these tools to gather context during orchestration.

## Example of Correct Flow (OpenCode)

1. Read spec from vault/specs/2026-04-20_*.md
2. Read .cortex/subagents/cortex-code-explorer.md to get the exploration prompt
3. Use Task(subagent='Explore', prompt=<exploration prompt>) to explore the codebase
4. Read .cortex/subagents/cortex-code-implementer.md to get the implementation prompt
5. Use Task(subagent='General', prompt=<implementation prompt>) to implement changes
6. Read .cortex/subagents/cortex-code-reviewer.md to get the review prompt
7. Use Task(subagent='General', prompt=<review prompt>) to review the implementation
8. Read .cortex/subagents/cortex-documenter.md to get the documentation prompt
9. Use Task(subagent='General', prompt=<documentation prompt>) to generate documentation
10. Call cortex_save_session to document the session

## Key Insight

Cortex subagents are NOT IDE profiles. They are PROMPTS that you pass to the IDE's native subagents (General, Explore). This allows Cortex to work with any IDE's native delegation system.
"""


def inject_opencode_profile():
    """Inject Cortex agent profiles for OpenCode."""
    print("[Cortex Profile Injector] Target: OpenCode")
    config_dir = Path.home() / ".config" / "opencode"
    config_file = config_dir / "opencode.json"
    config_dir.mkdir(parents=True, exist_ok=True)

    project_root = _find_cortex_project_root()

    # Create skills directory and write external skill files
    skills_dir = config_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Write cortex-sync skill file
    cortex_sync_skill = skills_dir / "cortex-sync.md"
    cortex_sync_skill.write_text(_get_cortex_sync_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Wrote cortex-sync skill to {cortex_sync_skill}")

    # Write cortex-SDDwork skill file
    cortex_sddwork_skill = skills_dir / "cortex-SDDwork.md"
    cortex_sddwork_skill.write_text(_get_cortex_sddwork_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Wrote cortex-SDDwork skill to {cortex_sddwork_skill}")

    # Create subagents directory and copy Cortex subagent prompts
    subagents_dir = config_dir / "subagents"
    subagents_dir.mkdir(parents=True, exist_ok=True)

    # Copy Cortex subagent prompts
    cortex_subagents_dir = project_root / ".cortex" / "subagents"
    if cortex_subagents_dir.exists():
        for subagent_file in cortex_subagents_dir.glob("*.md"):
            dest = subagents_dir / subagent_file.name
            dest.write_text(subagent_file.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  [OK] Copied {subagent_file.name} to {subagents_dir}")

    profiles = {
        "cortex-sync": {
            "mode": "primary",
            "description": "PRE-FLIGHT: Context gathering and spec preparation.",
            "prompt": "{file:/home/chucho/.config/opencode/skills/cortex-sync.md}",
            "tools": {
                "read": True,
                "write": False,
                "edit": False,
                "bash": False,
                "cortex_context": True,
                "cortex_search": True,
                "cortex_search_vector": True,
                "cortex_sync_ticket": True,
                "cortex_create_spec": True,
                "cortex_sync_vault": True,
            },
        },
        "cortex-SDDwork": {
            "mode": "primary",
            "description": "ORCHESTRATOR: Delegate subagents using IDE-native Task tool.",
            "prompt": "{file:/home/chucho/.config/opencode/skills/cortex-SDDwork.md}",
            "tools": {
                "read": True,
                "write": False,
                "edit": False,
                "bash": False,
                "cortex_context": True,
                "cortex_search": True,
                "cortex_search_vector": True,
                "cortex_save_session": True,
                "cortex_sync_vault": True,
                "Task": True,  # OpenCode's native delegation tool
            },
        },
    }

    # MCP configuration for Cortex Engine
    mcp_config = {
        "cortex": {
            "type": "local",
            "command": ["cortex", "mcp-server", "--stdio"],
            "enabled": True,
        }
    }

    config_data = {
        "agent": profiles,
        "mcp": mcp_config,
    }

    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex profiles and MCP config to {config_file}")


def inject_cursor_profile():
    """Inject Cortex agent profiles for Cursor."""
    print("[Cortex Profile Injector] Target: Cursor")
    agents_dir = Path.home() / ".cursor" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    project_root = _find_cortex_project_root()

    # cortex-sync
    cortex_sync_path = agents_dir / "cortex-sync.md"
    cortex_sync_path.write_text(_get_cortex_sync_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Injected cortex-sync profile to {cortex_sync_path}")

    # cortex-SDDwork
    cortex_sddwork_path = agents_dir / "cortex-SDDwork.md"
    cortex_sddwork_path.write_text(_get_cortex_sddwork_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Injected cortex-SDDwork profile to {cortex_sddwork_path}")

    # MCP configuration for Cortex Engine
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    mcp_data = {"mcpServers": {}}
    if mcp_config_path.exists():
        try:
            mcp_data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    cortex_mcp_config = {
        "cortex": {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio"],
            "env": {
                "PYTHONPATH": str(project_root),
                "PYTHONWARNINGS": "ignore",
            },
        }
    }

    mcp_data.setdefault("mcpServers", {})
    mcp_data["mcpServers"].update(cortex_mcp_config)

    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex MCP config to {mcp_config_path}")


def inject_claude_code_profile():
    """Inject Cortex agent profiles for Claude Code."""
    print("[Cortex Profile Injector] Target: Claude Code")
    claude_config_dir = Path.home() / ".claude"
    claude_config_dir.mkdir(parents=True, exist_ok=True)

    project_root = _find_cortex_project_root()

    # cortex-sync
    cortex_sync_path = claude_config_dir / "cortex-sync.md"
    cortex_sync_path.write_text(_get_cortex_sync_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Injected cortex-sync profile to {cortex_sync_path}")

    # cortex-SDDwork
    cortex_sddwork_path = claude_config_dir / "cortex-SDDwork.md"
    cortex_sddwork_path.write_text(_get_cortex_sddwork_prompt(project_root), encoding="utf-8")
    print(f"  [OK] Injected cortex-SDDwork profile to {cortex_sddwork_path}")

    # MCP configuration for Cortex Engine in Claude Code
    claude_mcp_config_dir = Path.home() / ".config" / "claude"
    claude_mcp_config_dir.mkdir(parents=True, exist_ok=True)
    
    mcp_config_path = claude_mcp_config_dir / "mcp.json"
    mcp_data = {"mcpServers": {}}
    if mcp_config_path.exists():
        try:
            mcp_data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    cortex_mcp_config = {
        "cortex": {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio"],
            "env": {
                "PYTHONPATH": str(project_root),
                "PYTHONWARNINGS": "ignore",
            },
        }
    }

    mcp_data.setdefault("mcpServers", {})
    mcp_data["mcpServers"].update(cortex_mcp_config)

    mcp_config_path.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex MCP config to {mcp_config_path}")


def inject_claude_desktop_profile():
    """Inject Cortex MCP configuration for Claude Desktop."""
    print("[Cortex Profile Injector] Target: Claude Desktop (MCP)")
    project_root = _find_cortex_project_root()
    config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    data = {"mcpServers": {}}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # MCP configuration for Cortex Engine
    mcp_config = {
        "cortex": {
            "command": "cortex",
            "args": ["mcp-server", "--stdio"],
            "env": {
                "PYTHONPATH": str(project_root),
                "PYTHONWARNINGS": "ignore",
            },
            "enabled": True,
        }
    }

    data.setdefault("mcpServers", {})
    data["mcpServers"].update(mcp_config)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex MCP config to {config_path}")

    # Claude Desktop doesn't use agent profiles like OpenCode - subagents are invoked via MCP tools


def inject_vscode_profile():
    """Inject Cortex agent profiles for VS Code Copilot."""
    print("[Cortex Profile Injector] Target: VS Code Copilot")
    
    # Find the project root for .github/copilot-instructions.md
    project_root = _find_cortex_project_root()
    github_dir = project_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)

    # Create combined instructions file with only cortex-sync and cortex-SDDwork
    combined_prompt = f"""# Cortex Agent Profiles

## cortex-sync
{_get_cortex_sync_prompt(project_root)}

## cortex-SDDwork
{_get_cortex_sddwork_prompt(project_root)}
"""
    instructions_path = github_dir / "copilot-instructions.md"
    instructions_path.write_text(combined_prompt, encoding="utf-8")
    print(f"  [OK] Injected Cortex profiles to {instructions_path}")

    # MCP configuration for Cortex Engine in VS Code settings.json
    vscode_config_dir = Path.home() / ".config" / "Code" / "User"
    vscode_config_dir.mkdir(parents=True, exist_ok=True)
    
    settings_path = vscode_config_dir / "settings.json"
    settings_data = {}
    if settings_path.exists():
        try:
            settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    cortex_mcp_config = {
        "github.copilot.mcp.servers": {
            "cortex": {
                "type": "stdio",
                "command": "cortex",
                "args": ["mcp-server", "--stdio"],
                "env": {
                    "PYTHONPATH": str(project_root),
                    "PYTHONWARNINGS": "ignore",
                },
            }
        }
    }

    settings_data.update(cortex_mcp_config)

    settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex MCP config to {settings_path}")


def inject_zed_profile():
    """Inject Cortex agent profiles for Zed."""
    print("[Cortex Profile Injector] Target: Zed")
    zed_config_dir = Path.home() / ".zed"
    zed_config_dir.mkdir(parents=True, exist_ok=True)

    project_root = _find_cortex_project_root()

    # Create agents.json
    agents_config = {
        "agents": {
            "cortex-sync": {
                "name": "Cortex Sync",
                "description": "Pre-flight analysis with context injection",
                "system_prompt": _get_cortex_sync_prompt(project_root),
            },
            "cortex-SDDwork": {
                "name": "Cortex SDDwork",
                "description": "Implementation orchestrator",
                "system_prompt": _get_cortex_sddwork_prompt(project_root),
            },
        }
    }

    agents_path = zed_config_dir / "agents.json"
    agents_path.write_text(json.dumps(agents_config, indent=2), encoding="utf-8")
    print(f"  [OK] Injected Cortex profiles to {agents_path}")


def inject(ide: str | None = None):
    """
    Inject Cortex agent profiles for specified IDE or all IDEs.
    
    Args:
        ide: IDE name ('opencode', 'cursor', 'claude', 'claude-desktop', 'vscode', 'zed'). 
             If None, injects for all available IDEs.
    """
    if ide:
        ide = ide.lower()
        if ide == "opencode":
            inject_opencode_profile()
        elif ide == "cursor":
            inject_cursor_profile()
        elif ide == "claude":
            inject_claude_code_profile()
        elif ide == "claude-desktop":
            inject_claude_desktop_profile()
        elif ide == "vscode":
            inject_vscode_profile()
        elif ide == "zed":
            inject_zed_profile()
        else:
            print(f"  [ERROR] Unknown IDE: {ide}")
            print(f"  Available IDEs: opencode, cursor, claude, claude-desktop, vscode, zed")
    else:
        # Inject for all IDEs
        print("[Cortex Profile Injector] Injecting profiles for all IDEs...")
        inject_opencode_profile()
        inject_cursor_profile()
        inject_claude_code_profile()
        inject_claude_desktop_profile()
        inject_vscode_profile()
        inject_zed_profile()
        print("[Cortex Profile Injector] All profiles injected successfully.")


def uninstall():
    """Remove Cortex agent profiles from all IDEs."""
    print("[Cortex Profile Uninstaller] Removing profiles...")
    # TODO: Implement uninstall logic for each IDE
    print("[Cortex Profile Uninstaller] Uninstall not yet implemented.")


if __name__ == "__main__":
    inject()
