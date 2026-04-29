"""
cortex.cli.main
---------------
Command-line interface for cortex.

Commands
--------
init              Bootstrap .memory/ and vault/ directory with default config.
setup             Full project setup with auto-detection and CI/CD integration.
context           Get enriched context for current work.
save-session      Persist a structured session note into the Cortex vault.
create-spec       Persist an implementation specification into the Cortex vault.
verify-docs       Check if PR includes agent-generated documentation.
validate-docs     Validate markdown docs stored in the vault.
index-docs        Index vault docs as semantic memory.
doctor            Validate Cortex runtime, vault and Git governance state.
org-config        Display the resolved enterprise organization config.
promote-knowledge  Promote local knowledge into enterprise vault (requires review by default).
review-knowledge   Approve/reject promotion candidates (enterprise pipeline).
sync-enterprise-vault Validate + index the enterprise vault knowledge base.
agent-guidelines  Display agent behavior guidelines for session-end documentation.
install-skills    Install Obsidian skills into the project's .cortex/skills/ directory.
remember          Store a new episodic memory from the command line.
search            Query both memory layers and print results.
hu                Import and inspect tracked work item notes.
sync-vault        Re-index the markdown vault.
stats             Print memory store statistics.
forget            Delete an episodic memory by ID.
pr-context        PR documentation pipeline (DevSecDocOps).
install-ide       Install Cortex inside OpenCode / Claude Code locally.
mcp-server        Start the standard MCP Server for universal IDE usage.
"""

from __future__ import annotations

import sys
import warnings

# SILENCE PROTOCOL v2.14: Suprimir advertencias de runpy/typer antes de que toquen stdout
warnings.filterwarnings("ignore")

import asyncio
import getpass
import json
import subprocess
from enum import Enum
from pathlib import Path

import typer
import yaml

from cortex.core import AgentMemory
from cortex.webgraph.cli import app as webgraph_app

app = typer.Typer(
    name="cortex",
    help="Cortex -- hybrid cognitive memory for AI agents.",
    add_completion=False,
)
app.add_typer(webgraph_app, name="webgraph")

_DEFAULT_CONFIG = {
    "episodic": {
        "persist_dir": ".memory/chroma",
        "collection_name": "cortex_episodic",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_backend": "onnx",  # lightweight default (no PyTorch required)
    },
    "semantic": {
        "vault_path": "vault",
    },
    "retrieval": {
        "top_k": 5,
        "episodic_weight": 1.0,
        "semantic_weight": 1.0,
    },
    "llm": {
        "provider": "none",
        "model": "",
    },
}


class DoctorScope(str, Enum):
    PROJECT = "project"
    ENTERPRISE = "enterprise"
    ALL = "all"


# ---------------------------------------------------------------------------
# pr-context  (DevSecDocOps subcommand group)
# ---------------------------------------------------------------------------

pr_context_app = typer.Typer(help="PR documentation pipeline (DevSecDocOps).")
app.add_typer(pr_context_app, name="pr-context")
hu_app = typer.Typer(help="Tracked work item management (read-only external import).")
app.add_typer(hu_app, name="hu")


@pr_context_app.command("capture")
def pr_context_capture(
    title: str = typer.Option("Untitled PR", help="PR title."),
    body: str = typer.Option("", help="PR body/description."),
    author: str = typer.Option("unknown", help="PR author."),
    branch: str = typer.Option("", help="Source branch."),
    commit: str = typer.Option("", help="Commit SHA."),
    pr_number: int = typer.Option(0, help="PR number."),
    target_branch: str = typer.Option("main", help="Target branch."),
    labels: str = typer.Option("", help="Comma-separated labels."),
    output: str = typer.Option(".pr-context.json", help="Output JSON file."),
) -> None:
    """Capture PR metadata and save as JSON context."""
    from cortex.pr_capture import capture_manual, save_context

    labels_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()] if labels else []

    ctx = capture_manual(
        title=title,
        body=body,
        author=author,
        branch=branch,
        commit=commit,
        pr_number=pr_number,
        target_branch=target_branch,
        labels=labels_list,
    )

    path = save_context(ctx, output)
    typer.echo(f"PR context captured -> {path}")
    typer.echo(f"   title: {ctx.title}")
    typer.echo(f"   author: {ctx.author}")
    typer.echo(f"   branch: {ctx.source_branch}")
    typer.echo(f"   files changed: {len(ctx.files_changed)}")


@pr_context_app.command("store")
def pr_context_store(
    context_file: str = typer.Option(".pr-context.json", help="PR context JSON file."),
    lint_result: str = typer.Option(None, help="Lint result (pass/fail)."),
    audit_result: str = typer.Option(None, help="Audit result (pass/fail)."),
    test_result: str = typer.Option(None, help="Test result (pass/fail)."),
) -> None:
    """Store PR context in episodic memory."""
    from cortex.pr_capture import capture_from_json, enrich_with_pipeline

    ctx = capture_from_json(context_file)
    ctx = enrich_with_pipeline(
        ctx,
        lint_result=lint_result,
        audit_result=audit_result,
        test_result=test_result,
    )

    mem = _load_memory()

    # Store as episodic memory
    summary = (
        f"PR #{ctx.pr_number}: {ctx.title} by {ctx.author} "
        f"({ctx.source_branch} -> {ctx.target_branch})"
    )
    content_parts = [summary]
    if ctx.body:
        content_parts.append(f"\nDescription: {ctx.body[:500]}")
    if ctx.diff_summary:
        content_parts.append(f"\nDiff:\n{ctx.diff_summary}")
    content_parts.append(f"\nLint: {ctx.lint_result or 'n/a'}")
    content_parts.append(f"\nAudit: {ctx.audit_result or 'n/a'}")
    content_parts.append(f"\nTests: {ctx.test_result or 'n/a'}")

    entry = mem.remember(
        content="\n".join(content_parts),
        memory_type="pr",
        tags=["pr", ctx.author] + ctx.labels,
        files=ctx.files_changed[:20],
    )
    typer.echo(f"PR context stored -> {entry.id}")


