# Handoff a nueva sesión — continuación del proyecto Pluggable Middle

> **Para el agente que abra esta sesión en blanco.** Este documento contiene
> todo lo que necesitás saber para retomar el desarrollo sin contexto previo.
> Leelo de arriba abajo antes de tocar una sola línea de código.

---

## 0. ESTADO ACTUAL (snapshot)

**Fecha del handoff:** 2026-05-16  
**Rama de trabajo:** `feature/nuevo-modo-autonomo`  
**Repo:** `C:\Cortex` (Windows; PowerShell + Git Bash disponibles)

### Tabla de progreso del proyecto

| Fase | Nombre | Estado | Próximo paso |
|---|---|---|---|
| 00 | Foundations (Session primitive) | ✅ **Completa** | — |
| 01 | Documenter Reconstruction (BYO) | ✅ **Completa** | — |
| 02 | SDDwork Migration (Managed) | ✅ **Completa** | — |
| 03 | **Autopilot Fusion + Observed Mode** | ⏸ **Pendiente — TU TRABAJO** | T3.1 |
| 04 | Interactive + Final Polish | ⏸ Pendiente | — |

### Lo que YA FUNCIONA end-to-end

1. **BYO mode**: `cortex create-spec ... --verification-hook ... → editar con cualquier herramienta → cortex finish-session` → session note persistido, Session cerrada.
2. **Managed mode**: `cortex create-spec → SDDwork emite checkpoints (Fast/Deep Track) → cortex finish-session` → mode inferido = MANAGED, checkpoints surface en session note.

### Lo que FALTA (todo Fase 03)

3. **Observed mode**: hooks de IDE (Claude Code, Cursor, Pi) que emiten checkpoints automáticamente.
4. **Autopilot fusion**: `cortex/autopilot/` reescrito como thin layer sobre Sessions.

### Commits pendientes

**NADA HA SIDO COMMITEADO**. Todo el trabajo está en working tree.
Los `progress logs` de cada fase dicen explícitamente "Commit final hecho [ ]"
porque estamos esperando autorización del usuario. **NO HAGAS COMMIT** salvo
que el usuario te lo pida explícitamente.

---

## 1. ORDEN DE LECTURA OBLIGATORIO

Antes de tocar nada, leé en este orden:

### 1.1 Filosofía y arquitectura

1. **`docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`** — documento maestro. Mínimo §4 (los 3 modos), §10.5 (Autopilot fusion).
2. **`docs/pluggable-middle/fases/README.md`** — Quality Charter (no negociable: cero deuda técnica, tests con cada implementación, mypy strict, ruff clean, coverage objetivo >85% en módulo nuevo).

### 1.2 Plan específico de Fase 03

3. **`docs/pluggable-middle/fases/03-AUTOPILOT-FUSION.md`** — el plan completo de Fase 03. Es tu hoja de ruta. Tiene 13 tareas (T3.1 a T3.13) con detalles exactos.

### 1.3 Progress logs de fases previas (para entender qué se construyó)

4. **`docs/pluggable-middle/fases/00-FOUNDATIONS.md`** — §8 "Progress Log" (qué quedó construido en cortex.session)
5. **`docs/pluggable-middle/fases/01-DOCUMENTER-RECONSTRUCTION.md`** — §8 "Progress Log" (qué quedó construido en cortex.documenter)
6. **`docs/pluggable-middle/fases/02-SDDWORK-MIGRATION.md`** — §8 "Progress Log" (cambios a skills/subagents)

### 1.4 Código existente que vas a tocar/leer

Antes de modificar nada, leé estos archivos enteros:

- **`cortex/autopilot/`** completo — todo el módulo a refactorizar. Empezá por:
  - `cortex/autopilot/service.py`
  - `cortex/autopilot/lifecycle.py`
  - `cortex/autopilot/state_store.py` (se va a ELIMINAR — Sessions ya lo hace)
  - `cortex/autopilot/models.py`
  - `cortex/autopilot/mcp_tools.py`
  - `cortex/autopilot/cli.py`
  - `cortex/autopilot/session_builder.py` y `session_writer.py` (también se eliminan — Documenter ya lo hace)
  - `cortex/autopilot/policies/` (carpeta)
  - `cortex/autopilot/budget_profiles.py`
  - `cortex/autopilot/context_budget.py`
  - `cortex/autopilot/detectors/`
  - `cortex/autopilot/hooks/`
