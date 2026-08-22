"""cortex.documenter.interactive — Interactive prompt UX for ``finish-session``.

Phase 04 (T4.1) of the Pluggable Middle architecture: when the user runs
``cortex finish-session --interactive`` (or sets ``documenter.default_mode:
interactive`` in ``config.yaml``), the documenter renders the
reconstruction output with :mod:`rich`, surfaces ADR suggestions one by
one, and waits for the user's verdict before persisting anything.

Design:
    * UI rendering lives behind narrow methods on :class:`InteractiveSession`
      so tests can stub them out and exercise the state machine in
      isolation.
    * Actual user input goes through ``console.input`` and
      :func:`click.edit` (for the multi-line body editor), both of which
      are trivially monkeypatchable in tests.
    * The state machine emits a single :class:`InteractiveResult`. The
      caller (``cortex finish-session``) translates that into a
      :class:`cortex.documenter.persistence.FinishOverrides` and either
      invokes the persister or leaves the session OPEN (on cancel).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

InputProvider = Callable[[str], str]
EditorOpener = Callable[[str | None], str | None]

from cortex.session.models import SessionStatus

if TYPE_CHECKING:
    from cortex.documenter.reconstruction import ReconstructionOutput


class InteractiveAction(StrEnum):
    """Top-level decision the user makes at the interactive prompt."""

    APPROVE = "approve"
    EDIT = "edit"
    HANDOFF = "handoff"
    CANCEL = "cancel"


@dataclass
class InteractiveResult:
    """Outcome of one :meth:`InteractiveSession.prompt` invocation.

    Mutable because the EDIT path may mutate fields incrementally; the
    caller treats it as a value after ``prompt()`` returns.
    """

    action: InteractiveAction
    approved_adr_indices: list[int] | None = None
    edited_note_title: str | None = None
    edited_note_body: str | None = None
    forced_status: SessionStatus | None = None

    @property
    def cancelled(self) -> bool:
        return self.action is InteractiveAction.CANCEL


# ── Helper renderers (pure: take reconstruction, return Renderable) ──


def _render_summary_panel(
    reconstruction: ReconstructionOutput,
) -> Panel:
    spec = reconstruction.spec
    title = spec.title or reconstruction.session_id
    diff_count = len(reconstruction.diff_entries)
    files = sum(1 for _ in reconstruction.files_touched)
    hooks = reconstruction.verification_results
    hook_passed = sum(1 for r in hooks if r.passed)
    out_of_scope = len(reconstruction.out_of_scope_files)
    unimplemented = len(reconstruction.unimplemented_files)
    contradictions = len(reconstruction.contradictions)

    lines = [
        f"[bold]Session:[/bold] {reconstruction.session_id}",
        f"[bold]Spec:[/bold]    {title}",
        f"[bold]Diff:[/bold]    {diff_count} entry(ies), {files} file(s)",
        (
            f"[bold]Hooks:[/bold]   {hook_passed}/{len(hooks)} passed"
            if hooks
            else "[bold]Hooks:[/bold]   (none declared)"
        ),
    ]
    if out_of_scope:
        lines.append(f"[yellow]Scope drift:[/yellow]   {out_of_scope} file(s)")
    if unimplemented:
        lines.append(f"[yellow]Unimplemented:[/yellow] {unimplemented} file(s)")
    if contradictions:
        lines.append(f"[red]Contradictions:[/red] {contradictions} finding(s)")
    return Panel("\n".join(lines), title="📋 Reconstruction summary", border_style="cyan")


def _render_draft_panel(reconstruction: ReconstructionOutput) -> Panel:
    """Render the would-be session note body as Markdown inside a Panel."""
    lines: list[str] = []
    spec = reconstruction.spec
    lines.append(f"# {spec.title or reconstruction.session_id}")
    if spec.goal:
        lines.append("")
        lines.append(f"**Goal:** {spec.goal}")
    if reconstruction.diff_entries:
        lines.append("")
        lines.append("## Changes made")
        for entry in reconstruction.diff_entries:
            lines.append(f"- {entry.action}: `{entry.path.as_posix()}`")
    notes = [cp.note for cp in reconstruction.raw_checkpoints if cp.note]
    if notes:
        lines.append("")
        lines.append("## Key decisions (from checkpoints)")
        for note in notes:
            lines.append(f"- {note}")
    if reconstruction.unimplemented_files:
        lines.append("")
        lines.append("## Unimplemented (next steps)")
        for path in reconstruction.unimplemented_files:
            lines.append(f"- `{path.as_posix()}`")
    return Panel(
        Markdown("\n".join(lines)),
        title="📝 DRAFT session note",
        border_style="green",
    )


def _render_adr_panel(reconstruction: ReconstructionOutput) -> Panel | None:
    if not reconstruction.suggested_adrs:
        return None
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", width=3, justify="right")
    table.add_column("Title")
    table.add_column("Why suggested")
    for idx, adr in enumerate(reconstruction.suggested_adrs):
        table.add_row(str(idx), adr.title, adr.rationale[:120])
    return Panel(table, title="📋 ADRs suggested", border_style="yellow")


def _render_actions_panel() -> Panel:
    body = (
        "[bold]A[/bold]pprove   — persist everything as-is\n"
        "[bold]E[/bold]dit      — review title / body / ADRs one by one\n"
        "[bold]H[/bold]andoff   — close as HANDOFF (work incomplete)\n"
        "[bold]C[/bold]ancel    — leave session OPEN, no changes"
    )
    return Panel(body, title="⚙ Actions", border_style="magenta")


class InteractiveSession:
    """Drive the interactive finish-session prompt loop.

    Construct with a :class:`rich.console.Console` (production wires the
    real terminal; tests pass a ``Console(file=io.StringIO(), force_terminal=False)``
    plus a stub for ``console.input`` via ``input_provider``).
    """

    def __init__(
        self,
        console: Console | None = None,
        *,
        input_provider: InputProvider | None = None,
        editor: EditorOpener | None = None,
    ) -> None:
        self._console = console or Console()
        self._input: InputProvider = input_provider or self._console.input
        # click.edit is overloaded; cast to our narrower Protocol.
        self._editor: EditorOpener = editor if editor is not None else click.edit  # type: ignore[assignment]

    # ── Public API ─────────────────────────────────────────────────

    def prompt(self, reconstruction: ReconstructionOutput) -> InteractiveResult:
        """Render the reconstruction and capture the user's verdict.

        Returns an :class:`InteractiveResult`. Always returns — even on
        cancel the result is well-formed (``action=CANCEL``).
        """
        self._render(reconstruction)
        while True:
            choice = self._ask_main_action()
            if choice is InteractiveAction.APPROVE:
                return InteractiveResult(action=InteractiveAction.APPROVE)
            if choice is InteractiveAction.CANCEL:
                return InteractiveResult(action=InteractiveAction.CANCEL)
            if choice is InteractiveAction.HANDOFF:
                reason = self._ask_handoff_reason()
                if reason is None:
                    continue  # user aborted handoff sub-flow → back to main
                return InteractiveResult(
                    action=InteractiveAction.HANDOFF,
                    forced_status=SessionStatus.HANDOFF,
                )
            if choice is InteractiveAction.EDIT:
                # EDIT loop mutates these and then re-prompts the main menu.
                title_override = self._maybe_edit_title(reconstruction)
                body_override = self._maybe_edit_body(reconstruction)
                approved_adrs = self._review_adrs(reconstruction)
                self._console.print("[dim]Edits captured. Returning to main action prompt.[/dim]\n")
                final = self._ask_main_action_after_edit()
                if final is InteractiveAction.CANCEL:
                    return InteractiveResult(action=InteractiveAction.CANCEL)
                if final is InteractiveAction.HANDOFF:
                    reason = self._ask_handoff_reason()
                    if reason is None:
                        reason = ""
                    return InteractiveResult(
                        action=InteractiveAction.HANDOFF,
                        forced_status=SessionStatus.HANDOFF,
                        edited_note_title=title_override,
                        edited_note_body=body_override,
                        approved_adr_indices=approved_adrs,
                    )
                # default: APPROVE with edits applied
                return InteractiveResult(
                    action=InteractiveAction.APPROVE,
                    edited_note_title=title_override,
                    edited_note_body=body_override,
                    approved_adr_indices=approved_adrs,
                )

    # ── Internals: rendering ───────────────────────────────────────

    def _render(self, reconstruction: ReconstructionOutput) -> None:
        self._console.print()
        self._console.print(_render_summary_panel(reconstruction))
        self._console.print(_render_draft_panel(reconstruction))
        adr_panel = _render_adr_panel(reconstruction)
        if adr_panel is not None:
            self._console.print(adr_panel)
        self._console.print(_render_actions_panel())

    # ── Internals: prompts ─────────────────────────────────────────

    def _ask_main_action(self) -> InteractiveAction:
        while True:
            raw = self._input("Action [A/E/H/C]: ").strip().lower()
            mapped = _MAIN_ACTION_KEYS.get(raw)
            if mapped is not None:
                return mapped
            self._console.print("[red]Invalid choice. Use A, E, H or C.[/red]")

    def _ask_main_action_after_edit(self) -> InteractiveAction:
        """Subset of the main prompt: after EDIT we only allow A / H / C."""
        while True:
            raw = self._input("Confirm [A/H/C]: ").strip().lower()
            mapped = _AFTER_EDIT_KEYS.get(raw)
            if mapped is not None:
                return mapped
            self._console.print("[red]Invalid choice. Use A, H or C.[/red]")

    def _ask_handoff_reason(self) -> str | None:
        reason = self._input("Reason for handoff (empty cancels): ").strip()
        if not reason:
            return None
        return reason

    def _maybe_edit_title(self, reconstruction: ReconstructionOutput) -> str | None:
        current = reconstruction.spec.title or reconstruction.session_id
        prompt_text = f"Title [{current}]: "
        raw = self._input(prompt_text).strip()
        if not raw or raw == current:
            return None
        return raw

    def _maybe_edit_body(self, reconstruction: ReconstructionOutput) -> str | None:
        raw = self._input("Edit body in $EDITOR? [y/N]: ").strip().lower()
        if raw not in {"y", "yes"}:
            return None
        seed = self._seed_body_for_editor(reconstruction)
        edited = self._editor(seed)
        if edited is None:
            return None
        edited = edited.strip()
        if not edited or edited == seed.strip():
            return None
        return edited

    def _review_adrs(self, reconstruction: ReconstructionOutput) -> list[int] | None:
        adrs = reconstruction.suggested_adrs
        if not adrs:
            return None
        approved: list[int] = []
        for idx, adr in enumerate(adrs):
            raw = self._input(f"Approve ADR {idx} '{adr.title}'? [Y/n]: ").strip().lower()
            if raw in {"", "y", "yes"}:
                approved.append(idx)
        return approved

    # ── Internals: misc ────────────────────────────────────────────

    @staticmethod
    def _seed_body_for_editor(reconstruction: ReconstructionOutput) -> str:
        """Seed text passed to ``$EDITOR``. The user's edits replace it."""
        title = reconstruction.spec.title or reconstruction.session_id
        seed_lines = [
            f"# {title}",
            "",
            "<!-- Edit this body. Lines starting with <!-- are kept as comments. -->",
            "",
        ]
        for cp in reconstruction.raw_checkpoints:
            if cp.note:
                seed_lines.append(f"- {cp.note}")
        return "\n".join(seed_lines) + "\n"


_MAIN_ACTION_KEYS = {
    "a": InteractiveAction.APPROVE,
    "approve": InteractiveAction.APPROVE,
    "e": InteractiveAction.EDIT,
    "edit": InteractiveAction.EDIT,
    "h": InteractiveAction.HANDOFF,
    "handoff": InteractiveAction.HANDOFF,
    "c": InteractiveAction.CANCEL,
    "cancel": InteractiveAction.CANCEL,
}

_AFTER_EDIT_KEYS = {
    "a": InteractiveAction.APPROVE,
    "approve": InteractiveAction.APPROVE,
    "h": InteractiveAction.HANDOFF,
    "handoff": InteractiveAction.HANDOFF,
    "c": InteractiveAction.CANCEL,
    "cancel": InteractiveAction.CANCEL,
}


__all__ = [
    "InteractiveAction",
    "InteractiveResult",
    "InteractiveSession",
]
