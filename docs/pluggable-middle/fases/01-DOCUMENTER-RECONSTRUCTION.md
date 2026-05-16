# Fase 01 — Documenter Reconstruction Mode (BYO)

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 00 · **Bloquea:** Fases 02, 03, 04 · **Esfuerzo estimado:** ~2 semanas

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 01 |
| Nombre | Documenter Reconstruction Mode (BYO) |
| Versión del plan | 1.0 |
| Dependencias | Fase 00 cerrada (Session primitive disponible) |
| Output principal | Modo BYO end-to-end funcional. `cortex finish-session` operativo. Verification hooks ejecutables. |
| Breaking changes para flujo actual | Sí controlados: el spec ahora requiere `verification_hooks`. Specs viejos siguen leyéndose pero generan warning. |

---

## 1. Required Reading (antes de tocar código)

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter, protocolo.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) — al menos:
  - §4 (los 3 modos),
  - §6 (flujo end-to-end),
  - §7 (Documenter reborn),
  - §8 (Verification hooks).
- [`00-FOUNDATIONS.md`](00-FOUNDATIONS.md) §7 (Handoff to next phase) — para saber qué quedó disponible.

### 1.2 Código existente que vas a tocar o necesitas conocer

Leé enteros:

- `C:\Cortex\cortex\session\` — todo el módulo de la Fase 00. Si no lo recordás, releelo.
- `C:\Cortex\cortex\handoff.py` — schema `AgentHandoff`. Lo seguimos usando como contrato interno entre reconstrucción y persistencia.
- `C:\Cortex\.cortex\subagents\cortex-documenter.md` — el subagent actual que vamos a actualizar.
- `C:\Cortex\.cortex\skills\cortex-sync.md` — el skill actual que vamos a actualizar.
- `C:\Cortex\cortex\services\note_service.py` (renombrado en Fase 00, antes era `session_service.py`) — donde vive `cortex_save_session` actual.
- `C:\Cortex\cortex\services\spec_service.py` — vamos a agregar validación de verification_hooks.
- `C:\Cortex\cortex\documentation\` — todos los writers canónicos, schemas, templates. Listar con `Glob`.
- `C:\Cortex\cortex\documentation\templates\spec.md.j2` — template del spec, vamos a extenderlo.
- `C:\Cortex\cortex\documentation\templates\session.md.j2` — template del session note (no se toca, pero entendelo).
- `C:\Cortex\cortex\doc_verifier.py` o `cortex/services/` (buscar con `Grep cortex_verify_session_claims`) — el verificador existente que vamos a reutilizar.
- `C:\Cortex\cortex\mcp\server.py` — para agregar la tool `cortex_finish_session`.
- `C:\Cortex\cortex\cli\main.py` — para registrar `cortex finish-session`.

Leé referencias bajo demanda:

- `C:\Cortex\cortex\autopilot\session_builder.py` y `session_writer.py` — patrones de construcción de session notes. NO copiar literal; aprender el patrón.
- Tests existentes de documenter / spec / handoff: `tests/unit/`, `tests/integration/`, `tests/e2e/`.

### 1.3 Documentación externa (consultar bajo demanda)

- Subprocess timeouts y captura de output en Python: https://docs.python.org/3/library/subprocess.html#subprocess.run
- Hypothesis para tests basados en propiedades: https://hypothesis.readthedocs.io/
- Pydantic v2 validators: https://docs.pydantic.dev/latest/concepts/validators/

---

## 2. Goal

Al finalizar esta fase:

1. **El spec ahora requiere `verification_hooks`.** Schema actualizado, template actualizado, validación dura.
2. **Existe un runner de verification hooks** (`cortex/session/verification.py`) que ejecuta los comandos del spec con timeout, captura output y retorna un `VerificationHookResult` por hook.
3. **Existe el módulo de reconstrucción** (`cortex/documenter/reconstruction.py`) que implementa el algoritmo de §7.2 de la arquitectura.
4. **Existe el comando `cortex finish-session`** (CLI + tool MCP `cortex_finish_session`) que dispara la reconstrucción y persiste el session note.
5. **El subagent `cortex-documenter`** sabe operar en modo reconstrucción (input: session_id) además del modo legacy (input: handoff YAML).
6. **El skill `cortex-sync`** ofrece 3 caminos al usuario después de crear el spec.
7. **Tests E2E** validan el escenario BYO completo: usuario crea spec → modifica archivos a mano → corre finish-session → session note correcto persistido.
8. **El flujo Cortex tripartito anterior sigue funcionando.** Los tests E2E previos siguen verdes.

**Lo que NO se hace en esta fase:**

- ❌ NO se reescribe SDDwork (es Fase 02).
- ❌ NO se eliminan los handoffs YAML inline (siguen funcionando como legacy).
- ❌ NO se implementa el modo interactivo del documenter (es Fase 04).
- ❌ NO se tocan los hooks IDE (es Fase 03).

---

## 3. Decisiones de diseño clave de esta fase

### 3.1 Verification hooks: obligatorios pero con escape hatch

Confirmado en §12 de la arquitectura: **obligatorios.** Pero hay dos categorías de spec donde "hooks ejecutables" no aplican naturalmente:

- **Specs tipo `research`** (investigar, escribir docs): el hook puede ser una checklist manual (`test -f docs/output.md`).
- **Specs tipo `non-code`** (config-only, asset-only): el hook puede ser un git-grep que verifique la existencia del cambio.

**Decisión:** un solo `verification_hooks` mandatory, pero validamos solo que tenga **al menos uno**, sin restringir el tipo. Documentar los patrones en el skill `cortex-sync`.

### 3.2 Compatibilidad con specs viejos (sin verification_hooks)

Decisión: **soft warning, no hard error.**

- Si el documenter recibe un spec sin `verification_hooks`, loguea warning y procede SIN ejecutar hooks.
- Esto evita romper specs ya escritos durante desarrollo (¡aunque no haya usuarios reales todavía, el repo tiene specs de ejemplo en `examples/`).
- En Fase 04 se promueve a hard error (después de validar que todos los specs nuevos sí los tienen).

### 3.3 Dos modos de invocación del documenter

A partir de esta fase, el documenter acepta **dos contratos de entrada**:

| Modo | Input | Cuándo se usa |
|---|---|---|
| **Reconstruction** (nuevo) | `session_id` | Disparado por `cortex finish-session` |
| **Legacy YAML** (existente) | `handoff YAML inline` | Disparado por SDDwork emitiendo YAML al final |

El subagent `.cortex/subagents/cortex-documenter.md` detecta cuál usar según el input.

### 3.4 Algoritmo de reconstrucción: 8 pasos (de la arquitectura §7.2)

Implementación literal de la arquitectura. **No reinventes.** Si en la implementación encontrás que un paso no aplica, anotalo en el Progress Log y consultá.

### 3.5 ¿Quién corre los verification hooks?

Decisión: **el módulo `cortex/session/verification.py`** (no el documenter directo, no el sync). El documenter lo invoca en el paso 3 del algoritmo. El sync NO los corre (solo los declara).

Razón: separación de responsabilidades. `verification` es una utilidad pura sin dependencias del documenter; el documenter la consume.

---

## 4. Task Breakdown

### T1.1 — Schema de verification hooks en spec

**Objetivo:** que el spec model represente verification_hooks.

**Archivos a modificar:**
- `cortex/documentation/data.py` (o donde viva `SpecData` — buscar con `Grep "class SpecData"`).
- `cortex/services/spec_service.py` — validación.
- `cortex/documentation/templates/spec.md.j2` — agregar sección.
- `cortex/documentation/schemas/spec.json` (si existe — chequear) — agregar campo.

**Schema esperado:**

```python
class VerificationHook(BaseModel):
    name: str  # human-readable, no vacío
    command: str  # comando a ejecutar
    required: bool = True
    success_criteria: str = "exit code 0"  # texto descriptivo, no se evalúa programáticamente; solo doc
    timeout_seconds: int = 300  # 5 min default, validar [1, 1800]

    model_config = ConfigDict(extra="forbid")

