# Cortex Autopilot - Plan por Fases

**Fecha:** 2026-05-09  
**Estado:** Propuesta tecnica para planificacion  
**Alcance:** Nuevo modo autonomo opcional, sin reemplazar el flujo actual  
**Principio rector:** alternativas primero, extensibilidad por contrato, bajo consumo de tokens

---

## 1. Resumen Ejecutivo

Cortex ya tiene el nucleo que necesita un modo autonomo:

- CLI Typer en `cortex/cli/main.py`
- memoria hibrida en `AgentMemory`
- servicios separados para specs, sesiones y PRs
- MCP server con herramientas `cortex_*`
- perfiles IDE y adapters
- skills y subagentes instalables en `.cortex/`
- `ContextEnricher` con presupuesto de contexto
- RRF adaptativo y embeddings ONNX locales

Lo que falta no es reescribir Cortex, sino agregar una capa nueva que convierta ese sistema en una experiencia de "piloto automatico" para usuarios que no quieren cambiar manualmente entre perfiles ni recordar comandos.

La propuesta es construir `Cortex Autopilot` como modulo aislado:

```text
cortex/
  autopilot/
    __init__.py
    models.py
    config.py
    state_store.py
    service.py
    lifecycle.py
    detectors.py
    context_budget.py
    session_builder.py
    registry.py
    cli.py
    mcp_tools.py
    hooks/
    skills/
    adapters/
```

El CLI existente queda intacto. Solo se agrega un grupo nuevo:

```bash
cortex autopilot ...
```

El usuario conserva los modos actuales:

- modo manual: `cortex-sync` -> `cortex-SDDwork` -> `cortex-documenter`
- modo CLI directo: `cortex context`, `cortex create-spec`, `cortex save-session`
- modo pipeline/enterprise
- modo nuevo: `cortex autopilot`

Autopilot debe ser opt-in y reversible.

---

## 2. Objetivos

### Objetivo principal

Crear una capa autonoma que active, observe y cierre el ciclo Cortex sin obligar al usuario a operar manualmente el flujo tripartito.

### Objetivos funcionales

1. Inyectar una meta-skill minima al inicio de sesion.
2. Detectar si la tarea requiere contexto, spec, implementacion o solo respuesta.
3. Ejecutar preflight Cortex con `cortex_sync_ticket` cuando corresponda.
4. Mantener la separacion Fast Track vs Deep Track.
5. Persistir una session note al finalizar una tarea significativa.
6. Reducir friccion diaria sin romper gobernanza.
7. Mantener presupuesto de tokens bajo y auditable.
8. Permitir futuras variantes por adicion de archivos.

### Objetivos de arquitectura

1. El modulo Autopilot debe ser independiente del CLI historico.
2. Cada extension futura debe poder agregarse mediante:
   - nuevo archivo de detector,
   - nuevo policy,
   - nuevo hook adapter,
   - nuevo renderer,
   - nuevo skill,
   - nuevo template,
   - o nuevo registry entry.
3. Ningun adapter IDE debe conocer detalles internos del servicio.
4. Ninguna policy debe escribir archivos directamente.
5. Ningun hook debe llamar servicios de memoria a mano: siempre entra por CLI o MCP tool.
6. El estado debe ser persistente en disco para sobrevivir procesos separados.

---

## 3. No Objetivos

Autopilot no debe:

1. Reemplazar `cortex-sync`, `cortex-SDDwork` ni `cortex-documenter`.
2. Forzar autonomia a usuarios que prefieren control manual.
3. Reescribir el MCP server completo.
4. Convertir todos los comandos actuales en headless.
5. Hacer full vault sync en cada cierre.
6. Leer todo el repositorio para construir contexto.
7. Llamar subagentes para tareas simples.
8. Guardar session notes inventando informacion no observada.
9. Agregar dependencias pesadas o servicios externos obligatorios.
10. Copiar Superpowers literalmente.
11. Crear branches automaticamente en MVP. El branching sigue gobernado por `cortex/git_policy.py`. Autopilot observa el branch actual pero no lo modifica.
12. Implementar un brainstorming completo previo a cada tarea. Cortex ya tiene el flujo tripartito (sync, work, document) que cumple esta funcion de forma mas estructurada.
13. Usar tags de urgencia en prompts (`EXTREMELY_IMPORTANT`, etc.) como mecanismo de control. Cortex tiene policies programaticas que son mas confiables que instrucciones de texto.

---

## 4. Filosofia de Diseno

### 4.1 Alternativas como contrato de producto

Cortex no debe tener un unico modo correcto de uso. Autopilot es una alternativa mas.

El usuario debe poder elegir:

```bash
cortex setup agent
cortex inject --ide cursor
cortex autopilot install --ide cursor
```

Y tambien debe poder desactivar:

```bash
cortex autopilot uninstall --ide cursor
cortex autopilot disable
```

### 4.2 Extension por archivo

Toda pieza que pueda cambiar por uso real debe ser conectable por registro.

Ejemplos:

- nuevo detector de tareas: agregar `cortex/autopilot/detectors/security.py`
- nuevo adapter: agregar `cortex/autopilot/adapters/copilot.py`
- nueva policy de presupuesto: agregar `cortex/autopilot/policies/strict_budget.py`
- nuevo renderer de session note: agregar `cortex/autopilot/renderers/security_session.py`
- nuevo evento de hook: agregar handler en `hooks/events.py`

El cambio ideal debe ser:

1. crear archivo,
2. registrarlo,
3. agregar test de contrato.

### 4.3 Servicio central, periferia fina

Los hooks, MCP tools y comandos CLI deben ser capas finas.

```text
Hook / MCP / CLI
    -> AutopilotService
        -> AgentMemory
        -> ContextEnricher
        -> SessionService
        -> SpecService
        -> StateStore
```

### 4.4 Presupuesto primero

Autopilot debe evitar el problema observado en Superpowers: workflows muy buenos pero potencialmente caros.

Reglas:

- bootstrap pequeno;
- skills completas solo bajo demanda;
- contexto compacto por defecto;
- `top_k` bajo;
- no full sync salvo instalacion, reparacion o comando explicito;
- session note basada en eventos observados;
- subagentes solo con umbral claro.

---

## 5. Diagnostico del Estado Actual

### 5.1 Componentes existentes reutilizables

| Area | Archivo actual | Uso en Autopilot |
|---|---|---|
| CLI | `cortex/cli/main.py` | Agregar subcomando `autopilot` aislado |
| Fachada memoria | `cortex/core.py` | Punto estable para memoria, spec, session |
| Specs | `cortex/services/spec_service.py` | Persistencia selectiva de specs |
| Sesiones | `cortex/services/session_service.py` | Persistencia selectiva de session notes |
| MCP | `cortex/mcp/server.py` | Exponer tools Autopilot |
| IDE adapters | `cortex/ide/adapters/*` | Base conceptual para adapters Autopilot |
| Prompts | `cortex/ide/prompts.py` | Lectura de skills/subagents desde layout |
| Workspace | `cortex/workspace/layout.py` | Resolver paths nuevos y legacy |
| Setup | `cortex/setup/cortex_workspace.py` | Generar assets iniciales |
| Contexto | `cortex/context_enricher/*` | Contexto compacto y budget-aware |
| Retrieval | `cortex/retrieval/hybrid_search.py` | RRF adaptativo |
| Docs | `cortex/documentation.py` | Render base de session/spec |

### 5.2 Brechas importantes

