"""
cortex.cli.main
---------------
Command-line interface for Cortex (Typer).

Surface area is split into top-level commands plus four sub-CLIs
(``webgraph``, ``autopilot``, ``pr-context``, ``hu``). Every command
accepts ``--help``; this docstring lists the canonical entrypoints
adopters are expected to use.

Setup
~~~~~
- ``cortex setup agent``        — agentic workspace only (`.cortex/` + IDE).
- ``cortex setup pipeline``     — CI/CD workflows only (supports ``--non-interactive``).
- ``cortex setup full``         — three pillars: agent + pipeline + webgraph
  (supports ``--non-interactive`` + ``--ide`` + ``--git-depth``).
- ``cortex setup webgraph``     — visualization module only.
- ``cortex setup enterprise``   — enterprise topology (wizard or preset).
- ``cortex init``               — alias for ``setup agent``.

Memory + retrieval
~~~~~~~~~~~~~~~~~~
- ``cortex search``             — hybrid RRF search (scope: local/enterprise/all).
- ``cortex context``            — enriched context for current work (``--format json|compact|markdown``).
- ``cortex remember``           — store an episodic memory (with ``--branch``, ``--commit``, ``--repo``).
- ``cortex forget``             — delete an episodic memory by id.
- ``cortex stats``              — memory store statistics (``--project-root`` aware).
- ``cortex embedding-status``   — active embedding model/backend + per-language config (Obra 04).
- ``cortex sync-vault``         — re-index the semantic vault.

Workflow (governance-guarded)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- ``cortex create-spec``        — persist a spec into ``.cortex/vault/specs/``.
- ``cortex save-session``       — persist a session note into ``.cortex/vault/sessions/``.

Documentation pipeline
~~~~~~~~~~~~~~~~~~~~~~
- ``cortex verify-docs``        — detect agent-generated docs in a PR diff.
- ``cortex validate-docs``      — validate markdown frontmatter and structure.
- ``cortex index-docs``         — selectively index vault docs as semantic memory.
- ``cortex pr-context``         — sub-app: ``capture / store / search / generate``.

Enterprise
~~~~~~~~~~
- ``cortex org-config``         — print the resolved enterprise org config.
- ``cortex promote-knowledge``  — promote vault docs to the enterprise vault.
- ``cortex review-knowledge``   — sub-app: ``pending / approve / reject / candidate``
  to triage the enterprise promotion review queue.
- ``cortex sync-enterprise-vault`` — validate + index the enterprise vault.
- ``cortex memory-report``      — health + promotion metrics (``--scope``, ``--json``).

Doctor + diagnostics
~~~~~~~~~~~~~~~~~~~~
- ``cortex doctor``             — runtime/layout/git checks (``--scope``, ``--strict``).
- ``cortex agent-guidelines``   — display the canonical AGENT.md.

Work items + integrations
~~~~~~~~~~~~~~~~~~~~~~~~~
- ``cortex hu``                 — sub-app: ``import / list / show`` (Jira read-only).

IDE + MCP
~~~~~~~~~
- ``cortex inject``             — inject Cortex into an IDE (``--ide``).
- ``cortex sync-ide``           — re-sync IDE-side artifacts.
- ``cortex install-skills``     — copy Obsidian skills into ``.cortex/skills/``.
- ``cortex install-ide``        — alias to ``cortex inject`` (deprecated, kept for compatibility).
- ``cortex mcp-server``         — start the MCP server (stdio).
- ``cortex mcp-serve``          — hidden alias of ``mcp-server``.

Autopilot
~~~~~~~~~
- ``cortex autopilot``          — sub-app: ``start / preflight / checkpoint / finish /
  status / doctor / report / cleanup / install / uninstall``.

Visualization
~~~~~~~~~~~~~
- ``cortex webgraph``           — sub-app: ``serve / export / setup``.

For adopter-facing onboarding, see ``docs/guides/getting-started-adopters.md``.
"""

from __future__ import annotations

import sys
import warnings

# Windows: reconfigurar stdout a UTF-8 para evitar UnicodeEncodeError con emojis
# cuando stdout es un pipe (ej. subprocess en tests E2E).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# SILENCE PROTOCOL v2.14: Suprimir advertencias de runpy/typer antes de que toquen stdout
warnings.filterwarnings("ignore")

import getpass
import json
from enum import Enum
from pathlib import Path

import typer
import yaml

from cortex.cli.review_knowledge import review_app
from cortex.webgraph.cli import app as webgraph_app
from cortex.workspace.layout import WorkspaceLayout