@pr_context_app.command("search")
def pr_context_search(
    context_file: str = typer.Option(".pr-context.json", help="PR context JSON file."),
    top_k: int = typer.Option(3, help="Max past PRs to return."),
    output: str = typer.Option(".past-context.json", help="Output JSON file."),
) -> None:
    """Search for similar past PRs in memory."""
    from cortex.pr_capture import capture_from_json

    ctx = capture_from_json(context_file)
    mem = _load_memory()

    query = f"{ctx.title} {ctx.body[:200]}"
    result = mem.retrieve(query, top_k=top_k)

    # Save to JSON
    Path(output).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Past context search saved -> {output}")

    # Print summary
    typer.echo(f"\nQuery: '{query[:100]}...'")
    if result.unified_hits:
        typer.echo(f"Found {len(result.unified_hits)} related memories:")
        for hit in result.unified_hits:
            typer.echo(f"  [{hit.source}] {hit.display_title} (score={hit.score:.4f})")
    else:
        typer.echo("No related memories found.")


@pr_context_app.command("generate")
def pr_context_generate(
    context_file: str = typer.Option(".pr-context.json", help="PR context JSON file."),
    vault: str = typer.Option("vault", help="Vault path for generated docs."),
) -> None:
    """Generate documentation from PR context."""
    from cortex.doc_generator import DocGenerator
    from cortex.pr_capture import capture_from_json

    ctx = capture_from_json(context_file)
    gen = DocGenerator(vault_path=vault)
    docs = gen.generate_all(ctx)
    written = gen.write_docs(docs)

    typer.echo(f"Generated {len(written)} documents:")
    for p in written:
        typer.echo(f"  {p}")


@pr_context_app.command("full")
def pr_context_full(
    title: str = typer.Option("Untitled PR", help="PR title."),
    body: str = typer.Option("", help="PR body/description."),
    author: str = typer.Option("unknown", help="PR author."),
    branch: str = typer.Option("", help="Source branch."),
    commit: str = typer.Option("", help="Commit SHA."),
    pr_number: int = typer.Option(0, help="PR number."),
    target_branch: str = typer.Option("main", help="Target branch."),
    labels: str = typer.Option("", help="Comma-separated labels."),
    lint_result: str = typer.Option(None, help="Lint result."),
    audit_result: str = typer.Option(None, help="Audit result."),
    test_result: str = typer.Option(None, help="Test result."),
    vault: str = typer.Option("vault", help="Vault path."),
    context_file: str = typer.Option(".pr-context.json", help="Context JSON file."),
) -> None:
    """Full pipeline: capture + store + search + generate + sync (all in one)."""
    from cortex.doc_generator import DocGenerator
    from cortex.pr_capture import capture_manual, enrich_with_pipeline, save_context

    typer.echo("🧠 Cortex DevSecDocOps — Full PR Context Pipeline")
    typer.echo("")

    # Step 1: Capture
    typer.echo("📸 Step 1: Capturing PR context...")
    labels_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()] if labels else []
    ctx = capture_manual(
        title=title,
        body=body,
        author=author,
        branch=branch,
        commit=commit,
        pr_number=pr_number,
        target_branch=target_branch,
        labels=labels_list,
    )
    ctx = enrich_with_pipeline(
        ctx,
        lint_result=lint_result,
        audit_result=audit_result,
        test_result=test_result,
    )
    path = save_context(ctx, context_file)
    typer.echo(f"  Context saved -> {path}")
    typer.echo("")

    # Step 2: Store in memory
    typer.echo("💾 Step 2: Storing in episodic memory...")
    mem = _load_memory()
    summary = (
        f"PR #{ctx.pr_number}: {ctx.title} by {ctx.author} "
        f"({ctx.source_branch} -> {ctx.target_branch})"
    )
    content_parts = [summary]
    if ctx.body:
        content_parts.append(f"\nDescription: {ctx.body[:500]}")
    if ctx.diff_summary:
        content_parts.append(f"\nDiff:\n{ctx.diff_summary}")
    content_parts.append(f"\nLint: {ctx.lint_result or 'n/a'}")
    content_parts.append(f"\nAudit: {ctx.audit_result or 'n/a'}")
    content_parts.append(f"\nTests: {ctx.test_result or 'n/a'}")

    entry = mem.remember(
        content="\n".join(content_parts),
        memory_type="pr",
        tags=["pr", ctx.author] + ctx.labels,
        files=ctx.files_changed[:20],
    )
    typer.echo(f"  Stored -> {entry.id}")
    typer.echo("")

    # Step 3: Search past context
    typer.echo("🔍 Step 3: Searching past context...")
    query = f"{ctx.title} {ctx.body[:200]}"
    result = mem.retrieve(query, top_k=3)
    if result.unified_hits:
        typer.echo(f"  Found {len(result.unified_hits)} related memories:")
        for hit in result.unified_hits:
            typer.echo(f"    [{hit.source}] {hit.display_title} (score={hit.score:.4f})")
    else:
        typer.echo("  No related memories found.")
    typer.echo("")

    # Step 4: Generate docs
    typer.echo("📄 Step 4: Generating documentation...")
    gen = DocGenerator(vault_path=vault)
    docs = gen.generate_all(ctx)
    written = gen.write_docs(docs)
    typer.echo(f"  Generated {len(written)} documents:")
    for p in written:
        typer.echo(f"    {p}")
    typer.echo("")

    # Step 5: Sync vault
    typer.echo("🔄 Step 5: Syncing vault...")
    count = mem.sync_vault()
    typer.echo(f"  Vault synced — {count} documents indexed.")
    typer.echo("")

    typer.echo("✅ DevSecDocOps pipeline complete")


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

setup_app = typer.Typer(help="Project setup with specialized profiles (agent, pipeline, full).")
app.add_typer(setup_app, name="setup")