1. No hay estado persistente de ciclo de vida de una tarea.
2. MCP guarda `_called_tools` solo en memoria del proceso.
3. No hay grupo `cortex autopilot`.
4. No hay meta-skill `using-cortex`.
5. No hay hooks instalables por adapter.
6. `cortex-SDDwork` menciona delegacion, pero el MCP no expone actualmente tools publicas `cortex_delegate_task` y `cortex_delegate_batch`.
7. No hay cierre automatico si el agente no documenta.
8. No hay contrato de presupuesto por modo.

---

## 6. Arquitectura Objetivo

### 6.1 Vista de alto nivel

```text
Usuario
  |
  v
IDE / Agent Harness
  |
  | SessionStart / TaskStart / Stop
  v
Autopilot Hook Adapter
  |
  | cortex autopilot start/preflight/finish
  v
cortex.autopilot.cli
  |
  v
AutopilotService
  |
  +-- StateStore
  +-- DetectorRegistry
  +-- PolicyRegistry
  +-- ContextBudget
  +-- SessionBuilder
  +-- AgentMemory
        +-- ContextEnricher
        +-- SpecService
        +-- SessionService
```

### 6.1.1 Flowchart de decision unificado

Este diagrama muestra el camino completo desde que el usuario envia un mensaje hasta que Autopilot decide que hacer. Cada agente implementador debe poder seguir este flujo sin ambiguedad.

```text
Usuario envia mensaje
    |
    v
Autopilot habilitado? ──No──> Flujo manual normal (cortex-sync, etc.)
    |Yes
    v
session-start hook emite bootstrap (using-cortex-autopilot.md)
    |
    v
AutopilotService.start() → crea estado, asigna session_id
    |
    v
DetectorRegistry.detect(request)
    |
    |── question-only ──> responder directo (budget=0, sin preflight)
    |── ambiguous ──────> pedir clarificacion al usuario antes de continuar
    |── docs-only ──────> cortex_context(max_chars=1200) → implementar → finish
    |── fast-code ──────> cortex_sync_ticket(top_k=3) → implementar → checkpoint → finish
    |── deep-code ──────> cortex_create_spec → delegacion opcional → checkpoints → finish
    |── security ───────> igual que deep-code pero con policy HumanApprovalPolicy
    |
    v
PolicyRegistry.evaluate(state) en CADA transicion
    |
    |── budget excedido ────> degradar a fast-code o emitir warning
    |── docs requerida ─────> bloquear finish sin session note
    |── aprobacion humana ──> pedir confirmacion (modo assist o security)
    |── auto-checkpoint ────> si hay N archivos cambiados sin checkpoint, forzar
    |
    v
finish(auto=True/False)
    |
    v
SessionBuilder.render(state) → genera draft desde eventos observados
    |
    v
Self-review del draft (placeholder scan, consistencia, completitud)
    |
    v
cortex_save_session() → persiste session note → marca estado "documented"
```

Nota para el implementador: este flowchart debe poder ejecutarse completo sin intervencion humana en modo `autopilot`, con confirmaciones en modo `assist`, y solo con observacion en modo `observe`.

### 6.2 Estado persistente

Autopilot necesita un estado de sesion independiente del proceso:

```text
.cortex/
  run/
    autopilot/
      sessions/
        <session-id>.json
      events/
        <session-id>.jsonl
```

En legacy layout se resuelve con `WorkspaceLayout`.

### 6.3 Contrato de estado

Modelo propuesto:

```python
class AutopilotSessionState(BaseModel):
    schema_version: int = 1
    session_id: str
    project_root: str
    workspace_root: str
    created_at: datetime
    updated_at: datetime
    status: Literal[
        "started",
        "preflight_done",
        "implementation_seen",
        "documented",
        "finished",
        "failed",
    ]
    mode: Literal["observe", "assist", "autopilot"]
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
    budget: AutopilotBudgetSnapshot
    warnings: list[str] = []
```

Evento propuesto:

```python
class AutopilotEvent(BaseModel):
    timestamp: datetime
    session_id: str
    event_type: str
    source: Literal["cli", "mcp", "hook", "agent", "detector"]
    payload: dict[str, Any]
```

### 6.4 Modos de Autopilot

Autopilot no debe ser binario. Propongo tres modos:

| Modo | Comportamiento | Uso |
|---|---|---|
| `observe` | Observa, registra estado, no fuerza cierre | Diagnostico y adopcion inicial |
| `assist` | Inyecta meta-skill y sugiere/pide cierre | Usuario semi-guiado |
| `autopilot` | Preflight y cierre automaticos con politicas | Usuario que quiere abstraccion |

Default recomendado para primera release: `assist`.

---

## 7. Contratos Modulares

### 7.1 Detector

Los detectores clasifican la tarea, pero no ejecutan acciones.

```python
class AutopilotDetector(Protocol):
    name: str

    def detect(self, request: DetectionRequest) -> DetectionResult:
        ...
```

El contrato `DetectionRequest` debe contener al menos:

```python
class DetectionRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None
    session_state: AutopilotSessionState | None = None
```

El contrato `DetectionResult` debe contener:

```python
class DetectionResult(BaseModel):
    task_type: Literal[
        "question-only", "docs-only", "fast-code",
        "deep-code", "security", "ambiguous", "noop"
    ]
    confidence: float  # 0.0 a 1.0
    reason: str  # explicacion corta para el event log
    suggested_complexity: Literal["none", "fast", "deep"] = "none"
```

Detectores iniciales:

- `CodeChangeDetector` — detecta si la tarea implica cambios de codigo
- `DocsOnlyDetector` — detecta tareas puramente documentales
- `QuestionOnlyDetector` — detecta preguntas que no requieren cambios
- `SecuritySensitiveDetector` — detecta cambios en auth, crypto, permisos, secrets
- `LargeRefactorDetector` — detecta tareas que afectan muchos archivos o modulos
- `AmbiguousRequestDetector` — detecta requests vagos que necesitan clarificacion
- `NoopDetector` — fallback cuando ningun detector tiene confianza suficiente

#### 7.1.1 AmbiguousRequestDetector (detalle)

Este detector es critico para evitar que el agente ejecute preflight sobre una interpretacion incorrecta del request. Superpowers resuelve esto con un brainstorming completo; Cortex lo resuelve con un gate de calidad de input mas liviano.

Heuristicas para detectar ambiguedad:

- request con menos de 8 palabras significativas
- verbos vagos sin objeto concreto ("mejorar", "arreglar", "cambiar", "actualizar")
- sin mencion de archivos, modulos o funciones especificas
- sin criterio de aceptacion implicito

Comportamiento esperado segun modo:

| Modo | Accion ante request ambiguo |
|---|---|
| `observe` | Registra warning, no interviene |
| `assist` | Sugiere al agente que pida clarificacion antes de continuar |
| `autopilot` | Bloquea preflight y emite evento `clarification_needed` |

Implementacion sugerida:

```python
class AmbiguousRequestDetector(AutopilotDetector):
    name = "ambiguous_request"

    VAGUE_VERBS = {"mejorar", "arreglar", "cambiar", "actualizar", "fixear", "improve", "fix", "change", "update", "refactor"}
    MIN_WORDS = 8

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if not request.user_request:
            return DetectionResult(
                task_type="ambiguous", confidence=0.9,
                reason="No user request provided"
            )

        words = request.user_request.lower().split()
        has_vague_verb = any(w in self.VAGUE_VERBS for w in words)
        is_short = len(words) < self.MIN_WORDS
        has_file_ref = any(
            "." in w and w.split(".")[-1] in ("py", "ts", "js", "md", "yaml", "json")
            for w in words
        )

        if is_short and has_vague_verb and not has_file_ref:
            return DetectionResult(
                task_type="ambiguous", confidence=0.7,
                reason=f"Short request ({len(words)} words) with vague verb, no file references"
            )

        return DetectionResult(
            task_type="noop", confidence=0.0,
            reason="Request appears sufficiently specific"
        )
```