class SpecData(BaseModel):
    # ... campos existentes ...
    verification_hooks: list[VerificationHook] = Field(default_factory=list, min_length=1)
    # min_length=1 — siempre al menos uno
```

**Validación en SpecService.create:**
- Si el caller no provee `verification_hooks`, lanzar error claro.
- Si provee lista vacía, lanzar error.
- Validar nombres únicos dentro de la lista (no duplicados).

**Template `spec.md.j2`:**

Agregar al final del template:

```jinja2
## Verification Hooks

Los siguientes comandos prueban objetivamente que el trabajo está hecho:

{% for hook in verification_hooks %}
### {{ hook.name }} {% if hook.required %}*(required)*{% endif %}

```bash
{{ hook.command }}
```

Success criteria: {{ hook.success_criteria }}
Timeout: {{ hook.timeout_seconds }}s
{% endfor %}
```

**Tests obligatorios:**
- `test_spec_requires_at_least_one_hook`.
- `test_spec_rejects_duplicate_hook_names`.
- `test_spec_template_renders_hooks`.
- `test_existing_specs_without_hooks_load_with_warning` — backward compat soft.

**Definition of Done T1.1:**
- Modelos actualizados, tests verdes, template renderiza.
- `cortex create-spec` desde CLI sin `--verification-hook` falla con error explicativo (porque el flag es nuevo y obligatorio — ver T1.2).

---

### T1.2 — CLI/MCP de `create-spec` admite verification_hooks

**Objetivo:** que el usuario / agente pueda pasar hooks al crear un spec.

**Archivos a modificar:**
- `cortex/cli/main.py` — flag `--verification-hook` repetible (multi-value).
- `cortex/mcp/server.py` — tool `cortex_create_spec` acepta `verification_hooks: list[dict]`.

**CLI:**

```bash
cortex create-spec \
  --title "Auth JWT refresh" \
  --goal "Implementar refresh tokens" \
  --verification-hook 'name=tests;command=pytest tests/auth/' \
  --verification-hook 'name=lint;command=ruff check src/auth.py;required=false'
