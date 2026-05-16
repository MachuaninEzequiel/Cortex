# Fase 00 — Foundations (Session Primitive)

> **Estado:** ⏸ Pendiente · **Bloquea:** Fases 01, 02, 03, 04 · **Esfuerzo estimado:** ~1 semana

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 00 |
| Nombre | Foundations — Session Primitive |
| Versión del plan | 1.0 |
| Dependencias | Ninguna (es la fase inicial) |
| Output principal | Módulo `cortex.session`, MCP tools `cortex_session_*`, CLI `cortex session ...` |
| Breaking changes para flujo actual | **Cero.** Esta fase es puramente aditiva. |

---

## 1. Required Reading (antes de tocar código)

Leé en este orden. **No saltes ningún archivo.**

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter, protocolo, dependencias.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) — al menos §5 (Session primitiva), §9 (CLI), §11 (Roadmap Fase 0).

### 1.2 Código existente que vas a tocar o necesitas conocer

Leé enteros:

- `C:\Cortex\cortex\core.py` — fachada principal, inyección de servicios.
- `C:\Cortex\cortex\workspace\layout.py` — **crítico:** todo path nuevo debe resolverse acá.
- `C:\Cortex\cortex\services\spec_service.py` — vas a integrar `session_open` acá al final.
- `C:\Cortex\cortex\mcp\server.py` — vas a agregar 5 tools nuevas.
- `C:\Cortex\cortex\cli\main.py` — vas a registrar un Typer subapp nuevo.
- `C:\Cortex\cortex\doctor.py` — vas a agregar una sección de validación.
- `C:\Cortex\cortex\handoff.py` — modelo Pydantic existente que sirve de referencia de estilo. NO lo modifiques en esta fase.

Leé referencias (no es necesario memorizar):

- `C:\Cortex\cortex\autopilot\models.py` — vas a referenciarlo en Fase 03; familiarizate con cómo serializan sesiones hoy.
- `C:\Cortex\cortex\autopilot\state_store.py` — patrón de persistencia que el módulo Session puede aprender.
- `C:\Cortex\cortex\autopilot\service.py` — para entender el lifecycle existente que vamos a fusionar después.
- `C:\Cortex\cortex\services\session_service.py` — el "session" actual que persiste session notes (NO confundir con la nueva primitiva Session: tareas de naming claro vienen abajo).
- `C:\Cortex\tests\unit\` — patrón de tests del proyecto.

### 1.3 Documentación externa (consultar bajo demanda)

Solo si tenés dudas sobre comportamiento de la librería:

- Pydantic v2: https://docs.pydantic.dev/latest/concepts/models/
- Typer: https://typer.tiangolo.com/tutorial/commands/
- FastMCP server tools: ver `cortex/mcp/server.py` para el patrón actual.
- pytest fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html
- mypy strict: https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict

---

## 2. Goal

Al finalizar esta fase:

1. Existe un módulo nuevo `cortex/session/` que implementa la primitiva **Session** descrita en §5 de la arquitectura.
2. Las sesiones se persisten en `.cortex/sessions/` con un schema YAML estable y atómico.
3. El MCP server expone 5 tools nuevas: `cortex_session_open`, `cortex_session_checkpoint`, `cortex_session_close`, `cortex_session_status`, `cortex_session_list`.
4. La CLI expone un subapp `cortex session` con comandos `current`, `list`, `show`, `diff`, `switch`, `abandon`.
5. `cortex create-spec` abre automáticamente una Session (silencioso, no breaking).
6. `cortex doctor` valida la salud de las sesiones.
7. Tests unitarios + integración cubren el módulo con >85% coverage.
8. El flujo Cortex actual (sync → SDDwork → documenter) sigue funcionando **idéntico** al estado pre-fase.

**Lo que NO se hace en esta fase (intencionalmente):**

- ❌ No se modifica el documenter.
- ❌ No se modifica SDDwork.
- ❌ No se implementa el algoritmo de reconstrucción (es Fase 01).
- ❌ No se implementa `cortex finish-session` (es Fase 01).
- ❌ No se tocan los hooks de Autopilot (es Fase 03).
- ❌ No se modifican los skills/subagents (es Fase 01 en adelante).

---

## 3. Naming: la confusión "session" y cómo la resolvemos

**Atención.** El proyecto ya usa la palabra "session" para referirse a las **session notes** (las notas markdown que el documenter persiste al final de un trabajo). El servicio actual `cortex/services/session_service.py` se llama así por eso.

La primitiva NUEVA es distinta: es un **registro de tracking del ciclo de vida de un desarrollo**. Para evitar colisiones de naming:

### Decisión

- **Mantener `session note` para la nota persistida (markdown).** Es como se le llama en el README y en el vault.
- **La primitiva nueva se llama `Session` (capitalizada en docs) en código `cortex.session.Session` / `SessionRecord`.**
- **Renombrar `cortex/services/session_service.py` a `cortex/services/note_service.py`** al final de la fase (tarea T0.10). Mantener `session_service` como alias deprecated por un release.

Esto evita que dos módulos llamados "session" coexistan ambiguamente.

---

## 4. Task Breakdown

> **Reglas:** una tarea a la vez. Cada tarea termina con tests verdes + Definition of Done cumplida. Marcá la tarea en el Progress Log al final de este documento al cerrarla.

### T0.1 — Schema y modelos Pydantic (`cortex/session/models.py`)

**Objetivo:** definir todos los modelos de datos del módulo.

**Archivos a crear:**
- `cortex/session/__init__.py`
- `cortex/session/models.py`
- `tests/unit/session/__init__.py`
- `tests/unit/session/test_models.py`

**Contenido de `models.py`:**

```python
# Estructura esperada — NO copies literal, leé Pydantic v2 docs y aplicalo bien.
# - Usá ConfigDict(frozen=True, extra='forbid') donde corresponda.
# - Todos los datetimes deben ser timezone-aware (UTC).
# - Usá Literal[...] para enums textuales si tienen pocos valores; Enum si son más de 4 o tienen lógica asociada.

class SessionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    HANDOFF = "handoff"
    ABANDONED = "abandoned"

class SessionMode(str, Enum):
    UNKNOWN = "unknown"   # default al abrir
    MANAGED = "managed"   # inferido si el middle fue SDDwork
    OBSERVED = "observed" # inferido si hubo checkpoints externos
    BYO = "byo"           # inferido si no hubo checkpoints

class CheckpointSource(str, Enum):
    CORTEX_SYNC = "cortex-sync"
    CORTEX_SDDWORK = "cortex-SDDwork"
    CORTEX_CODE_EXPLORER = "cortex-code-explorer"
    CORTEX_CODE_IMPLEMENTER = "cortex-code-implementer"
    USER_SKILL = "user-skill"
    IDE_HOOK = "ide-hook"
    MANUAL = "manual"

class Checkpoint(BaseModel):
    timestamp: datetime  # tz-aware UTC
    source: CheckpointSource
    verified_claims: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    artifacts_touched: list[str] = Field(default_factory=list)
    note: str = ""

class VerificationHookResult(BaseModel):
    name: str
    command: str
    passed: bool
    exit_code: int
    output: str  # capturado, truncado a 10KB max (definir constante)
    duration_ms: int
    run_at: datetime

class SessionRecord(BaseModel):
    # Identity
    session_id: str  # pattern: YYYY-MM-DD_<slug> — validar con regex
    spec_path: Path  # ruta relativa al workspace
    spec_summary: str

    # Repo snapshot al abrir
    start_commit: str  # SHA full
    start_branch: str
    opened_at: datetime  # tz-aware UTC

    # Estado actual
    status: SessionStatus = SessionStatus.OPEN
    mode: SessionMode = SessionMode.UNKNOWN

    # Enriquecimiento
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    verification_results: list[VerificationHookResult] = Field(default_factory=list)

    # Cierre (None si OPEN)
    closed_at: datetime | None = None
    end_commit: str | None = None
    documenter_decision: SessionStatus | None = None
    session_note_path: Path | None = None
    adrs_created: list[Path] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
