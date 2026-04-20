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
index-docs        Index vault docs as semantic memory.
agent-guidelines  Display agent behavior guidelines for session-end documentation.
install-skills    Install Obsidian skills into the project's .cortex/skills/ directory.
remember          Store a new episodic memory from the command line.
search            Query both memory layers and print results.
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
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import json
import typer
import yaml

from cortex.core import AgentMemory

app = typer.Typer(
    name="cortex",
    help="Cortex -- hybrid cognitive memory for AI agents.",
    add_completion=False,
)

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


# ---------------------------------------------------------------------------
# pr-context  (DevSecDocOps subcommand group)
# ---------------------------------------------------------------------------

pr_context_app = typer.Typer(help="PR documentation pipeline (DevSecDocOps).")
app.add_typer(pr_context_app, name="pr-context")


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
) -> None:
    """
    Setup only local agent/cognitive components (Vault, Memory, .cortex, IDE).
    """
    from cortex.setup.orchestrator import SetupOrchestrator, SetupMode, format_summary
    if git_depth is None:
        git_depth = typer.prompt("📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?", default=50, type=int)
    typer.echo("🧠 Cortex — Setting up Agent profile...")
    typer.echo("")
    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.AGENT, git_depth=git_depth)
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
    from cortex.setup.orchestrator import SetupOrchestrator, SetupMode, format_summary

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
    from cortex.setup.orchestrator import SetupOrchestrator, SetupMode, format_summary
    if git_depth is None:
        git_depth = typer.prompt("📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?", default=50, type=int)
    typer.echo("🧠 Cortex — Setting up Full project...")
    typer.echo("")
    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.FULL, git_depth=git_depth)
    typer.echo(format_summary(summary))


# ---------------------------------------------------------------------------
# init (Alias for setup agent)
# ---------------------------------------------------------------------------

@app.command()
def init() -> None:
    """Bootstrap cortex: Alias for `cortex setup agent`."""
    setup_agent(dry_run=False)


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
) -> None:
    """
    Verify whether the PR includes agent-generated documentation.

    Checks the vault/ directory for new or modified markdown files.
    Outputs a JSON status file for use in CI workflows.
    """
    from cortex.doc_verifier import DocVerifier

    vault_path = Path(vault)
    if not vault_path.exists():
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
        typer.echo(f"✅ Agent documentation found ({result.total_vault_files} files)")
        typer.echo(f"   New: {', '.join(result.new_files) or 'none'}")
        typer.echo(f"   Modified: {', '.join(result.modified_files) or 'none'}")
        typer.echo("true")
    else:
        typer.echo("⚠ No agent documentation found — fallback mode")
        typer.echo("false")


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
) -> None:
    """Query both memory layers and print results."""
    mem = _load_memory()
    result = mem.retrieve(query, top_k=top_k)

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"\nQuery: '{query}'\n")

    if result.unified_hits:
        typer.echo("Unified Results (RRF-fused across both sources):")
        for hit in result.unified_hits:
            source_tag = "EPISODIC" if hit.source == "episodic" else "SEMANTIC"
            typer.echo(
                f"  [{source_tag}] {hit.display_title}  "
                f"({hit.display_path})  score={hit.score:.4f}"
            )
    else:
        if result.episodic_hits:
            typer.echo("Episodic Memory:")
            for hit in result.episodic_hits:
                e = hit.entry
                typer.echo(
                    f"  [{e.id}] ({e.memory_type}) {e.content[:80]}...  "
                    f"score={hit.score:.3f}"
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
def install_ide() -> None:
    """Install Cortex inside OpenCode / Claude Code locally."""
    from cortex.ide_installer import install
    install()

@app.command()
def uninstall_ide() -> None:
    """Uninstall Cortex from OpenCode / Claude Code locally."""
    from cortex.ide_installer import uninstall
    uninstall()

@app.command(name="mcp-server")
def mcp_server(
    stdio: bool = typer.Option(True, "--stdio", help="Use stdio transport (required for IDE integration)."),
) -> None:
    """Start the Cortex v2.1 MCP Server (stdio transport)."""
    import asyncio
    import sys
    
    # Redirección temporal de stdout a stderr para proteger el handshake JSON-RPC
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    
    try:
        from cortex.mcp.server import CortexMCPServer
        server = CortexMCPServer(project_root=Path.cwd())
    finally:
        sys.stdout = old_stdout
        
    asyncio.run(server.run())

@app.command(name="mcp-serve", hidden=True)
def mcp_serve_legacy() -> None:
    """Legacy alias for mcp-server."""
    mcp_server()

@app.command(name="inject")
def inject(
    agent: str = typer.Option("opencode", help="Agent/IDE to inject (opencode, claude).")
) -> None:
    """Inject Cortex MCP configuration into the specified agent/IDE."""
    from cortex.ide_installer import install_opencode_profile, install_claude_desktop_profile
    
    if agent == "opencode":
        install_opencode_profile()
    elif agent == "claude":
        install_claude_desktop_profile()
    else:
        typer.echo(f"Agent '{agent}' not supported yet.")

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
    import subprocess

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