```

Parser: `key=value;key=value`. Sencillo, sin sobre-ingeniería.

**MCP:**

Input schema actualizado del tool `cortex_create_spec`:
```json
"verification_hooks": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "command": {"type": "string"},
      "required": {"type": "boolean"},
      "success_criteria": {"type": "string"},
      "timeout_seconds": {"type": "integer"}
    },
    "required": ["name", "command"]
  },
  "minItems": 1
}
```

**Tests:**
- CLI parse correctly.
- MCP tool validates schema.
- E2E: crear spec desde MCP retorna spec con hooks en el frontmatter.

---

### T1.3 — Runner de verification hooks (`cortex/session/verification.py`)

**Objetivo:** ejecutar hooks de manera segura y capturar resultados.

**Archivos a crear:**
- `cortex/session/verification.py`
- `tests/unit/session/test_verification.py`

**API esperada:**

```python
class VerificationRunner:
    def __init__(self, repo_root: Path, max_output_bytes: int = 10_000) -> None: ...

    def run_hook(self, hook: VerificationHook) -> VerificationHookResult:
        """
        Executes hook.command with subprocess in repo_root.
        - Timeout via subprocess.run(timeout=hook.timeout_seconds)
        - Captures stdout+stderr merged
        - Truncates output to max_output_bytes (last N bytes if exceeded)
        - Returns VerificationHookResult always (never raises for hook failure;
          only raises for infrastructure failure like 'command not found in shell')
        """

    def run_all(self, hooks: list[VerificationHook]) -> list[VerificationHookResult]:
        """Runs sequentially, returns all results."""
```

**Detalles críticos:**

- **Shell:** ejecutar con `shell=True` para soportar pipes, env vars, etc. Documentar el riesgo de inyección (el comando viene del spec; si el spec es maligno, el sistema ya está comprometido — out of scope).
- **Encoding:** usar `text=True, encoding='utf-8', errors='replace'`.
- **Working directory:** siempre `repo_root`.
- **Timeout:** si timeout vence, capturar `subprocess.TimeoutExpired`, retornar resultado con `passed=False, exit_code=-1`, mensaje claro en output.
- **Truncation:** si output > `max_output_bytes`, mantener los últimos N bytes (la cola es lo informativo de un fail), prefijar con `[... truncated N bytes ...]`.

**Tests obligatorios:**
- `test_run_hook_success` — `echo hello` → passed=True.
- `test_run_hook_failure` — `exit 1` → passed=False.
- `test_run_hook_timeout` — `sleep 10` con timeout=1 → passed=False, exit_code=-1.
- `test_run_hook_truncates_long_output` — `seq 1 100000` → output truncated.
- `test_run_all_runs_sequentially` — orden preservado.
- `test_run_hook_captures_stderr` — comando que escribe a stderr, output lo incluye.
- `test_unicode_in_output` — output con caracteres no-ASCII no rompe.
- `test_run_hook_uses_repo_root_cwd` — verificar con pwd.

**Definition of Done T1.3:** Runner funcional, robusto, tests cubren happy + edge + error.

---

### T1.4 — Módulo de reconstrucción (`cortex/documenter/reconstruction.py`)

**Objetivo:** implementar el algoritmo de 8 pasos de la arquitectura §7.2.

**Archivos a crear:**
- `cortex/documenter/__init__.py` (si no existe ya — verificar; si existe `cortex/documenter` evaluar si subdirectorio o reusar)
- `cortex/documenter/reconstruction.py`
- `tests/unit/documenter/test_reconstruction.py`
- `tests/integration/documenter/test_reconstruction_integration.py`

**Pre-check:** verificar con `Glob` si `cortex/documenter/` ya existe. Si existe, integrar acá. Si no, crearlo limpio.

**API esperada:**

```python
@dataclass(frozen=True)
class ReconstructionInput:
    session_id: str