- **`cortex/session/service.py`** — para entender qué API exponer/envolver.
- **`cortex/documenter/reconstruction.py`** + `persistence.py` — para entender qué dispara `finish-session`.
- **`cortex/ide/`** completo — patrones de IDE adapters (los hooks de Fase 03 viven acá o en `cortex/session/hooks/`).

### 1.5 Documentación externa permitida (bajo demanda)

- **Claude Code hooks JSON nativos**: https://docs.claude.com/en/docs/agents-and-tools/agent-skills (sección hooks). Usá WebFetch si necesitás validar el formato exacto.
- **Git hooks**: https://git-scm.com/docs/githooks — para el adapter de Cursor (vía git post-commit).
- **Pi Coding Agent**: ver `cortex-pi/` en el repo para entender el task runner integration.

---

## 2. CONTEXTO CRÍTICO QUE NO ESTÁ EN LOS DOCS

Lo siguiente es información que aprendí en sesiones previas y que no
necesariamente está documentada. **Es lo que más te puede salvar de
re-aprender o de cometer errores.**

### 2.1 Stack y convenciones

- **Python 3.13** local, pero el proyecto target es `py311` (ver `pyproject.toml`).
- Imports modernos: `list[X]`, `dict[K,V]`, `X | None`. Nada de `typing.List`.
- **mypy `strict = false`** globalmente, **pero strict en `cortex.documentation.*`** (override en pyproject). Mi código nuevo lo paso con `mypy --strict --follow-imports=silent <archivo>` y debe quedar limpio.
- **ruff config** en `pyproject.toml`: `select = ["E","F","I","UP","B","SIM"]`, line-length 100. Aplicar `ruff check --fix` y `ruff format`.
- **pytest** addopts incluye `--cov=cortex` por default; usá `--no-cov` cuando solo querés ver pass/fail rápido.
- **Pydantic v2**: `ConfigDict(extra="forbid", frozen=True)` para records inmutables. `@field_validator` y `@model_validator(mode="after")`.

### 2.2 Patrones del proyecto que YA seguí (y vos también)

- **Dataclass para input**, **Pydantic para validación**: ver `cortex/documentation/data.py` (dataclasses) vs `cortex/documentation/schemas/` (Pydantic). Repetí ese split.
- **Renderers de prompts**: si tocás `.cortex/subagents/*.md` o `.cortex/skills/*.md`, **tenés que actualizar el `render_*()` correspondiente** en `cortex/setup/cortex_workspace.py`. El test `tests/unit/ide/test_adapters_phase4.py::test_canonical_subagent_files_in_disk_match_renders` compara hashes SHA-256. **Gotcha que me pasó**: el Write tool deja un trailing `"""\n` al final si copio un Python multiline literal — borralo a mano del archivo `.md`.
- **canonical_tools vocabulary**: si agregás una MCP tool nueva, registrala en `cortex/ide/canonical_tools.py` (en el `Literal[...]` Y en `_TOOL_NAME_BY_IDE`). Si no, los IDE adapters tests rompen.
- **Tests con `typer.Exit`**: NO uses `pytest.raises(SystemExit)`. Usá `pytest.raises(typer.Exit)`.

### 2.3 AgentMemory: dos servicios "session"

- `cortex/services/note_service.py::NoteService` — escribe **session notes** (markdown). **Renombrado en Fase 00** desde `session_service.py` (queda alias deprecated).
- `cortex/session/service.py::SessionService` — la primitiva nueva (open/checkpoint/close).
- En `AgentMemory`: `self._note_service` (notes) y `self._session_service` (primitive). **NO confundir**. Mi facade methods en `core.py` ya separan las dos cosas correctamente.

