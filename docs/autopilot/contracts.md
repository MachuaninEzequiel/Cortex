# Cortex Autopilot — Contratos Estables

**Fecha:** 2026-05-09  
**Versión del contrato:** 1.0  
**Estado:** Aprobado para implementación Fase 1+

---

## 1. Contrato de Estado (`AutopilotSessionState`)

### 1.1 Propósito
Representa el estado mutable de una sesión de Autopilot en un momento dado. Es la única fuente de verdad para el ciclo de vida de una tarea.

### 1.2 Esquema (Pydantic)

```python
class AutopilotBudgetSnapshot(BaseModel):
    chars_injected: int = 0
    items_retrieved: int = 0
    embeddings_used: bool = False
    subagents_spawned: int = 0
    deep_track_reason: str | None = None


class AutopilotCheckpoint(BaseModel):
    timestamp: datetime
    summary: str
    files_at_checkpoint: list[str] = []
    verified: bool = False


class AutopilotSessionState(BaseModel):
    schema_version: int = 1
    session_id: str               # uuid.uuid4().hex[:12]
    project_root: str             # absoluto
    workspace_root: str           # absoluto (resuelto por WorkspaceLayout)
    created_at: datetime
    updated_at: datetime
    status: Literal[
        "started",
        "preflight_done",
        "implementation_seen",
        "documented",
        "finished",
        "failed",
    ] = "started"
    mode: Literal["observe", "assist", "autopilot"] = "assist"
    user_request: str | None = None
    title_hint: str | None = None
    detected_task_type: str | None = None
    complexity: Literal["none", "fast", "deep"] = "none"
    spec_path: str | None = None
    session_note_path: str | None = None
    changed_files: list[str] = []
    commands_seen: list[str] = []
    tools_seen: list[str] = []
    checkpoints: list[AutopilotCheckpoint] = []
    budget: AutopilotBudgetSnapshot = Field(default_factory=AutopilotBudgetSnapshot)
    warnings: list[str] = []
```

### 1.3 Reglas de evolución
- `schema_version` se incrementa solo en cambios breaking de campos obligatorios.
- `session_id` es inmutable después de `start()`.
- `updated_at` se refresca en **cada** transición de estado o evento.
- `mode` puede degradarse (ej. `autopilot` → `assist`) pero nunca promocionarse sin reinicio.

### 1.4 Compatibilidad con `WorkspaceLayout`
- `workspace_root` se obtiene **exclusivamente** de `WorkspaceLayout.workspace_root`.
- En layout legacy, `workspace_root == project_root`.
- En layout nuevo, `workspace_root == project_root / ".cortex"`.
- **Prohibido** hardcodear `.cortex/`, `config.yaml` o `vault/`.

---

## 2. Contrato de Eventos (`AutopilotEvent`)

### 2.1 Propósito
Secuencia inmutable de hechos observados. Fuente de verdad para renders y auditoría.

### 2.2 Esquema

```python
class AutopilotEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    event_type: str          # "start", "preflight", "checkpoint", "finish",
                             # "tool_call", "policy_eval", "mode_change", etc.
    source: Literal["cli", "mcp", "hook", "agent", "detector", "policy"]
    payload: dict[str, Any] = {}
```

### 2.3 Persistencia
- Formato: **JSON Lines** (`.jsonl`), un evento por línea.
- Ruta: `{workspace_root}/run/autopilot/events/{session_id}.jsonl`.
- Escritura: append-only, sin reescribir líneas existentes.
- Lectura: línea por línea; saltar líneas vacías o malformadas con warning.

### 2.4 Reglas
- Todo cambio de estado debe dejar al menos un evento.
- `payload` puede contener cualquier dato serializable; no se valida estrictamente salvo en tests.
- El orden cronológico es el orden de aparición en el archivo.

---

## 3. Contrato de Detección

### 3.1 `DetectionRequest`

```python
class DetectionRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None
    session_state: AutopilotSessionState | None = None
```

### 3.2 `DetectionResult`

```python
class DetectionResult(BaseModel):
    task_type: Literal[
        "question-only", "docs-only", "fast-code",
        "deep-code", "security", "ambiguous", "noop"
    ]
    confidence: float          # 0.0 – 1.0
    reason: str                # explicación corta para logs
    suggested_complexity: Literal["none", "fast", "deep"] = "none"
```