@dataclass(frozen=True)
class ReconstructionOutput:
    handoff: AgentHandoff  # schema de cortex.handoff
    diff_text: str
    files_touched: list[Path]
    in_scope_files: list[Path]
    out_of_scope_files: list[Path]
    unimplemented_files: list[Path]  # estaban en spec pero no se tocaron
    verification_results: list[VerificationHookResult]
    contradictions: list[ContradictionFinding]
    suggested_status: SessionStatus  # CLOSED | HANDOFF | ABANDONED
    suggested_adrs: list[ADRSuggestion]
    raw_checkpoints: list[Checkpoint]

class Reconstructor:
    def __init__(
        self,
        session_service: SessionService,
        spec_service: SpecService,  # para cargar el spec
        verification_runner: VerificationRunner,
        memory_search: MemorySearcher,  # para detectar contradicciones (usa cortex.retrieval)
    ) -> None: ...

    def reconstruct(self, input: ReconstructionInput) -> ReconstructionOutput:
        """Implements §7.2 algorithm — 8 steps."""
```

**Implementación de los 8 pasos (referencia: §7.2 de arquitectura):**

```
STEP 1: Cargar contexto
  - session = session_service.get(input.session_id)
  - spec = spec_service.load(session.spec_path)  # leer YAML frontmatter
  - checkpoints = session.checkpoints

STEP 2: Computar diff observable
  - diff_text = git_subprocess.diff(session.start_commit, "HEAD", repo_root)
  - files_touched = parse_diff_files(diff_text)
  - end_commit = git_subprocess.head_sha(repo_root)

STEP 3: Ejecutar verification hooks
  - if spec.verification_hooks:
      verification_results = verification_runner.run_all(spec.verification_hooks)
    else:
      log.warning("Spec has no verification_hooks (legacy); skipping verification.")
      verification_results = []

STEP 4: Cross-check contra spec
  - in_scope_files = files_touched ∩ spec.files_in_scope
  - out_of_scope_files = files_touched - spec.files_in_scope
  - unimplemented_files = spec.files_in_scope - files_touched

STEP 5: Detectar contradicciones (memoria)
  - contradictions = memory_search.find_contradictions(spec.summary, diff_text)
  - (implementación: usa cortex_search filtrando por embedding similitud + heurísticas)

STEP 6: Construir AgentHandoff sintético
  - verified_claims = [...]  # archivos modificados, tests pasados
  - unverified_claims = [...]  # acceptance_criteria no probados por hooks
  - artifacts_produced = [ArtifactProduced(path=f, action=..., lines_changed=...) for f in files_touched]
  - context_for_next = [cp.note for cp in checkpoints if cp.note] + scope_drift_notes
  - suggested_adr = apply_3of3_criteria(checkpoints, diff_text)

STEP 7: Decidir status sugerido
  - all_required_hooks_passed = all(r.passed for r in verification_results if r.required)
  - if all_required_hooks_passed and not unimplemented_files:
      suggested_status = CLOSED
  - elif unimplemented_files or any unrequired hook failure:
      suggested_status = HANDOFF
  - else:
      suggested_status = HANDOFF (más conservador)