@setup_app.command(name="agent")
def setup_agent(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes."
    ),
    git_depth: int = typer.Option(
        None, "--git-depth", help="Number of git commits to index for context."
    ),
    ide: str | None = typer.Option(
        None, "--ide", help="IDE to configure (skip prompt)."
    ),
) -> None:
    """
    Setup only local agent/cognitive components (Vault, Memory, .cortex, IDE).
    """
    import cortex.ide as cortex_ide
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    if git_depth is None:
        git_depth = typer.prompt("📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?", default=50, type=int)

    # IDE selection
    selected_ide = ide
    if selected_ide is None:
        typer.echo("\n🔧 Select IDE to configure:")
        supported = cortex_ide.get_supported_ides()
        for i, ide_name in enumerate(supported, 1):
            typer.echo(f"  {i}. {ide_name}")
        typer.echo("  0. Skip IDE configuration")

        choice = typer.prompt("\nEnter IDE number or name", default="0")

        if choice == "0":
            selected_ide = None
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(supported):
                selected_ide = supported[idx]
        elif choice in supported:
            selected_ide = choice
        else:
            typer.echo("⚠ Invalid selection, skipping IDE configuration.")
            selected_ide = None

    typer.echo("🧠 Cortex — Setting up Agent profile...")
    typer.echo("")

    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.AGENT, git_depth=git_depth, ide=selected_ide)
    typer.echo(format_summary(summary))


@setup_app.command(name="pipeline")
def setup_pipeline(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes."
    ),
) -> None:
    """
    Setup only CI/CD / DevOps components (Workflows, Scripts, Config).
    """
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    typer.echo("🧠 Cortex — Setting up Pipeline profile...")
    typer.echo("")

    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.PIPELINE)
    typer.echo(format_summary(summary))


@setup_app.command(name="full")
def setup_full(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes."
    ),
    git_depth: int = typer.Option(
        None, "--git-depth", help="Number of git commits to index for context."
    ),
) -> None:
    """
    Full project setup (Agent + Pipeline).
    """
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary
    if git_depth is None:
        git_depth = typer.prompt("📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?", default=50, type=int)
    typer.echo("🧠 Cortex — Setting up Full project...")
    typer.echo("")
    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.FULL, git_depth=git_depth)
    typer.echo(format_summary(summary))


@setup_app.command(name="webgraph")
def setup_webgraph(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes."
    ),
    attach_project_root: str | None = typer.Option(
        None,
        "--attach-project-root",
        help="Optional project root to register in .cortex/webgraph/workspace.yaml.",
    ),
) -> None:
    """
    Setup only the hybrid memory visualization module.
    """
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    del dry_run
    typer.echo("🧠 Cortex — Setting up WebGraph profile...")
    typer.echo("")

    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.WEBGRAPH, attach_project_root=attach_project_root)
    typer.echo(format_summary(summary))


@setup_app.command(name="enterprise")
def setup_enterprise(
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="Enterprise preset (small-company, multi-project-team, regulated-organization).",
    ),
    org_config: str | None = typer.Option(
        None,
        "--org-config",
        help="Path to YAML overrides merged on top of the selected preset.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without creating files.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Require preset/config input and skip wizard prompts.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print setup summary as JSON.",
    ),
) -> None:
    """Setup enterprise topology with wizard or declarative preset/config."""
    from cortex.enterprise.config import list_enterprise_presets
    from cortex.setup.enterprise_presets import (
        load_org_config_overrides,
        resolve_enterprise_setup,
        validate_enterprise_preset,
    )
    from cortex.setup.enterprise_wizard import run_enterprise_wizard
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    selected_preset = preset
    overrides: dict = {}
    if org_config:
        overrides = load_org_config_overrides(Path(org_config).expanduser().resolve())

    if not selected_preset and not org_config:
        if non_interactive:
            typer.echo(
                "Non-interactive mode requires --preset or --org-config.",
                err=True,
            )
            raise typer.Exit(code=1)
        selected_preset, wizard_overrides = run_enterprise_wizard()
        overrides = {**overrides, **wizard_overrides}
    elif not selected_preset:
        selected_preset = "small-company"

    if selected_preset:
        selected_preset = validate_enterprise_preset(selected_preset)
    else:
        selected_preset = "small-company"

    if selected_preset == "custom" and not org_config:
        typer.echo("Preset 'custom' requires --org-config.", err=True)
        raise typer.Exit(code=1)

    resolved = resolve_enterprise_setup(
        project_name=Path.cwd().name,
        profile=selected_preset,
        overrides=overrides,
        github_actions_enabled=True,
    )

    typer.echo("🧠 Cortex — Setting up Enterprise profile...")
    typer.echo(f"Preset: {resolved.profile}")
    typer.echo(f"Supported presets: {', '.join(list_enterprise_presets())}")
    typer.echo("")

    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(
        mode=SetupMode.ENTERPRISE,
        dry_run=dry_run,
        enterprise_profile=resolved.profile,
        enterprise_overrides=resolved.overrides,
    )
    if json_output:
        typer.echo(json.dumps(summary, indent=2, default=str))
        return
    typer.echo(format_summary(summary))


# ---------------------------------------------------------------------------
# init (Alias for setup agent)
# ---------------------------------------------------------------------------

@app.command()
def init() -> None:
    """Bootstrap cortex: Alias for `cortex setup agent`."""
    setup_agent(dry_run=False)


@app.command()
def doctor(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where config.yaml lives).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail on warnings as well as hard errors.",
    ),
    scope: DoctorScope = typer.Option(
        DoctorScope.PROJECT,
        "--scope",
        help="Validation scope: project, enterprise, or all.",
    ),
) -> None:
    """Validate Cortex runtime prerequisites and governance state."""
    from cortex.doctor import run_doctor

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    report = run_doctor(root, scope=scope.value)

    for check in report.checks:
        if check.ok:
            typer.secho(f"[OK] {check.name}: {check.detail}", fg=typer.colors.GREEN)
            continue

        if check.severity == "fail":
            typer.secho(f"[FAIL] {check.name}: {check.detail}", fg=typer.colors.RED, err=True)
        elif check.severity == "warn":
            typer.secho(f"[WARN] {check.name}: {check.detail}", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"[INFO] {check.name}: {check.detail}", fg=typer.colors.BLUE)

    if report.has_failures:
        raise typer.Exit(code=1)
    if strict and report.has_warnings:
        raise typer.Exit(code=1)


