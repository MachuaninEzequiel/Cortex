# ESTADO ACTUAL DEL PROGRAMA

> **ACTUALIZADO 2026-08-27 (ba ja definitiva completa — RUTA 1/2 + FASE FÍSICA).**
> Obra 07 (migración total a Rust): **P0–P12 ✅ + cierre T1–T7 ✅ · CIERRE
> COMPLETO · BAJA DEFINITIVA EJECUTADA**. El CLI nativo clap está wireado
> por completo; el passthrough fue ELIMINADO (`CORTEX_PY=1` = aviso
> histórico, catch-all = `No such command` rc 2, fallback.rs muerto);
> goldens archivados en `bench/parity/archive/`; README a binarios. Suite
> Python ORÁCULO de CI: **2552 passed, 21 skipped, 0 failed, 0 errors**.
> Handoff activo para agentes: `HANDOFF.md` §"HANDOFF ACTIVO".

## Estado consolidado al cierre

### Completado y verificado con paridad byte-a-byte vs Python

| Fase | Alcance | Gate |
|---|---|---|
| P0 | crates cortex-config/cortex-app + harness `bench/parity/` | doctor.txt · next_stats.json PASS |
| P1 | CortexConfig completa en serde | dumps idénticos ×2 fixtures |
| P2 | vault + embeddings ort + hybrid search | BM25 100/100 · semántico 100/100 rankings |
| P3 | episódica nativa (lectura) + exportador chroma→JSONL | round-trip 12/12 · vector 6/6 · keyword/entity ✓ |
| P4 | Session primitive + storage YAML + verification + gates | dumps 4/4 · hooks 5/5 · gates 6/6 · infer_mode 4/4 |
| P5 | reconstructor gitless/git-aware + DocumenterPersister | dump idéntico · note_body byte-parity |
| P6 🅰 | crate cortex-actions (ActionEngine+FeedbackStore) | 16/16 salidas `next` byte-a-byte |
| P7 🅰 | módulo context en cortex-app (Enricher+budget) | 3 bundles --json byte-a-byte |
| P8 🅱 | cortex-setup: minijinja+YAML réplica+writers+11 IDE+hooks | YAML 138/138+fuzz · renders/writers idénticos · ide 33/33 · hooks 38/38 |
| P9 🅱 | cortex-mcp (rmcp): catálogo+ruteo congelados | list_tools byte-a-byte · ping golden |
| P10 | branding + TUI ratatui + logo | snapshot <50ms · tests del stream |
| P11-ci 🅰 | plugin CI + SessionService completo | 23/23 comandos `cortex ci` byte-a-byte |

Verificación integral post-cierre (esta sesión): workspace tests +
clippy/fmt limpios, todos los oráculos golden re-verificados, suite Python
ORÁCULO **2552 passed, 21 skipped, 0 failed, 0 errors** (primera vez 100%
verde desde la recatorización; T5 `f6fb828`). Gates del cierre: T1
`cierre_mcp_golden` (51 escenarios), T2 `cierre_cli_golden` (39 casos + MCP
stdio bounded), T3 `cierre_autopilot_golden` (236 líneas) + `cierre_autopilot_check`, T4 `pipeline_golden_p12b` (3 casos Documentation + A-D), T6/T6-b
`sessions_screen` (5) + `t6b_session_watch` (3).

### Bugs reales descubiertos/corregidos durante la migración

1. OOM del kernel ×2 (`bench/int8_probe.py`) → fix + lección de memoria.
2. Keyword bypass episódico roto con chromadb moderno → filtro `$contains`.
3. `lstrip("./")` anulaba exención de artefactos procesales en quality_gates.
4. Glob patterns tratados como literales en claude_code uninstall (atrapado
   por el gate P8d antes del commit — stream B).
5. Test `blit_copia_solo_lo_opaco` de branding con fixture imposible
   (introducido por commit de banner post-P10) → fixture corregido
   (`dded2da`). Único fallo del workspace en la verificación final.

### Lo que TODAVÍA depende de Python (deuda residual documentada)