STEP 8: Retornar el ReconstructionOutput
```

**Sub-módulos auxiliares (dentro de `cortex/documenter/`):**

- `git_introspection.py`: wrapper subprocess para git (diff, head_sha). Si ya hay uno en `cortex/session/git.py` (de Fase 00 T0.4), reusarlo, no duplicar.
- `diff_parser.py`: parsear `git diff --name-only` y extraer paths con action (created/modified/deleted/renamed). Tests aparte.
- `adr_evaluator.py`: aplicar criterios 3/3 de la arquitectura §12 (de doc cortex-documenter.md). Tests aparte.
- `contradiction_detector.py`: lógica de búsqueda en memoria. **No reinventar**: usa `cortex.retrieval` que ya existe.

**Tests obligatorios:**
- Test por cada step en aislamiento (mockear lo que no se prueba).
- Tests E2E del algoritmo completo con un repo de prueba (fixture: repo temp con un commit, una spec, un diff).
- Edge cases:
  - Session sin checkpoints (BYO puro).
  - Session con muchos checkpoints (Managed).
  - Spec con 0 acceptance_criteria.
  - Diff vacío (no se desarrolló nada) → status=HANDOFF con razón.
  - Verification hook que falla.
  - Verification hook que timeout.
  - Archivos fuera de scope.
  - Archivos en scope no tocados.

**Definition of Done T1.4:** algoritmo invocable, tests > 90% coverage, edge cases cubiertos.

---

### T1.5 — Persistencia + finish flow (`cortex/documenter/persistence.py`)

**Objetivo:** dado un `ReconstructionOutput`, persistir el session note + ADRs + actualizar Session.

**Archivos a crear:**
- `cortex/documenter/persistence.py`
- `tests/unit/documenter/test_persistence.py`

**API esperada:**

```python
@dataclass(frozen=True)
class FinishSessionResult:
    session_note_path: Path
    adrs_created: list[Path]
    final_status: SessionStatus
    summary: str  # texto resumen para CLI output

class DocumenterPersister:
    def __init__(
        self,
        note_service: NoteService,  # renombrado de SessionService viejo
        adr_writer: ADRWriter,  # del módulo cortex.documentation.writers
        session_service: SessionService,
        context_md_updater: ContextMdUpdater,  # si existe; sino, dejar como no-op por ahora
    ) -> None: ...

    def finalize(
        self,
        reconstruction: ReconstructionOutput,
        user_overrides: FinishOverrides | None = None,  # para Fase 04 interactive
    ) -> FinishSessionResult:
        """
        - Escribe el session note vía note_service (template existente)
        - Si reconstruction.suggested_adrs no vacío y modo auto, los crea
        - Actualiza CONTEXT.md si aplica
        - Cierra la session vía session_service.close
        - Retorna paths
        """
```

**Detalles:**

- Para escribir el session note, usar el `NoteService` (renombrado en Fase 00). NO duplicar lógica de escritura.
- Para ADRs, usar el writer canónico existente (`cortex/documentation/writers.py` — `write_adr_note`).
- `FinishOverrides` se define como dataclass vacío en esta fase, lo poblamos en Fase 04 (`approved_adrs`, `edited_note_body`, etc.).
- En esta fase, el modo es siempre AUTO (sin pregunta al usuario).

**Tests obligatorios:**
- `test_finalize_persists_session_note`.
- `test_finalize_creates_adrs_when_suggested`.
- `test_finalize_closes_session_with_correct_status`.
- `test_finalize_clears_active_session_pointer`.
- `test_finalize_idempotent_for_closed_session` — llamar dos veces no rompe.

---

### T1.6 — CLI `cortex finish-session` + alias `cortex session close`

**Objetivo:** comando único para disparar todo el flujo de cierre.

**Archivos a modificar:**
- `cortex/cli/main.py` — top-level command `finish-session`.
- `cortex/cli/session.py` — agregar `close` subcommand (alias).

**Comportamiento:**

```bash
cortex finish-session [SESSION_ID]
  # SESSION_ID opcional, default: active session
  # Flags:
  #   --handoff               # fuerza status=HANDOFF
  #   --abandon               # fuerza status=ABANDONED
  #   --reason TEXT           # razón si --handoff o --abandon
  #   --json                  # output machine-readable
```

**Flujo del comando:**

1. Resolver session_id (arg o active).
2. Verificar status=OPEN (sino, error).
3. Instanciar Reconstructor + Persister.
4. Ejecutar reconstruction.
5. Pasar a Persister.finalize.
6. Imprimir resumen (paths, ADRs creados, status).

**Output ejemplo (texto):**

```
🔄 Reconstruyendo sesión 2026-05-16_auth-jwt-refresh
   Spec: vault/specs/2026-05-16_auth-jwt-refresh.md
   Diff: 4 archivos, +127 -45 líneas
   Verification:
     ✓ Tests unitarios (3.2s)
     ✓ Type check (0.8s)
     ✓ Lint (0.3s)
   Contradicciones: 0
   Scope drift: 0 archivos
   ADRs sugeridos: 1 (creado)
   Status: ✅ CLOSED