@app.command(name="org-config")
def org_config(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where .cortex/org.yaml lives).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the resolved enterprise config as JSON.",
    ),
    required: bool = typer.Option(
        False,
        "--required",
        help="Fail if the enterprise config is missing.",
    ),
) -> None:
    """Display the resolved enterprise organization config."""
    from cortex.enterprise.config import (
        describe_enterprise_topology,
        discover_enterprise_config_path,
        load_enterprise_config,
    )

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    discovered = discover_enterprise_config_path(root)
    expected = root / ".cortex" / "org.yaml"
    if discovered is None:
        message = f"Enterprise config not found under {expected}"
        if required:
            typer.echo(message, err=True)
            raise typer.Exit(code=1)
        typer.echo(message)
        return

    try:
        config = load_enterprise_config(root, required=True, path=discovered)
    except Exception as exc:
        typer.echo(f"Failed to load enterprise config: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(config.model_dump_json(indent=2))
        return

    typer.echo(f"Enterprise config: {discovered}")
    typer.echo(f"Organization: {config.organization.name} ({config.organization.profile})")
    typer.echo(f"Topology: {describe_enterprise_topology(config, root)}")
    typer.echo("")
    typer.echo(yaml.safe_dump(config.model_dump(mode='json'), sort_keys=False, allow_unicode=False))


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------

@app.command()
def context(
    files: list[str] = typer.Option(
        [], "--files", "-f", help="Files to check context for."
    ),
    format: str = typer.Option(
        "markdown", "--format", help="Output format: markdown, compact, json."
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Save to file."
    ),
    expand: bool = typer.Option(
        False, "--expand", "-e", help="Show full content of items."
    ),
    no_graph: bool = typer.Option(
        False, "--no-graph", help="Skip graph expansion."
    ),
) -> None:
    """
    Get enriched context for current work.

    Automatically detects what you're working on and searches
    the project's memory for related memories.
    """
    mem = _load_memory()

    if not files:
        # Auto-detect from git staged files
        files = _get_staged_files()

    if not files:
        typer.echo("No changed files detected. Use --files to specify manually.")
        raise typer.Exit(1)

    enriched = mem.enrich(changed_files=files)

    # Format output
    if format == "json":
        typer.echo(enriched.model_dump_json(indent=2))
    elif format == "compact":
        typer.echo(enriched.to_prompt_format(compact=True))
    else:
        typer.echo(enriched.to_prompt_format(expand=expand))

    if output:
        if format == "json":
            Path(output).write_text(enriched.model_dump_json(indent=2), encoding="utf-8")
        elif format == "compact":
            Path(output).write_text(enriched.to_prompt_format(compact=True), encoding="utf-8")
        else:
            Path(output).write_text(enriched.to_prompt_format(expand=expand), encoding="utf-8")


# ---------------------------------------------------------------------------
# save-session
# ---------------------------------------------------------------------------

@app.command(name="save-session")
def save_session(
    title: str = typer.Option(..., help="Session title."),
    spec_summary: str = typer.Option(..., help="Original specification or task summary."),
    changes_made: list[str] = typer.Option([], "--change", help="Change description (repeatable)."),
    files_touched: list[str] = typer.Option([], "--file", help="Touched file (repeatable)."),
    key_decisions: list[str] = typer.Option([], "--decision", help="Key decision (repeatable)."),
    next_steps: list[str] = typer.Option([], "--next-step", help="Follow-up task (repeatable)."),
    tags: list[str] = typer.Option([], "--tag", help="Session tags (repeatable)."),
    no_sync: bool = typer.Option(False, "--no-sync", help="Skip vault sync after writing."),
) -> None:
    """Persist a structured session note into the vault."""
    mem = _load_memory()
    path = mem.save_session_note(
        title=title,
        spec_summary=spec_summary,
        changes_made=changes_made,
        files_touched=files_touched,
        key_decisions=key_decisions,
        next_steps=next_steps,
        tags=tags,
        sync_vault=not no_sync,
    )
    typer.echo(f"Session note saved -> {path}")


# ---------------------------------------------------------------------------
# create-spec
# ---------------------------------------------------------------------------

@app.command(name="create-spec")
def create_spec(
    title: str = typer.Option(..., help="Specification title."),
    goal: str = typer.Option(..., help="Primary implementation goal."),
    requirements: list[str] = typer.Option([], "--requirement", help="Requirement (repeatable)."),
    files_in_scope: list[str] = typer.Option([], "--file", help="File in scope (repeatable)."),
    constraints: list[str] = typer.Option([], "--constraint", help="Constraint (repeatable)."),
    acceptance_criteria: list[str] = typer.Option(
        [], "--acceptance", help="Acceptance criterion (repeatable)."
    ),
    tags: list[str] = typer.Option([], "--tag", help="Spec tags (repeatable)."),
    no_sync: bool = typer.Option(False, "--no-sync", help="Skip vault sync after writing."),
) -> None:
    """Persist an implementation spec into the vault."""
    mem = _load_memory()
    path = mem.create_spec_note(
        title=title,
        goal=goal,
        requirements=requirements,
        files_in_scope=files_in_scope,
        constraints=constraints,
        acceptance_criteria=acceptance_criteria,
        tags=tags,
        sync_vault=not no_sync,
    )
    typer.echo(f"Specification saved -> {path}")


# ---------------------------------------------------------------------------
# verify-docs
# ---------------------------------------------------------------------------

@app.command(name="verify-docs")
def verify_docs(
    vault: str = typer.Option("vault", help="Path to the vault directory."),
    base_branch: str = typer.Option("main", help="Branch to diff against."),
    changed_files: str = typer.Option(
        None, "--files", help="Comma-separated list of changed files (CI mode)."
    ),
    output: str = typer.Option(
        ".doc-status.json", help="Output JSON status file."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only output the boolean result (true/false)."
    ),
) -> None:
    """
    Verify whether the PR includes agent-generated documentation.

    Checks the vault/ directory for new or modified markdown files.
    Outputs a JSON status file for use in CI workflows.
    """
    from cortex.doc_verifier import DocVerifier

    vault_path = Path(vault)
    if not vault_path.exists():
        if not quiet:
            typer.echo(f"⚠ Vault directory not found: {vault}", err=True)
        Path(output).write_text('{"has_agent_docs": false, "errors": ["vault not found"]}', encoding="utf-8")
        typer.echo("false")
        raise typer.Exit(1)

    verifier = DocVerifier(vault_path=vault)

    if changed_files:
        files = [f.strip() for f in changed_files.split(",") if f.strip()]
        result = verifier.verify_from_list(files)
    else:
        result = verifier.verify_from_diff(base_branch=base_branch)

    # Write status
    Path(output).write_text(result.to_json(), encoding="utf-8")

    if result.has_agent_docs:
        if not quiet:
            typer.echo(f"✅ Agent documentation found ({result.total_vault_files} files)")
            typer.echo(f"   New: {', '.join(result.new_files) or 'none'}")
            typer.echo(f"   Modified: {', '.join(result.modified_files) or 'none'}")
        typer.echo("true")
    else:
        if not quiet:
            typer.echo("⚠ No agent documentation found — fallback mode")
        typer.echo("false")


# ---------------------------------------------------------------------------
# validate-docs
# ---------------------------------------------------------------------------

@app.command(name="validate-docs")
def validate_docs(
    vault: str = typer.Option("vault", help="Path to the vault directory."),
    files: str = typer.Option(
        None,
        "--files",
        help="Comma-separated list of markdown files to validate (relative to repo root or vault).",
    ),
    output: str = typer.Option(
        ".doc-validation.json",
        help="Output JSON validation report.",
    ),
    strict_warnings: bool = typer.Option(
        False,
        "--strict-warnings",
        help="Treat validation warnings as blocking.",
    ),
) -> None:
    """Validate Cortex markdown docs stored in the vault."""
    from cortex.doc_validator import DocValidator

    vault_path = Path(vault)
    if not vault_path.exists():
        typer.echo(f"Vault directory not found: {vault}", err=True)
        Path(output).write_text('{"is_valid": false, "errors": ["vault not found"]}', encoding="utf-8")
        raise typer.Exit(1)

    validator = DocValidator(vault_path=vault_path)

    selected_files: list[Path]
    if files:
        selected_files = []
        for raw in [item.strip() for item in files.split(",") if item.strip()]:
            candidate = Path(raw)
            if not candidate.is_absolute():
                root_candidate = (Path.cwd() / candidate).resolve()
                vault_candidate = (vault_path / candidate).resolve()
                candidate = root_candidate if root_candidate.exists() else vault_candidate
            selected_files.append(candidate)
    else:
        selected_files = sorted(vault_path.rglob("*.md"))

    results = validator.validate_batch(selected_files)
    payload = {
        "is_valid": all(result.is_valid for result in results),
        "files": [result.to_dict() for result in results],
        "error_count": sum(len(result.errors) for result in results),
        "warning_count": sum(len(result.warnings) for result in results),
    }
    Path(output).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    if payload["error_count"]:
        typer.echo(f"Documentation validation failed with {payload['error_count']} error(s).", err=True)
        raise typer.Exit(1)
    if strict_warnings and payload["warning_count"]:
        typer.echo(
            f"Documentation validation raised {payload['warning_count']} warning(s) in strict mode.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(
        f"Documentation validation passed ({len(selected_files)} file(s), {payload['warning_count']} warning(s))."
    )


# ---------------------------------------------------------------------------
# index-docs
# ---------------------------------------------------------------------------

@app.command(name="index-docs")
def index_docs(
    vault: str = typer.Option("vault", help="Path to the vault directory."),
) -> None:
    """
    Index vault documentation as semantic memory.

    Reads all markdown files in the vault, parses frontmatter and content,
    and stores them as semantic memories for hybrid retrieval.
    """
    from cortex.doc_validator import DocValidator

    mem = _load_memory()

    validator = DocValidator(vault_path=vault)
    vault_path = Path(vault)
    md_files = list(vault_path.rglob("*.md"))

    if not md_files:
        typer.echo("No markdown files found in vault.")
        return

    typed_files = []
    skipped = []
    for f in md_files:
        rel = str(f.relative_to(vault_path))
        vr = validator.validate_file(f)
        if vr.is_valid or not vr.errors:
            typed_files.append(rel)
        else:
            skipped.append(rel)
            for err in vr.errors:
                typer.echo(f"  ⚠ {rel}: {err.message}")

    count = mem.sync_vault()
    typer.echo(f"Indexed {count} documents from vault/")
    if skipped:
        typer.echo(f"Skipped {len(skipped)} files with errors: {', '.join(skipped)}")


# ---------------------------------------------------------------------------
# agent-guidelines
# ---------------------------------------------------------------------------

@app.command(name="agent-guidelines")
def agent_guidelines() -> None:
    """
    Display agent behavior guidelines.

    Shows the guidelines that AI agents should follow when working
    with this project. These guidelines instruct agents to generate
    documentation at the end of each work session.
    """
    import importlib.resources as importlib_resources
    try:
        content = importlib_resources.files("cortex").joinpath("agent_guidelines.md").read_text(encoding="utf-8")
    except AttributeError:
        content = (Path(__file__).parent.parent / "agent_guidelines.md").read_text(encoding="utf-8")

    typer.echo(content)


# ---------------------------------------------------------------------------
# install-skills
# ---------------------------------------------------------------------------

@app.command(name="install-skills")
def install_skills(
    dest: str = typer.Option(
        ".cortex/skills", help="Directory to install skills into."
    ),
) -> None:
    """
    Install Obsidian skills into the project.

    Copies bundled Obsidian Markdown skills (obsidian-markdown, json-canvas,
    obsidian-bases, obsidian-cli, defuddle) into the target directory so
    that AI agents working on this project know how to write proper docs.
    """
    from cortex.skills import install_skills as _install_skills

    target_path = Path(dest)
    installed = _install_skills(target_path)

    if installed:
        typer.echo(f"✅ Installed {len(installed)} skills into {dest}/")
        for skill in installed:
            typer.echo(f"   • {skill}")
    else:
        typer.echo("All skills already installed.")


# ---------------------------------------------------------------------------
# remember
# ---------------------------------------------------------------------------

@app.command()
def remember(
    content: str = typer.Argument(..., help="What the agent did / what happened."),
    memory_type: str = typer.Option("general", "--type", "-t", help="Memory category."),
    tags: list[str] = typer.Option([], "--tag", help="Tags (repeatable)."),
    files: list[str] = typer.Option([], "--file", help="Related files (repeatable)."),
    branch: str | None = typer.Option(None, "--branch", help="Explicit branch metadata override."),
    repo: str | None = typer.Option(None, "--repo", help="Explicit repo metadata override."),
    commit: str | None = typer.Option(None, "--commit", help="Attach one commit SHA as metadata."),
    summarize: bool = typer.Option(
        False,
        "--summarize",
        "-s",
        help="Compress with LLM (requires provider configured).",
    ),
) -> None:
    """Store a new episodic memory."""
    mem = _load_memory()

    if summarize and mem.config.llm.provider == "none":
        typer.echo(
            "⚠ Warning: --summarize was requested but no LLM provider is configured.\n"
            "  Falling back to simple truncation (300 chars).\n"
            "  Configure an LLM provider in config.yaml to enable true summarization.",
            err=True,
        )

    entry = mem.remember(
        content,
        memory_type=memory_type,
        tags=tags,
        files=files,
        summarize=summarize,
        extra_metadata={
            key: value
            for key, value in {
                "branch": branch,
                "repo": repo,
                "commit": commit,
            }.items()
            if value
        },
    )
    typer.echo(f"Memory stored -> {entry.id}")
    typer.echo(f"   type: {entry.memory_type}")
    typer.echo(f"   summary: {entry.content[:120]}")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@app.command()
def search(
    query: str = typer.Argument(..., help="Natural-language search query."),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Max results per source."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
    cross_branch: bool = typer.Option(
        False,
        "--cross-branch",
        help="Allow episodic results from other branches when branch namespacing is enabled.",
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help="Retrieval scope override: local, enterprise, all. If omitted, uses org default.",
    ),
    show_scores: bool = typer.Option(
        False,
        "--show-scores",
        help="Show per-hit metadata and source details.",
    ),
    project_id: str | None = typer.Option(
        None,
        "--project-id",
        help="Optional source project identifier filter.",
    ),
) -> None:
    """Query both memory layers and print results."""
    mem = _load_memory()
    if scope is not None and scope not in {"local", "enterprise", "all"}:
        typer.echo("Invalid --scope value. Use one of: local, enterprise, all.", err=True)
        raise typer.Exit(1)
    try:
        result = mem.retrieve(
            query,
            top_k=top_k,
            cross_branch=cross_branch,
            scope=scope,
            project_id=project_id,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"\nQuery: '{query}'\n")

    if result.unified_hits:
        typer.echo("Unified Results (RRF-fused across both sources):")
        for hit in result.unified_hits:
            source_tag = "EPISODIC" if hit.source == "episodic" else "SEMANTIC"
            details = f"  [{source_tag}] {hit.display_title}  ({hit.display_path})  score={hit.score:.4f}"
            if show_scores:
                details += (
                    f"  scope={hit.metadata.get('scope', 'local')}"
                    f" project_id={hit.metadata.get('project_id', '')}"
                )
            typer.echo(details)
        if show_scores and result.source_breakdown:
            typer.echo("")
            typer.echo(f"Source breakdown: {json.dumps(result.source_breakdown, ensure_ascii=True)}")
    else:
        if result.episodic_hits:
            typer.echo("Episodic Memory:")
            for e_hit in result.episodic_hits:
                e = e_hit.entry
                typer.echo(
                    f"  [{e.id}] ({e.memory_type}) {e.content[:80]}...  "
                    f"score={e_hit.score:.3f}"
                )
        else:
            typer.echo("Episodic Memory: (no results)")

        typer.echo("")

        if result.semantic_hits:
            typer.echo("Semantic Knowledge:")
            for doc in result.semantic_hits:
                typer.echo(f"  {doc.title} ({doc.path})  score={doc.score:.3f}")
        else:
            typer.echo("Semantic Knowledge: (no results)")


# ---------------------------------------------------------------------------
# Enterprise promotion pipeline (EPIC 3)
# ---------------------------------------------------------------------------


@app.command(name="promote-knowledge")
def promote_knowledge(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where .cortex/org.yaml lives).",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Dry-run by default. Use --apply to execute promotion.",
    ),
    actor: str | None = typer.Option(
        None,
        "--actor",
        help="Actor name for audit records (default: current OS user).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output raw JSON payload (plan + results).",
    ),
) -> None:
    """Promote reviewed knowledge candidates into the enterprise vault."""
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    actor_name = actor or getpass.getuser()
    service = KnowledgePromotionService.from_project_root(root)
    plan = service.plan_promotion()

    payload: dict[str, object] = {
        "project_root": str(root),
        "enterprise_vault": str(service.paths.enterprise_vault),
        "dry_run": dry_run,
        "planned": [c.model_dump(mode="json") for c in plan],
    }

    if dry_run:
        if json_output:
            typer.echo(json.dumps(payload, indent=2, default=str))
            return
        if not plan:
            typer.echo("No reviewed candidates ready for promotion.")
            return
        typer.echo(f"Planned promotions: {len(plan)}")
        for c in plan:
            typer.echo(f"  - {c.local_rel_path} -> {c.dest_rel_path}  ({c.origin_id})")
        return

    written = service.apply_promotion(candidates=plan, actor=actor_name)
    payload["written"] = [r.model_dump(mode="json") for r in written]

    if json_output:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    typer.echo(f"Promoted {len(written)} document(s) into {service.paths.enterprise_vault}")
    for r in written:
        typer.echo(f"  - {r.local_rel_path} -> {r.dest_rel_path}  ({r.origin_id})")