### 3.3 Reglas de resolución (DetectorRegistry)
1. Ejecutar todos los detectores registrados.
2. Filtrar resultados con `confidence > 0.3`.
3. Si `SecuritySensitiveDetector` tiene `confidence > 0.5`, toma prioridad absoluta.
4. Si `AmbiguousRequestDetector` tiene `confidence > 0.6`, bloquea antes de cualquier otro.
5. En caso contrario, elegir el de mayor `confidence`.
6. En empate, preferir el más conservador (mayor complejidad sugerida).

---

## 4. Contrato de Policies

### 4.1 `PolicyDecision`

```python
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None
```

### 4.2 Semántica de acciones
| Acción | Significado |
|--------|-------------|
| `proceed` | Continuar normalmente. |
| `warn` | Registrar warning, pero permitir avance. |
| `degrade` | Cambiar modo/complejidad y continuar. |
| `block` | Detener la transición; requiere intervención (o auto-draft en finish). |

### 4.3 Evaluación
- Se evalúan en **cada** transición de estado.
- Orden: `AmbiguousRequestDetector` primero (pre-policy), luego policies estándar.
- Una policy `block` tiene veto; no se sobrescribe por otra policy.

---

## 5. Contrato de Renderers / Session Builder

### 5.1 `SessionDraft`

```python
class SessionDraft(BaseModel):
    title: str
    body: str                        # markdown
    confidence: Literal["high", "medium", "auto-draft"] = "medium"
    warnings: list[str] = []
    source_events: int = 0
```

### 5.2 Reglas de seguridad epistémica
1. Si no se observó un cambio, **no** se declara como realizado.
2. Si no se ejecutaron tests, se escribe `"No registrado"`.
3. Si no hay spec, se escribe `"No se detectó spec asociada"`.
4. Si el cierre es automático y faltan datos, `confidence = "auto-draft"`.
5. El self-review debe ejecutarse antes de persistir.

---

## 6. Contrato de Presupuesto (Context Budget)

### 6.1 Profiles

| Profile | max_items | max_chars | embeddings | subagents | Uso |
|---------|-----------|-----------|------------|-----------|-----|
| `question_only` | 0 | 0 | no | no | Respuesta directa, sin retrieval. |
| `docs_only` | 3 | 1 200 | keyword primero | no | Tareas puramente documentales. |
| `fast_code` | 5 | 2 000 | sí | no | Cambios simples, 1-2 archivos. |
| `deep_code` | 8 | 3 500 | sí | permitido | Refactor o arquitectura nueva. |
| `finish_only` | n/a | 2 000 | no | no | Cierre de sesión, solo eventos. |

### 6.2 Reglas generales
- `cortex_context` se invoca con formato `compact` por defecto en Autopilot.
- `cortex_sync_ticket` usa `top_k` bajo (3 en fast, 5 en deep).
- No full `sync-vault` salvo:
  - instalación / reparación,
  - comando explícito del usuario,
  - policy enterprise que lo requiera.
- El estado guarda snapshot del budget en cada transición.

---

## 7. Contrato de Hook Adapters

### 7.1 Protocolo

```python
class AutopilotHookAdapter(Protocol):
    name: str
    supported_events: set[str]

    def install(self, project_root: Path, config: AutopilotConfig) -> list[Path]: ...
    def uninstall(self, project_root: Path) -> list[Path]: ...
    def emit_session_start(self, state: AutopilotSessionState, bootstrap: str) -> str: ...
```

### 7.2 Output de `session-start`

El hook debe emitir JSON por stdout. El wrapper del harness debe adaptar el formato:

```python
class HookSessionStartOutput(BaseModel):
    session_id: str
    mode: Literal["observe", "assist", "autopilot"]
    bootstrap_content: str
    budget_profile: str
    available_tools: list[str]
    cortex_version: str
```

#### Formato por plataforma (contrato de serialización)

| Plataforma | Wrapper esperado |
|------------|------------------|
| Cursor | `{"additional_context": <payload>}` |
| Claude Code | `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <payload>}}` |
| Copilot CLI / OpenCode / genérico | `{"additionalContext": <payload>}` |

Detección por variables de entorno:
- `CURSOR_PLUGIN_ROOT` → Cursor
- `CLAUDE_PLUGIN_ROOT` (sin `COPILOT_CLI`) → Claude Code
- `COPILOT_CLI` → Copilot CLI