### 2.4 Tests preexistentes que SIEMPRE fallan (no son tu problema)

Estas 4 failures existen desde antes de Fase 00 y persisten. Documentado en cada Progress Log:

- `tests/unit/security/test_paths.py::TestResolveSafe::test_rejects_traversal_via_symlink` — requiere permisos Admin en Windows para crear symlinks.
- `tests/unit/test_mcp_server.py::TestVerifySessionClaims::test_claim_matched_in_diff_is_verified`
- `tests/unit/test_mcp_server.py::TestVerifySessionClaims::test_claim_without_evidence_is_asserted`
- `tests/unit/test_mcp_server.py::TestVerifySessionClaims::test_reports_branch_in_summary`

Esas 3 últimas son por un bug en `cortex/mcp/_subprocess.py:140` (no es mi código). Lo verifiqué en Fase 00 con `git stash` — fallan idénticas en master. **NO LAS ARREGLES.** Out of scope per Quality Charter §9.

**Target del test suite tras Fase 02**: `1811 passed, 6 skipped, 4 failures preexistentes`. Si tras Fase 03 ves más de 4 failures, **algo nuevo se rompió**.

### 2.5 Cosas que ya descubrí y NO tenés que re-descubrir

1. **Las dependencias dev no están instaladas por default**: `pip install pytest-cov ruff mypy hypothesis jinja2` (jinja2 es runtime, no dev, pero falta en el venv local).
2. **`pyproject.toml` addopts** incluye `--cov=cortex --cov-report=term-missing`. Si pasás `--no-cov` te ahorrás ruido.
3. **El alias `cortex.services.session_service`** emite `DeprecationWarning` al importar. Es esperado — los warnings hooks/test capturan esto. NO los suprimas.
4. **`finish-session` necesita AgentMemory completo** (vault + episodic + semantic). El subapp `cortex session ...` es lightweight (solo SessionService). Diseño intencional.
5. **`ContradictionDetector` en `cortex/documenter/contradiction_detector.py`** es un Protocol con `NoOpContradictionDetector` por default. La implementación real requiere AgentMemory loaded; está deferred a fase 04 según el plan.

---

## 3. INSTRUCCIONES ESPECÍFICAS PARA FASE 03

### 3.1 Lo que entrega Fase 03

Al cerrarla:

1. **Autopilot reescrito como capa sobre Sessions** — sus comandos (`cortex autopilot start/checkpoint/finish/status`) son aliases que delegan a `SessionService` + `PolicyEnforcer`.
2. **Modos `observe | assist | autopilot`** preservados como configuración del comportamiento (no entidades paralelas).
3. **Hooks IDE para 3 IDEs**:
   - Claude Code (hooks JSON nativos en settings.json)
   - Cursor (vía git post-commit hook — funciona también para Cline/VSCode)
   - Pi Coding Agent (vía just recipes)
4. **CLI `cortex session hooks install/uninstall/status --ide <name>`**
5. **Tests E2E del modo Observed** validan: con hook instalado, un commit → checkpoint en la session activa.
6. **Eliminación** de `cortex/autopilot/state_store.py`, `session_builder.py`, `session_writer.py`.
7. **NO breaking changes** en la UX del CLI: `cortex autopilot start` etc. siguen funcionando (como alias).

### 3.2 Orden de tareas recomendado

Seguí EXACTAMENTE este orden — está pensado para minimizar refactors:

1. **T3.1 — Auditoría del módulo autopilot**: crear `docs/pluggable-middle/fases/_internal/autopilot-audit.md` (NO es deuda, es working note) con tabla de cada archivo del módulo y su destino en Sessions. **Esto NO es opcional**. Sin auditoría el refactor se vuelve adivinanza.
2. **T3.2 — `cortex/autopilot/policies.py`** consolidado: API de policies (modes, budget, detectors).
3. **T3.3 — Reescribir `service.py`**: AutopilotService delegando a SessionService. Eliminar state_store/session_builder/session_writer.
4. **T3.4 — CLI Autopilot**: aliases que llaman a la nueva AutopilotService.
5. **T3.5 — MCP tools Autopilot**: idéntico, signatures iguales, body nuevo.
6. **T3.6 — Hooks installer system** (`cortex/session/hooks/`): infraestructura genérica + HookAdapter Protocol.
7. **T3.7 — Adapter Claude Code**: usá `WebFetch` para verificar formato de hooks JSON nativos.
8. **T3.8 — Adapter Cursor**: git post-commit. **Decisión: git hooks**, NO Cursor command palette. Razón: independiente de IDE específico, funciona para VSCode/Cline/Roo también.
9. **T3.9 — Adapter Pi**: integración con `just` recipes en `cortex-pi/justfile`.
10. **T3.10 — CLI `cortex session hooks ...`**: commands install/uninstall/list/status.
11. **T3.11 — Tests E2E Observed**: con hook git instalado, commit → checkpoint registrado en la session.
12. **T3.12 — Doctor extensions**: validar hooks + policy config.
13. **T3.13 — Documentación**.

### 3.3 Decisiones que ya están tomadas (NO re-debatas)

- **3 adapters mínimo** (Claude Code, Cursor, Pi). No agregues VSCode-nativo, opencode, Codex, JetBrains. Esos son post-MVP per Fase 03 §10.
- **`cortex autopilot ...` CLI se mantiene** como alias (aunque no haya usuarios reales). UX continuity.
- **Eliminar `state_store.py`**, `session_builder.py`, `session_writer.py`. **Sin nostalgia.** Pero confirmá con `Grep` que no hay imports huérfanos antes de borrar.
- **Hooks NO deben abortar la operación del IDE** si Cortex falla. Patrón: `|| true` en bash scripts, try/except en hooks Python.

### 3.4 Reglas anti-error que aprendí a la fuerza

- **Cada vez que actualices un `.cortex/subagents/*.md` o `.cortex/skills/*.md`**: actualizá el `render_*()` correspondiente en `cortex/setup/cortex_workspace.py`. Corré `pytest tests/unit/ide/test_adapters_phase4.py --no-cov -q` después.
- **Si agregás una MCP tool nueva** (probablemente en hooks): actualizá `cortex/ide/canonical_tools.py` (Literal + dict). Corré `pytest tests/unit/ide/` para validar.
- **NUNCA dejes `"""` literal al final de un archivo `.md`** (es el error de copy-paste más común). El Write tool no lo filtra.
- **NUNCA toques los 4 tests preexistentes que fallan** (§2.4 arriba).
- **Tests con `typer.Exit`** usan `pytest.raises(typer.Exit)`, no `SystemExit`.

---

## 4. CÓMO RETOMAR: PRIMER PROMPT QUE DEBERÍAS EJECUTAR

Cuando abras la nueva sesión, lo primero que tenés que hacer es:

```
1. Leer este archivo entero: docs/pluggable-middle/fases/HANDOFF-TO-NEXT-SESSION.md
2. Leer en orden los archivos de §1 (Required Reading).
3. Verificar estado del repo: git status (debería estar limpio o con working changes en .cortex/, cortex/, tests/, docs/).
4. Verificar que los tests baseline pasan:
   python -m pytest tests/unit/ tests/integration/ tests/e2e/test_byo_flow.py tests/e2e/test_managed_flow.py --no-cov 2>&1 | tail -3
   Expected: 1811 passed, 6 skipped, 4 failures preexistentes.
5. Crear los 13 tasks de Fase 03 vía TaskCreate (sólo si vas a hacer la fase completa; si solo vas a hacer 1-2 tareas, crear sólo esas).
6. Empezar con T3.1 (auditoría — es NO-CODE, pura comprensión del módulo).
```

### Pre-flight checklist

```
[ ] He leído ARQUITECTURA-PLUGGABLE-MIDDLE.md §4 + §10.5
[ ] He leído fases/README.md (Quality Charter)
[ ] He leído fases/03-AUTOPILOT-FUSION.md completo
[ ] He leído los Progress Logs de Fases 00/01/02
[ ] He inspeccionado cortex/autopilot/ con `ls` y `Read`
[ ] El test baseline corre y muestra "1811 passed, 4 failures preexistentes"
[ ] Tengo TaskCreate ready para trackear T3.1-T3.13
```