@app.command(name="review-knowledge")
def review_knowledge(
    selector: str = typer.Argument(..., help="Candidate selector: origin_id or vault-relative path."),
    approve: bool = typer.Option(
        True,
        "--approve/--reject",
        help="Approve by default. Use --reject to reject a candidate.",
    ),
    actor: str | None = typer.Option(
        None,
        "--actor",
        help="Actor name for audit records (default: current OS user).",
    ),
    reason: str | None = typer.Option(
        None,
        "--reason",
        help="Optional rationale for approve/reject.",
    ),
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where .cortex/org.yaml lives).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON record."),
) -> None:
    """Approve or reject a promotion candidate (review is required by default)."""
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    actor_name = actor or getpass.getuser()
    service = KnowledgePromotionService.from_project_root(root)
    try:
        record = service.review(selector=selector, approve=approve, actor=actor_name, reason=reason)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if json_output:
        typer.echo(record.model_dump_json(indent=2))
        return

    typer.echo(f"Recorded review: {record.origin_id}")
    typer.echo(f"  status: {record.status}")
    if record.decision:
        typer.echo(f"  decision: {record.decision.decision} by {record.decision.actor}")


@app.command(name="sync-enterprise-vault")
def sync_enterprise_vault(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where .cortex/org.yaml lives).",
    ),
    output: str = typer.Option(
        ".enterprise-doc-validation.json",
        help="Output JSON validation report for the enterprise vault.",
    ),
    strict_warnings: bool = typer.Option(
        False,
        "--strict-warnings",
        help="Treat validation warnings as blocking.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output raw JSON payload (validation + index summary).",
    ),
) -> None:
    """Validate and index the enterprise vault knowledge base."""
    from cortex.doc_validator import DocValidator
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService
    from cortex.semantic.vault_reader import VaultReader

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    service = KnowledgePromotionService.from_project_root(root)
    enterprise_vault = service.paths.enterprise_vault
    if not enterprise_vault.exists():
        typer.echo(f"Enterprise vault directory not found: {enterprise_vault}", err=True)
        raise typer.Exit(1)

    validator = DocValidator(vault_path=enterprise_vault)
    md_files = sorted(enterprise_vault.rglob("*.md"))
    results = validator.validate_batch(md_files)
    payload = {
        "enterprise_vault": str(enterprise_vault),
        "is_valid": all(r.is_valid for r in results),
        "files": [r.to_dict() for r in results],
        "error_count": sum(len(r.errors) for r in results),
        "warning_count": sum(len(r.warnings) for r in results),
    }
    Path(output).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    if payload["error_count"]:
        if json_output:
            typer.echo(json.dumps(payload, indent=2, default=str))
        typer.echo(f"Enterprise vault validation failed with {payload['error_count']} error(s).", err=True)
        raise typer.Exit(1)
    if strict_warnings and payload["warning_count"]:
        if json_output:
            typer.echo(json.dumps(payload, indent=2, default=str))
        typer.echo(
            f"Enterprise vault validation raised {payload['warning_count']} warning(s) in strict mode.",
            err=True,
        )
        raise typer.Exit(1)

    mem = _load_memory()
    reader = VaultReader(
        vault_path=str(enterprise_vault),
        embedding_model=mem.config.episodic.embedding_model,
        embedding_backend=mem.config.episodic.embedding_backend,
    )
    indexed = reader.sync()
    payload["indexed_docs"] = indexed

    if json_output:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    typer.echo(
        f"Enterprise vault synced ({indexed} docs indexed, {payload['warning_count']} warning(s)). "
        f"Validation report: {output}"
    )