```

**Validaciones obligatorias (usar Pydantic `@field_validator` o `@model_validator`):**

1. `session_id` matchea regex `^\d{4}-\d{2}-\d{2}_[a-z0-9-]+$`.
2. Si `status == CLOSED | HANDOFF | ABANDONED`, entonces `closed_at`, `end_commit`, `documenter_decision` no pueden ser None.
3. Si `status == OPEN`, los campos de cierre deben ser None.
4. `start_commit` y `end_commit` matchean `^[a-f0-9]{40}$`.

**Tests obligatorios (`test_models.py`):**

- `test_session_id_valid_format` — pattern OK.
- `test_session_id_invalid_format_raises` — pattern KO.
- `test_open_session_has_no_closed_fields` — invariante OPEN.
- `test_closed_session_requires_closed_fields` — invariante CLOSED.
- `test_handoff_status_treated_as_closed` — variante CLOSED.
- `test_commit_sha_validation` — 40 chars hex.
- `test_checkpoint_immutability` — frozen donde aplique.
- `test_serialization_roundtrip_yaml` — `model_dump(mode='json')` → YAML → load → equals.
- `test_extra_fields_forbidden` — `extra='forbid'`.
- `test_datetime_must_be_tz_aware` — naive datetime falla.
- Property-based con Hypothesis: dados los campos válidos, el modelo siempre serializa y vuelve. (Ver tests existentes del repo para ejemplos de Hypothesis.)

**Definition of Done T0.1:**

- [ ] `pytest tests/unit/session/test_models.py -v` pasa.
- [ ] `mypy --strict cortex/session/models.py` limpio.
- [ ] `ruff check cortex/session/models.py tests/unit/session/test_models.py` limpio.
- [ ] Coverage del modelo > 95% (es código declarativo, debería ser alto).
- [ ] `cortex/session/__init__.py` exporta `SessionRecord`, `Checkpoint`, `SessionStatus`, `SessionMode`, `CheckpointSource`, `VerificationHookResult`.

---

### T0.2 — Storage atómico (`cortex/session/storage.py`)

**Objetivo:** persistir y recuperar SessionRecords en `.cortex/sessions/` con garantías de atomicidad y consistencia.

**Archivos a crear:**
- `cortex/session/storage.py`
- `tests/unit/session/test_storage.py`

**API esperada:**

```python
class SessionStorage:
    def __init__(self, sessions_dir: Path) -> None: ...

    def save(self, record: SessionRecord) -> Path:
        """Persist (overwrites if exists). Atomic via tmp+rename."""

    def load(self, session_id: str) -> SessionRecord:
        """Raises SessionNotFound if missing."""

    def exists(self, session_id: str) -> bool: ...

    def list_all(self) -> list[SessionRecord]:
        """Loaded and parsed (skip files that fail to parse, log warning)."""

    def list_by_status(self, status: SessionStatus) -> list[SessionRecord]: ...

    def delete(self, session_id: str) -> None:
        """For tests + abandon command. Raises SessionNotFound if missing."""

    # Active session pointer
    def get_active_session_id(self) -> str | None:
        """Reads .cortex/sessions/active.txt or returns None."""

    def set_active_session_id(self, session_id: str | None) -> None:
        """Writes pointer atomically. None clears the pointer."""
```

**Detalles de implementación:**

- **Atomicidad:** escribir a `<session_id>.yaml.tmp`, fsync, `os.replace(tmp, final)`. Esto es atómico en POSIX y en Windows NTFS.
- **Serialización:** YAML (`yaml.safe_dump` con `sort_keys=False, allow_unicode=True`). Usar `model_dump(mode='json')` antes de pasar a YAML para serializar `datetime`, `Path`, enums correctamente.
- **Deserialización:** `yaml.safe_load` → `SessionRecord.model_validate(...)`.
- **Active pointer:** archivo `.cortex/sessions/active.txt` con un solo session_id, o vacío. Atómico también.
- **Locking:** NO usar file locks (over-engineering). Asumir un único proceso de Cortex CLI a la vez. Si hay race conditions futuras, las resolvemos cuando aparezcan datos.
- **Errores:** lanzar `SessionNotFound`, `SessionStorageCorrupted` (ver T0.3 para definirlos en `errors.py`).

**Tests obligatorios:**

- `test_save_creates_file` — el archivo aparece en sessions_dir.
- `test_save_atomic_no_partial_writes` — interrumpir el save no deja basura.
- `test_load_returns_equal_record` — roundtrip exacto.
- `test_load_missing_raises_not_found`.
- `test_list_all_skips_corrupted_files` — un YAML inválido loguea warning y se ignora, no rompe.
- `test_list_by_status_filters_correctly`.
- `test_delete_removes_file`.
- `test_active_pointer_set_get_clear`.
- `test_active_pointer_idempotent_unset`.
- Edge case: `test_concurrent_writes_no_corruption` — dos `save` en sucesión rápida no corrompen (sin lock, pero por atomic rename está OK; documentar el supuesto).

**Definition of Done T0.2:** ver §2.4 del README + tests específicos pasando.

---

### T0.3 — Errores de dominio (`cortex/session/errors.py`)

**Objetivo:** definir las excepciones del módulo.

**Archivos a crear:**
- `cortex/session/errors.py`
- `tests/unit/session/test_errors.py` (mínimo, solo validar jerarquía)

**Excepciones:**

```python
class SessionError(Exception):
    """Base for all session errors."""