📝 Session note: vault/sessions/2026-05-16_auth-jwt-refresh.md
📋 ADR: vault/adrs/2026-05-16_jwt-ttl-hardcoded.md
🗂  Session cerrada
```

**Tests:**
- `test_finish_session_default_uses_active`.
- `test_finish_session_explicit_id`.
- `test_finish_session_no_active_no_arg_errors`.
- `test_finish_session_handoff_flag`.
- `test_finish_session_json_output`.
- `test_finish_session_already_closed_errors`.

---

### T1.7 — MCP tool `cortex_finish_session`

**Objetivo:** exposición MCP del flow de cierre.

**Archivos a modificar:**
- `cortex/mcp/server.py`

**Tool:**

```
cortex_finish_session(
    session_id: str | None = None,  # default: active
    intent: str = "auto",  # "auto" | "handoff" | "abandon"
    reason: str | None = None,
) -> {
    "session_note_path": str,
    "adrs_created": [str],
    "final_status": str,
    "summary_text": str,
}
```

**Razón de exponerlo en MCP:** el subagent `cortex-documenter` lo va a llamar desde un IDE (Claude Code, Cursor, etc.) en modo reconstrucción.

**Tests:**
- Invocación válida.
- Invocación con session_id inválido.
- Schema de output estable.

---

### T1.8 — Actualizar subagent `cortex-documenter.md`

**Objetivo:** que el documenter sepa operar en dos modos.

**Archivos a modificar:**
- `C:\Cortex\.cortex\subagents\cortex-documenter.md`

**Cambios concretos:**

1. **Nuevo section "Modos de operación"** al principio:

```markdown
## Modos de operación

Cortex Documenter puede ser invocado en dos modos:

### Modo Reconstruction (default desde Fase 01)
- Input: `session_id` (la sesión activa o explícita)
- Activado por: `cortex finish-session` o `cortex_finish_session` MCP tool
- Flow: invoca `cortex_finish_session(session_id)`. La reconstrucción + verificación + persistencia ocurren en el backend; vos confirmás y comunicás al usuario.

### Modo Legacy YAML (compatibilidad)
- Input: bloque YAML `AgentHandoff` inline (emitido por `cortex-SDDwork` o similar)
- Flow: validás el YAML con `cortex_validate_handoff`, ejecutás el verification gate tradicional, llamás a `cortex_save_session`.
- **Se mantiene por compatibilidad hasta Fase 02.**
```

2. **Mantener verification gate, ADR criteria, CONTEXT.md maintenance** existentes — siguen aplicando.

3. **Output contract** (final message):
   - En modo reconstruction: confirmación del path del session note + ADRs, sin emitir YAML AgentHandoff (el flow ya cerró la sesión).
   - En modo legacy: emitir YAML como hoy.

**Reglas de operación:**

Agregar al subagent las reglas:

```markdown
## Detección de modo

Si recibís un `session_id` en el contexto:
  → Modo Reconstruction
  → Llamá a `cortex_finish_session(session_id=<id>)`
  → El resultado contiene todo lo que necesitás.

Si recibís un bloque YAML `AgentHandoff`:
  → Modo Legacy
  → Procedé como hasta ahora (validate, verify, save_session)

Si recibís ambos o ninguno:
  → Error explícito. Pedí clarificación al usuario.
```

**Tests:** este archivo no se testea programáticamente, pero hay un test E2E en T1.10 que valida el flow completo desde el agente.

---

### T1.9 — Actualizar skill `cortex-sync.md`

**Objetivo:** que sync (a) requiera verification_hooks y (b) ofrezca 3 caminos al usuario.

**Archivos a modificar:**
- `C:\Cortex\.cortex\skills\cortex-sync.md`

**Cambios:**

1. **Sección nueva "Verification Hooks (obligatorios)":**

```markdown
## Verification Hooks (OBLIGATORIO)

Toda spec debe declarar al menos un `verification_hook`. Son comandos
ejecutables que prueban objetivamente que el trabajo está hecho.

### Patrones por tipo de tarea

| Tipo de tarea | Hook típico |
|---|---|
| Code change | `pytest tests/<modulo>/` |
| Type-checked refactor | `mypy --strict <archivos>` |
| Config-only | `python -c "import json; json.load(open('config.json'))"` |
| Docs / research | `test -f docs/<output>.md` |
| Asset / styling | `test -f <archivo> && grep <pattern> <archivo>` |

### Reglas

1. Mínimo UN hook.
2. Cada hook tiene `name`, `command`, opcionalmente `required` (default true), `timeout_seconds` (default 300).
3. Si un hook se marca `required=false`, su falla NO bloquea el cierre como CLOSED.
```

2. **Sección "Mensaje final" actualizada:**

```markdown
## Contrato de Salida (mensaje al usuario)