# ---------------------------------------------------------------------------
# sync-vault
# ---------------------------------------------------------------------------

@app.command(name="sync-vault")
def sync_vault() -> None:
    """Re-index the markdown vault."""
    mem = _load_memory()
    count = mem.sync_vault()
    typer.echo(f"Vault synced -- {count} documents indexed.")


# ---------------------------------------------------------------------------
# IDE / MCP
# ---------------------------------------------------------------------------

@app.command()
def install_ide(
    ide: str | None = typer.Option(None, "--ide", help="IDE to configure (e.g. opencode, cursor, claude-code)."),
    all_ides: bool = typer.Option(False, "--all", help="Configure all IDE adapters (deprecated/experimental)."),
) -> None:
    """Install Cortex agent profiles and MCP config in supported IDEs."""
    from cortex.ide import get_supported_ides, inject, inject_all

    if all_ides or ide is None:
        typer.echo("Warning: --all uses deprecated/experimental bulk installation. Prefer --ide <name>.")
        inject_all(project_root=Path.cwd())
        return

    inject(ide, project_root=Path.cwd())
    typer.echo(f"Supported IDEs: {', '.join(get_supported_ides())}")

@app.command()
def uninstall_ide(
    ide: str | None = typer.Option(None, "--ide", help="IDE to clean (e.g. opencode, cursor, claude-code)."),
    all_ides: bool = typer.Option(False, "--all", help="Clean all IDE adapters (deprecated/experimental)."),
) -> None:
    """Remove Cortex agent profiles and MCP config from supported IDEs."""
    from cortex.ide import uninstall, uninstall_all

    if all_ides or ide is None:
        typer.echo("Warning: --all uses deprecated/experimental bulk removal. Prefer --ide <name>.")
        uninstall_all()
        return

    uninstall(ide)