class SessionNotFound(SessionError):
    """Session ID does not exist in storage."""

class SessionAlreadyExists(SessionError):
    """Trying to create a session with an existing ID."""

class InvalidStateTransition(SessionError):
    """E.g., trying to close an already-closed session."""

class SessionStorageCorrupted(SessionError):
    """YAML on disk failed to parse."""

class NoActiveSession(SessionError):
    """An operation that requires an active session was called without one."""
```

**Definition of Done T0.3:** archivos creados, exportados desde `cortex/session/__init__.py`, tests pasan.

---

### T0.4 — Servicio de sesión (`cortex/session/service.py`)

**Objetivo:** API pública del módulo. Orquesta storage + git introspection.

**Archivos a crear:**
- `cortex/session/service.py`
- `tests/unit/session/test_service.py`

**Dependencias del servicio:**

- `SessionStorage` (inyectado).
- Acceso a git (sub-proceso o lib). **Recomendación:** subprocess wrapper minimal en `cortex/session/git.py` con `get_head_commit(repo_root: Path) -> str` y `get_current_branch(repo_root: Path) -> str`. NO usar GitPython (peso, no es dependencia actual del proyecto). Si dudás, ver si el repo ya tiene un wrapper de git (grep `subprocess.*git`).

**API esperada:**

```python
class SessionService:
    def __init__(
        self,
        storage: SessionStorage,
        repo_root: Path,
    ) -> None: ...

    def open(
        self,
        spec_id: str,
        spec_path: Path,
        spec_summary: str,
    ) -> SessionRecord:
        """
        Creates a new Session. Captures current HEAD + branch.
        Sets it as the active session.
        Raises SessionAlreadyExists if spec_id collides.
        """

    def checkpoint(
        self,
        session_id: str,
        source: CheckpointSource,
        verified_claims: list[str] = [],
        unverified_claims: list[str] = [],
        artifacts_touched: list[str] = [],
        note: str = "",
    ) -> SessionRecord:
        """Appends a checkpoint. Raises if session not OPEN."""

    def close(
        self,
        session_id: str,
        status: SessionStatus,  # CLOSED, HANDOFF, ABANDONED
        documenter_decision: SessionStatus,
        session_note_path: Path | None = None,
        adrs_created: list[Path] = [],
    ) -> SessionRecord:
        """
        Closes a Session. Captures HEAD as end_commit.
        Infers mode from checkpoints (managed/observed/byo).
        Clears active pointer if it was this session.
        """

    def abandon(self, session_id: str, reason: str) -> SessionRecord:
        """Convenience for close(ABANDONED, ...)."""

    def get(self, session_id: str) -> SessionRecord: ...

    def get_active(self) -> SessionRecord | None: ...

    def set_active(self, session_id: str) -> None:
        """Validates session exists and is OPEN."""

    def list(self, status: SessionStatus | None = None) -> list[SessionRecord]: ...

    def compute_diff(self, session_id: str) -> str:
        """
        Returns `git diff <start_commit>..HEAD`. Used by `cortex session diff`.
        If session is closed, uses end_commit instead of HEAD.
        Raises SessionNotFound or git errors propagados.
        """

    @staticmethod
    def infer_mode(checkpoints: list[Checkpoint]) -> SessionMode:
        """
        - 0 checkpoints → BYO
        - Checkpoints todos de fuentes Cortex (SDDwork/explorer/implementer) → MANAGED
        - Mixed o IDE_HOOK / USER_SKILL → OBSERVED
        """
