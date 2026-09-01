# Entendimiento de Cortex — síntesis completa (foco Rust)

> Documento generado el 2026-08-27 tras una exploración con subagentes especializados.
> Foco: la parte Rust. El Python (`cortex/`, `pyproject.toml`) está **deprecado** — solo sobrevive como oráculo de paridad del CI.

---

## 1. Qué es

**Cortex es una capa de memoria y gobernanza para agentes de IA** ("memoria cognitiva híbrida + gobernanza", v0.7.0) que vive dentro del repositorio del proyecto. Le da a cualquier agente — Claude Code, Cursor, Codex, OpenCode, Pi o cualquier cliente MCP — el mismo contexto persistente, el mismo flujo disciplinado y el mismo cierre verificable que tiene un buen equipo de ingeniería: *specs → trabajo verificado → sesiones documentadas*. Todo corre **local**: un binario nativo Rust, un vault markdown, y opcionalmente un LLM local. Sin API keys, sin nube, sin telemetría.

## 2. La filosofía (por qué existe)

Resuelve **tres fallas** de los agentes de IA ("potentes y amnésicos"):

| Falla | Solución |
|---|---|
| **Amnesia** | Memoria híbrida persistente (episódica + semántica), bilingüe ES/EN |
| **Sin disciplina** | Sesiones spec-driven con checkpoints, quality gates y cierre verificable — **"Done means proven, not said"** |
| **Sin contexto compartido** | Un solo vault/sesiones/reglas leídos por todos los agentes vía CLI + MCP (single source of truth) |

Principios de diseño transversales:

- **La Sesión es la unidad de trabajo**: abre desde una spec → checkpoints → `cortex finish` (verificación real, hooks de la spec ejecutados) → `cortex next` (Action Engine sugiere el siguiente paso). Tres modos inferidos automáticamente: Managed / Observed / BYO.
- **Todo local por diseño**: embeddings ONNX (ES: multilingual-e5-large MRR@10 0.96; EN: MiniLM-L6-v2 1.0) y LLM opcional llama.cpp/GGUF.
- **El Brain "propone, nunca muta"**: asistente local read-only que devuelve el comando CLI exacto; las mutaciones son imposibles por diseño.
- **Verificabilidad**: cierre CLOSED solo si todos los hooks requeridos pasaron y no hay trabajo unimplementado; doctor de salud; pipeline con gates que abortan temprano.

## 3. Historia: por qué Python quedó deprecado

- **Obra 03**: el núcleo caliente (búsqueda, BM25, webgraph) se migró a Rust vía PyO3; el dueño exigía rendimiento máximo (query Python pura sin numpy: ~900 ms cold start, ~100 MB RSS).
- **Obra 07 (2026-08)**: decisión de **migración total** con *paridad byte-a-byte como contrato* — los tests Python son la especificación; los outputs `--json` se comparan byte-a-byte contra fixtures. ~25k LOC Python → ~94k LOC Rust en 20 crates. Fases P0–P12 + cierres T1–T7, cada una con gates `*_golden*.py` (build/verify).
- **Baja física (ago-2026)**: el **passthrough a Python fue eliminado por completo**. `CORTEX_PY=1` es solo un aviso histórico; catch-all = `No such command` rc 2. **El CLI nativo no delega nada en Python.** El paquete Python sobrevive únicamente como **oráculo de paridad congelado del CI** (2552 passed / 21 skipped / 0 failed), a la espera de la decisión del dueño sobre su borrado físico.

Regla operativa vigente: *"Paridad antes que velocidad; drift visible ⇒ revert"*. Por eso se rechazan f32/SIMD (cambiaría bits), BM25 casero en vez de tantivy (el oráculo cuenta substrings, no tokens), suma compensada de Neumaier para replicar `sum()` de CPython.

## 4. Arquitectura Rust actual (20 crates, 4 capas, sin ciclos)

| Capa | Crates | Rol |
|---|---|---|
| **Base / dominio puro** | `cortex-core` (BM25, scoring coseno, store vectorial v3, webgraph), `cortex-config`, `cortex-embed` (ONNX, dim siempre paramétrica), `cortex-branding` | Sin pyo3, 100% offline, bit-exactitud |
| **Infraestructura** | `cortex-setup` (11 adapters IDE + hooks + jinja/yaml byte-parity), `cortex-workspace` (layout, handoff, pyyaml), `cortex-py` (fachada PyO3 histórica, código de transición) | Ports de setup/workspace |
| **Aplicación / dominio portado** | `cortex-app` (el más grande: session+quality gates+verification, documenter, semantic, episodic, context), `cortex-services` (SpecService/NoteService transaccionales), `cortex-actions` (Action Engine), `cortex-mcp` (32 tools rmcp), `cortex-enterprise`, `cortex-autopilot`, `cortex-pipeline`, `cortex-tui` | Lógica de negocio |
| **Fachadas / binarios** | `cortex-cli` (dispatch manual por primer token), `cortex-doctor`, `cortex-webgraph-server` (axum), `cortex-tutor`, `cortex-brain` | Superficies |

