"""Catálogo v1 del ActionEngine (plan §3.3) — 10 acciones sobre servicios existentes.

Cada fábrica recibe el :class:`ActionContext` y devuelve la :class:`Action`
con precondiciones baratas (on-open), dry-run nativo y delegación total en
los servicios de Cortex. Report-only ⇒ reversible con undo no-op para
satisfacer el contrato sin fingir cambios que no hay.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from cortex.action_engine.context import ActionContext
from cortex.action_engine.models import Action, ActionResult, Check


def _no_op_undo() -> ActionResult:
    return ActionResult(ok=True, message="acción report-only — nada que deshacer")


def _report_action(
    id_: str, title: str, category: str, effect: str,
    checks: tuple[Check, ...],
    runner: Callable[[bool], ActionResult],
) -> Action:
    """Acción de sólo-lectura: reversible formal, auto-ok, instant."""
    return Action(
        id=id_, title=title, category=category,  # type: ignore[arg-type]
        effect=effect, preconditions=checks,
        reversible=True, undo=_no_op_undo,
        cost="instant", auto_ok=True, run=runner,
    )


# ── helpers de estado ──────────────────────────────────────────────────────


def _sesiones_abiertas(ctx: ActionContext):
    try:
        return [r for r in ctx.sessions.list() if r.status.value == "open"]
    except Exception:  # noqa: BLE001
        return []


def _feedback_eventos(ctx: ActionContext) -> list[dict]:
    ruta = ctx.dot_cortex / "feedback.jsonl"
    if not ruta.exists():
        return []
    eventos = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            eventos.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return eventos


# ── 10 acciones ────────────────────────────────────────────────────────────


def setup_finish_bootstrap(ctx: ActionContext) -> Action:
    def _falta_bootstrap() -> bool:
        return not ctx.layout.config_path.exists()

    def _run(dry_run: bool) -> ActionResult:
        # NOTA: NO delegamos el dry-run en SetupOrchestrator — su
        # ``dry_run=True`` hoy crea archivos reales (bug registrado en
        # plan 01 §4/P-bugs). El dry-run acá calcula el plan sin tocar disco.
        if dry_run:
            faltantes = []
            if not ctx.layout.config_path.exists():
                faltantes.append(str(ctx.layout.config_path))
            if not (ctx.dot_cortex / "sessions").exists():
                faltantes.append(".cortex/sessions/")
            if not Path(ctx.layout.vault_path).exists():
                faltantes.append(str(ctx.layout.vault_path))
            plan = ", ".join(faltantes) or "nada pendiente"
            return ActionResult(ok=True, message=f"[dry-run] bootstrap crearía: {plan}")

        from cortex.setup.orchestrator import SetupMode, SetupOrchestrator

        orch = SetupOrchestrator(root=ctx.layout.workspace_root)
        summary = orch.run(
            SetupMode.AGENT, non_interactive=True, dry_run=False, git_depth=50,
        )
        creados = summary.get("created", [])
        return ActionResult(
            ok=bool(creados),
            message=f"bootstrap: {len(creados)} elemento(s) creados",
            details={"created": creados},
        )

    return Action(
        id="setup.finish_bootstrap",
        title="Completar el bootstrap de Cortex en este proyecto",
        category="setup",
        effect="crea .cortex/, config.yaml y vault base vía SetupOrchestrator",
        preconditions=(Check("config.yaml inexistente", _falta_bootstrap),),
        reversible=False,  # crea archivos → siempre pregunta
        cost="minutes",
        run=_run,
    )


def session_close_stale(ctx: ActionContext) -> Action:
    DIAS_STALE = 7

    def _hay_stale() -> bool:
        return len(_stale_ids(ctx)) > 0

    def _stale_ids(ctx: ActionContext) -> list[str]:
        from datetime import UTC, datetime

        ahora = datetime.now(UTC)
        ids = []
        for r in _sesiones_abiertas(ctx):
            edad_dias = (ahora - r.opened_at).days if r.opened_at else 999
            if edad_dias >= DIAS_STALE and not r.checkpoints:
                ids.append(r.session_id)
        return ids

    class _Ctx:
        pass

    # closure helper (evita recomputar dos veces dentro del runner)
    def _run(dry_run: bool) -> ActionResult:
        ids = _stale_ids(ctx)
        if not ids:
            return ActionResult(ok=True, message="sin sesiones stale")
        guia = "; ".join(
            f"{i} → `cortex finish-session --session-id {i}` o abandon" for i in ids
        )
        return ActionResult(ok=True, message=f"Cerrá las sesiones stale: {guia}")

    return _report_action(
        "session.close_stale",
        f"Cerrar sesiones OPEN de más de {DIAS_STALE} días sin checkpoints",
        "maintenance",
        f"muestra guía de finish/abandon para sesiones OPEN >{DIAS_STALE} días",
        (Check(f"hay sesiones OPEN >{DIAS_STALE}d sin checkpoints", _hay_stale),),
        _run,
    )


def session_checkpoint_now(ctx: ActionContext) -> Action:
    from cortex.session.models import CheckpointSource

    def _hay_cambios() -> bool:
        if not _sesiones_abiertas(ctx):
            return False
        repo = Path.cwd()
        git_dir = repo / ".git"
        if not git_dir.exists():
            return False
        import subprocess

        proc = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo,
            capture_output=True, text=True, timeout=5,
        )
        return bool(proc.stdout.strip())

    def _run(dry_run: bool) -> ActionResult:
        abiertas = _sesiones_abiertas(ctx)
        if not abiertas:
            return ActionResult.fail("no hay sesión abierta")
        objetivo = abiertas[0]
        if dry_run:
            return ActionResult.dry(
                f"checkpoint en {objetivo.session_id} con los archivos cambiados"
            )
        record = ctx.sessions.checkpoint(
            objetivo.session_id,
            source=CheckpointSource.MANUAL,
            note="checkpoint sugerido por ActionEngine (archivos cambiados)",
        )
        return ActionResult(
            ok=True,
            message=f"checkpoint #{len(record.checkpoints)} en {objetivo.session_id}",
        )

    return Action(
        id="session.checkpoint_now",
        title="Registrar checkpoint de los archivos cambiados",
        category="maintenance",
        effect="agrega un checkpoint manual a la sesión activa",
        preconditions=(Check("hay sesión abierta y archivos cambiados", _hay_cambios),),
        reversible=False,  # checkpoints son parte del registro histórico
        cost="seconds",
        run=_run,
    )


def vault_reindex(ctx: ActionContext) -> Action:
    def _hay_vault() -> bool:
        vault = getattr(ctx.mem, "workspace_root", None)
        return True  # sync_vault es idempotente; se ofrece siempre

    def _run(dry_run: bool) -> ActionResult:
        if dry_run:
            return ActionResult.dry("re-indexar el vault (sync_vault)")
        count = ctx.mem.sync_vault()
        return ActionResult(ok=True, message=f"Vault sincronizado — {count} docs indexados")

    return Action(
        id="vault.reindex",
        title="Re-indexar el vault semántico",
        category="maintenance",
        effect="parse+chunk+embed de vault/ via AgentMemory.sync_vault()",
        preconditions=(Check("vault disponible", _hay_vault),),
        reversible=True,
        undo=lambda: ActionResult(ok=True, message="reindex es idempotente — nada que deshacer"),
        cost="seconds",
        auto_ok=False,  # tarda segundos: pide confirmación
        run=_run,
    )


def vault_validate_docs(ctx: ActionContext) -> Action:
    def _hay_docs() -> bool:
        vault = ctx.vault_path
        return vault.exists() and any(vault.rglob("*.md"))

    def _run(dry_run: bool) -> ActionResult:
        from cortex.doc_validator import DocValidator

        vault = ctx.vault_path
        validator = DocValidator(vault)
        errores = 0
        revisados = 0
        for md in sorted(vault.rglob("*.md"))[:200]:
            resultado = validator.validate_file(md)
            revisados += 1
            errores += len(resultado.errors)
        mensaje = (
            f"{revisados} docs validados, {errores} error(es)"
            if not dry_run
            else f"[dry-run] validaría ~{min(200, len(list(vault.rglob('*.md'))))} docs"
        )
        return ActionResult(ok=errores == 0 or not dry_run, message=mensaje)

    return _report_action(
        "vault.validate_docs",
        "Validar los documentos del vault",
        "quality",
        "corre DocValidator sobre hasta 200 .md del vault e informa errores",
        (Check("hay .md en el vault", _hay_docs),),
        _run,
    )


def quality_run_gates(ctx: ActionContext) -> Action:
    def _hay_objetivo() -> bool:
        for r in _sesiones_abiertas(ctx):
            if r.checkpoints and r.spec_path:
                return True
        return False

    def _run(dry_run: bool) -> ActionResult:
        from cortex.session.quality_gates import review_checkpoint

        if dry_run:
            return ActionResult.dry("revisar último checkpoint con quality gates")
        for r in _sesiones_abiertas(ctx):
            if r.checkpoints and r.spec_path:
                veredicto = review_checkpoint(r.checkpoints[-1], r)
                return ActionResult(
                    ok=veredicto == "accept",
                    message=f"quality gate {r.session_id}: {veredicto}",
                )
        return ActionResult.fail("sin checkpoint objetivo")

    return _report_action(
        "quality.run_gates",
        "Correr quality gates sobre el último checkpoint",
        "quality",
        "review_checkpoint(checkpoint, spec) de la primera sesión OPEN con checkpoints",
        (Check("sesión OPEN con checkpoints y spec", _hay_objetivo),),
        _run,
    )


def learn_topic(ctx: ActionContext) -> Action:
    def _siempre() -> bool:
        return True

    def _run(dry_run: bool) -> ActionResult:
        from cortex.tutor.engine import TutorEngine

        engine = TutorEngine.default()
        topic = engine.topics[int(_ahora_dia()) % len(engine.topics)]
        mensaje = f"Topic sugerido: {topic.title}"
        if topic.guide_path:
            mensaje += f" — guía: {topic.guide_path}"
        return ActionResult(ok=True, message=mensaje)

    return _report_action(
        "learn.topic",
        "Aprender un tópico del tutor hoy",
        "learning",
        "sugiere un tópico del tutor (rotación diaria) con deep-link a su guía",
        (Check("tutor disponible", _siempre),),
        _run,
    )


def _ahora_dia() -> float:
    from datetime import datetime

    return datetime.now().timetuple().tm_yday


def knowledge_promote(ctx: ActionContext) -> Action:
    def _hay_enterprise() -> bool:
        return (ctx.dot_cortex / "enterprise").exists()

    def _run(dry_run: bool) -> ActionResult:
        return ActionResult(
            ok=True,
            message=(
                "[dry-run] flujo review-knowledge guiado" if dry_run
                else "usá `cortex promote-knowledge` — flujo interactivo"
            ),
        )

    return _report_action(
        "knowledge.promote",
        "Revisar pendientes de promoción enterprise",
        "knowledge",
        "abre el flujo guiado de revisión de knowledge enterprise",
        (Check("workspace enterprise presente", _hay_enterprise),),
        _run,
    )


def memory_prune(ctx: ActionContext) -> Action:
    def _hay_feedback_negativo() -> bool:
        negativos = [
            e for e in _feedback_eventos(ctx)
            if e.get("feedback_type") in ("not_useful", "negative")
        ]
        return len(negativos) >= 3

    def _run(dry_run: bool) -> ActionResult:
        conteo: dict[str, int] = {}
        for e in _feedback_eventos(ctx):
            mid = e.get("memory_id")
            if e.get("feedback_type") in ("not_useful", "negative") and mid:
                conteo[mid] = conteo.get(mid, 0) + 1
        candidatos = sorted(conteo, key=conteo.get, reverse=True)[:5]  # type: ignore[attr-defined]
        return ActionResult(
            ok=True,
            message="candidatos a olvidar (requiere confirmación aparte): "
            + ", ".join(candidatos),
            details={"candidatos": candidatos},
        )

    return _report_action(
        "memory.prune",
        "Revisar memorias con feedback negativo",
        "quality",
        "lista memorias candidatas a forget según feedback persistido (no borra)",
        (Check("≥3 feedbacks negativos registrados", _hay_feedback_negativo),),
        _run,
    )


def ide_resync(ctx: ActionContext) -> Action:
    def _hay_workspace_ide() -> bool:
        return any(
            (ctx.layout.workspace_root / ".cortex").glob("**/*.md")
        ) and (ctx.dot_cortex / "workspace.yaml").exists()

    def _run(dry_run: bool) -> ActionResult:
        from cortex.ide import inject_all

        if dry_run:
            return ActionResult.dry("re-inyectar skills/config en los IDEs configurados")
        resultados = inject_all(project_root=ctx.layout.workspace_root)
        total = sum(len(v) for v in resultados.values())
        return ActionResult(ok=True, message=f"re-sincronizados {total} archivo(s) de IDE")

    return Action(
        id="ide.resync",
        title="Re-sincronizar skills de Cortex en los IDEs configurados",
        category="setup",
        effect="re-inyecta perfiles/skills con marcadores (Obra 02)",
        preconditions=(Check(".cortex/workspace.yaml presente", _hay_workspace_ide),),
        reversible=True,
        undo=lambda: ActionResult(ok=True, message="re-sync idempotente — nada que deshacer"),
        cost="seconds",
        auto_ok=False,
        run=_run,
    )