```

**Generación del `session_id`:**

- Formato: `YYYY-MM-DD_<slug>` donde slug es la parte slugificada del título del spec.
- Función helper `_make_session_id(date: date, title: str) -> str` en `service.py`.
- Si colisión (mismo título mismo día), append `-2`, `-3`, etc.

**Tests obligatorios:**

- `test_open_creates_record_and_sets_active`.
- `test_open_duplicate_id_appends_counter` — `2026-05-16_foo`, `2026-05-16_foo-2`.
- `test_checkpoint_appends_to_open_session`.
- `test_checkpoint_rejects_closed_session` — raises `InvalidStateTransition`.
- `test_close_captures_end_commit_and_clears_active`.
- `test_close_infers_mode_byo` — sin checkpoints.
- `test_close_infers_mode_managed` — checkpoints solo de SDDwork.
- `test_close_infers_mode_observed` — checkpoints de IDE_HOOK.
- `test_abandon_closes_with_reason_in_documenter_decision_field`. (Decisión: el reason va como nota en `checkpoints` con `source=MANUAL`. Confirmar al implementar.)
- `test_get_active_returns_none_when_no_active`.
- `test_set_active_validates_existence_and_open_status`.
- `test_compute_diff_calls_git_correctly` — mock subprocess.
- `test_infer_mode_static_function` — tabla exhaustiva.

**Definition of Done T0.4:** Service usable end-to-end vía tests, coverage > 90% del service.

---

### T0.5 — Integración con WorkspaceLayout

**Objetivo:** asegurar que `WorkspaceLayout` resuelve `sessions_dir` correctamente para layout v2 y layout legacy.

**Archivos a modificar:**
- `cortex/workspace/layout.py`

**Archivos a tocar como referencia:**
- Leer cómo se exponen otros directorios (`vault_dir`, `memory_dir`, etc.) y replicar el patrón EXACTO.

**API esperada (agregar al WorkspaceLayout):**

```python
@property
def sessions_dir(self) -> Path:
    """
    Returns .cortex/sessions/ in layout v2, .cortex/sessions/ also in legacy
    (decisión: las sesiones SOLO viven en layout v2, porque son una primitiva
    nueva. En proyectos legacy sin .cortex/, esto debe lanzar un error
    explicativo guiando al usuario a `cortex setup agent`).
    """