app = typer.Typer(
    name="cortex",
    help="Cortex -- hybrid cognitive memory for AI agents.",
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        from cortex import __version__

        typer.echo(f"cortex {__version__}")
        raise typer.Exit()


@app.callback()
def _root_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Print Cortex version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Cortex — hybrid cognitive memory for AI agents."""


app.add_typer(webgraph_app, name="webgraph")

# Autopilot subcommand (Fase 3)
from cortex.autopilot.cli import app as autopilot_app

app.add_typer(autopilot_app, name="autopilot")

# Session subcommand (Pluggable Middle architecture — Phase 00 / T0.8)
from cortex.cli.session import session_app

app.add_typer(session_app, name="session")

# Unified IDE surface (Obra 02 / Fase 3) — `cortex ide list|setup|remove|status`.
from cortex.cli.ide import ide_app

app.add_typer(ide_app, name="ide")

_IDE_PROJECT_ROOT_HELP = "Path to the Cortex project root (defaults to current directory)."

# Embeddings + MCP server (extraídos del monolito — Obra 01 P4)
from cortex.cli.embedding import register as _register_embedding
from cortex.cli.mcp_cmd import register as _register_mcp

_register_embedding(app)
_register_mcp(app)

# pr-context + hu (extraídos del monolito — Obra 01 P4)
from cortex.cli.hu import hu_app
from cortex.cli.pr_context import pr_context_app

app.add_typer(pr_context_app, name="pr-context")
app.add_typer(hu_app, name="hu")

# CI subcommand (Pluggable Middle Phase 07)
from cortex.cli.ci import ci_app

app.add_typer(ci_app, name="ci")

# Canonical documentation system (Fase 02 of canonical-documentation initiative)
from cortex.cli.docs_subcommand import app as docs_app

app.add_typer(docs_app, name="docs")

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


def _echo_dry_run_plan(profile: str, actions: list[str]) -> None:
    """Print a ``[dry-run]`` action plan without touching the filesystem."""
    typer.echo(f"🧠 Cortex — [dry-run] Setup {profile} profile (simulation)")
    typer.echo("")
    for action in actions:
        typer.echo(f"[dry-run] crearía: {action}")
    typer.echo("")
    typer.echo("✅ Dry-run complete — no changes were made.")


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
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip prompts (uses safe defaults). Required for CI/scripted setups.",
    ),
) -> None:
    """
    Setup only local agent/cognitive components (Vault, Memory, .cortex, IDE).
    """
    from cortex.cli._setup_helpers import select_ide_interactive
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    if dry_run:
        _echo_dry_run_plan(
            "agent",
            [
                ".cortex/ workspace directories",
                "config.yaml (project config)",
                ".cortex/org.yaml (enterprise org config)",
                "vault docs (architecture.md, context.md, decisions.md, runbooks/)",
                "enterprise vault structure",
                "agent guidelines + skills install",
                "memory init (git history indexing)",
                *( [f"IDE config for '{ide}'"] if ide else [] ),
            ],
        )
        return

    if git_depth is None:
        if non_interactive:
            git_depth = 50
        else:
            git_depth = typer.prompt("📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?", default=50, type=int)

    # Fase 6 plan multi-IDE & MCP hardening: la seleccion de IDE vive en
    # cortex.cli._setup_helpers para evitar duplicacion entre setup_agent
    # y setup_full. Respeta --ide explicito y --non-interactive.
    selected_ide = select_ide_interactive(provided_ide=ide, non_interactive=non_interactive)

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
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip prompts (auto-accept detected vault). Required for CI/scripted setups.",
    ),
) -> None:
    """
    Setup only CI/CD / DevOps components (Workflows, Scripts, Config).
    """
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    if dry_run:
        _echo_dry_run_plan(
            "pipeline",
            [
                ".github/workflows/ CI workflows (ci-feature, ci-pull-request, cd-deploy)",
                "scripts/ DevSecDocOps pipeline script",
                "config.yaml (project config)",
                "enterprise vault structure (CI/CD docs)",
            ],
        )
        return

    typer.echo("🧠 Cortex — Setting up Pipeline profile...")
    typer.echo("")

    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(mode=SetupMode.PIPELINE, non_interactive=non_interactive)
    typer.echo(format_summary(summary))


@setup_app.command(name="full")
def setup_full(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes."
    ),
    git_depth: int = typer.Option(
        None, "--git-depth", help="Number of git commits to index for context."
    ),
    ide: str | None = typer.Option(
        None,
        "--ide",
        help="IDE to configure profiles for (claude-code, opencode, pi, codex, ...).",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip prompts (uses safe defaults). Required for CI/scripted setups.",
    ),
) -> None:
    """
    Full project setup — agent + pipeline + webgraph (the three pillars).

    With ``--non-interactive`` plus ``--git-depth N`` (and optional ``--ide X``),
    this command runs end-to-end without prompts. Recommended for adopters
    onboarding fresh repos and for scripted/CI provisioning.

    Sin ``--non-interactive``, prompt-ea por commits de git Y por IDE
    (usando el mismo helper que ``cortex setup agent``). Esto cierra la
    asimetria pre-Fase 6 donde ``setup full`` no preguntaba por IDE,
    obligando al adopter a correr ``setup agent`` despues.
    """
    from cortex.cli._setup_helpers import select_ide_interactive
    from cortex.setup.orchestrator import SetupMode, SetupOrchestrator, format_summary

    if dry_run:
        _echo_dry_run_plan(
            "full",
            [
                ".cortex/ workspace directories",
                "config.yaml (project config)",
                ".cortex/org.yaml (enterprise org config)",
                "vault docs (architecture.md, context.md, decisions.md, runbooks/)",
                "enterprise vault structure",
                ".github/workflows/ CI workflows + scripts/ DevSecDocOps script",
                "agent guidelines + skills install",
                "webgraph visualization module (.cortex/webgraph/)",
                "memory init (git history indexing) + .gitignore update",
                *( [f"IDE config for '{ide}'"] if ide else [] ),
            ],
        )
        return

    if git_depth is None:
        if non_interactive:
            git_depth = 50
        else:
            git_depth = typer.prompt(
                "📈 ¿Cuántos commits de Git deseas indexar para el contexto inicial?",
                default=50,
                type=int,
            )

    # Fase 6 plan multi-IDE & MCP hardening: el helper unifica la seleccion
    # de IDE entre setup_agent y setup_full. Respeta --ide explicito y
    # --non-interactive sin prompts.
    selected_ide = select_ide_interactive(provided_ide=ide, non_interactive=non_interactive)

    typer.echo("🧠 Cortex — Setting up Full project (agent + pipeline + webgraph)...")
    typer.echo("")
    orchestrator = SetupOrchestrator()
    summary = orchestrator.run(
        mode=SetupMode.FULL,
        git_depth=git_depth,
        ide=selected_ide,
        non_interactive=non_interactive,
    )
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

    if dry_run:
        _echo_dry_run_plan(
            "webgraph",
            [
                "webgraph module files under .cortex/webgraph/",
                ".cortex/webgraph/workspace.yaml",
                *(
                    [f"registration of project root '{attach_project_root}' in workspace.yaml"]
                    if attach_project_root
                    else []
                ),
            ],
        )
        return

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
    verification_hook: list[str] = typer.Option(
        [],
        "--verification-hook",
        help=(
            "Verification hook in 'key=value;key=value' format "
            "(repeatable). Keys: name, command, required (true/false, "
            "default true), success_criteria, timeout_seconds. "
            "Example: 'name=tests;command=pytest tests/auth/'."
        ),
    ),
    no_sync: bool = typer.Option(False, "--no-sync", help="Skip vault sync after writing."),
    proposal_mode: str = typer.Option(
        "optional",
        "--proposal-mode",
        help=(
            "Phase 09.A: gate on the cortex-sync proposal step. "
            "'optional' (default) lets the spec proceed without explicit "
            "confirmation; 'required' fails unless --proposal-confirmed is "
            "passed; 'skip' bypasses the gate entirely."
        ),
    ),
    proposal_confirmed: bool = typer.Option(
        False,
        "--proposal-confirmed",
        help=(
            "Phase 09.A: signal that the cortex-sync proposal has been "
            "acknowledged by the user. Only consulted when "
            "--proposal-mode=required."
        ),
    ),
    with_tasks: bool = typer.Option(
        False,
        "--with-tasks",
        help=(
            "Phase 09.C: ask SDDwork to emit a granular task "
            "decomposition for this spec (Deep Track only). Adds the "
            "``tasks-required`` tag to the spec frontmatter."
        ),
    ),
) -> None:
    """Persist an implementation spec into the vault."""
    hooks = _parse_verification_hooks(verification_hook)
    mem = _load_memory()
    try:
        result = mem.create_spec_note(
            title=title,
            goal=goal,
            requirements=requirements,
            files_in_scope=files_in_scope,
            constraints=constraints,
            acceptance_criteria=acceptance_criteria,
            tags=tags,
            verification_hooks=hooks,
            sync_vault=not no_sync,
            proposal_mode=proposal_mode,
            proposal_confirmed=proposal_confirmed,
            with_tasks=with_tasks,
        )
    except ValueError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Specification saved -> {result.path}")
    if result.session is not None and result.session.is_gitless:
        typer.echo(
            "\n⚠️  No git repository detected. Session opened in degraded mode:\n"
            "   • cortex finish-session will skip git diff reconstruction\n"
            "   • documenter will rely exclusively on checkpoints\n"
            "   • To enable full session capabilities, run:\n"
            "       git init && git add -A && git commit -m \"initial\"",
            err=True,
        )


def _parse_verification_hooks(specs: list[str]) -> list[dict[str, object]]:
    """Parse repeatable ``--verification-hook 'name=...;command=...'`` arguments.

    Each token between semicolons is a ``key=value`` pair. Boolean and
    integer fields are coerced. Unknown keys cause a clear CLI error.
    """
    parsed: list[dict[str, object]] = []
    allowed = {"name", "command", "required", "success_criteria", "timeout_seconds"}
    for raw in specs:
        if not raw.strip():
            continue
        hook: dict[str, object] = {}
        for pair in raw.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            if "=" not in pair:
                typer.echo(
                    f"Invalid --verification-hook entry {pair!r}: expected key=value.",
                    err=True,
                )
                raise typer.Exit(1)
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key not in allowed:
                typer.echo(
                    f"Unknown verification_hook key {key!r}. "
                    f"Allowed: {sorted(allowed)}",
                    err=True,
                )
                raise typer.Exit(1)
            if key == "required":
                hook[key] = value.lower() in {"true", "1", "yes"}
            elif key == "timeout_seconds":
                try:
                    hook[key] = int(value)
                except ValueError:
                    typer.echo(
                        f"timeout_seconds must be an integer, got {value!r}.", err=True
                    )
                    raise typer.Exit(1) from None
            else:
                hook[key] = value
        if hook:
            parsed.append(hook)
    return parsed


# ---------------------------------------------------------------------------
# finish-session (Pluggable Middle — Phase 01)
# ---------------------------------------------------------------------------

def _resolve_interactive_mode(mem: object, cli_flag: bool | None) -> bool:
    """Resolve whether ``finish-session`` should enter interactive mode.

    CLI flag wins; if absent, fall back to ``documenter.default_mode``
    from the loaded :class:`CortexConfig` (``"interactive"`` → True,
    anything else → False).
    """
    if cli_flag is not None:
        return cli_flag
    try:
        cfg = getattr(mem, "config", None)
        documenter_cfg = getattr(cfg, "documenter", None) if cfg is not None else None
        mode = getattr(documenter_cfg, "default_mode", "auto") if documenter_cfg else "auto"
        return mode == "interactive"
    except Exception:
        return False


@app.command(name="finish-session")
def finish_session(
    session_id: str | None = typer.Argument(
        None, help="Session id (defaults to the active session)."
    ),
    handoff: bool = typer.Option(
        False, "--handoff", help="Force the session to close as HANDOFF."
    ),
    abandon: bool = typer.Option(
        False, "--abandon", help="Force the session to close as ABANDONED (no note)."
    ),
    reason: str = typer.Option(
        "",
        "--reason",
        help="Reason recorded in the session note (required when --handoff/--abandon).",
    ),
    interactive: bool | None = typer.Option(
        None,
        "--interactive/--no-interactive",
        help=(
            "Override the documenter mode for this call. Default reads "
            "`documenter.default_mode` from config.yaml (auto unless changed)."
        ),
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Emit a machine-readable JSON summary."
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root (defaults to current directory)."
    ),
) -> None:
    """Close a Session: reconstruct context, run verification hooks, persist."""
    if handoff and abandon:
        typer.echo("--handoff and --abandon are mutually exclusive.", err=True)
        raise typer.Exit(1)
    if (handoff or abandon) and not reason.strip():
        typer.echo("--reason is required with --handoff or --abandon.", err=True)
        raise typer.Exit(1)

    mem = _load_memory(project_root) if project_root else _load_memory()
    target_id = (session_id or "").strip()
    if not target_id:
        active = mem.get_active_session()
        if active is None:
            typer.echo(
                "No active session. Pass an explicit session id or open one with "
                "`cortex create-spec`.",
                err=True,
            )
            raise typer.Exit(1)
        target_id = active.session_id

    from cortex.documenter import (
        DocumenterPersister,
        FinishOverrides,
        ReconstructionInput,
        Reconstructor,
    )
    from cortex.session import SessionStatus
    from cortex.session.verification import VerificationRunner

    record = mem.get_session(target_id)
    if record.status is not SessionStatus.OPEN:
        typer.echo(
            f"Session {target_id!r} is already {record.status.value}; nothing to finish.",
            err=True,
        )
        raise typer.Exit(1)

    reconstructor = Reconstructor(
        session_service=mem._session_service,
        verification_runner=VerificationRunner(repo_root=mem.repo_root),
        repo_root=mem.repo_root,
    )
    out = reconstructor.reconstruct(ReconstructionInput(session_id=target_id))

    forced_status: SessionStatus | None = None
    if abandon:
        forced_status = SessionStatus.ABANDONED
    elif handoff:
        forced_status = SessionStatus.HANDOFF

    # Resolve interactive mode: CLI flag wins; otherwise config default
    # (documenter.default_mode, see cortex.core.DocumenterConfig).
    use_interactive = _resolve_interactive_mode(mem, interactive)
    overrides = FinishOverrides(forced_status=forced_status)
    if use_interactive and not (handoff or abandon):
        from cortex.documenter.interactive import InteractiveAction, InteractiveSession

        prompt_session = InteractiveSession()
        verdict = prompt_session.prompt(out)
        if verdict.action is InteractiveAction.CANCEL:
            typer.echo(
                "✗ Cancelled. The session is still OPEN — re-run "
                "`cortex finish-session` when ready.",
                err=True,
            )
            raise typer.Exit(0)
        overrides = FinishOverrides(
            approved_adr_indices=verdict.approved_adr_indices,
            edited_note_title=verdict.edited_note_title,
            edited_note_body=verdict.edited_note_body,
            forced_status=verdict.forced_status or forced_status,
        )

    persister = DocumenterPersister(
        note_service=mem._note_service,
        session_service=mem._session_service,
        vault_path=mem._vault_path_resolved,
    )
    result = persister.finalize(out, overrides=overrides)

    if output_json:
        typer.echo(
            json.dumps(
                {
                    "session_id": result.session_id,
                    "final_status": result.final_status.value,
                    "session_note_path": (
                        str(result.session_note_path)
                        if result.session_note_path
                        else None
                    ),
                    "adrs_created": [str(p) for p in result.adrs_created],
                    "summary": result.summary,
                    "already_closed": result.already_closed,
                },
                ensure_ascii=False,
            )
        )
        return

    if result.already_closed:
        typer.echo(f"⚠ Session {result.session_id} was already closed.")
        return

    typer.echo(f"✓ Session {result.session_id} closed as {result.final_status.value}.")
    typer.echo(f"  {result.summary}")
    if result.session_note_path is not None:
        typer.echo(f"  Session note: {result.session_note_path}")
    for adr in result.adrs_created:
        typer.echo(f"  ADR: {adr}")
    # Phase 09.A+ / May 2026: nudge users toward the editorial closing
    # anchor. CLI auto-persist remains valid for scripting/CI, but for
    # interactive use the /cortex-documenter skill produces higher-signal
    # notes (LLM writes prose with judgement instead of Jinja templates
    # filling slots from checkpoints).
    typer.echo(
        "\n💡 Tip: for higher-signal documentation (LLM writes the note "
        "with editorial criterion), use the /cortex-documenter skill in "
        "your IDE instead of this CLI command. This auto-persist path "
        "remains valid for scripting and CI.",
    )


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
# tutor
# ---------------------------------------------------------------------------

@app.command()
def tutor(
    topic: str | None = typer.Argument(
        None,
        help="Tópico directo (ej: 'pipeline', 'vault', 'commands'). Sin argumento abre el menú.",
    ),
) -> None:
    """Guía interactiva offline de Cortex. Zero tokens.

    Abre un menú navegable con tópicos sobre cómo usar Cortex,
    su pipeline, vault, enterprise y más. Todo se muestra en la
    terminal sin consumir tokens de ningún modelo de IA.

    Uso directo:  cortex tutor pipeline
    Menú:         cortex tutor
    """
    from cortex.tutor.engine import TutorEngine

    engine = TutorEngine.default()

    if topic:
        if not engine.show_topic_by_slug(topic):
            slugs = [t.slug for t in engine.topics]
            typer.echo(f"Tópico '{topic}' no encontrado. Disponibles: {', '.join(slugs)}", err=True)
            raise typer.Exit(1)
    else:
        engine.run()


# ---------------------------------------------------------------------------
# hint
# ---------------------------------------------------------------------------

@app.command()
def hint() -> None:
    """Tip contextual: qué hacer ahora con Cortex. Zero tokens.

    Analiza el estado actual de tu proyecto (¿tiene config.yaml?,
    ¿tiene vault?, ¿tiene specs?) y sugiere el siguiente paso
    lógico con el comando concreto a ejecutar.
    """
    from cortex.tutor.hint import HintEngine, ProjectState

    state = ProjectState.detect(Path.cwd())
    engine = HintEngine()
    tip = engine.get_hint(state)
    tip.render()


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
    doc_type: list[str] = typer.Option(
        [],
        "--doc-type",
        help="Filter by DocType slug (repeatable). Enables canonical search path.",
    ),
    exclude_doc_type: list[str] = typer.Option(
        [],
        "--exclude-doc-type",
        help="Exclude these DocType slugs (repeatable).",
    ),
    status: list[str] = typer.Option(
        [], "--status", help="Only keep items with one of these frontmatter statuses."
    ),
    tag: list[str] = typer.Option(
        [], "--tag", help="Items must contain ALL given tags (repeatable)."
    ),
    tag_any: list[str] = typer.Option(
        [], "--tag-any", help="Items must contain at least one of the given tags."
    ),
    max_age_days: int | None = typer.Option(
        None, "--max-age-days", help="Drop items older than N days."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Drop items without doc_type when --doc-type is set."
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        help="Output format when structural filters are used: text | json | compact.",
    ),
) -> None:
    """Query both memory layers and print results.

    Without structural flags this command keeps the legacy RRF-fused output
    over both episodic and semantic memory. When any of ``--doc-type``,
    ``--exclude-doc-type``, ``--status``, ``--tag``, ``--tag-any``,
    ``--max-age-days`` or ``--strict`` is set, results are produced by the
    ``ContextEnricher`` honouring those structural filters (same engine as
    ``cortex docs search``).
    """
    if scope is not None and scope not in {"local", "enterprise", "all"}:
        typer.echo("Invalid --scope value. Use one of: local, enterprise, all.", err=True)
        raise typer.Exit(1)

    from cortex.cli._search_filters import build_enrichment_filters_from_cli, has_any_filter

    structural_mode = has_any_filter(
        doc_type=doc_type,
        exclude_doc_type=exclude_doc_type,
        status=status,
        tag=tag,
        tag_any=tag_any,
        max_age_days=max_age_days,
        project_id=None,
        strict=strict,
        scope="local",
    )

    if structural_mode:
        if output_format not in {"text", "json", "compact"}:
            typer.echo(f"Invalid --format value: {output_format!r}", err=True)
            raise typer.Exit(1)
        try:
            filters = build_enrichment_filters_from_cli(
                doc_type=doc_type,
                exclude_doc_type=exclude_doc_type,
                status=status,
                tag=tag,
                tag_any=tag_any,
                scope=scope or "local",
                max_age_days=max_age_days,
                project_id=[project_id] if project_id else None,
                strict=strict,
            )
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

        from cortex.context_enricher.config import ContextEnricherConfig
        from cortex.context_enricher.enricher import ContextEnricher
        from cortex.context_enricher.presenter import ContextPresenter
        from cortex.models import WorkContext

        mem = _load_memory()
        enricher = ContextEnricher(
            episodic=mem.episodic,
            semantic=mem.semantic,
            config=ContextEnricherConfig(),
        )
        work = WorkContext(
            source="manual",
            changed_files=[],
            keywords=query.split(),
            search_queries=[query],
        )
        ctx = enricher.enrich(work, top_k=top_k, filters=filters)
        if output_format == "json":
            typer.echo(ContextPresenter.to_json(ctx))
            return
        if output_format == "compact":
            typer.echo(ContextPresenter.to_compact_grouped(ctx))
            return
        typer.echo(ContextPresenter.to_markdown_grouped(ctx))
        return

    mem = _load_memory()
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
    layout = WorkspaceLayout.discover(root)
    service = KnowledgePromotionService.from_project_root(root, workspace_layout=layout)
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


app.add_typer(review_app, name="review-knowledge")


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
    layout = WorkspaceLayout.discover(root)
    service = KnowledgePromotionService.from_project_root(root, workspace_layout=layout)
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
        embedding_model=mem._effective_embedding[0],
        embedding_backend=mem._effective_embedding[1],
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
# IDE / MCP
# ---------------------------------------------------------------------------

@app.command()
def install_ide(
    ide: str | None = typer.Option(None, "--ide", help="IDE to configure (e.g. opencode, cursor, claude-code)."),
    all_ides: bool = typer.Option(False, "--all", help="Configure all IDE adapters (deprecated/experimental)."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_IDE_PROJECT_ROOT_HELP),
) -> None:
    """(Deprecated) Install Cortex agent profiles and MCP config in supported IDEs.

    Delegates to the unified `cortex ide setup` implementation.
    """
    from cortex.cli.ide import DEPRECATION_SETUP, run_bulk_inject, run_setup
    from cortex.ide import get_supported_ides

    typer.echo(f"Warning: {DEPRECATION_SETUP}")
    if all_ides or ide is None:
        typer.echo("Warning: --all uses deprecated/experimental bulk installation. Prefer `cortex ide setup --ide <name>`.")
        run_bulk_inject(project_root)
        return

    run_setup(ide, project_root=project_root)
    typer.echo(f"Supported IDEs: {', '.join(get_supported_ides())}")

@app.command()
def uninstall_ide(
    ide: str | None = typer.Option(None, "--ide", help="IDE to clean (e.g. opencode, cursor, claude-code)."),
    all_ides: bool = typer.Option(False, "--all", help="Clean all IDE adapters (deprecated/experimental)."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_IDE_PROJECT_ROOT_HELP),
) -> None:
    """(Deprecated) Remove Cortex profiles and MCP config from supported IDEs.

    Delegates to the unified `cortex ide remove` implementation.
    """
    from cortex.cli.ide import DEPRECATION_REMOVE, run_bulk_uninstall, run_remove

    typer.echo(f"Warning: {DEPRECATION_REMOVE}")
    if all_ides or ide is None:
        typer.echo("Warning: --all uses deprecated/experimental bulk removal. Prefer `cortex ide remove --ide <name>`.")
        run_bulk_uninstall(project_root)
        return

    run_remove(ide, project_root=project_root)

@app.command(name="inject")
def inject(
    ide: str | None = typer.Option(None, "--ide", help="IDE to inject (canonical names or aliases such as claude-code / claude-desktop)."),
    sync_canonical: bool = typer.Option(
        True,
        "--sync-canonical/--no-sync-canonical",
        help=(
            "(Pi only) Mirror .cortex/subagents/ into cortex-pi/.pi/agents/ "
            "before copying the bundle. Default: enabled. Pass --no-sync-canonical "
            "to copy the bundle as-is (snapshot mode)."
        ),
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_IDE_PROJECT_ROOT_HELP),
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
    from cortex.cli.ide import DEPRECATION_SETUP, resolve_project_root, run_setup

    typer.echo(f"Warning: {DEPRECATION_SETUP}")
    resolved_root = resolve_project_root(project_root)

    if ide:
        # Direct injection for specified IDE — delegates to `cortex ide setup`.
        run_setup(ide, project_root=resolved_root, sync_canonical=sync_canonical)
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
            run_setup(selected_ide, project_root=resolved_root, sync_canonical=sync_canonical)
            typer.echo(f"\n✅ Successfully configured {selected_ide}")
            typer.echo("Run 'cortex inject' again to configure another IDE.")
        else:
            typer.echo(f"❌ Invalid selection. Supported IDEs: {', '.join(supported)}")


@app.command(name="sync-ide")
def sync_ide(
    ide: str = typer.Option(..., "--ide", help="IDE to sync (required)."),
    force: bool = typer.Option(False, "--force", help="Ignored: setup is idempotent."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_IDE_PROJECT_ROOT_HELP),
) -> None:
    """(Deprecated) Sync IDE configuration with current .cortex/skills/ content.

    `cortex ide setup` is idempotent and re-syncs on every run; this command
    only delegates to it.
    """
    from cortex.cli.ide import DEPRECATION_SETUP, run_setup

    typer.echo("Notice: sync-ide is deprecated; setup es idempotente. "
               f"Use `cortex ide setup --ide {ide}` (Warning: {DEPRECATION_SETUP})")
    run_setup(ide, project_root=project_root)
    typer.echo(f"\n✅ Successfully synced {ide} configuration")

@app.command()
def stats(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the project root. Defaults to CWD.",
    ),
) -> None:
    """Print memory store statistics."""
    mem = _load_memory(project_root)
    s = mem.stats()
    typer.echo(json.dumps(s, indent=2))


@app.command(name="memory-report")
def memory_report(
    project_root: str | None = typer.Option(
        None,
        "--project-root",
        help="Absolute path to the target project root (where config.yaml lives).",
    ),
    scope: str = typer.Option(
        "all",
        "--scope",
        help="Reporting scope: local, enterprise, or all.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the report as JSON.",
    ),
    telemetry: bool = typer.Option(
        False,
        "--telemetry",
        help="Include the in-vault retrieval telemetry section (Fase 05).",
    ),
    since_days: int = typer.Option(
        30,
        "--since-days",
        help="Telemetry window in days (used only with --telemetry).",
    ),
) -> None:
    """Report enterprise memory health and promotion visibility."""
    from cortex.enterprise.reporting import EnterpriseReportingService

    if scope not in {"local", "enterprise", "all"}:
        typer.echo("Invalid --scope value. Use one of: local, enterprise, all.", err=True)
        raise typer.Exit(1)

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    layout = WorkspaceLayout.discover(root)
    service = EnterpriseReportingService.from_project_root(root, workspace_layout=layout)
    report = service.build_memory_report(scope=scope)  # type: ignore[arg-type]

    telemetry_payload: dict | None = None
    if telemetry:
        from cortex.context_enricher.telemetry import make_observer

        observer = make_observer(layout, enabled=True)
        telemetry_payload = observer.aggregate(since_days=since_days)
        telemetry_payload["events_path"] = str(observer.path)

    if json_output:
        # Merge telemetry into the JSON output without touching the existing
        # report schema. Adopters that already parse the report keep working.
        payload = report.model_dump(mode="json")
        if telemetry_payload is not None:
            payload["telemetry"] = telemetry_payload
        import json as _json

        typer.echo(_json.dumps(payload, indent=2, default=str))
        return

    typer.echo("")
    typer.echo("Cortex Enterprise Memory Report")
    typer.echo("-----------------------------")
    typer.echo(f"Project root: {report.project_root}")
    typer.echo(f"Enterprise enabled: {report.enterprise_enabled}")
    typer.echo(f"Scope: {scope}")
    typer.echo("")

    for src in report.sources:
        typer.echo(f"[{src.scope}] vault={src.vault_path or '(disabled)'}")
        typer.echo(f"  markdown_files: {src.markdown_files}")
        typer.echo(f"  validation_errors: {src.validation_errors}")
        typer.echo(f"  validation_warnings: {src.validation_warnings}")
        for note in src.notes:
            typer.echo(f"  note: {note}")
        typer.echo("")

    promo = report.promotion
    typer.echo("Promotion")
    typer.echo("---------")
    typer.echo(f"enabled: {promo.enabled}")
    if promo.enabled:
        typer.echo(f"require_review: {promo.require_review}")
        typer.echo(f"records_path: {promo.records_path}")
        typer.echo(f"candidates_discovered: {promo.candidates_discovered}")
        typer.echo(f"candidates_ready_to_promote: {promo.candidates_ready_to_promote}")
        if promo.latest_events:
            typer.echo("latest_events:")
            for ev in promo.latest_events:
                actor = f" actor={ev.actor}" if ev.actor else ""
                at = f" at={ev.updated_at}" if ev.updated_at else ""
                typer.echo(f"  - {ev.origin_id} status={ev.status}{actor}{at}")
    if promo.warnings:
        typer.echo("warnings:")
        for w in promo.warnings:
            typer.echo(f"  - {w}")

    if telemetry_payload is not None:
        typer.echo("")
        typer.echo("Retrieval Telemetry (Fase 05)")
        typer.echo("-----------------------------")
        typer.echo(f"events_path: {telemetry_payload['events_path']}")
        typer.echo(
            f"window_days: {telemetry_payload['window_days']} "
            f"(0 events found)" if telemetry_payload["enrichments"] == 0
            else f"window_days: {telemetry_payload['window_days']}"
        )
        typer.echo(f"enrichments: {telemetry_payload['enrichments']}")
        typer.echo(f"citations: {telemetry_payload['citations']}")
        typer.echo(f"items_offered: {telemetry_payload['items_offered']}")
        typer.echo(f"items_used: {telemetry_payload['items_used']}")
        typer.echo(f"hit_rate: {telemetry_payload['hit_rate']:.3f}")
        if telemetry_payload["by_strategy"]:
            typer.echo("by_strategy:")
            for strategy, stats in telemetry_payload["by_strategy"].items():
                typer.echo(
                    f"  - {strategy}: offered={stats['offered']} "
                    f"used={stats['used']} hit_rate={stats['hit_rate']:.3f}"
                )
        if telemetry_payload["latency"]:
            lat = telemetry_payload["latency"]
            typer.echo(
                f"latency: p50={lat.get('p50_ms', 0):.0f}ms "
                f"p95={lat.get('p95_ms', 0):.0f}ms "
                f"p99={lat.get('p99_ms', 0):.0f}ms"
            )


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
# Internal helpers (implementación en cortex.cli.common)
# ---------------------------------------------------------------------------

from cortex.cli.common import _get_staged_files, _load_memory  # noqa: E402

if __name__ == "__main__":
    app()