### 7.3 Wrapper cross-platform
- El runtime del hook debe ser **Python** (`python -m cortex.autopilot.hooks.<nombre>`), no bash puro.
- En Windows se provee un wrapper `.cmd` que invoca Python.
- Esto garantiza compatibilidad sin depender de WSL ni Git Bash.

---

## 8. Matriz de Compatibilidad IDE

| IDE / Harness | Adapter actual (cortex.ide) | Adapter Autopilot (fase 7) | Hooks soportados | MCP nativo | Notas |
|---------------|----------------------------|----------------------------|------------------|------------|-------|
| Claude Code | `ClaudeCodeAdapter` | `ClaudeCodeAutopilotAdapter` | `session-start`, `session-finish` | vía `.mcp.json` | Skill dirs en `.claude/skills` |
| Cursor | `CursorAdapter` | `CursorAutopilotAdapter` | `session-start`, `session-finish` | vía `~/.cursor/mcp.json` | Agents en `~/.cursor/agents` |
| OpenCode | `OpenCodeAdapter` | `OpenCodeAutopilotAdapter` | `session-start` | vía `~/.config/opencode` | Per-project config |
| VS Code | `VSCodeAdapter` | — (futuro) | — | vía `claude_desktop_config.json` | Requiere Claude Desktop bridge |
| Windsurf | `WindsurfAdapter` | — (futuro) | — | vía `~/.codeium/windsurf/mcp_config.json` | MCP only |
| Zed | `ZedAdapter` | — (futuro) | — | vía `~/.zed/agents.json` | Agents only |
| Pi | `PiAdapter` | — (futuro) | — | No | Copia de archivos estáticos |
| Antigravity | `AntigravityAdapter` | — (futuro) | — | No | Config global `~/.gemini` |
| Hermes | `HermesAdapter` | — (futuro) | — | No | Config global `~/.config/hermes` |
| Claude Desktop | `ClaudeDesktopAdapter` | — (futuro) | — | Sí | Config usuario, no proyecto |

### 8.1 Reglas de convivencia
- Los adapters Autopilot viven en `cortex/autopilot/adapters/`, separados de `cortex/ide/adapters/`.
- Pueden reusar utilidades de `cortex.ide.base` (ej. `_backup_file`, `_deep_merge_dict`).
- **No** deben conocer detalles internos de `AutopilotService`; solo reciben `state` y `bootstrap`.
- `install` y `uninstall` deben crear backups y remover **solo** bloques Autopilot.

---

## 9. Contrato de Delegación (Two-Stage Review)

### 9.1 `DelegationResult`

```python
class DelegationResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "rejected"]
    diff_summary: str = ""
    files_changed: list[str] = []
    tests_passed: bool | None = None
    spec_path: str | None = None
    rejection_reason: str | None = None
```

### 9.2 Protocolo
```text
Subagente completa tarea
    |
    v
Stage 1: Spec compliance (automático)
    - ¿El diff coincide con la spec?
    - ¿Se modificaron solo los archivos esperados?
    - Si FALLA → rechazar y re-despachar
    |
    v
Stage 2: Quality review (agente orquestador)
    - Revisión de calidad del código
    - ¿Tests pasan?
    - Si FALLA → rechazar con feedback específico
    |
    v
Aceptar y registrar checkpoint
```

### 9.3 Regla de degradación
Si no hay runtime de subagente disponible en el harness, Autopilot debe:
- Degradar a **Fast Track**, o
- Pedir confirmación en modo `assist`,  
**nunca** fallar silenciosamente.

---

## 10. Extension Points

Autopilot debe ser extensible por adición de archivos:

| Extensión | Mecanismo | Registro |
|-----------|-----------|----------|
| Detector | Heredar protocolo `AutopilotDetector` | `DetectorRegistry.register(...)` |
| Policy | Heredar protocolo `AutopilotPolicy` | `PolicyRegistry.register(...)` |
| Renderer | Heredar protocolo `SessionRenderer` | `RendererRegistry.register(...)` |
| Hook Adapter | Heredar protocolo `AutopilotHookAdapter` | `AdapterRegistry.register(...)` |
| Budget Profile | Definir clase de configuración | `BudgetProfileRegistry.register(...)` |
| Skill | Archivo `.md` en `.cortex/skills/` | Descubrimiento por nombre en setup |