@app.command(name="mcp-server")
def mcp_server(
    project_root: str = typer.Option(None, "--project-root", help="Ruta absoluta al directorio del proyecto Cortex (donde está config.yaml)."),
    stdio: bool = typer.Option(True, "--stdio", help="Use stdio transport (required for IDE integration)."),
) -> None:
    """Start the Cortex v2.1 MCP Server (stdio transport).
    
    Para integración con IDEs (Cursor, VSCode, Claude Desktop), usa --project-root
    para especificar la ruta del proyecto Cortex cuando el cwd del IDE no coincide
    con el directorio del proyecto.
    """
    import sys
    
    # Determinar el directorio raíz del proyecto
    root = Path(project_root) if project_root else Path.cwd()
    
    # Redirección temporal de stdout a stderr para proteger el handshake JSON-RPC
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    
    try:
        from cortex.mcp.server import CortexMCPServer
        server = CortexMCPServer(project_root=root)
    finally:
        sys.stdout = old_stdout
        
    asyncio.run(server.run())

@app.command(name="mcp-serve", hidden=True)
def mcp_serve_legacy() -> None:
    """Legacy alias for mcp-server."""
    mcp_server()

@app.command(name="inject")
def inject(
    ide: str | None = typer.Option(None, "--ide", help="IDE to inject (canonical names or aliases such as claude-code / claude-desktop)."),
) -> None:
    """Inject Cortex agent profiles into the specified IDE.

    This injects Cortex agent prompts (cortex-sync, cortex-SDDwork) in the
    native format of each IDE. The profiles instruct the IDE's native agent
    to use Cortex Engine tools for memory/search and IDE-native delegation
    tools for subagent orchestration.

    IMPORTANT: Cortex performs a safe merge of configurations:
    - JSON files: Deep merge (preserves existing settings)
    - Markdown files: Writes with autogeneration header (never overwrites manual edits)
    - Automatic backup created before any modification
    """
    import cortex.ide as cortex_ide

    if ide:
        # Direct injection for specified IDE
        cortex_ide.inject(ide, project_root=Path.cwd())
        typer.echo(f"\n✅ Successfully configured {ide}")
        typer.echo("Run 'cortex inject' again to configure another IDE.")
    else:
        # Interactive selection
        supported = cortex_ide.get_supported_ides()
        typer.echo("\n🔧 Cortex IDE Configuration")
        typer.echo("=" * 40)
        typer.echo("Select an IDE to configure:")
        for i, ide_name in enumerate(supported, 1):
            typer.echo(f"  {i}. {ide_name}")

        choice = typer.prompt("\nEnter IDE number or name", default="")

        # Parse choice
        selected_ide = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(supported):
                selected_ide = supported[idx]
        elif choice in supported:
            selected_ide = choice

        if selected_ide:
            cortex_ide.inject(selected_ide, project_root=Path.cwd())
            typer.echo(f"\n✅ Successfully configured {selected_ide}")
            typer.echo("Run 'cortex inject' again to configure another IDE.")
        else:
            typer.echo(f"❌ Invalid selection. Supported IDEs: {', '.join(supported)}")


