"""``cortex pr-context`` — pipeline DevSecDocOps (captura → docs → memoria).

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4). Los
comandos conservan nombres y comportamiento exactos.
"""

from __future__ import annotations

from pathlib import Path

import typer

from cortex.cli.common import _load_memory

pr_context_app = typer.Typer(help="PR documentation pipeline (DevSecDocOps).")


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