Extension futura:

```text
cortex/autopilot/detectors/performance.py
```

Se registra en:

```python
DetectorRegistry.register(PerformanceDetector())
```

#### 7.1.2 DetectorRegistry (detalle de resolucion)

Cuando multiples detectores retornan resultados, el registry debe:

1. Ejecutar todos los detectores registrados.
2. Filtrar los que retornaron `confidence > 0.3`.
3. Si `SecuritySensitiveDetector` tiene confianza > 0.5, toma prioridad.
4. Si `AmbiguousRequestDetector` tiene confianza > 0.6, bloquea antes de cualquier otro.
5. En caso contrario, usar el detector con mayor `confidence`.
6. Si hay empate, preferir el mas conservador (el que asigna mayor complejidad).

### 7.2 Policy

Las policies deciden si se puede avanzar. Se evaluan en CADA transicion de estado.

```python
class AutopilotPolicy(Protocol):
    name: str

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        ...
```

El contrato `PolicyDecision` debe contener:

```python
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None
```

Policies iniciales:

- `BudgetPolicy` — bloquea si chars inyectados superan el limite del profile
- `DocumentationRequiredPolicy` — bloquea finish si no hay session note
- `SpecRequiredPolicy` — requiere spec para deep-code
- `NoExternalMemoryPolicy` — prohibe que el agente use memoria fuera de Cortex
- `NoFullSyncByDefaultPolicy` — bloquea sync-vault salvo excepciones
- `HumanApprovalPolicy` — requiere confirmacion humana para tareas security o deep
- `AutoCheckpointPolicy` — fuerza checkpoint si hay muchos cambios sin registrar

#### 7.2.1 AutoCheckpointPolicy (detalle)

Superpowers descubrio que los agentes se olvidan de hacer checkpoints intermedios. Esta policy lo resuelve programaticamente.

Reglas:

- Si pasaron mas de 10 minutos desde el ultimo checkpoint Y hay archivos cambiados en `git diff --stat`, emitir warning.
- Si `git diff --stat` muestra mas de 5 archivos cambiados sin checkpoint, forzar checkpoint en modo `autopilot` o sugerir en modo `assist`.
- En modo `observe`, solo registrar el evento sin intervenir.

Implementacion sugerida:

```python
class AutoCheckpointPolicy(AutopilotPolicy):
    name = "auto_checkpoint"
    MAX_FILES_WITHOUT_CHECKPOINT = 5
    MAX_MINUTES_WITHOUT_CHECKPOINT = 10

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        if not state.checkpoints:
            minutes = (datetime.now() - state.created_at).total_seconds() / 60
        else:
            last = state.checkpoints[-1]
            minutes = (datetime.now() - last.timestamp).total_seconds() / 60

        files_since = len(state.changed_files) - self._files_at_last_checkpoint(state)

        if files_since > self.MAX_FILES_WITHOUT_CHECKPOINT:
            return PolicyDecision(
                allowed=False,
                reason=f"{files_since} files changed without checkpoint",
                action="block" if state.mode == "autopilot" else "warn",
            )
        if minutes > self.MAX_MINUTES_WITHOUT_CHECKPOINT and files_since > 0:
            return PolicyDecision(
                allowed=True,
                reason=f"{minutes:.0f}min since last checkpoint, {files_since} files changed",
                action="warn",
            )
        return PolicyDecision(allowed=True, reason="ok", action="proceed")
```

### 7.3 Renderer

Los renderers producen texto, no escriben archivos.

```python
class SessionRenderer(Protocol):
    name: str

    def render(self, state: AutopilotSessionState) -> SessionDraft:
        ...
```

El contrato `SessionDraft` debe contener:

```python
class SessionDraft(BaseModel):
    title: str
    body: str  # markdown formateado
    confidence: Literal["high", "medium", "auto-draft"]
    warnings: list[str] = []  # problemas detectados durante render
    source_events: int  # cuantos eventos se usaron para generar
```

Renderers iniciales:

- `MinimalSessionRenderer` — titulo, resumen, archivos. Para tareas simples.
- `ImplementationSessionRenderer` — cambios, decisiones, archivos, spec ref. Para fast-code y deep-code.
- `DocsOnlySessionRenderer` — documentos creados/modificados. Para docs-only.
- `FallbackDraftRenderer` — genera draft seguro con status `auto-draft` cuando faltan datos.

#### 7.3.1 Self-review automatizado del draft

Inspirado en el patron de "Spec Self-Review" de Superpowers (skill `brainstorming`). Antes de que `finish()` persista la session note, el `SessionBuilder` debe ejecutar un self-review del draft generado:

1. **Placeholder scan:** Buscar "TBD", "TODO", secciones vacias, o textos genericos.
2. **Consistencia interna:** El titulo coincide con el contenido? Los archivos listados son los mismos que los eventos registraron?
3. **Completitud:** Si hubo eventos de tipo `checkpoint`, estan reflejados en la nota?
4. **Evidencia:** Si hay afirmaciones de "tests pasan" o "build exitoso", hay un evento de verificacion que lo respalde?

Si el self-review encuentra problemas:
- En modo `autopilot`: corregir automaticamente lo que se pueda, marcar el resto como `auto-draft`.
- En modo `assist`: listar los problemas al agente y pedir correccion.
- En modo `observe`: registrar los problemas como warnings sin bloquear.

Implementacion sugerida:

```python
def self_review(draft: SessionDraft, state: AutopilotSessionState) -> SessionDraft:
    warnings = list(draft.warnings)

    # Placeholder scan
    for marker in ["TBD", "TODO", "FIXME", "[pendiente]"]:
        if marker.lower() in draft.body.lower():
            warnings.append(f"Placeholder found: {marker}")

    # Completitud de archivos
    files_in_body = set()  # parsear del body
    files_in_state = set(state.changed_files)
    missing = files_in_state - files_in_body
    if missing:
        warnings.append(f"Files in state but not in draft: {missing}")

    # Evidencia de verificacion
    has_success_claim = any(
        w in draft.body.lower()
        for w in ["tests pass", "build exitoso", "linter clean", "verificado"]
    )
    has_verification_event = any(
        e.event_type == "verification" for e in state.events
    )
    if has_success_claim and not has_verification_event:
        warnings.append("Success claim without verification event")
        draft.confidence = "auto-draft"

    draft.warnings = warnings
    return draft
```

### 7.4 Hook Adapter

Cada harness tiene un adapter propio.

```python
class AutopilotHookAdapter(Protocol):
    name: str
    supported_events: set[str]

    def install(self, project_root: Path, config: AutopilotConfig) -> list[Path]:
        ...

    def uninstall(self, project_root: Path) -> list[Path]:
        ...

    def emit_session_start(self, state: AutopilotSessionState, bootstrap: str) -> str:
        """Retorna JSON formateado segun el harness."""
        ...
```

#### 7.4.1 Contrato de output del hook session-start

El hook `session-start` es el punto critico de integracion. Si cada adapter emite un formato distinto, la interoperabilidad se rompe. El output debe seguir este contrato:

```python
class HookSessionStartOutput(BaseModel):
    """Lo que emite session-start por stdout como JSON."""
    session_id: str
    mode: Literal["observe", "assist", "autopilot"]
    bootstrap_content: str  # contenido de using-cortex-autopilot.md
    budget_profile: str  # "question_only" | "fast_code" | etc.
    available_tools: list[str]  # tools MCP disponibles
    cortex_version: str
```

Pero el JSON final difiere por plataforma. Superpowers descubrio (tras muchos bugs) que cada harness espera un wrapper distinto:

```python
def format_for_platform(output: HookSessionStartOutput) -> str:
    """Formatea el output segun la plataforma detectada."""
    payload = output.model_dump_json()

    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        # Cursor espera snake_case top-level
        return json.dumps({"additional_context": payload})
    elif os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
        # Claude Code espera nested hookSpecificOutput
        return json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": payload
            }
        })
    else:
        # Copilot CLI, OpenCode, y otros: SDK standard
        return json.dumps({"additionalContext": payload})
```

Nota para el implementador: detectar la plataforma por variables de entorno (`CURSOR_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `COPILOT_CLI`). Testear en Windows con wrapper `.cmd`.

Adapters iniciales:

- `ClaudeCodeAutopilotAdapter`
- `CursorAutopilotAdapter`
- `OpenCodeAutopilotAdapter`
- `CodexPluginAutopilotAdapter`

No deben vivir mezclados con `cortex/ide/adapters` al principio. Se pueden apoyar en utilidades compartidas, pero Autopilot necesita evolucionar sin romper la inyeccion IDE actual.

---

## 8. Diseno del CLI

### 8.1 Nuevo grupo

Crear:

```text
cortex/autopilot/cli.py
```

Y en `cortex/cli/main.py` solo:

```python
from cortex.autopilot.cli import app as autopilot_app
app.add_typer(autopilot_app, name="autopilot")
```

Esa debe ser la unica conexion inicial con el CLI historico.

### 8.2 Comandos propuestos

```bash
cortex autopilot status
cortex autopilot init
cortex autopilot enable
cortex autopilot disable
cortex autopilot install --ide cursor
cortex autopilot uninstall --ide cursor
cortex autopilot start --mode assist --json
cortex autopilot preflight --session-id <id> --request "..."
cortex autopilot checkpoint --session-id <id> --summary "..."
cortex autopilot finish --session-id <id> --auto
cortex autopilot doctor
```

### 8.3 Reglas CLI

1. Todos los comandos deben aceptar `--project-root`.
2. Todos los comandos que use un hook deben aceptar `--json`.
3. Ningun comando debe preguntar interactivamente si `--json` o `--auto`.
4. `finish --auto` debe guardar draft seguro si faltan datos.
5. `doctor` debe explicar que adapter esta instalado y que hooks estan activos.

---

## 9. Diseno MCP

### 9.1 Tools nuevas

Agregar tools bajo el prefijo Cortex:

- `cortex_autopilot_start`
- `cortex_autopilot_preflight`
- `cortex_autopilot_checkpoint`
- `cortex_autopilot_finish`
- `cortex_autopilot_status`

### 9.2 Contrato

Las MCP tools deben delegar a `AutopilotService`, igual que el CLI.

No deben duplicar logica.

### 9.3 Relacion con tools existentes

Autopilot usa internamente o instruye al agente a usar:

- `cortex_sync_ticket`
- `cortex_context`
- `cortex_create_spec`
- `cortex_save_session`
- `cortex_sync_vault`

Pero el usuario no debe tener que recordar esos nombres.

### 9.4 Gate tecnico recomendado

Agregar validacion persistente:

- `cortex_create_spec` debe poder verificar `StateStore` si hay `session_id`.
- `cortex_save_session` debe marcar el estado como `documented`.
- Si no hay `session_id`, mantiene comportamiento actual.

Esto conserva compatibilidad.

### 9.5 Contrato de delegacion con two-stage review

Si en el futuro se implementan `cortex_delegate_task` / `cortex_delegate_batch` (ver Fase 9), el resultado de un subagente NO debe aceptarse directamente. Superpowers usa un protocolo de "two-stage review" probado:

```text
Subagente completa tarea
    |
    v
Stage 1: Spec compliance (automatizado)
    - El diff del subagente coincide con la spec?
    - Se modificaron solo los archivos esperados?
    - Si FALLA: rechazar y re-despachar
    |
    v
Stage 2: Quality review (por el agente orquestador)
    - Revision de calidad del codigo
    - Tests pasan?
    - Si FALLA: rechazar con feedback especifico
    |
    v
Aceptar y registrar checkpoint
```

El contrato de `cortex_get_task_result` debe incluir:

```python
class DelegationResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "rejected"]
    diff_summary: str  # output de git diff --stat
    files_changed: list[str]
    tests_passed: bool | None = None  # None si no se corrieron
    spec_path: str | None = None  # referencia a la spec usada
    rejection_reason: str | None = None
```

Importante: si no hay runtime de subagente disponible en el harness, Autopilot debe degradar a Fast Track o pedir confirmacion, nunca fallar silenciosamente.

---

## 10. Meta-skill `using-cortex-autopilot`

### 10.1 Objetivo

Ser el bootstrap minimo, inspirado en Superpowers, pero ajustado a Cortex.

No debe cargar todo el metodo completo. La meta-skill se inyecta via hook de session-start y es lo primero que el agente lee.

### 10.2 Contenido esperado

Archivo:

```text
.cortex/skills/using-cortex-autopilot.md
```

Debe contener:

1. Prioridad de instrucciones (usuario > Autopilot > sistema).
2. Regla de no usar memoria externa.
3. Criterios para activar preflight.
4. Criterios para evitar preflight.
5. Presupuesto de contexto.
6. Regla de documentacion final.
7. Uso de Fast Track por defecto.
8. Uso de Deep Track solo con umbral.
9. Como cerrar si una tool falla.
10. Guard anti-racionalizacion (ver 10.4).
11. Regla de verificacion antes de completar (ver 10.5).

### 10.3 Principio de tokens

La meta-skill debe ser menor a 1500 palabras en la primera version.

Las skills completas se cargan bajo demanda:

- `cortex-sync`
- `cortex-SDDwork`
- `cortex-documenter`

### 10.4 Guard anti-racionalizacion

Superpowers descubrio (tras 440+ commits de iteracion) que sin una tabla explicita de racionalizaciones que el agente usa para saltarse el flujo, el agente se las salta. La meta-skill DEBE incluir esta tabla.

Contenido obligatorio en `using-cortex-autopilot.md`:

```markdown
## Senales de que estas saltando el flujo

Si te encontras pensando alguna de estas cosas, PARA. Estas racionalizando.

| Pensamiento | Realidad |
|-------------|----------|
| "Es una pregunta simple, no necesito preflight" | Si modifica archivos, necesita al menos un checkpoint |
| "Ya se la respuesta, no busco contexto" | El contexto tiene informacion que no recordas. Usa cortex_context |
| "Documento despues" | El cierre automatico no inventa. Si no documentas, queda auto-draft |
| "No vale la pena una session note" | Si hubo cambios observados, vale la pena |
| "Cortex ya tiene toda la info" | Verifica con cortex_context antes de asumir |
| "Es solo un fix rapido" | Los fix rapidos sin contexto son los que mas rompen |
| "Puedo saltar el checkpoint" | Si cambiaste archivos, el checkpoint protege tu trabajo |
| "No necesito verificar, se que funciona" | Ejecuta el comando de verificacion. Confianza != evidencia |
| "Esto es muy simple para el flujo completo" | Lo simple con proceso es rapido. Lo simple sin proceso se complica |
```

Esta tabla NO es prosa decorativa. Es codigo de comportamiento. Los agentes la leen y la usan como checklist interna.

### 10.5 Regla de verificacion antes de completar

Inspirado en la skill `verification-before-completion` de Superpowers, que es su mecanismo anti-alucinacion mas efectivo.

Contenido obligatorio en `using-cortex-autopilot.md`:

```markdown
## Regla de verificacion

Antes de afirmar que un cambio funciona:

1. Identifica que comando prueba tu afirmacion (test, build, lint).
2. Ejecuta el comando COMPLETO (no parcial, no de memoria).
3. Lee la salida completa. Verifica exit code.
4. Solo entonces afirma el resultado.
5. Si no ejecutaste verificacion, escribi "No verificado" en el checkpoint.