Tras el cierre de la Obra 07 + RUTA 1 + RUTA 2 + FASE FÍSICA de la baja
definitiva, el passthrough de `cortex-cli` quedó ELIMINADO por completo
(`CORTEX_PY=1` = aviso histórico que continúa nativo; catch-all =
`No such command` rc 2; fallback.rs muerto). Todo subcomando expuesto por
el oráculo es NATIVO. Deuda documentada no bloqueante: `hu import` con
base_url http(s) real no tiene cliente HTTP nativo (requiere ADR de deps
en tarea futura; gate hermético con file://); `reindex` real = fallo
explícito (sin escritor de vectors persistente nativo).

Lo nativo en esta Obra (P0–P12 + cierre T1–T7 + RUTA 1 + RUTA 2): motores
híbridos (vault/embeddings/context/session/documenter/persister), CLI clap
(search/context/stats/session ×14/next/hu ×3/pr-context ×5/docs ×6/ci ×4/
setup ×5/ide ×4/autopilot ×6/remember/forget/reindex/mcp-serve/
webgraph ×3), MCP handlers no-sesión (T1), autopilot service+cli+mcp×5
(T3-paralelo), pipeline stage Documentation (T4), pantalla ratatui sesiones
+ `session watch/tui` (T6/T6-b). Auditoría exhaustiva:
`docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.2/§9.5/§9.6;
registros de los paquetes: `progreso-baja-a/b.md` (ruta 1) y
`progreso-baja-2a/2b.md` (ruta 2).

### Próximos pasos (post-cierre — baja definitiva de Python)

La Obra 07 (P0–P12 + cierre T1–T7) está completa, y la **baja definitiva
EJECUTADA** (RUTA 1 + RUTA 2 + FASE FÍSICA, 2026-08-26/27): todos los
leaves wireados, `CORTEX_PY=1` = rollback histórico, goldens archivados en
`bench/parity/archive/`, README a binarios. Queda para el dueño (fuera del
repo):

1. Decisión de borrado físico de `cortex/` + `tests/` + `pyproject.toml`
   (hoy son el ORÁCULO VIVO de CI: ci-gates.yml corre pytest 2552; borrarlos
   requiere mover la verificación a Rust puro primero).
2. Publicación de wheels solo-Rust (release, no repo) — `cargo install
   --path rust/crates/cortex-cli` ya es la instalación documentada.
3. Limpiezas: untracked + deprecaciones runtime.

Hasta ahí llegó esta Obra. Los pasos 2-3 son un **paquete separado** (ver
definición de hecho en `PROMPT-CIERRE-OBRA07.md` §"Definición de hecho").

## Obra 08 — Stream A: Modo COMPOSED y skills expertas (2026-08-28) ✅

Spec: `13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md` (RESUELTO). Plan:
`PLAN-OBRA08-STREAM-A.md`. Ejecución SDD en rama `feature/obra08-streamA`
(worktree hermano), 13 tasks + 1 fix round (R12).

**Features entregadas (gates G-A1…G-A6 PASS):**

- **Schema**: `CheckpointPhase` (grill/spec/plan/implement/review/close) +
  campo `phase: Option` en Checkpoint — round-trip YAML, backward-compat
  (sin fase ⇒ serialización idéntica, emisores actuales intactos).
- **4º modo**: `SessionMode::Composed` (serializa `"composed"`) —
  `infer_mode` con la prioridad exacta de la spec (∃fase ⇒ COMPOSED gana a
  MANAGED).`phase` visible en `session show/list --json`.
- **Barra de calidad por fase** (`check_phase_gate`, pure): spec/review
  requieren claim con evidencia; plan/implement exigen artifacts (implement
  sin evidencia ⇒ redelegate); grill sin gate; `phase: None` ⇒ comportamiento
  actual exacto.
- **Validación dura**: `phase` inválida rechazada en `SessionService` +
  handler MCP con mensaje canónico; contrato MCP congelado (`list_tools.json`)
  recapturado sin cambios.
- **Documenter**: `phase_line` (`grill → spec → …`) + evidencia agrupada por
  fase; sección `## Fases` en la nota solo cuando hay fases (template SSoT
  condicional ⇒ oráculo intacto, R9 validado); soft close
  (`require_close_phase: true` ⇒ HANDOFF + warning; default soft).
