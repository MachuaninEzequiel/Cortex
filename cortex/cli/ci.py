"""``cortex ci`` — CI plugin subapp (Pluggable Middle Phase 07).

Subcommands:

* ``validate-pr`` (Level 1): runs the validator against the matching
  Session + spec and emits JSON / text / pr-comment output. Exit code
  doubles as the CI gate (0 pass / 1 warn / 2 blocked / 3 error).
* ``open-review-session`` / ``report-checkpoint`` /
  ``close-review-session`` (Level 3): drive a CI-owned Session that
  records the validation history of a PR.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from cortex.ci.diff_io import DiffResolutionError, read_diff_from_args
from cortex.ci.markdown_formatter import render_pr_comment
from cortex.ci.result import ValidationInput, ValidationResult
from cortex.ci.validator import EXIT_ERROR, CiValidator
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner
from cortex.workspace.layout import WorkspaceLayout

ci_app = typer.Typer(
    name="ci",
    help="CI plugin: validate PRs against Cortex Sessions.",
    no_args_is_help=True,
)

_PROJECT_ROOT_HELP = "Project root (defaults to current directory)."


def _build_validator(project_root: Path | None) -> tuple[CiValidator, Path]:
    root = (project_root or Path.cwd()).resolve()
    layout = WorkspaceLayout.discover(root)
    storage = SessionStorage(layout.sessions_dir)
    service = SessionService(storage, repo_root=layout.repo_root)
    runner = VerificationRunner(repo_root=layout.repo_root)
    return CiValidator(service, runner, repo_root=layout.repo_root), layout.repo_root


def _resolve_format(value: str) -> str:
    allowed = {"json", "text", "pr-comment"}
    if value not in allowed:
        typer.echo(f"✗ --format must be one of {sorted(allowed)}", err=True)
        raise typer.Exit(EXIT_ERROR)
    return value


@ci_app.command("validate-pr")
def validate_pr_command(
    diff: Path | None = typer.Option(None, "--diff", help="Path to a diff file."),
    base_commit: str | None = typer.Option(None, "--base-commit"),
    head_commit: str | None = typer.Option(None, "--head-commit"),
    base_branch: str | None = typer.Option(None, "--base-branch"),
    head_branch: str | None = typer.Option(None, "--head-branch"),
    pr_number: int | None = typer.Option(None, "--pr-number"),
    pr_author: str | None = typer.Option(None, "--pr-author"),
    session_id: str | None = typer.Option(
        None,
        "--session",
        help="Explicit session id (overrides auto-detection).",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json (default), text, pr-comment.",
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
) -> None:
    """Validate a pull request against the matching Cortex Session + spec."""
    fmt = _resolve_format(output_format)
    validator, repo_root = _build_validator(project_root)

    try:
        diff_text = read_diff_from_args(
            diff_file=diff,
            base_commit=base_commit,
            head_commit=head_commit,
            repo_root=repo_root,
        )
    except DiffResolutionError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from None

    payload = ValidationInput(
        diff_text=diff_text,
        repo_root=repo_root,
        base_commit=base_commit,
        head_commit=head_commit,
        base_branch=base_branch,
        head_branch=head_branch,
        pr_number=pr_number,
        pr_author=pr_author,
        explicit_session_id=session_id,
    )
    result = validator.validate(payload)
    _emit(result, fmt)
    raise typer.Exit(result.exit_code)


def _emit(result: ValidationResult, fmt: str) -> None:
    if fmt == "json":
        typer.echo(json.dumps(result.to_json_dict(), ensure_ascii=False, indent=2))
        return
    if fmt == "pr-comment":
        typer.echo(render_pr_comment(result))
        return
    # text
    console = Console()
    console.print(f"[bold]{result.summary_text}[/bold]")
    if result.matched_session is not None:
        console.print(f"  session: {result.matched_session.session_id}")
    console.print(f"  status:  {result.status}")
    for w in result.warnings:
        console.print(f"  [yellow]warn:[/yellow] {w}")
    for b in result.blockers:
        console.print(f"  [red]block:[/red] {b}")


# ---------------------------------------------------------------------------
# Level 3 — review session commands
# ---------------------------------------------------------------------------


def _build_session_service(project_root: Path | None) -> tuple[SessionService, Path]:
    root = (project_root or Path.cwd()).resolve()
    layout = WorkspaceLayout.discover(root)
    storage = SessionStorage(layout.sessions_dir)
    return SessionService(storage, repo_root=layout.repo_root), layout.repo_root


@ci_app.command("open-review-session")
def open_review_session_command(
    pr_number: int | None = typer.Option(None, "--pr-number"),
    base_commit: str = typer.Option(
        ..., "--base-commit", help="Base SHA of the PR (used as start_commit)."
    ),
    head_branch: str = typer.Option(
        ..., "--head-branch", help="PR source branch (used as start_branch)."
    ),
    spec_path: Path | None = typer.Option(
        None, "--spec", help="Spec path; defaults to a synthetic one if missing."
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Open a CI-owned review Session (Phase 07 / Level 3)."""
    from cortex.ci.review_session import open_review_session

    service, _ = _build_session_service(project_root)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    suffix = (
        f"pr-{pr_number}-review"
        if pr_number is not None
        else f"{head_branch.replace('/', '-').lower()}-review"
    )
    spec_id = f"{today}_{suffix}"
    record = open_review_session(
        service,
        spec_id=spec_id,
        base_commit=base_commit,
        head_branch=head_branch,
        pr_number=pr_number,
        spec_path=spec_path,
    )
    if output_json:
        typer.echo(
            json.dumps(
                {"session_id": record.session_id, "status": record.status.value},
                ensure_ascii=False,
            )
        )
        return
    typer.echo(record.session_id)