### 10.1 Regla de registro
- Cada registry debe exponer `register(instance)` y `list_all() -> list`.
- El orden de evaluación de detectores/policies es el orden de registro, salvo prioridades definidas (ej. seguridad > ambigüedad).

---

## 11. No-Objetivos Reafirmados

1. No reemplazar `cortex-sync`, `cortex-SDDwork` ni `cortex-documenter`.
2. No forzar autonomía a usuarios manuales.
3. No reescribir el MCP server completo (solo agregar tools en Fase 5).
4. No convertir comandos actuales en headless.
5. No hacer full vault sync en cada cierre.
6. No leer todo el repositorio para contexto.
7. No llamar subagentes para tareas simples.
8. No guardar session notes inventando información no observada.
9. No agregar dependencias pesadas.
10. No crear branches automáticamente en MVP.
11. No implementar brainstorming completo previo a cada tarea.
12. No usar tags de urgencia en prompts (`EXTREMELY_IMPORTANT`, etc.).

---

## 12. Decisiones de Contrato Tomadas en Fase 0

### 12.1 Layout de persistencia
- Estado JSON: `{workspace_root}/run/autopilot/sessions/{session_id}.json`
- Eventos JSONL: `{workspace_root}/run/autopilot/events/{session_id}.jsonl`
- Justificación: `run/` ya es un directorio de runtime en el layout nuevo; en legacy se creará bajo `.cortex/run/` porque `workspace_root == project_root`.

### 12.2 Modo por defecto
- `assist` es el modo por defecto para todas las sesiones nuevas.
- Justificación: minimiza riesgo de adopción; el usuario siempre puede promocionar a `autopilot` explícitamente.

### 12.3 CLI vs MCP vs Hook
- Tres capas finas que delegan a `AutopilotService`.
- Ninguna capa periférica debe contener lógica de negocio.
- Esto asegura que el comportamiento sea idéntico sin importar el punto de entrada.

### 12.4 Versionado de estado
- `schema_version = 1` para el MVP.
- Si en el futuro cambiamos campos obligatorios, se incrementa y se escribe migrador en `StateStore`.

### 12.5 Presupuesto agresivo por defecto
- `fast_code` es el default para tareas con cambios de código no ambiguos.
- `deep_code` requiere umbral claro (múltiples archivos, refactor, seguridad).
- Esto evita el problema de "Superpowers": workflows buenos pero potencialmente caros.

---

## 13. Validación contra Código Existente

### 13.1 `WorkspaceLayout`
- ✅ Soporta new y legacy layout.
- ✅ `workspace_root` se resuelve correctamente en ambos modos.
- ✅ No se requiere modificar `layout.py` para soportar `run/autopilot`; se usa `resolve_workspace_relative()` si fuera necesario.
- ⚠️ **Observación:** `WorkspaceLayout` no tiene propiedad `autopilot_run_dir`. Se agregará en Fase 1 como helper opcional o se usará `resolve_workspace_relative("run/autopilot")`.

### 13.2 `cortex/cli/main.py`
- ✅ Usa `typer` con `app = typer.Typer(...)`.
- ✅ Ya tiene múltiples `app.add_typer(...)`.
- ✅ Agregar `app.add_typer(autopilot_app, name="autopilot")` no rompe comandos existentes.
- ✅ Todos los comandos actuales permanecen intactos.

### 13.3 `cortex/mcp/server.py`
- ✅ Expone tools con `types.Tool` y schemas JSON.
- ✅ Tiene `_called_tools` en memoria de proceso (limitación conocida; se resuelve en Fase 5 con estado persistente).
- ✅ No se toca en esta fase.

### 13.4 `cortex/setup/cortex_workspace.py`
- ✅ Genera skills en `.cortex/skills/`.
- ✅ No conflictos con la meta-skill `using-cortex-autopilot.md` que se agregará en Fase 6.
- ✅ El setup normal sin Autopilot queda igual.

### 13.5 `cortex/ide/adapters/*`
- ✅ Cada adapter tiene `name`, `display_name`, `get_config_paths()`, `inject_profiles()`.
- ✅ No conocen Autopilot; convivencia segura.
- ✅ Los adapters Autopilot reutilizarán `_backup_file` y `_deep_merge_dict` de `cortex.ide.base`.

---

*Fin del documento de contratos.*