NO es aceptable:
- Decir "deberia funcionar" sin haber corrido tests
- Decir "listo" sin verificar que compila
- Confiar en el reporte de un subagente sin verificar el diff
- Usar "probablemente", "seguramente" o "deberia" para describir estado
```

### 10.6 Prioridad de instrucciones

Contenido obligatorio en `using-cortex-autopilot.md`:

```markdown
## Prioridad de instrucciones

1. Instrucciones explicitas del usuario (AGENT.md, system-prompt.md, requests directos) — maxima prioridad
2. Skills de Cortex Autopilot — sobreescriben comportamiento default del sistema
3. Prompt de sistema del IDE — minima prioridad

Si el usuario dice "no uses preflight" y Autopilot dice "siempre usa preflight", segui al usuario. El usuario tiene el control.
```

---

## 11. Presupuesto de Tokens

### 11.1 Presupuestos iniciales

| Caso | Max items | Max chars | Embeddings |
|---|---:|---:|---|
| question-only | 0 | 0 | no |
| docs-only | 3 | 1200 | keyword primero |
| fast code task | 5 | 2000 | si |
| deep task | 8 | 3500 | si |
| finish auto | n/a | 2000 | no full search |

### 11.2 Reglas

1. `cortex_context` debe llamarse con formato compacto por defecto.
2. `cortex_sync_ticket` debe usar `top_k` bajo por defecto en Autopilot.
3. El cierre no debe reconsultar todo el vault.
4. El documenter no debe leer todos los contextos acumulados si Autopilot ya tiene eventos estructurados.
5. No se debe ejecutar full `sync-vault` salvo:
   - instalacion,
   - reparacion,
   - comando explicito,
   - o policy enterprise que lo requiera.

### 11.3 Observabilidad de presupuesto

`AutopilotSessionState` debe guardar:

- chars inyectados,
- cantidad de items,
- tools llamadas,
- si hubo embeddings,
- si hubo subagentes,
- motivo de Deep Track.

---

## 12. Plan por Fases

## Fase 0 - Contrato y Cimientos

### Objetivo

Definir el contrato estable antes de tocar runtime.

### Archivos a crear

```text
docs/autopilot/README.md
docs/autopilot/contracts.md
docs/autopilot/testing-strategy.md
```

### Archivos a revisar

```text
cortex/cli/main.py
cortex/mcp/server.py
cortex/workspace/layout.py
cortex/setup/cortex_workspace.py
cortex/ide/adapters/*
```

### Entregables

- Contrato de estado.
- Contrato de eventos.
- Contrato de adapters.
- Contrato de presupuesto.
- Matriz de compatibilidad IDE.

### Checklist

- [ ] Documentar `AutopilotSessionState`.
- [ ] Documentar `AutopilotEvent`.
- [ ] Documentar modos `observe`, `assist`, `autopilot`.
- [ ] Documentar extension points.
- [ ] Documentar no objetivos.

### Gate de salida

- El equipo puede implementar Fase 1 sin decidir arquitectura nueva.
- No hay contradicciones con `WorkspaceLayout`.
- El plan mantiene el CLI actual como modo valido.

---

## Fase 1 - Skeleton del Modulo

### Objetivo

Crear el paquete `cortex.autopilot` sin comportamiento invasivo.

### Archivos a crear

```text
cortex/autopilot/__init__.py
cortex/autopilot/models.py
cortex/autopilot/config.py
cortex/autopilot/state_store.py
cortex/autopilot/registry.py
cortex/autopilot/errors.py
tests/unit/autopilot/test_models.py
tests/unit/autopilot/test_state_store.py
```

### Responsabilidades

`models.py`

- Define estado, eventos, checkpoints, budget snapshot, decisions.

`config.py`

- Carga config opcional desde `.cortex/autopilot.yaml`.
- Provee defaults si no existe.

`state_store.py`

- Lee/escribe JSON y JSONL.
- Usa `WorkspaceLayout`.
- Operaciones atomicas cuando sea posible.

`registry.py`

- Registro de detectors, policies, renderers y adapters.

### Criterios de diseno

- No importar MCP.
- No importar Typer.
- No importar adapters IDE.
- No llamar `AgentMemory` todavia.

### Checklist

- [ ] `AutopilotSessionState` serializa y deserializa.
- [ ] `StateStore.create_session()` genera un id estable.
- [ ] `StateStore.append_event()` escribe JSONL.
- [ ] `StateStore.load()` falla con error claro si no existe.
- [ ] Tests unitarios cubren new layout y legacy layout.

### Gate de salida

- `pytest tests/unit/autopilot` pasa.
- El modulo puede importarse sin inicializar Chroma ni ONNX.

---

## Fase 2 - Servicio de Ciclo de Vida

### Objetivo

Crear `AutopilotService` como unica API de negocio.

### Archivos a crear

```text
cortex/autopilot/service.py
cortex/autopilot/lifecycle.py
cortex/autopilot/detectors/base.py
cortex/autopilot/detectors/default.py
cortex/autopilot/policies/base.py
cortex/autopilot/policies/default.py
cortex/autopilot/context_budget.py
tests/unit/autopilot/test_service.py
tests/unit/autopilot/test_detectors.py
tests/unit/autopilot/test_policies.py
```

### API propuesta

```python
class AutopilotService:
    def start(self, request: StartRequest) -> StartResult: ...
    def preflight(self, request: PreflightRequest) -> PreflightResult: ...
    def checkpoint(self, request: CheckpointRequest) -> CheckpointResult: ...
    def finish(self, request: FinishRequest) -> FinishResult: ...
    def status(self, session_id: str | None = None) -> StatusResult: ...
```

### Reglas

- `start()` crea estado, no busca memoria pesada.
- `preflight()` decide si necesita contexto.
- `checkpoint()` solo agrega informacion observada.
- `finish()` decide si guardar session note.
- Todas las decisiones deben dejar evento.

### Checklist

- [ ] `start()` no carga ONNX.
- [ ] `preflight()` puede operar sin user_request y dejar warning.
- [ ] `checkpoint()` agrega archivos, comandos, tools y resumen.
- [ ] `finish(auto=True)` genera draft si falta documentacion.
- [ ] Policies pueden bloquear o degradar modo.

### Gate de salida

- Servicio testeado con memoria fake.
- Ningun test de esta fase requiere Chroma real.

---

## Fase 3 - CLI Headless

### Objetivo

Agregar `cortex autopilot` sin alterar los comandos actuales.

### Archivos a crear

```text
cortex/autopilot/cli.py
tests/unit/autopilot/test_cli.py
```

### Archivo a tocar

```text
cortex/cli/main.py
```

Solo para registrar:

```python
app.add_typer(autopilot_app, name="autopilot")
```

### Comandos

```bash
cortex autopilot start
cortex autopilot preflight
cortex autopilot checkpoint
cortex autopilot finish
cortex autopilot status
cortex autopilot doctor
```

### Checklist

- [ ] Todos aceptan `--project-root`.
- [ ] Todos aceptan `--json` si son consumidos por hooks.
- [ ] `start --json` devuelve `session_id`.
- [ ] `finish --auto --json` devuelve path o razon de no-op.
- [ ] `doctor` no modifica archivos.

### Gate de salida

- El CLI viejo sigue pasando sus tests.
- `cortex autopilot status --json` funciona en repo sin hooks instalados.

---

## Fase 4 - Session Builder y Persistencia Automatica

### Objetivo

Construir session notes confiables desde estado observado.

### Archivos a crear

```text
cortex/autopilot/session_builder.py
cortex/autopilot/renderers/base.py
cortex/autopilot/renderers/minimal.py
cortex/autopilot/renderers/implementation.py
cortex/autopilot/renderers/docs_only.py
tests/unit/autopilot/test_session_builder.py
```

### Integracion

Usar `AgentMemory.save_session_note()` o `SessionService` por la fachada.

### Reglas de seguridad epistemica

1. Si no se observo un cambio, no se declara como realizado.
2. Si no se ejecutaron tests, se escribe "No registrado".
3. Si no hay spec, se escribe "No se detecto spec asociada".
4. Si el cierre es automatico y falta contexto, status `auto-draft`.

### Checklist

- [ ] Render minimo con titulo, resumen, archivos y eventos.
- [ ] Render implementacion con cambios y decisiones.
- [ ] Render docs-only para tareas de documentacion.
- [ ] `finish()` marca estado `documented`.
- [ ] `finish()` no duplica session notes si ya existe `session_note_path`.

### Gate de salida

- Session note util con cero invencion.
- Indexacion selectiva sigue siendo el mecanismo default.

---

## Fase 5 - MCP Tools Autopilot

### Objetivo

Exponer Autopilot al agente por MCP, sin duplicar logica.

### Archivos a crear

```text
cortex/autopilot/mcp_tools.py
tests/unit/autopilot/test_mcp_tools.py
```

### Archivo a tocar

```text
cortex/mcp/server.py
```

Cambio esperado:

- importar definiciones desde `cortex.autopilot.mcp_tools`;
- registrar tools;
- delegar llamadas a `AutopilotService`.

### Tools

```text
cortex_autopilot_start
cortex_autopilot_preflight
cortex_autopilot_checkpoint
cortex_autopilot_finish
cortex_autopilot_status
```

### Checklist

- [ ] Tools aparecen en `list_tools`.
- [ ] Tools devuelven texto compacto y JSON si conviene.
- [ ] Errores se registran como eventos.
- [ ] `cortex_save_session` puede marcar estado si recibe `session_id`.

### Gate de salida

- MCP server sigue soportando todas las tools anteriores.
- Autopilot no rompe `cortex_create_spec` sin session id.

---

## Fase 6 - Meta-skill y Assets de Workspace

### Objetivo

Instalar la meta-skill minima y prompts asociados.

### Archivos a crear

```text
cortex/autopilot/skills/using-cortex-autopilot.md
cortex/autopilot/skills/cortex-autopilot-finish.md
tests/unit/autopilot/test_skills_assets.py
```

### Archivos a tocar

```text
cortex/setup/cortex_workspace.py
cortex/ide/prompts.py
```

### Regla importante

No cambiar las skills actuales en esta fase salvo referencia opcional.

### Checklist

- [ ] `using-cortex-autopilot` se instala solo si Autopilot esta habilitado.
- [ ] El setup normal sin Autopilot queda igual.
- [ ] `build_all_prompts()` no carga Autopilot por defecto.
- [ ] Hay una funcion separada `build_autopilot_prompts()`.

### Gate de salida

- El usuario puede instalar skills Autopilot sin afectar perfiles manuales.

---

## Fase 7 - Hook Adapters

### Objetivo

Instalar hooks por harness de forma segura y reversible.

### Archivos a crear

```text
cortex/autopilot/adapters/base.py
cortex/autopilot/adapters/registry.py
cortex/autopilot/adapters/platform_detect.py
cortex/autopilot/adapters/claude_code.py
cortex/autopilot/adapters/cursor.py
cortex/autopilot/adapters/opencode.py
cortex/autopilot/adapters/codex.py
cortex/autopilot/hooks/session_start.py
cortex/autopilot/hooks/session_finish.py
cortex/autopilot/hooks/run_hook.cmd
cortex/autopilot/hooks/run_hook.sh
tests/unit/autopilot/test_adapters.py
tests/unit/autopilot/test_platform_detect.py
```

### Detalle: `platform_detect.py`

Este modulo encapsula la deteccion de plataforma por variables de entorno. Es usado por todos los adapters y por el hook de session-start.

```python
from enum import Enum
import os

class Platform(Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    COPILOT_CLI = "copilot-cli"
    OPENCODE = "opencode"
    CODEX = "codex"
    UNKNOWN = "unknown"

def detect_platform() -> Platform:
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return Platform.CURSOR
    if os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
        return Platform.CLAUDE_CODE
    if os.environ.get("COPILOT_CLI"):
        return Platform.COPILOT_CLI
    # Agregar deteccion para OpenCode y Codex cuando se definan sus vars
    return Platform.UNKNOWN
```

### Detalle: `run_hook.cmd` (wrapper Windows)

Superpowers tiene un wrapper probado para resolver el problema bash-en-Windows. Cortex debe tener su propio wrapper Python que funcione cross-platform sin depender de bash:

```cmd
@echo off
python -m cortex.autopilot.hooks.%1 %2 %3 %4 %5
```

El equivalente `run_hook.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python -m cortex.autopilot.hooks."$1" "${@:2}"
```

Nota para el implementador: usar Python como runtime del hook en lugar de bash puro. Esto garantiza compatibilidad Windows sin `WSL` ni `Git Bash`.

### Comandos relacionados

```bash
cortex autopilot install --ide claude-code
cortex autopilot install --ide cursor
cortex autopilot uninstall --ide cursor
```

### Inspiracion de Superpowers

Copiar el patron conceptual:

- wrapper cross-platform;
- hook de session start;
- salida JSON de additional context con formato por plataforma (ver 7.4.1);
- bootstrap minimo.

No copiar:

- contenido exacto;
- comportamiento que fuerce skills en cada micro-paso;
- dependencia de un solo harness.

### Checklist

- [ ] Cada adapter declara eventos soportados.
- [ ] Instalacion crea backup antes de modificar config.
- [ ] Uninstall remueve solo bloques Autopilot.
- [ ] Windows funciona con wrapper `.cmd` (sin dependencia de bash).
- [ ] Si falta Python en PATH, falla con error claro.
- [ ] Hook session-start emite JSON segun contrato 7.4.1.
- [ ] `platform_detect.py` tiene tests para cada variable de entorno.
- [ ] Hook session-start incluye contenido de `using-cortex-autopilot.md`.

### Gate de salida

- Al menos un adapter piloto funciona end-to-end.
- Los perfiles IDE actuales siguen intactos.
- Output JSON validado contra `HookSessionStartOutput` schema.

---

## Fase 8 - Integracion con Contexto y Budget

### Objetivo

Hacer que Autopilot use contexto con presupuesto agresivo y medible.

### Archivos a crear

```text
cortex/autopilot/context.py
cortex/autopilot/budget_profiles.py
tests/unit/autopilot/test_context_budget.py
```

### Integracion

Usar:

- `AgentMemory.enrich()`
- `ContextEnricherConfig`
- `RetrievalResult.to_prompt(max_chars=...)`

### Profiles

```text
question_only
docs_only
fast_code
deep_code
finish_only
```

### Checklist

- [ ] `question_only` no llama embeddings.
- [ ] `fast_code` limita `max_chars`.
- [ ] `deep_code` requiere motivo de complejidad.
- [ ] `finish_only` no hace retrieval pesado.
- [ ] Estado guarda budget snapshot.

### Gate de salida

- Se puede explicar cuanto contexto inyecto Autopilot y por que.

---

## Fase 9 - Delegacion y Deep Track Real

### Objetivo

Cerrar la inconsistencia actual de delegacion.

### Archivos a revisar

```text
cortex/mcp/server.py
.cortex/skills/cortex-SDDwork.md
cortex/setup/cortex_workspace.py
tests/integration/mcp/test_server.py
```

### Opcion A

Exponer tools MCP:

```text
cortex_delegate_task
cortex_delegate_batch
cortex_get_task_result
```

### Opcion B

Quitar esas referencias de Autopilot y depender solo de delegacion nativa de cada IDE.

### Recomendacion

Opcion A, pero marcada como experimental.

### Two-stage review obligatorio

Cualquier resultado de delegacion debe pasar por el protocolo two-stage review definido en la seccion 9.5. El servicio `AutopilotService` debe:

1. Recibir el `DelegationResult` del subagente.
2. Ejecutar Stage 1 (spec compliance) automaticamente.
3. Si pasa, el agente orquestador ejecuta Stage 2 (quality review).
4. Solo si ambos pasan, se registra checkpoint y se acepta.
5. Si falla, se rechaza con `rejection_reason` y se re-despacha o se degrada a manual.

### Checklist

- [ ] La skill y el MCP dicen lo mismo.
- [ ] Si no hay runtime de subagente, Autopilot degrada a Fast Track o pide confirmacion.
- [ ] Deep Track registra motivo y costo.
- [ ] `DelegationResult` incluye diff, archivos, y resultado de tests.
- [ ] Resultados rechazados quedan registrados en el event log con motivo.

### Gate de salida

- No hay instrucciones que pidan tools inexistentes.

---

## Fase 10 - Doctor, Observabilidad y Auditoria

### Objetivo

Hacer visible el estado de Autopilot y detectar conflictos.

### Archivos a crear

```text
cortex/autopilot/doctor.py
cortex/autopilot/reporting.py
tests/unit/autopilot/test_doctor.py
```

### Comandos

```bash
cortex autopilot doctor
cortex autopilot status --session-id <id>
cortex autopilot report --last 10
```

### Doctor debe validar

- config presente o defaults;
- hooks instalados;
- adapter reconocido;
- MCP tools disponibles;
- run dir escribible;
- skills instaladas;
- ultimo cierre documentado;
- warnings de presupuesto;
- **conflicto con Superpowers** (ver detalle abajo);
- **rotacion de JSONL de eventos** (ver detalle abajo).

### Deteccion de conflicto con Superpowers

Si un usuario tiene Superpowers instalado simultaneamente con Cortex Autopilot, ambos van a intentar inyectar bootstraps al inicio de sesion, causando conflictos e inflacion de tokens.

Doctor debe detectar:

```python
def check_superpowers_conflict(project_root: Path) -> str | None:
    """Detecta si Superpowers esta instalado en el mismo proyecto."""
    indicators = [
        project_root / ".claude" / "plugins" / "superpowers",
        project_root / ".cursor" / "plugins" / "superpowers",
    ]
    # Tambien verificar por variable de entorno
    if os.environ.get("CLAUDE_PLUGIN_ROOT", "").endswith("superpowers"):
        return "Superpowers detected via CLAUDE_PLUGIN_ROOT env var"
    for path in indicators:
        if path.exists():
            return f"Superpowers detected at {path}"
    return None
```

Si se detecta, doctor debe emitir:

```text
⚠ WARNING: Superpowers plugin detected alongside Cortex Autopilot.
  Both inject bootstraps at session start, which may cause:
  - Duplicate instructions
  - Token budget inflation
  - Conflicting workflow rules
  
  Recommendation: Disable one of the two plugins.
  Run `cortex autopilot uninstall` or remove Superpowers.
```

### Rotacion de JSONL de eventos

El archivo `.cortex/run/autopilot/events/<session-id>.jsonl` puede crecer sin limite en sesiones largas. Doctor debe verificar:

- Si algun archivo JSONL supera 5MB, emitir warning.
- `StateStore` debe implementar rotacion: archivar sesiones de mas de 30 dias.
- Rotacion manual: `cortex autopilot cleanup --older-than 30d`.

### Gate de salida

- Un usuario puede diagnosticar por que Autopilot no se activo.
- Conflictos con Superpowers se detectan automaticamente.

---

## Fase 11 - Tests End-to-End y Evals

### Objetivo

Probar comportamiento real con tareas representativas.

### Archivos a crear

```text
tests/e2e/scenarios/test_autopilot_basic.py
tests/e2e/scenarios/test_autopilot_finish.py
tests/e2e/scenarios/test_autopilot_budget.py
docs/autopilot/evals.md
```

### Escenarios minimos

1. Pregunta simple: no crea spec ni session.
2. Cambio simple: Fast Track, session auto.
3. Docs-only: session docs-only.
4. Tarea compleja: Deep Track sugerido o ejecutado segun modo.
5. Cierre sin datos: draft seguro.
6. Tool failure: warning y no invencion.
7. Uninstall: deja config limpia.

### Metricas

- session note creada cuando corresponde;
- no session note cuando no corresponde;
- chars de contexto;
- cantidad de retrievals;
- cantidad de subagentes;
- tiempo de startup;
- numero de archivos tocados por instalacion.

### Gate de salida

- Acceptance test documentado por harness piloto.
- Evals muestran que no hay consumo excesivo en casos simples.

---

## Fase 12 - Packaging y Marketplace

### Objetivo

Preparar distribucion como plugin oficial. Los formatos de plugin deben ser compatibles con los estandares de facto del ecosistema.

### Archivos a crear

```text
.codex-plugin/plugin.json
.claude-plugin/plugin.json
.cursor-plugin/plugin.json
docs/autopilot/marketplace.md
```

### Formato de `plugin.json`

Superpowers (184k stars) ha establecido formatos de plugin que son estandares de facto. El `plugin.json` de Cortex Autopilot debe seguir la misma estructura para que usuarios de Superpowers puedan adoptar Cortex sin friccion:

```json
{
  "name": "cortex-autopilot",
  "version": "0.1.0",
  "description": "Autonomous workflow layer for Cortex cognitive memory",
  "author": "DevSecDocOps",
  "homepage": "https://github.com/MachuaninEzequiel/Cortex",
  "skills": {
    "directory": "skills"
  },
  "hooks": {
    "directory": "hooks"
  },
  "requires": {
    "python": ">=3.10",
    "cortex": ">=2.0.0"
  }
}
```

Nota para el implementador: verificar que el formato actual de Superpowers no haya cambiado al momento de implementar esta fase. Los formatos evolucionan.

### Regla

El plugin debe instalar Autopilot, no reemplazar Cortex base.

### Checklist

- [ ] Manifest incluye metadata clara.
- [ ] Skills apuntan a carpeta Autopilot.
- [ ] Hooks usan wrapper Python cross-platform.
- [ ] Documentar install/uninstall.
- [ ] Versionar compatibilidad por harness.
- [ ] Formato compatible con ecosistema Superpowers.

### Gate de salida

- Instalacion limpia en workspace nuevo.
- Desinstalacion limpia.
- Sin dependencia externa obligatoria.

---

## 13. Roadmap Recomendado

### Milestone A - MVP local

Incluye fases 0 a 4.

Resultado:

- `cortex autopilot start/preflight/checkpoint/finish/status`
- estado persistente;
- cierre automatico basico;
- sin hooks todavia.

### Milestone B - MCP y meta-skill

Incluye fases 5 y 6.

Resultado:

- agente puede llamar tools Autopilot;
- meta-skill disponible;
- no hay instalacion automatica por hooks aun.

### Milestone C - Primer harness piloto

Incluye fase 7 para un solo adapter.

Recomendacion:

1. Claude Code si el objetivo es hook robusto.
2. Cursor si el objetivo es adopcion IDE.
3. Codex App si el objetivo es marketplace interno.

### Milestone D - Budget hardening

Incluye fase 8.

Resultado:

- costos observables;
- perfiles de contexto;
- defaults conservadores.

### Milestone E - Deep Track y marketplace

Incluye fases 9 a 12.

Resultado:

- Autopilot completo;
- packaging;
- evals;
- distribucion.

---

## 14. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Hooks distintos por IDE | Alto | Adapter por harness, no logica compartida forzada |
| Consumo alto de tokens | Alto | Meta-skill corta, budget profiles, no full sync |
| Session notes inventadas | Alto | Render desde eventos observados, status `auto-draft` |
| Romper CLI actual | Alto | Subcomando aislado y tests de regresion |
| Agente ignora meta-skill | Critico | Guard anti-racionalizacion (seccion 10.4), policies programaticas |
| Conflicto con Superpowers instalado | Alto | Deteccion automatica en doctor (seccion Fase 10), warning explicito |
| Estado perdido entre procesos | Medio | StateStore en `.cortex/run/autopilot` |
| JSONL de eventos crece sin limite | Medio | Rotacion en StateStore, cleanup command, warning en doctor |
| Skills demasiado rigidas | Medio | Modo `observe`, `assist`, `autopilot` |
| Delegacion inexistente | Medio | Fase dedicada para alinear MCP y skills |
| Marketplace prematuro | Medio | Packaging recien despues de evals |
| `finish --auto` sin review humano | Medio | Status `auto-draft` visible en la nota, no se marca como `documented` completo |

---

## 15. Decisiones Iniciales Recomendadas

1. Autopilot debe estar deshabilitado por defecto.
2. Primer release debe usar modo `assist`, no `autopilot`.
3. `finish --auto` debe guardar `auto-draft` cuando falten datos.
4. El estado debe vivir en `.cortex/run/autopilot`.
5. El grupo CLI debe vivir en `cortex/autopilot/cli.py`.
6. La meta-skill no debe superar 1500 palabras.
7. Deep Track debe ser excepcional y medido.
8. No agregar dependencias nuevas en MVP.
9. Marketplace recien despues de un adapter probado end-to-end.

---

## 16. Definicion de Done Global

Autopilot se considera listo para piloto cuando:

- [ ] Existe modulo `cortex.autopilot`.
- [ ] Existe subcomando `cortex autopilot`.
- [ ] Estado persistente funciona.
- [ ] Cierre automatico genera session note segura.
- [ ] MCP expone tools Autopilot.
- [ ] Meta-skill se instala opcionalmente.
- [ ] Al menos un adapter instala hooks.
- [ ] `doctor` diagnostica instalacion.
- [ ] Evals cubren pregunta simple, cambio simple y cierre automatico.
- [ ] Documentacion explica enable, disable, install y uninstall.
- [ ] El flujo manual anterior sigue funcionando igual.

---

## 17. Primer Paso de Implementacion Sugerido

La primera tarea concreta deberia ser una mini-epica:

```text
EPIC-AUTOPILOT-01 - Skeleton y estado persistente
```

Con estas tareas:

1. Crear `cortex/autopilot/__init__.py` — package marker.
2. Crear `cortex/autopilot/models.py` — todos los modelos Pydantic.
3. Crear `cortex/autopilot/state_store.py` — persistencia JSON/JSONL.
4. Crear tests unitarios de serializacion y paths.
5. Crear `cortex/autopilot/service.py` con `start()` y `status()`.
6. Crear `cortex/autopilot/cli.py` con `start` y `status`.
7. Registrar el typer en `cortex/cli/main.py`.

### Detalle de `models.py` para el implementador

Este archivo debe contener TODOS los modelos base del sistema. Los modelos estan definidos a lo largo de este documento; aqui se consolidan para referencia del implementador:

```python
"""cortex.autopilot.models — Domain models for the Autopilot module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


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
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_root: str
    workspace_root: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: Literal[
        "started", "preflight_done", "implementation_seen",
        "documented", "finished", "failed",
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
    budget: AutopilotBudgetSnapshot = Field(
        default_factory=AutopilotBudgetSnapshot
    )
    warnings: list[str] = []


class AutopilotEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    event_type: str  # "start", "preflight", "checkpoint", "finish", etc.
    source: Literal["cli", "mcp", "hook", "agent", "detector", "policy"]
    payload: dict[str, Any] = {}


class DetectionRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None
    session_state: AutopilotSessionState | None = None


class DetectionResult(BaseModel):
    task_type: Literal[
        "question-only", "docs-only", "fast-code",
        "deep-code", "security", "ambiguous", "noop"
    ]
    confidence: float = 0.0
    reason: str = ""
    suggested_complexity: Literal["none", "fast", "deep"] = "none"


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None


class SessionDraft(BaseModel):
    title: str
    body: str
    confidence: Literal["high", "medium", "auto-draft"] = "medium"
    warnings: list[str] = []
    source_events: int = 0


class HookSessionStartOutput(BaseModel):
    session_id: str
    mode: Literal["observe", "assist", "autopilot"]
    bootstrap_content: str
    budget_profile: str
    available_tools: list[str] = []
    cortex_version: str = ""


class DelegationResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "rejected"]
    diff_summary: str = ""
    files_changed: list[str] = []
    tests_passed: bool | None = None
    spec_path: str | None = None
    rejection_reason: str | None = None
```

### Detalle de `state_store.py` para el implementador

```python
"""cortex.autopilot.state_store — Persistent state for Autopilot sessions."""
from pathlib import Path
import json
from .models import AutopilotSessionState, AutopilotEvent


class StateStore:
    """JSON/JSONL persistence for Autopilot state.

    Directory layout:
        .cortex/run/autopilot/sessions/<session-id>.json
        .cortex/run/autopilot/events/<session-id>.jsonl
    """

    def __init__(self, workspace_root: Path) -> None:
        self.root = workspace_root / "run" / "autopilot"
        self.sessions_dir = self.root / "sessions"
        self.events_dir = self.root / "events"

    def _ensure_dirs(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: AutopilotSessionState) -> Path:
        self._ensure_dirs()
        path = self.sessions_dir / f"{state.session_id}.json"
        path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def load_state(self, session_id: str) -> AutopilotSessionState | None:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        return AutopilotSessionState.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def append_event(self, event: AutopilotEvent) -> None:
        self._ensure_dirs()
        path = self.events_dir / f"{event.session_id}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def load_events(self, session_id: str) -> list[AutopilotEvent]:
        path = self.events_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(AutopilotEvent.model_validate_json(line))
        return events

    def list_sessions(self) -> list[str]:
        if not self.sessions_dir.exists():
            return []
        return [
            p.stem for p in self.sessions_dir.glob("*.json")
        ]
```

Gate:

```bash
pytest tests/unit/autopilot -q
pytest tests/unit/cli/test_main.py -q
```

Este primer paso ya daria una base extensible sin comprometer el sistema actual.

---

## 18. Nota Final para Agentes Implementadores

Si sos un agente de IA leyendo este documento para implementar Autopilot, segui estas reglas:

1. **No improvises.** Usa los modelos exactos definidos en la seccion 17. No inventes campos ni renombres clases.
2. **No saltees tests.** Cada fase tiene un gate de salida con tests. Si los tests no pasan, la fase no esta completa.
3. **No toques el CLI existente** salvo la linea `app.add_typer(autopilot_app, name="autopilot")`.
4. **No toques el MCP server** hasta la Fase 5.
5. **Segui el flowchart** de la seccion 6.1.1 para entender el flujo completo.
6. **Usa `WorkspaceLayout`** para resolver paths. No hardcodees `.cortex/` ni `config.yaml`.
7. **Cada archivo nuevo** debe tener su test unitario correspondiente.
8. **Si algo no esta claro**, pregunta antes de asumir. La racionalizacion es el enemigo (ver seccion 10.4).