```

**Tests obligatorios:**
- `test_sessions_dir_layout_v2` — resuelve correctamente.
- `test_sessions_dir_legacy_raises_with_helpful_message` — error claro.

**Setup integration:**
- Modificar `cortex/setup/` para que `cortex setup agent` cree el directorio `.cortex/sessions/` con un `.gitkeep`.

---

### T0.6 — Integración con `cortex create-spec`

**Objetivo:** que `cortex_create_spec` abra una Session automáticamente al persistir un spec.

**Archivos a modificar:**
- `cortex/services/spec_service.py`
- `tests/unit/services/test_spec_service.py` (o donde estén los tests actuales — verificar con `Grep`)

**Cambios concretos:**

1. `SpecService.create(...)` recibe (o construye internamente) un `SessionService`.
2. Después de persistir el spec exitosamente, llama a `session_service.open(spec_id, spec_path, spec_summary)`.
3. **Si la apertura de session falla**, NO falla la creación del spec. Loguea warning y continúa. La Session es enrichment, no requirement, en esta fase.

**Razón de no-failure:** queremos que Fase 00 sea aditiva sin breaking. Si algún test viejo no proporciona SessionService, no debe romperse.

**Tests obligatorios:**
- `test_create_spec_opens_session` — happy path.
- `test_create_spec_succeeds_when_session_open_fails` — robustez.

---

### T0.7 — MCP tools

**Objetivo:** exponer las 5 tools del módulo Session vía MCP.

**Archivos a modificar:**
- `cortex/mcp/server.py`
- Tests correspondientes en `tests/integration/mcp/` o donde estén los tests MCP — chequear con `Grep`.

**Tools a agregar:**

1. **`cortex_session_open`**
   - Inputs: `spec_id: str`, `spec_path: str`, `spec_summary: str`
   - Output: `{ session_id, opened_at, start_commit, start_branch }`
   - Decisión: NO exponerla públicamente para uso directo. Es invocada internamente por `cortex_create_spec`. Pero exponerla en el MCP igual permite testing.

2. **`cortex_session_checkpoint`**
   - Inputs: `session_id: str`, `source: str`, `verified_claims: list[str]`, `unverified_claims: list[str]`, `artifacts_touched: list[str]`, `note: str`
   - Output: `{ session_id, checkpoint_count, last_checkpoint_at }`
   - Validación: source debe ser un valor de `CheckpointSource`. Si no, retornar error con la lista de valores válidos.

3. **`cortex_session_close`**
   - Inputs: `session_id: str`, `status: str` (CLOSED|HANDOFF|ABANDONED), `documenter_decision: str`, `session_note_path: str | null`, `adrs_created: list[str]`
   - Output: `{ session_id, closed_at, end_commit, mode_inferred }`

4. **`cortex_session_status`**
   - Inputs: `session_id: str | null` — si null, usa la sesión activa.
   - Output: el SessionRecord completo serializado.

5. **`cortex_session_list`**
   - Inputs: `status: str | null` (filtro opcional)
   - Output: `list[SessionRecord]` resumidos (no incluir checkpoints completos, solo count).

**Tests obligatorios:**
- Test de cada tool: validación de inputs, output schema correcto, manejo de errores (session not found, etc.).
- Test E2E del flow: `open → checkpoint → checkpoint → close → status`.

**Definition of Done T0.7:** MCP tools invocables, validadas, con tests.

---

### T0.8 — CLI subcommands (`cortex session ...`)

**Objetivo:** exponer las operaciones de Session al usuario vía CLI.

**Archivos a crear:**
- `cortex/cli/session.py`
- `tests/unit/cli/test_session_cli.py`

**Archivos a modificar:**
- `cortex/cli/main.py` — registrar el subapp.

**Comandos a implementar:**

| Comando | Descripción | Argumentos | Output |
|---|---|---|---|
| `cortex session current` | ID de la sesión activa | — | session_id o "no active session" |
| `cortex session list` | Lista todas las sesiones | `--status <open\|closed\|handoff\|abandoned>` opcional | tabla formateada como mockup en arquitectura §9.3 |
| `cortex session show <id>` | Detalle de una sesión | `<id>` opcional (default: active); `--json` para output JSON | tabla como mockup §9.4 |
| `cortex session diff [<id>]` | Diff git desde start_commit | `<id>` opcional | output de `git diff` |
| `cortex session switch <id>` | Cambia la sesión activa | `<id>` requerido | confirmación |
| `cortex session abandon <id>` | Marca como abandonada | `<id>` requerido, `--reason <str>` requerido, `--yes` para skip confirm | confirmación |

**Output formatting:**
- Usar `rich` (ya presente en el repo, ver `pyproject.toml` o `Grep`) para tablas.
- `--json` flag global del subapp para output machine-readable.

**Tests obligatorios:**
- Test cada comando con `CliRunner` (Typer testing).
- Test salidas tabular y JSON.
- Test mensajes de error legibles (ej. session not found → mensaje claro, no traceback).

**Definition of Done T0.8:** comandos invocables, tests verdes, output legible.

---

### T0.9 — Doctor section para sessions

**Objetivo:** `cortex doctor` valida la salud de las sesiones.

**Archivos a modificar:**
- `cortex/doctor.py` — agregar una sección.

**Validaciones a implementar:**

1. El directorio `.cortex/sessions/` existe y es escribible.
2. El pointer `active.txt` (si existe) apunta a una sesión existente.
3. Todas las sesiones en disco parsean OK (warning para las que no).
4. No hay más de UNA sesión con `status == OPEN` Y la misma como activa (consistency check).
5. Verificación de invariantes: cada sesión CLOSED tiene `end_commit` y `closed_at`.

**Salida esperada (texto):**

```
[sessions]
  ✓ Directory exists and writable: .cortex/sessions/
  ✓ Active session: 2026-05-16_auth-jwt-refresh (open)
  ✓ 12 sessions on disk parsed correctly
  ⚠ 1 session has invariant violation: 2026-04-10_x (status=closed but end_commit=null)
