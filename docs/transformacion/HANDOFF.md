> **HISTÓRICO (Obra 07 + 08).** A partir de 2026-08-29 la autoridad de
> *qué está hecho / qué falta / qué se construye* es
> `docs/transformacion/16-DEUDA-REAL-Y-NORTE-DE-PULIDO.md`.
> Este HANDOFF es crónica de cierre. Si contradice el 16, gana el 16.

> **HANDOFF ACTIVO (2026-08-26, cierre completo OBRA 07).**
> Obra 07: P0–P12 ✅ COMPLETADAS + cierre T1–T7 ✅ · **OBRA 07 — CIERRE
> COMPLETO**. Si algo acá contradice historia vieja, MANDA ESTA SECCIÓN.
> El paso siguiente (baja definitiva de Python) es un paquete separado,
> fuera de esta Obra.

## 0. Contexto en 30 segundos

Cortex (`cortex-memory` v0.7.0): memoria cognitiva híbrida + gobernanza.
Programa: migración TOTAL Python→Rust (Obra 07, plan maestro
`docs/transformacion/08-MIGRACION-TOTAL-RUST.md`). **Obra 07 EN CIERRE
COMPLETO** (P0–P12 + cierre T1–T7). Suite Python = ORÁCULO (2552 passed,
21 skipped, 0 failed, 0 errors). Paridad-como-contrato en todo. Lo que sigue
(baja definitiva de Python) es un paquete separado.

## 1. Estado por fases

P0–P12 ✅ + cierre T1–T7 ✅ (detalle y gates: `ESTADO-ACTUAL.md`). El
CLI nativo clap tiene wireados: search/context/stats/reindex/next/session
×9/hu ×2/pr-context ×5/docs ×2/ci ×4/setup ×5/mcp-serve; MCP handlers
no-sesión (T1); autopilot service+cli+mcp×5 (T3); pipeline Documentation
real (T4); pantalla ratatui + `session watch/tui` (T6/T6-b). Verificación:
workspace tests + clippy/fmt, suite Python **2552 passed, 21 skipped**.

## 2. LÉEME ANTES DE TOCAR NADA — estado post-cierre

**La Obra 07 está en cierre completo.** El CLI nativo `cortex-cli` tiene
wireados la mayoría de los subcomandos (ver §1); el passthrough residual
quedó reducido a `CORTEX_PY=1` (rollback) más leaves fuera del inventario
T2-cola (brief prohibió expandir sin requisito vinculante):

- `session task/hooks`, `ide`, `docs validate/restore/list-backups`,
  `hu import`, `remember/forget/init/inject`, `webgraph serve/doctor`,
  `autopilot doctor/install/uninstall`.

Son deuda abierta documentada (ver `ESTADO-ACTUAL.md` §"deuda residual"),
no falla del cierre. La auditoría exhaustiva pre-cierre vive en
`docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.2 (con ítems
resueltos marcados post-cierre).

## 3. Cómo verificar (SIEMPRE)

```bash
cd rust
cargo fmt --all --check && cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace            # 219 passed al cierre; igualmente
                                  # preferí -p <crate> si tocas uno solo