Después del YAML AgentHandoff, decí:

> ✅ **Spec técnica lista** (vault/specs/<file>.md)
>
> Verification hooks: <N> declarados
>
> ¿Cómo querés desarrollar?
>
> 1. **Managed** (recomendado para empezar): cambiá al perfil `cortex-SDDwork`.
> 2. **Observed**: usá tu agente/skills preferidos (Cortex te observará el resultado).
> 3. **BYO**: implementá manualmente o con cualquier herramienta.
>
> Cuando termines: `cortex finish-session`
```

3. **Mantener** las reglas existentes (mandatory `cortex_sync_ticket`, CONTEXT.md, etc.).

---

### T1.10 — Tests E2E del modo BYO

**Objetivo:** validar el flow completo BYO.

**Archivos a crear:**
- `tests/e2e/test_byo_flow.py`

**Escenarios:**

```python
def test_byo_flow_simple_code_change(tmp_repo_with_cortex):
    """
    Setup: repo con Cortex inicializado, archivo `src/foo.py` con función simple.
    Flow:
      1. cortex_create_spec con verification_hooks
      2. Modificar src/foo.py manualmente (sin SDDwork)
      3. Commit
      4. cortex_finish_session
    Assert:
      - Session note creado en vault/sessions/
      - Session cerrada con status=CLOSED
      - Mode inferido = BYO
      - Verification hooks ejecutados y pasaron
      - Files in scope correctos
    """

def test_byo_flow_failing_verification(tmp_repo_with_cortex):
    """
    Mismo setup pero con hook que falla → status=HANDOFF.
    Session note debe contener `status: handoff`, blockers, next-session-needs.
    """

def test_byo_flow_scope_drift(tmp_repo_with_cortex):
    """
    Setup: spec con files_in_scope=[src/foo.py].
    Acción: modificar src/foo.py Y src/bar.py.
    Assert: session note documenta `out_of_scope: [src/bar.py]`.
    """

def test_byo_flow_no_changes(tmp_repo_with_cortex):
    """
    Setup: spec creada, nada desarrollado.
    Acción: cortex finish-session.
    Assert: status=HANDOFF, unimplemented=todos los files_in_scope.
    """
```

Si los fixtures no existen aún (`tmp_repo_with_cortex`), créalos en `tests/e2e/conftest.py`. Patrón: usar `pytest.tmpdir`, copiar templates de `cortex/setup/`, init git, crear commit inicial.

**Definition of Done T1.10:** todos los escenarios pasan; el flow BYO está demostrado end-to-end.

---

### T1.11 — Documentación pública

**Archivos a modificar:**
- `C:\Cortex\README.md` — sección "Sessions" actualizada con `finish-session`; sección "Verification Hooks" nueva en parte de specs.
- `C:\Cortex\docs\architecture\session-primitive.md` (de Fase 00) — agregar sección "Lifecycle: Open → Develop → Close" con ejemplo del BYO flow.
- `C:\Cortex\docs\pluggable-middle\README.md` — marcar Fase 01 como ✅ Completa en la tabla.

---

## 5. Cross-cutting concerns

### 5.1 Backward compatibility en esta fase

- Specs viejos sin `verification_hooks`: **soft warning**, no se rechazan.
- El flujo viejo (sync → SDDwork → documenter via YAML) **debe seguir funcionando**. Los tests E2E previos no deben romperse.
- Tests previos que asuman ausencia de verification_hooks: actualizarlos para incluir hooks (no skipearlos).

### 5.2 Performance

- `cortex finish-session` puede tardar hasta `sum(timeout_seconds_de_hooks) + overhead`. Es aceptable (es disparado manualmente).
- Reconstrucción puro (sin hooks): debería ser < 2 segundos para repos medianos.

### 5.3 Logging

- En reconstrucción, loguear a INFO: session loaded, diff computed, hooks running, status decided.
- A WARNING: contradicciones detectadas, scope drift.
- A ERROR: si algo aborta la reconstrucción.

### 5.4 Errores legibles al usuario

Cuando `cortex finish-session` falla, el mensaje debe ser actionable:

```
✗ Cannot finish session: No active session.
  Sugerencia: cortex session list --status=open