Principios estructurales: `#![forbid(unsafe_code)]` en la lógica de negocio, backends inyectables para determinismo, recursos reales embebidos con `include_str!`, patrón **P6/P9** (lo que no es nativo da fallo EXPLÍCITO documentado, nunca se finge paridad), serializadores réplica de CPython (`pyjson`/`pyyaml`).

## 5. Qué hace: las 5 superficies sobre un núcleo único

1. **CLI** (`cortex-cli` — 27 familias): `session` (current/checkpoint/task/hooks/watch…), `next` (Action Engine), `search`, `context`, `remember/forget`, `docs` (validate/restore/list-backups/routing-table), `ci` (validate-pr, review sessions), `setup` (agent/pipeline/full/enterprise), `ide`, `hu` (historias de usuario), `pr-context`, `mcp-serve`, `webgraph` (export/serve/doctor), `autopilot` (start/preflight/checkpoint/finish/status), `tutor`, `hint`, `doctor`, `org-config`, `promote/review-knowledge`, `memory-report`, `install-skills`, `agent-guidelines`, `stats`, `reindex` (solo `--dry-run` nativo). Salidas texto + `--json` byte-parity. Códigos canónicos: 0 ok / 1 runtime / 2 comando desconocido.
2. **TUI** (ratatui, ELM-lite): splash, home, sesiones, detalle, búsqueda, pantalla de aprobación de acciones (lote auto-ok con `a`). Render nunca muta dominio.
3. **MCP server**: 32 tools canónicas congeladas (contrato `list_tools.json` byte-a-byte, server_version 2.2), transporte stdio rmcp.
4. **IDE**: 11 adaptadores (claude_code, codex, cursor, pi, vscode, zed, windsurf, opencode, claude_desktop, hermes, antigravity) que instalan hooks/prompts/skills/MCP config con paridad fiel; session hooks que emiten checkpoints.
5. **Brain**: asistente local determinista por defecto (cero tokens, sin modelo), con LLM opcional LFM2.5 GGUF vía llama.cpp; protocolo TOOL con confirmación; **read-only por diseño**.

**Action Engine** (la capa proactiva): catálogo de 10 acciones, scheduler `score = (impacto × frescura − costo) × aprendido`, feedback del usuario (±25%, ventana 14d), dry-run nativo, irrevocables exigen aprobación.

## 6. Qué aporta concretamente (valor medido y documentado)

- **Rendimiento**: cold start de comandos livianos **2–9 ms** (objetivo <100 ms; Python ~900 ms); scoring 27.6×, ingesta 3684×, BM25 p99 1.85 ms, webgraph n1000 3162→345 ms; RSS <25 MB objetivo.
- **Disciplina verificable**: sesiones que solo cierran con evidencia (claims verificadas vs no verificadas, placeholders prohibidos, ADRs sugeridos); quality gates en 2 etapas (spec compliance + calidad).
- **Memoria híbrida real**: RRF k=60 con pesos por intención (episodic/semantic/mixed), embeddings per-language, feedback persistido (`feedback.jsonl`), webgraph para descubrimiento relacional.
- **Gobernanza que escala**: enterprise con org.yaml, clasificación public/internal/confidential, promoción de conocimiento con records auditable, retrieval multi-scope.
- **Un solo binario**: `cargo install` — sin runtime Python, sin pipx.

## 7. Estado actual y lo que queda (verificado 2026-08-27)

- `cargo test --workspace`: **587 passed / 0 failed**; clippy y check limpios. Oráculo Python 2552/21/0/0.
- **WIP sin commitear** (40 archivos): P8d porteos de adaptadores IDE (pi, claude_desktop, vscode, zed, codex) + TUI sessions/branding — rama `feature/transformacion-2026-08`.
- **Deuda documentada, no bloqueante**: `hu import` http(s) real (falta cliente HTTP, requiere ADR), `reindex` real = fallo explícito, `webgraph_dependencies` no-op, brain aún delega por subprocess al CLI (plan: integrarlo in-process), fachada `cortex-py` sin consumidor productivo.
- **Decisiones del dueño pendientes**: borrado físico de Python (hoy es el oráculo del CI), release 0.7.0, GPU para e2e, ventana `pct_motor`, destino del tutor.

## 8. Convenciones del repo (para trabajar en él)

- Commits Conventional en **español** con scope de obra: `feat(obra07 baja fisica):`, `fix(obra07 baja ruta2 A round1):`; mensajes densos con evidencia + métricas.
- "Un gate por commit", suite verde antes de commitear, verificación contra código real no checkboxes.
- Docs por obra en `docs/transformacion/` (01–12 + ADRs) con `ESTADO-ACTUAL.md`/`HANDOFF.md` como fuente de verdad.
- Verificación por crate (`cargo test -p <crate>`), 43 archivos de tests de integración, self-golden del CLI, 586 tests unitarios.

---

**Síntesis en 3 líneas**: Cortex convierte a los agentes de IA de amnésicos e indisciplinados en trabajadores con memoria institucional, sesiones verificables y contexto compartido — 100% local. El proyecto acaba de completar el hito histórico: migración total a un binario Rust nativo (~94k LOC, 20 crates) con paridad byte-a-byte contra el Python, que quedó deprecado como oráculo congelado del CI. El foco actual es cerrar el porteo de adaptadores IDE (P8d) y las decisiones finales del dueño.