@app.command(name="sync-ide")
def sync_ide(
    ide: str = typer.Option(..., "--ide", help="IDE to sync (required)."),
    force: bool = typer.Option(False, "--force", help="Force regeneration even if file exists."),
) -> None:
    """Sync IDE configuration with current .cortex/skills/ content.

    This regenerates the IDE configuration files from the current .cortex/skills/
    and .cortex/subagents/ content. Use this after modifying Cortex skills to
    update your IDE configuration.

    The generated files include an autogeneration header with the command to
    regenerate them manually.
    """
    import cortex.ide as cortex_ide

    cortex_ide.inject(ide, project_root=Path.cwd())
    typer.echo(f"\n✅ Successfully synced {ide} configuration")
    typer.echo("Configuration regenerated from .cortex/skills/ and .cortex/subagents/")

@hu_app.command("import")
def hu_import(
    external_id: str = typer.Argument(..., help="External item key, for example PROJ-123."),
    provider: str = typer.Option("jira", "--provider", help="External provider name."),
    no_remember: bool = typer.Option(False, "--no-remember", help="Skip episodic summary storage."),
) -> None:
    """Import one external tracked item into ``vault/hu/``."""
    mem = _load_memory()
    path = mem.import_work_item(external_id, provider=provider, remember=not no_remember)
    typer.echo(f"Tracked item imported -> {path}")


@hu_app.command("list")
def hu_list() -> None:
    """List tracked item notes already stored in ``vault/hu/``."""
    mem = _load_memory()
    notes = mem.list_work_item_notes()
    if not notes:
        typer.echo("No tracked items imported yet.")
        return
    for note in notes:
        typer.echo(str(note))


@hu_app.command("show")
def hu_show(
    item_id: str = typer.Argument(..., help="Tracked item ID, for example PROJ-123."),
) -> None:
    """Show the local vault note path for one tracked item."""
    mem = _load_memory()
    try:
        note = mem.get_work_item_note(item_id)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(str(note))


@app.command()
def stats() -> None:
    """Print memory store statistics."""
    mem = _load_memory()
    s = mem.stats()
    typer.echo(json.dumps(s, indent=2))


# ---------------------------------------------------------------------------
# forget
# ---------------------------------------------------------------------------

@app.command()
def forget(
    memory_id: str = typer.Argument(..., help="ID of the memory to delete (e.g. mem_abc123)."),
) -> None:
    """Delete an episodic memory by ID."""
    mem = _load_memory()
    ok = mem.forget(memory_id)
    if ok:
        typer.echo(f"Memory {memory_id} deleted.")
    else:
        typer.echo(
            f"✗ Memory '{memory_id}' not found.\n"
            f"  Run `cortex stats` to see available memory counts, or\n"
            f"  `cortex search <query>` to find the ID you want.",
            err=True,
        )
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_memory() -> AgentMemory:  # noqa: F821
    from cortex.core import AgentMemory

    config_path = Path("config.yaml")
    if not config_path.exists():
        typer.echo("config.yaml not found. Run `cortex init` first.", err=True)
        sys.exit(1)
    return AgentMemory(config_path=config_path)


def _get_staged_files() -> list[str]:
    """Get list of staged (and modified) files from git."""

    files: list[str] = []
    try:
        # Staged files
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            files.extend(f for f in result.stdout.strip().split("\n") if f)

        # Modified (not staged)
        result2 = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        if result2.stdout.strip():
            files.extend(f for f in result2.stdout.strip().split("\n") if f)

        # Untracked
        result3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=10,
        )
        if result3.stdout.strip():
            files.extend(f for f in result3.stdout.strip().split("\n") if f)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return list(dict.fromkeys(files))  # Deduplicate preserving order


if __name__ == "__main__":
    app()
