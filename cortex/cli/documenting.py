"""``save-session`` / ``create-spec`` / ``finish-session`` — flujo documental.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).
``_parse_verification_hooks`` vive acá y se re-exporta desde main para
no romper imports existentes (tests/unit/cli/).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cortex.cli.common import _load_memory



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


def register(app) -> None:
    """Registra save-session / create-spec / finish-session en el app principal."""
    # ---------------------------------------------------------------------------
    # save-session
    # ---------------------------------------------------------------------------

    @app.command(name="save-session", hidden=True)
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
        typer.echo(
            "⚠ Deprecated: los checkpoints automáticos / `cortex session checkpoint` reemplazan este comando.", err=True
        )
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




    # ---------------------------------------------------------------------------
    # finish-session (Pluggable Middle — Phase 01)
    # ---------------------------------------------------------------------------

    app.command(name="create-spec", hidden=True)(create_spec)
    app.command(name="start")(create_spec)

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

    app.command(name="finish-session", hidden=True)(finish_session)
    app.command(name="finish")(finish_session)