```

Paridad: cada fase tiene su oráculo en `bench/parity/*_golden*.py`
(modos build/verify). Suite Python:
`.venv/bin/python -m pytest tests/unit tests/integration --no-cov`.

## 4. Decisiones cerradas (no re-discutir)

1. Paridad bit-exacta; f32/SIMD prohibido sin ADR que re-valide.
2. BM25 casero (substring semantics); tantivy descartado.
3. Embeddings por ort sobre artefactos chroma/fastembed cacheados.
4. ChromaDB sale → store nativo JSONL/export neutro.
5. minijinja/ratatui/rmcp/tokio/git2 aprobados como deps del porteo.
6. Brain: propone-nunca-muta; LFM2.5 GGUF vía llama.cpp.
7. Fachada passthrough cortex-cli (G6): subcomandos nativos se agregan ahí
   cuando existan, sin romper el passthrough mientras dure la transición.
8. MCP wire-format exacto (nulls explícitos vs omisión rmcp): RESUELTO
   por el dueño (2026-08-24): OMISIÓN rmcp como formato canónico del
   ENVELOPE (stdio y http); payloads de tools siguen byte-a-byte; gate de
   equivalencia estructural contra golden list_tools.json (null ≡ ausente,
   descriptions/schemas profundos idénticos). Análisis completo:
   docs/transformacion/11-COMPANION-ENGINE-P13.md Anexo A.
9. Los motores no-nativos devuelven fallo EXPLÍCITO documentado (patrón
   P6/P9): nunca se finge paridad conductual.

## 5. Reglas de trabajo heredadas

Suite verde antes de cada commit · planes mandan · verificación contra código
real, no checkboxes · un gate por commit · commits atómicos prefijados ·
reglas de memoria: un modelo residente por vez, batches ≤64, caché jamás en
/tmp.

## 6. Deudas/decisiones pendientes del dueño

GPU para ≥5× e2e · release 0.7.0 (CHANGELOG normalizado) · ventana pct_motor
(≥2 semanas uso real) · tutor: ¿migrar o reemplazar por ratatui/no-migrar? ·
limpieza de untracked (progress.md scratch, uv.lock, runtime jsonl/json)
cuando corresponda. Wire-format MCP: RESUELTO (ver §4.8). Passthrough
residual post-cierre: ver §2 (deuda documentada, decisión del dueño para el
paquete de baja definitiva separado).

## 7. CIERRE OBRA 07 — métricas y registros (2026-08-26)

**OBRA 07 — CIERRE COMPLETO.** T1–T7 gateados; oráculo 100% verde.

**RUTA 1 BAJA DEFINITIVA — COMPLETA (2026-08-26).** Tras la Obra 07, el
paquete "BAJA DEFINITIVA — RUTA 1" (doc
`PROMPT-BAJA-DEFINITIVA-RUTA1.md`) wireó en dos mitades paralelas A/B
(territorios disjuntos, main.rs/mod.rs congelados por scaffold):

- MITAD A (`14bfcfd`+`24885b8`): session task ×5, session hooks ×4,
  remember/forget (portes SessionService::list_tasks/update_task_status y
  NativeEpisodicStore::delete; ensure_ascii=False local).
- MITAD B (`ebc0cad`+`6934564`): ide ×4, docs validate/restore/
  list-backups/routing-table (portes list_backups/restore_backup tar y
  RouteSpec completo).
- Gates: `cierre_leaves_a_golden` 33 casos (188 líneas) +
  `cierre_leaves_b_golden` 26 casos (554 líneas), byte-parity vs CLI
  Python REAL. Oráculo **2552 passed, 21 skipped, 0F 0E** (120 s, lock).
- Cold start N=20: livianos 2.4–6.4 ms; remember/forget ~117–187 ms (ONNX
  honesto). Revisión por tarea + fix rounds: ambas Approved.

**RUTA 2 BAJA DEFINITIVA — COMPLETA (2026-08-26).** Paquete
`PROMPT-BAJA-DEFINITIVA-RUTA2.md`, dos mitades paralelas A/B:
- MITAD A (`5ad44ab`+`f53bdc6`): `autopilot doctor` nativo (port exacto de
  run_diagnosis; rc 0 como el oráculo) — `autopilot install/uninstall`
  ELIMINADOS en Fase 04 del oráculo: rechazo nativo rc=2 SIN Python.
- MITAD B (`b62b0e1`): `webgraph serve` (wrapper create_app axum,
  smoke P12B-2), `webgraph doctor` (5 checks byte-parity), `hu import`
  (glue WorkItemService + JiraProvider file://).
- Gates A/B PASS (5+5 casos byte-parity + equivalencias Fase 04/S19 +
  smoke serve); oráculo **2552/21/0/0**; cold start 2.0–55 ms.
- DEUDA documentada: hu import con http(s) real requiere cliente HTTP
  nativo (ADR de deps futuro); webgraph_dependencies no-op fuera del venv.

**Passthrough de `cortex-cli` = SOLO rollback `CORTEX_PY=1`.**
Ruta 2 resuelta; decisión de archivo/borrado de Python y goldens pendiente
del dueño (paquete separado). Registros: `progreso-baja-2a.md` +
`progreso-baja-2b.md`.

**FASE FÍSICA EJECUTADA (2026-08-27, `a61122c`+`27410dc`+`9611f69`, paquete
`PROMPT-BAJA-FISICA.md`):** passthrough ELIMINADO — `CORTEX_PY=1` = aviso
histórico que continúa nativo, catch-all = `No such command '<cmd>'.` rc 2,
`fallback.rs` muerto, `reindex` real = fallo explícito rc 1, `init` = alias
nativo de setup agent; goldens archivados en `bench/parity/archive/` con
README histórico (ningún workflow de CI los corre); README instalación por
binario (`cargo install --path rust/crates/cortex-cli`), wheel Python =
legado congelado (oráculo CI vivo). Verificación: `cargo test --workspace`
83/83, oráculo **2552/21/0/0**, smokes manuales ✓, revisión Approved.
**El CLI nativo NO ejerce ningún passthrough a Python.**

Métricas:
- Suite Python ORÁCULO: **2552 passed, 21 skipped, 0 failed, 0 errors**
  (primera vez verde desde la recatorización).
- Subcomandos CLI wireados nativos: search, context, stats, reindex, next,
  session ×9 (current/checkpoint/switch/diff/abandon/list/show/watch/tui),
  hu ×2 (list/show), pr-context ×5 (capture/store/search/generate/full),
  docs ×2 (search/migrate), ci ×4 (validate-pr/open-review-session/
  report-checkpoint/close-review-session), setup ×5 (agent/pipeline/
  full/webgraph/enterprise), mcp-server/mcp-serve.
- Familias MCP in-process: search/context/sync_ticket, write_doc ×11 + design
  + HU, spec/proposal/governance/gap, finish/briefing (T1, 51 escenarios).
- Autopilot service + subapp cli + tools MCP ×5 (T3-paralelo, 236 líneas).
- Pipeline Documentation stage nativa conectada al persister/reconstructor
  (P5), con gate `pipeline_golden_p12b` (3 casos + flows A–D).
- Pantalla sesiones ratatui nativa + integración `session watch/tui`
  (T6/T6-b), 5 + 3 tests.
- Cold start release N=20: comandos livianos 2–9 ms (<100 ms); comandos con
  memoria/ONNX (pr-context store/search/full) ~308–366 ms reporte honesto.

Registros de la sesión (fuentes de verdad):
- `docs/transformacion/progreso-cierre.md` (stream principal T2/T4/T6-b)
- `docs/transformacion/progreso-cierre-paralelo.md` (stream paralelo T3/T6)

El paso siguiente (baja definitiva de Python, paquete separado) está fuera
de esta Obra.
---



## 8. OBRA 08 STREAM A — Modo COMPOSED y skills expertas (2026-08-28)

> Si algo contradice §0–§7 (historia Obra 07), MANDA ESTA SECCIÓN para el
> stream A. El stream B (Herdr Companion) se integró en el mismo merge
> (ver §9 abajo).

**Estado: COMPLETO** — spec `13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md`
(RESUELTO), plan `PLAN-OBRA08-STREAM-A.md`, 13 tasks + fix R12. Rama
`feature/obra08-streamA` (HEAD `fix(obra08 streamA markers R12)` + docs de
cierre). Ver detalle y métricas en `ESTADO-ACTUAL.md` §"Obra 08 — Stream A".

**Qué cambió para quien trabaje en el repo:**

- `Checkpoint.phase: Option<CheckpointPhase>` (grill/spec/plan/implement/
  review/close) en `cortex-app/src/session/`. Checkpoint CON fase ⇒
  `infer_mode` ⇒ `SessionMode::Composed` ("composed" en --json).
- Gates por fase en `quality_gates::check_phase_gate` (puro); validación
  dura de fase inválida en `SessionService::checkpoint` + handler MCP
  (mensaje canónico, patrón P6/P9).
- Documenter: `phase_line` + `evidence_by_phase` → sección `## Fases`
  condicional en la nota (template SSoT `cortex/documentation/templates/
  session.md.j2`, R9: Python lee el mismo archivo, sin fase ⇒ idéntico).
- Skills de la tríada thin + craft hermanos on-demand (R10 flat); SSoT en
  `cortex/setup/workspace_files/`; `.cortex/skills/` del repo alineado.
- `cortex setup composed`: familia de 8 skills + INSTALL-COMPOSED.md +
  bloque `## Agent skills` con marcadores DEDICADOS (R12 — coexiste con
  codex en AGENTS.md).
- `session.suggest_next_phase` en el Action Engine (11 acciones).

**Deuda restante del stream A (documentada, no bloqueante):**

1. `cortex finish` sin wirear (R13 — documentado en ESTADO-ACTUAL; paquete
   separado).
2. `phase` NO en el inputSchema congelado de `cortex_session_checkpoint`
   (el arg se acepta y valida; schema = contrato congelado; recaptura solo
   con decisión de dueño).
3. Migración de las skills a formato directorio `SKILL.md + references/` →
   obra POST-baja del oráculo (R10).
4. Menores del ledger SDD (headers "10 acciones", cache de fase, scoring
   6.0, etc.) — ver `.superpowers/sdd/PLAN-OBRA08-STREAM-A/progress.md`.


## 9. OBRA 08 STREAM B — Herdr Companion (2026-08-28) — COMPLETO

Estado: tasks B1–B10 con review Approved cada una (fueron necesarias 4 rondas
de fix: B5 hit-test, B6 comando modal, B7 'q' en Search + deadlock test +
geometría input, B9 min_herdr_version). Suite workspace: **594 passed / 0
failed / 1 ignored** (el ignore = rss_measure manual). clippy --all-targets
-D warnings y fmt limpios.

Superficie: crate `cortex-companion` (ratatui mouse-first, Backend in-process
con paridad JSON byte-idéntica vs CLI por construcción, run_guarded con
auditoría, brain híbrido con tools enrutadas 1:1 al engine, menú de 27
familias anti-olvido) + plugin herdr declarativo (`integrations/herdr/`,
manifest verificado en herdr 0.7.3 real del dueño).

Deuda/fase 2 (documentada en 14-… §9):
- Web Hub localhost (axum + /brain/chat SSE) como segunda superficie.
- Backend MCP/remoto del Companion (costura del trait Backend; P13 encaja).
- Brain 100% in-process standalone (el Companion ya lo logra para sus tools).
- Reuso de widgets cortex-tui post-estabilización (P8d/TUI).
- Integración documenter finalize para close_session real (hoy P6/P9 honesto).
- `herdr plugin re-link` tras merge: el link actual apunta al worktree
  /home/chucho/Cortex-obra08-B/integrations/herdr; ejecutar
  `herdr plugin unlink cortex.companion && herdr plugin link
  /home/chucho/Cortex/integrations/herdr` tras integrar la rama.
- Verificación manual del dueño: pane open (INSTALL.md §Verificar, “Paso
  manual (UI)”) + navegación por clic en su sesión herdr (INSTALL.md §Uso).