---

## 5. ARCHIVOS QUE TE PRESERVAN EL CONTEXTO

El estado completo del proyecto vive en estos artefactos. Si te confundís
en algún momento, **vuelve acá**:

| Documento | Para qué |
|---|---|
| `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` | Diseño completo (la "fuente de verdad" del proyecto) |
| `docs/pluggable-middle/arquitectura-visual.html` | Versión visual (gráficos) — útil para refrescar la imagen mental |
| `docs/pluggable-middle/README.md` | Tabla de progreso global |
| `docs/pluggable-middle/fases/README.md` | Quality Charter + protocolos |
| `docs/pluggable-middle/fases/0*.md` | Planes de cada fase |
| `docs/architecture/session-primitive.md` | Referencia técnica de la Session |
| `cortex/session/` | Módulo de la primitiva (Fase 00, 100% coverage) |
| `cortex/documenter/` | Módulo de reconstrucción (Fase 01, 100% coverage) |
| Este archivo | Resumen ejecutivo para retomar |

---

## 6. RESUMEN EN UNA TABLA: QUÉ EXISTE HOY EN EL CÓDIGO

| Capa | Path | Estado | Coverage |
|---|---|---|---|
| Session primitive | `cortex/session/` | Estable, no tocar | 100% |
| Documenter reconstruction | `cortex/documenter/` | Estable, no tocar | 100% |
| MCP tools `cortex_session_*` (5) | `cortex/mcp/server.py` | Estable | ~96% |
| MCP `cortex_finish_session` | `cortex/mcp/server.py` | Estable | con tests |
| CLI `cortex session ...` (6 cmds) | `cortex/cli/session.py` | Estable | tests E2E |
| CLI `cortex finish-session` | `cortex/cli/main.py` | Estable | tests E2E |
| NoteService (notes markdown) | `cortex/services/note_service.py` | Renombrado en Fase 00 | sin regresión |
| SpecService (con verification_hooks) | `cortex/services/spec_service.py` | Extendido en Fase 01 | sin regresión |
| Skills/subagents prompts | `.cortex/skills/`, `.cortex/subagents/` | Reescritos en Fase 02 (checkpoints) | hash test verde |
| Agent guidelines | `cortex/agent_guidelines.md` | Reescrito en Fase 02 | — |
| **Autopilot module** | **`cortex/autopilot/`** | **A REFACTORIZAR en Fase 03** | varía |
| **IDE hooks** | **`cortex/session/hooks/` (no existe)** | **A CREAR en Fase 03** | — |

---

## 7. CIERRE

**El trabajo está limpio.** No hay deuda técnica abierta en los módulos
nuevos. Los Progress Logs de Fases 00/01/02 documentan cada decisión.

**Quality Charter**: cero TODO/FIXME en código nuevo, coverage 100% en
`cortex.session` y `cortex.documenter`, mypy strict limpio, ruff limpio.

**Lo que el usuario espera de vos**:

- **Quality first**, no velocidad: el usuario fue explícito en sesiones
  previas — "lo que cuesta hoy es bueno para después".
- **Sin saltarse tareas**: el plan de Fase 03 tiene 13 tareas por una
  razón. T3.1 (auditoría) es la más crítica y la más fácil de saltar.
- **Sin agregar features fuera del plan**: si surgen ideas, anotalas en
  un Progress Log nuevo, NO las implementes.
- **Sin commitear** salvo que se te pida.
- **Test-driven**: tests con el código, no después.

**Si te trabás:** parar, leer el Progress Log de la fase actual, releer
la arquitectura, NUNCA improvisar. Si seguís trabado, marcá la tarea como
⚠️ Bloqueada en `docs/pluggable-middle/README.md` y pedile al usuario
revisión arquitectónica.

**Suerte.** El proyecto está en muy buen estado. Solo seguí el plan.