- **Skills thin + craft on-demand** (R10 flat): sync 144→83,
  SDDwork 249→99, documenter 305→77 líneas + 4 craft hermanos
  (`cortex-sync-spec-craft.md`, `cortex-sync-proposal-craft.md`,
  `cortex-SDDwork-implement-craft.md`, `cortex-documenter-close-craft.md`);
  gobernanza/contrato MCP intactos; map Python y tests congelados sin tocar;
  copias del repo (`.cortex/skills/`) alineadas byte-a-byte con SSoT.
- **Familia COMPOSED** (8 skills de referencia en directorio: grill, to-spec,
  to-tickets, implement+craft, tdd+craft, diagnose, review+craft,
  glossary; SKILL.md + agents/openai.yaml doble harness) +
  `INSTALL-COMPOSED.md` + **`cortex setup composed`** (fixture e2e + smoke
  con binario release: familia byte-exacta + tríada + bloque AGENTS.md).
- **Action Engine**: `session.suggest_next_phase` (cadena grill→spec→plan→
  implement→review→close; precondición sesión activa con fase; costo instant,
  reversible, auto-ok).
- **R12 (fix del gate)**: bloque `## Agent skills` con marcadores DEDICADOS
  (`COMPOSED_MARKER_*`) — coexiste con la sección codex en el mismo
  AGENTS.md (antes se pisaban en silencio); test unit + e2e de coexistencia
  y replay.

**Verificación:** `cargo test --workspace` **569 passed / 0 failed** ·
`cargo clippy --workspace --all-targets -- -D warnings` limpio ·
`cargo fmt --check` OK. Cold start release N=20: `setup composed --help`
mediana **4–6 ms** (objetivo <100 ms); `doctor` mediana 38–40 ms (rc 1
esperado fuera de proyecto). Smoke real `setup composed` sobre fixture:
rc 0, familia byte-igual al template, tríada thin+craft, AGENTS.md con
marcadores dedicados.

**Divergencias declaradas (registro oficial, no recapturar):**

1. **Schema `phase` = extensión nativa Rust-only** (R1): oráculo congelado;
   sus fixtures no usan fase; campos nuevos omiten serialización ⇒ dumps
   idénticos.
2. **`bench/parity/archive/golden_actions/*/next_why_not.json`**: los
   goldens archivados ganan entrada `session.suggest_next_phase` en
   explicaciones why-not. **CI-inerte** (gates archivados); no se recaptura;
   se regeneraría solo si revive el gate.
3. **`cortex finish` NO está wireado** (R13): el nombre documentado
   (`docs/transformacion/05`) no existe en `dispatch_native` (catch-all
   rc 2); los flujos reales de cierre son `cortex autopilot finish` /
   `cortex session abandon` + documenter. Wiring = paquete separado.
4. **`## Fases` en nota de sesión**: template SSoT condicional (R9) — Python
   lee el mismo archivo; sin fase ⇒ salida idéntica (goldens `test_session_
   template_conditional` pasan sin recaptura).

**Deuda menor registrada (deferred, ver ledger SDD):** ~60-70 líneas
objectivo no estricto en SDDwork (99); headers "10 acciones" (ahora 11) en
docs; `cortex next` sin cache de fase (re-parse triple); scoring
suggest_next_phase 6.0 (Mantenimiento) desplaza acciones 5.0 — una línea a
Learning si el dueño quiere prioridad mínima; `session current --json` no
muestra `mode` (list/show sí).

## Reglas operativas vigentes

1. Suite Python completa = oráculo hasta la baja final; verificar Rust
   SIEMPRE por crate (`cargo test -p …`).
2. Paridad antes que velocidad; drift visible ⇒ revert.
3. Memoria: un modelo residente por vez · batches ≤64 · sin `/tmp` como caché.
4. Commits atómicos un-gate-por-commit · suite verde antes de commitear.
5. Dual-stream CERRADO: las reglas §4b de coordinación quedan históricas;
   el refresco documental vuelve a ser parte del flujo normal.