```

NO mostrar traceback al usuario por defecto. `--debug` activa traceback.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests
pytest tests/unit/session/test_verification.py -v
pytest tests/unit/documenter/ -v
pytest tests/integration/documenter/ -v
pytest tests/e2e/test_byo_flow.py -v
# expected: all green

# 2. Type checking
mypy --strict cortex/session/verification.py cortex/documenter/
# expected: clean

# 3. Lint
ruff check cortex/documenter/ cortex/session/verification.py tests/unit/documenter/ tests/e2e/test_byo_flow.py
ruff format --check cortex/documenter/ cortex/session/verification.py tests/unit/documenter/ tests/e2e/test_byo_flow.py
# expected: clean

# 4. Coverage de nuevo código
pytest --cov=cortex.documenter --cov=cortex.session.verification tests/
# expected: > 85%

# 5. El flujo viejo sigue funcionando
pytest tests/e2e/ -v
# expected: all green (incluyendo tests previos no-BYO)

# 6. Smoke E2E manual: crear spec + finish-session
# (en repo temporal o sandbox)
cortex create-spec --title "smoke test byo" \
  --goal "validate finish-session" \
  --files-in-scope "smoke.txt" \
  --acceptance-criteria "smoke.txt exists with content" \
  --verification-hook 'name=existence;command=test -f smoke.txt'
echo "test content" > smoke.txt
git add smoke.txt && git commit -m "smoke"
cortex finish-session
# expected: status=CLOSED, session note creado, verification pasó
```

---

## 7. Handoff to next phase

Al cerrar Fase 01:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Schema `VerificationHook` en spec | `cortex/documentation/data.py` |
| Spec template actualizado | `cortex/documentation/templates/spec.md.j2` |
| Verification runner | `cortex/session/verification.py` |
| Reconstruction module | `cortex/documenter/reconstruction.py` |
| Persister module | `cortex/documenter/persistence.py` |
| CLI `cortex finish-session` | `cortex/cli/main.py`, `cortex/cli/session.py` |
| MCP tool `cortex_finish_session` | `cortex/mcp/server.py` |
| Subagent actualizado | `.cortex/subagents/cortex-documenter.md` |
| Skill actualizado | `.cortex/skills/cortex-sync.md` |
| E2E tests BYO | `tests/e2e/test_byo_flow.py` |

### Lo que la Fase 02 puede asumir como dado

1. El modo BYO está demostrado y testeado.
2. El documenter sabe operar desde un `session_id` sin necesidad de YAML inline.
3. `cortex finish-session` cierra Sessions correctamente.
4. Los verification hooks son ejecutables y bien testeados.
5. El skill `cortex-sync` ofrece 3 caminos al usuario.

### Lo que NO se entrega

- SDDwork sigue emitiendo YAML inline (Fase 02).
- Subagents `cortex-code-explorer` y `cortex-code-implementer` siguen como están.
- No hay modo interactivo del documenter (Fase 04).
- No hay hooks IDE (Fase 03).

---

## 8. Progress Log

- [ ] T1.1 — Schema de verification hooks en spec
- [ ] T1.2 — CLI/MCP de create-spec admite verification_hooks
- [ ] T1.3 — Runner de verification hooks
- [ ] T1.4 — Módulo de reconstrucción (algoritmo 8 pasos)
- [ ] T1.5 — Persister + finish flow
- [ ] T1.6 — CLI `cortex finish-session`
- [ ] T1.7 — MCP tool `cortex_finish_session`
- [ ] T1.8 — Actualizar subagent `cortex-documenter.md`
- [ ] T1.9 — Actualizar skill `cortex-sync.md`
- [ ] T1.10 — Tests E2E del modo BYO
- [ ] T1.11 — Documentación pública
- [ ] Completion Verification Commands — TODOS pasaron
- [ ] Tabla de progreso en `../README.md` actualizada con ✅
- [ ] Commit final hecho

**Notas durante la ejecución:**

> Reservado para anotaciones del agente ejecutor.

---

## 9. Notas para el agente ejecutor

- **Esta fase es la más crítica del proyecto.** Es donde el modo BYO empieza a funcionar. Calidad acá es no-negociable.
- **El algoritmo de reconstrucción es el corazón.** Si dudás de un paso, releé §7.2 de la arquitectura. Si sigue ambiguo, parar y consultar.
- **Tests E2E son la prueba final.** Si T1.10 no pasa, la fase no está cerrada, sin importar cuántas tareas anteriores estén verdes.
- **No optimices prematuramente.** El algoritmo es secuencial y claro. Optimizá solo si se demuestra que es lento (con datos reales).
- **Cuidado con la verification hooks ejecución:** son comandos arbitrarios del spec. Asumir confianza en el spec (es del usuario), pero loguear claramente cada comando antes de ejecutar.