@ci_app.command("report-checkpoint")
def report_checkpoint_command(
    session_id: str = typer.Option(..., "--session-id"),
    from_validation_result: Path | None = typer.Option(
        None,
        "--from-validation-result",
        help="JSON file produced by `cortex ci validate-pr --format json`.",
    ),
    manual_claim: list[str] = typer.Option(
        [], "--manual-claim", help="Manual verified claim (repeatable)."
    ),
    manual_artifact: list[str] = typer.Option(
        [], "--manual-artifact", help="Manual artifact path (repeatable)."
    ),
    note: str = typer.Option("", "--note"),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Emit a ``CI_BOT`` checkpoint into the review session."""
    from cortex.ci.review_session import report_ci_checkpoint

    service, _ = _build_session_service(project_root)
    payload: dict[str, object] | None = None
    if from_validation_result is not None:
        try:
            payload = json.loads(from_validation_result.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            typer.echo(f"✗ could not load --from-validation-result: {exc}", err=True)
            raise typer.Exit(EXIT_ERROR) from None
    record = report_ci_checkpoint(
        service,
        session_id=session_id,
        validation_payload=payload,
        manual_claims=manual_claim,
        manual_artifacts=manual_artifact,
        note=note,
    )
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "session_id": record.session_id,
                    "checkpoint_count": len(record.checkpoints),
                },
                ensure_ascii=False,
            )
        )
        return
    typer.echo(f"checkpoint emitted; total={len(record.checkpoints)}")


@ci_app.command("close-review-session")
def close_review_session_command(
    session_id: str = typer.Option(..., "--session-id"),
    status: str = typer.Option(
        "closed",
        "--status",
        help="Terminal status: closed | handoff | abandoned.",
    ),
    reason: str = typer.Option("", "--reason"),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Close the review session into a terminal status."""
    from cortex.ci.review_session import close_review_session
    from cortex.session import SessionStatus

    allowed = {"closed", "handoff", "abandoned"}
    if status not in allowed:
        typer.echo(f"✗ --status must be one of {sorted(allowed)}", err=True)
        raise typer.Exit(EXIT_ERROR)
    service, _ = _build_session_service(project_root)
    record = close_review_session(
        service,
        session_id=session_id,
        status=SessionStatus(status),
        reason=reason,
    )
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "session_id": record.session_id,
                    "status": record.status.value,
                    "mode": record.mode.value,
                },
                ensure_ascii=False,
            )
        )
        return
    typer.echo(f"{record.session_id} → {record.status.value} (mode={record.mode.value})")


__all__ = ["ci_app"]