```

**Tests obligatorios:**
- Mockear escenarios: dir ausente, active pointer roto, sesión inválida.

---

### T0.10 — Renombrar `session_service.py` → `note_service.py`

**Objetivo:** eliminar la ambigüedad de naming.

**Archivos a tocar:**

- Renombrar `cortex/services/session_service.py` → `cortex/services/note_service.py`.
- Renombrar la clase `SessionService` (existente, para session notes) → `NoteService`.
- **Búsqueda exhaustiva** con `Grep` de todas las referencias (`cortex/services/session_service`, `from cortex.services.session_service`, `SessionService(`) y actualizar.
- Mantener compatibilidad: en `cortex/services/session_service.py` (re-crear como alias):
  ```python
  from cortex.services.note_service import NoteService as SessionService
  import warnings
  warnings.warn(
      "cortex.services.session_service is deprecated; use cortex.services.note_service.NoteService",
      DeprecationWarning,
      stacklevel=2,
  )
  ```

**Tests obligatorios:**
- Todos los tests existentes deben seguir pasando.
- Test específico del alias deprecated (que el warning se emite).

**Razón de hacerlo en Fase 00 y no en Fase 01:**
- En Fase 01, `cortex/session/service.py` (la primitiva nueva) coexistirá con el viejo `cortex/services/session_service.py`. Si no resolvemos el naming ahora, en Fase 01 vamos a estar tocando dos archivos llamados "session_service" simultáneamente. Limpieza ahora = simplicidad después.

---

### T0.11 — Setup integration

**Objetivo:** que `cortex setup agent` cree la infraestructura de sesiones.

**Archivos a modificar:**
- `cortex/setup/` — encontrar el orquestador del setup de agent (usar `Grep` por `setup_agent` o `setup agent`).

**Cambios concretos:**
1. `cortex setup agent` crea `.cortex/sessions/` con un `.gitkeep`.
2. NO crea archivos de sesión (no hay sesiones todavía).
3. NO crea `active.txt`.

**Test obligatorio:**
- Test E2E del setup en un directorio temporal: verificar que `.cortex/sessions/` existe al finalizar.

---

### T0.12 — Documentación pública

**Objetivo:** que un usuario pueda descubrir la primitiva Session desde el README principal.

**Archivos a modificar:**
- `C:\Cortex\README.md` — agregar sección "Sessions" en CLI Reference y un párrafo en "Conceptos clave" o equivalente.
- `C:\Cortex\docs\architecture\session-primitive.md` (nuevo) — referencia técnica del módulo.

**Contenido de `docs/architecture/session-primitive.md`:**
- Qué es una Session.
- Cuándo se abre, cuándo se cierra.
- Comandos CLI disponibles.
- Tools MCP disponibles.
- Diagrama de estados (copiar de la arquitectura §5.3).
- **Link al documento maestro** `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`.

**Definition of Done T0.12:** README actualizado, doc técnica creada, links válidos.

---

## 5. Cross-cutting concerns

### 5.1 Logging

- Usar el logger del proyecto (buscar con `Grep "logging.getLogger"`).
- Niveles:
  - DEBUG: detalles de I/O (paths leídos, comandos git ejecutados).
  - INFO: eventos importantes (session abierta, cerrada).
  - WARNING: situaciones recuperables (archivo de sesión corrupto, ignorado).
  - ERROR: fallos que rompen una operación.
- NO usar `print()` en código de producción.

### 5.2 Performance

- Una `SessionStorage.list_all()` con 1000 sesiones debe ser < 500ms. Si supera, considerar caching en memoria (decisión: NO hacerlo en esta fase, optimizar solo si se observa).
- El YAML por sesión es pequeño (< 10KB típicamente). No optimización necesaria.

### 5.3 Concurrencia

- Asumir un único proceso CLI a la vez. Documentar el supuesto en el module docstring.
- Si dos procesos abren sesiones simultáneamente: el `active.txt` puede tener race (último gana). Es aceptable.

### 5.4 Backward compatibility

- **Cero breaking changes en esta fase.** Si una tarea introduce uno, parar.
- El alias `session_service` deprecated debe seguir funcionando hasta una mayor (release próxima).

---

## 6. Completion Verification Commands

Al cerrar la fase, **TODOS** estos comandos deben pasar:

```bash
# 1. Tests del módulo nuevo
cd C:\Cortex
pytest tests/unit/session/ -v
pytest tests/integration/ -v -k session
# expected: all green

# 2. Type checking
mypy --strict cortex/session/
# expected: Success: no issues found

# 3. Lint
ruff check cortex/session/ tests/unit/session/
ruff format --check cortex/session/ tests/unit/session/
# expected: All clean

# 4. Coverage
pytest --cov=cortex.session tests/unit/session/ tests/integration/
# expected: coverage > 85%

# 5. Que el flujo viejo SIGUE funcionando idéntico
# (smoke test del happy path tripartito; NO debe romperse nada)
pytest tests/e2e/ -v
# expected: all green

# 6. CLI smoke test
cortex session --help
# expected: shows subcommands

cortex doctor --section sessions
# expected: validates sessions dir

# 7. Verificar que create-spec sigue funcionando + abre sesión
# (en un repo de prueba)
cortex create-spec --title "test session integration" --goal "verify"
cortex session current
# expected: muestra el ID de la sesión recién abierta
cortex session list
# expected: muestra la sesión nueva en estado open
```

---

## 7. Handoff to next phase

Al cerrar la Fase 00, queda disponible para la Fase 01:

### Artefactos producidos

| Artefacto | Descripción | Path |
|---|---|---|
| Módulo `cortex.session` | Primitiva completa | `cortex/session/` |
| `SessionRecord`, `Checkpoint`, etc. | Modelos Pydantic | `cortex/session/models.py` |
| `SessionService` | API pública del módulo | `cortex/session/service.py` |
| `SessionStorage` | Persistencia atómica | `cortex/session/storage.py` |
| MCP tools `cortex_session_*` (5) | Acceso vía MCP | `cortex/mcp/server.py` |
| CLI `cortex session ...` (6 cmds) | Acceso vía CLI | `cortex/cli/session.py` |
| Integración con `create-spec` | Apertura automática | `cortex/services/spec_service.py` |
| Doctor section | Validación de salud | `cortex/doctor.py` |
| `NoteService` (renombrado) | Lo que antes era `SessionService` | `cortex/services/note_service.py` |
| Docs técnicas | Referencia de la primitiva | `docs/architecture/session-primitive.md` |

### Lo que la Fase 01 puede asumir como dado

1. Al crear un spec, hay una Session activa abierta automáticamente.
2. Cualquier código puede llamar `cortex_session_checkpoint()` (vía MCP) o `SessionService.checkpoint()` (vía Python) para enriquecer una sesión.
3. La diferencia entre BYO y Managed se infiere desde checkpoints (lógica en `SessionService.infer_mode`).
4. El usuario puede inspeccionar/listar sesiones vía CLI.

### Lo que NO se entrega (es trabajo de fases posteriores)

- **No existe `cortex finish-session`** todavía (es T1.5).
- **El documenter NO sabe leer una Session.** Sigue operando con el handoff YAML viejo.
- **SDDwork NO emite checkpoints.** Sigue emitiendo handoff YAML viejo.
- **No hay verification hooks runner.**

---

## 8. Progress Log (actualizar durante la ejecución)

Marcá ✅ cada tarea al cerrarla. Si interrumpís, este es el ancla para retomar.

- [ ] T0.1 — Schema y modelos Pydantic
- [ ] T0.2 — Storage atómico
- [ ] T0.3 — Errores de dominio
- [ ] T0.4 — Servicio de sesión
- [ ] T0.5 — Integración con WorkspaceLayout
- [ ] T0.6 — Integración con `cortex create-spec`
- [ ] T0.7 — MCP tools
- [ ] T0.8 — CLI subcommands
- [ ] T0.9 — Doctor section
- [ ] T0.10 — Renombrar session_service → note_service
- [ ] T0.11 — Setup integration
- [ ] T0.12 — Documentación pública
- [ ] **Completion Verification Commands** (§6) — TODOS pasaron
- [ ] Tabla de progreso en `../README.md` actualizada con ✅
- [ ] Commit final hecho

**Notas durante la ejecución:**

> Espacio reservado para que el agente registre decisiones puntuales, blockers encontrados, desviaciones del plan. Si una decisión cambia algo del plan, anotala acá y mencionala en el commit message.

---

## 9. Notas para el agente ejecutor

- **No saltes Required Reading.** Leer los archivos del repo antes de tocarlos es lo que evita romper convenciones existentes.
- **Cuando dudes de un patrón:** `Grep` cómo se hace en el resto del proyecto. Replicá el patrón existente.
- **Cuando dudes de una librería:** `WebFetch` su doc oficial.
- **No bypasses tests.** Si un test falla, arreglá la implementación. Nunca el test.
- **Si descubrís un bug pre-existente en el repo durante esta fase:** anotalo en el Progress Log, NO lo arregles (out of scope). Reportalo al cierre de fase.
