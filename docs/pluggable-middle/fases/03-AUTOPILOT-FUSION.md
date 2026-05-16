# Fase 03 — Autopilot Fusion + Observed Mode

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 02 · **Bloquea:** Fase 04 · **Esfuerzo estimado:** ~2 semanas

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 03 |
| Nombre | Autopilot Fusion + Observed Mode |
| Versión del plan | 1.0 |
| Dependencias | Fase 02 cerrada (Managed sobre Sessions; documenter unificado) |
| Output principal | Autopilot reescrito sobre Sessions. Modo Observed con hooks IDE funcional. |
| Breaking changes | Sí, intencionales: Autopilot ya no tiene su propio lifecycle paralelo. Sus comandos siguen existiendo como aliases pero delegan a Sessions. |

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md):
  - §4.3 (Modo Observed con diagrama secuencial),
  - §10.5 (Autopilot fusion).
- Fases anteriores §7 (Handoff to next phase).

### 1.2 Código existente que vas a tocar

Leé enteros:

- **TODO el módulo `cortex/autopilot/`.** Es lo que vas a refactorizar. Mínimo:
  - `cortex/autopilot/service.py`
  - `cortex/autopilot/lifecycle.py`
  - `cortex/autopilot/models.py`
  - `cortex/autopilot/state_store.py`
  - `cortex/autopilot/mcp_tools.py`
  - `cortex/autopilot/cli.py`
  - `cortex/autopilot/policies/`
  - `cortex/autopilot/detectors/`
  - `cortex/autopilot/hooks/`
  - `cortex/autopilot/session_builder.py`
  - `cortex/autopilot/session_writer.py`
  - `cortex/autopilot/renderers/`
  - `cortex/autopilot/budget_profiles.py`
  - `cortex/autopilot/context_budget.py`
  - `cortex/autopilot/reporting.py`
- `cortex/session/service.py` — para entender la API que vas a delegar.
- `cortex/documenter/reconstruction.py` — para entender lo que `finish` debe disparar.
- `cortex/ide/` — adaptadores IDE existentes (los vas a usar y extender).

Leé bajo demanda:

- Tests existentes de Autopilot: `tests/unit/autopilot/`, `tests/integration/autopilot/`.
- Documentación de Autopilot en `docs/autopilot/`.

### 1.3 Documentación externa

- Claude Code hooks: https://docs.claude.com/en/docs/agents-and-tools/agent-skills (sección hooks) — si necesitás verificar el formato de hooks JSON.
- Cursor extensions API (si existe): consultar al diseñar hooks de Cursor.
- Git hooks: https://git-scm.com/docs/githooks — para el adapter de hooks vía git.

---

## 2. Goal

Al finalizar esta fase:

1. **Autopilot vive como capa fina** encima de Sessions. Sus comandos (`cortex autopilot start/checkpoint/finish/status`) son aliases que delegan a la API de Sessions con políticas aplicadas.
2. **Las políticas de Autopilot** (modos `observe | assist | autopilot`, budget profiles, detectores, etc.) se preservan como **configuración del comportamiento**, no como entidades paralelas.
3. **Existen hooks IDE adaptadores** para emitir checkpoints automáticamente al ocurrir eventos del IDE (post-commit, post-tool-use, etc.). Mínimo soportado en esta fase:
   - **Claude Code** (hooks JSON nativos).
   - **Cursor** (vía git hooks o command palette).
   - **Pi Coding Agent** (vía task runner hooks).
4. **Existe el comando `cortex session hooks install --ide <name>`** que instala los hooks correspondientes.
5. **Tests E2E del modo Observed** validan: con hook instalado, un git commit → checkpoint en la session activa.
6. **El estado interno `autopilot/active.json`** se migra a `.cortex/sessions/` (o se elimina). El módulo `state_store.py` se reescribe sobre `SessionStorage`.
7. **Tests previos siguen pasando.**

**Lo que NO se hace en esta fase:**

- ❌ NO se elimina el módulo `cortex/autopilot/` (su API CLI sigue funcionando como alias).
- ❌ NO se rompe el alias `cortex autopilot finish` para usuarios que ya lo conocían (aunque no hay usuarios reales, mantener UX).
- ❌ NO se implementa el modo interactive del documenter (Fase 04).
- ❌ NO se hacen hooks para opencode, Codex, VSCode (sería duplicación de esfuerzo; los más estratégicos son Claude Code + Cursor + Pi).

---

## 3. Decisiones de diseño clave

### 3.1 Alcance de "fusion"

**Decisión:** Autopilot NO se elimina como concepto. Se redefine como:

> **Autopilot = Sessions + políticas + hooks IDE instalados.**

- La primitiva Session ya hace el tracking (Fase 00-02).
- Lo que Autopilot agrega: **políticas** (cuándo emitir warnings, qué budget enforce, qué detectores correr) y **hooks** (mecanismo automático de emisión de checkpoints).
- Los comandos CLI `cortex autopilot ...` se mantienen como **wrappers semánticos** que llaman a `cortex session ...` aplicando políticas.

### 3.2 Modos `observe | assist | autopilot`: qué significan ahora

| Modo (config) | Comportamiento |
|---|---|
| `observe` | Hooks instalados emiten checkpoints. Cortex NO interviene en el flujo. Solo registra. |
| `assist` | Igual a observe + warnings activos (ej. "vas a hacer un cambio fuera de scope, ¿continuar?"). Pide confirmación en momentos clave. |
| `autopilot` | Hooks emiten checkpoints. Políticas pueden disparar acciones automáticas (ej. correr verification hooks pre-commit). Más automático. |

**El default sugerido para nuevos usuarios:** `assist`.

### 3.3 Hooks IDE: dónde viven

**Decisión:** Cada hook IDE es **un script o config** que:

1. Se instala en el IDE (en su carpeta de configuración).
2. Cuando se dispara (ej. post-commit), invoca `cortex_session_checkpoint` vía CLI o MCP.

NO incrustar lógica compleja en los hooks. Los hooks son **disparadores**, no procesadores.

### 3.4 Migración del state de Autopilot existente

El módulo Autopilot actual persiste estado en `cortex/autopilot/state_store.py` (verificar ubicación exacta). Como no hay usuarios reales, **no necesitamos migración de datos** — basta con que el código nuevo no lea el formato viejo y que `cortex doctor` detecte si quedó basura.

### 3.5 Compatibilidad CLI

`cortex autopilot start` debe seguir funcionando. Internamente:

```
cortex autopilot start --mode assist
  → invoca SessionService logic con policy=assist
  → si no hay spec activo (no hay session abierta), retorna error indicando crear spec primero
```

**Cambio sutil:** Autopilot ya no abre sesiones por sí mismo. Si el usuario pidió "start" sin tener spec activo, el comando le dice qué hacer:

```
✗ No active session. Run `cortex create-spec` first to open one.
```

---

## 4. Task Breakdown

### T3.1 — Auditar y mapear módulo `cortex/autopilot/`

**Objetivo:** entender exactamente qué hace cada archivo del módulo y planear el mapeo a Sessions.

**Acción:** crear un documento de trabajo (no público, solo para el agente):

`docs/pluggable-middle/fases/_internal/autopilot-audit.md`

Contenido esperado:

```markdown
# Autopilot module audit (Fase 03 internal)

## Inventory

| Archivo | LOC | Responsabilidad actual | Destino en Sessions |
|---|---|---|---|
| service.py | ... | AutopilotService.start/checkpoint/finish | Mapeo a SessionService + AutopilotPolicy |
| lifecycle.py | ... | Lifecycle hooks | Reescribir como AutopilotPolicy.before/after_X |
| state_store.py | ... | Persistencia de active.json | Eliminar (SessionStorage lo hace) |
| ... | ... | ... | ... |
```

**Cómo hacerla:** abrir cada archivo, leer, anotar.

**Razón de hacerla:** sin este mapeo, la refactor se vuelve adivinanza. Es el equivalente a un Tech Spec interno de la fase.

**Definition of Done T3.1:** documento creado, todos los archivos del módulo listados con su destino.

---

### T3.2 — Crear módulo `cortex/autopilot/policies.py` (consolidado)

**Objetivo:** consolidar todas las políticas (modos, budgets, detectors) en una API clara.

**Archivos a crear/modificar:**
- `cortex/autopilot/policies.py` (nuevo, consolidado)
- Migrar contenido de `cortex/autopilot/policies/` (que es un subdirectorio actualmente) si tiene sentido aplanar.

**API esperada:**

```python
class AutopilotMode(str, Enum):
    OBSERVE = "observe"
    ASSIST = "assist"
    AUTOPILOT = "autopilot"

@dataclass(frozen=True)
class AutopilotPolicy:
    mode: AutopilotMode
    budget_profile: str  # nombre del preset, ver budget_profiles.py
    pre_commit_verification: bool = False  # solo modo autopilot
    out_of_scope_warning: bool = True  # modos assist+
    # ... otros flags que existan en el módulo actual

    @classmethod
    def from_config(cls, config: dict) -> AutopilotPolicy:
        """Carga desde .cortex/config.yaml sección [autopilot]."""

class PolicyEnforcer:
    """Aplica políticas en hooks específicos del lifecycle de Sessions."""

    def on_session_open(self, session: SessionRecord, policy: AutopilotPolicy) -> None: ...
    def on_checkpoint(self, session: SessionRecord, checkpoint: Checkpoint, policy: AutopilotPolicy) -> EnforcementResult: ...
    def on_pre_close(self, session: SessionRecord, policy: AutopilotPolicy) -> EnforcementResult: ...
```

**Tests obligatorios:**
- Por cada modo, validar comportamiento esperado.
- Test que `out_of_scope_warning` se dispara correctamente.
- Test que `pre_commit_verification` corre los hooks (en modo autopilot).

---

### T3.3 — Reescribir `cortex/autopilot/service.py` sobre Sessions

**Objetivo:** la API pública de Autopilot delega a SessionService.

**Archivos a modificar:**
- `cortex/autopilot/service.py` — reescribir.
- `cortex/autopilot/lifecycle.py` — eliminar o reducir a thin re-exports.
- `cortex/autopilot/state_store.py` — eliminar (Sessions ya persiste).
- `cortex/autopilot/session_builder.py` y `session_writer.py` — eliminar duplicación (lo hace Documenter ahora).

**API nueva:**

```python
class AutopilotService:
    def __init__(
        self,
        session_service: SessionService,
        spec_service: SpecService,
        policy_enforcer: PolicyEnforcer,
        config: AutopilotConfig,
    ) -> None: ...

    def start(self, mode: AutopilotMode) -> AutopilotStartResult:
        """
        Si no hay sesión activa: error indicando crear spec.
        Si hay sesión activa: asocia la policy + arma el contexto.
        """

    def checkpoint(self, source: CheckpointSource, **kwargs) -> AutopilotCheckpointResult:
        """Wrapper de session_service.checkpoint con policy enforcement."""

    def finish(self, auto: bool = False) -> AutopilotFinishResult:
        """
        Si auto=True: invoca cortex_finish_session directamente.
        Si auto=False: solo cierra la sesión sin documentar (modo observe).
        """

    def status(self) -> AutopilotStatusResult:
        """Forwards a session_service.get_active() + policy state."""

    def doctor(self) -> AutopilotDoctorResult:
        """Validates: policy config, IDE hooks installation, session consistency."""
```

**Eliminaciones:**
- `state_store.py`: borrar archivo. Toda persistencia ya está en SessionStorage.
- `session_builder.py` y `session_writer.py`: borrar (eran para construir session notes; ya lo hace `cortex/documenter/persistence.py`).

**Tests obligatorios:**
- Mockear SessionService y verificar que cada método delega correctamente.
- Test E2E con un mini-repo simulando el flujo entero.

---

### T3.4 — Actualizar CLI de Autopilot (`cortex/autopilot/cli.py`)

**Objetivo:** comandos siguen funcionando, internamente delegan.

**Archivos a modificar:**
- `cortex/autopilot/cli.py`

**Comportamiento esperado:**

```bash
cortex autopilot start --mode assist
# → AutopilotService.start(AutopilotMode.ASSIST)
# → si no hay sesión activa: error con sugerencia

cortex autopilot checkpoint --source ide-hook \
  --verified-claim "tests pass" --artifact "src/foo.py"
# → AutopilotService.checkpoint(...)

cortex autopilot finish --auto
# → AutopilotService.finish(auto=True)
# → internamente llama a cortex finish-session

cortex autopilot status
# → AutopilotService.status()

cortex autopilot doctor
# → AutopilotService.doctor()

cortex autopilot install --ide claude-code
# → AutopilotService delega a cortex session hooks install (T3.6)

cortex autopilot uninstall --ide claude-code
# → análogo
```

**Tests:**
- Cada comando con CliRunner.
- Mensajes de error claros cuando faltan precondiciones.

---

### T3.5 — Actualizar MCP tools de Autopilot (`cortex/autopilot/mcp_tools.py`)

**Objetivo:** las tools MCP de Autopilot delegan a Sessions/Documenter.

**Archivos a modificar:**
- `cortex/autopilot/mcp_tools.py`

**Tools (mismas signatures, internals nuevos):**

- `cortex_autopilot_start(mode)` → AutopilotService.start
- `cortex_autopilot_checkpoint(...)` → AutopilotService.checkpoint
- `cortex_autopilot_finish(auto)` → AutopilotService.finish (que delega a cortex_finish_session)
- `cortex_autopilot_status()` → AutopilotService.status

Estas tools ya están registradas vía FastMCP. Solo cambia el body.

**Tests:**
- Cada tool retorna schemas estables (no romper consumers).

---

### T3.6 — Hooks installer system (`cortex/session/hooks/`)

**Objetivo:** infraestructura para instalar/desinstalar hooks IDE.

**Archivos a crear:**
- `cortex/session/hooks/__init__.py`
- `cortex/session/hooks/installer.py`
- `cortex/session/hooks/adapters/__init__.py`
- `cortex/session/hooks/adapters/claude_code.py`
- `cortex/session/hooks/adapters/cursor.py`
- `cortex/session/hooks/adapters/pi.py`
- `tests/unit/session/hooks/test_installer.py`
- Tests por adapter.

**API esperada:**

```python
class HookAdapter(Protocol):
    name: str  # ide identifier

    def is_supported(self) -> bool:
        """Detecta si el IDE está disponible en este sistema."""

    def install(self, target_dir: Path) -> InstallResult:
        """Instala hooks en target_dir (project root o user config)."""

    def uninstall(self, target_dir: Path) -> UninstallResult:
        """Remueve hooks limpios."""

    def status(self, target_dir: Path) -> HookStatus:
        """Reporta: instalado/no, version del hook, last activity."""

class HookInstaller:
    def __init__(self, adapters: dict[str, HookAdapter]) -> None: ...
    def install(self, ide: str, target_dir: Path) -> InstallResult: ...
    def uninstall(self, ide: str, target_dir: Path) -> UninstallResult: ...
    def list_supported(self) -> list[str]: ...
```

**Definition of Done T3.6:** infraestructura genérica + tests.

---

### T3.7 — Adapter Claude Code

**Archivos a crear:**
- `cortex/session/hooks/adapters/claude_code.py`
- Tests en `tests/unit/session/hooks/test_claude_code.py`

**Diseño:**

Claude Code soporta hooks JSON nativos en su settings. El adapter:

1. **Instala:** modifica/crea `~/.claude/settings.json` (user) o `.claude/settings.json` (project) agregando una entrada de hook tipo `PostToolUse` o equivalente que detecta cambios en archivos.

   El hook ejecuta:
   ```bash
   cortex session checkpoint --source ide-hook --artifact "${file_path}" --note "edited via Claude Code"
   ```

2. **Desinstala:** remueve la entrada agregada (preserva otras entradas).

3. **Status:** lee el settings.json y reporta si la entrada existe.

**Investigación previa requerida:**
- Antes de codear, leer la documentación de hooks de Claude Code via `WebFetch` para confirmar el formato exacto y los eventos disponibles.
- Investigar qué evento dispara post-modificación de archivo (PostToolUse con tool="Edit"|"Write" probablemente).

**Tests:**
- Test instala correctamente en directorio temporal.
- Test desinstala sin afectar otras entradas.
- Test idempotencia: install + install = install (no duplica).

---

### T3.8 — Adapter Cursor

**Archivos a crear:**
- `cortex/session/hooks/adapters/cursor.py`
- Tests.

**Diseño:**

Cursor no tiene hooks nativos como Claude Code. Estrategias:

**Opción A (preferida):** usar git hooks (`.git/hooks/post-commit`) — independiente del IDE.

**Opción B:** usar Cursor commands custom (.cursor/commands.json o equivalente).

**Decisión:** **Opción A** porque:
- Es independiente del IDE específico de la familia VSCode.
- No depende de APIs internas de Cursor que pueden cambiar.
- Funciona también para usuarios de VSCode con Cline/Roo.

El hook git post-commit:
```bash
#!/bin/sh
# .git/hooks/post-commit (instalado por cortex)
cortex session checkpoint --source ide-hook \
  --note "git commit $(git rev-parse --short HEAD): $(git log -1 --pretty=%s)" 2>/dev/null || true
```

**Cuidado:** el hook NO debe abortar el commit si Cortex falla. De ahí el `|| true`.

**Naming:** el adapter se llama `cursor` por UX, pero funciona para cualquier IDE basado en VSCode.

**Tests:** crea repo temporal con git init, instala hook, hace commit, verifica que se invocó.

---

### T3.9 — Adapter Pi

**Archivos a crear:**
- `cortex/session/hooks/adapters/pi.py`

**Diseño:**

Pi Coding Agent ya tiene una integración fuerte con Cortex via `cortex-pi/`. El adapter delega al task runner (`just`):

- `just` recipes en `cortex-pi/justfile` que invocan `cortex session checkpoint` en momentos clave.
- El adapter "instala" agregando recipes adicionales si no existen.

**Tests:** depende de si Pi está disponible en el entorno de test. Si no, mockear.

---

### T3.10 — CLI: `cortex session hooks install/uninstall/status`

**Archivos a modificar:**
- `cortex/cli/session.py`

**Comandos:**

```bash
cortex session hooks list
# Lista los IDEs soportados y su estado

cortex session hooks install --ide claude-code
# Instala el adapter de Claude Code

cortex session hooks install --ide cursor --target user
# Instala globalmente (--target user) o en el proyecto (--target project, default)

cortex session hooks uninstall --ide claude-code

cortex session hooks status
# Tabla con cada IDE: instalado/no, versión del hook
```

**Tests:** CLI tests con CliRunner.

---

### T3.11 — Tests E2E del modo Observed

**Archivos a crear:**
- `tests/e2e/test_observed_flow.py`

**Escenarios:**

```python
def test_observed_flow_with_git_hook(tmp_repo_with_cortex):
    """
    Setup: repo + cortex + hook git instalado vía adapter cursor.
    Flow:
      1. cortex_create_spec → session abierta
      2. Modificar archivo manualmente
      3. git commit -m "manual change"  → hook dispara checkpoint
      4. Verificar que session tiene un checkpoint con source=IDE_HOOK
      5. cortex_finish_session
    Assert:
      - Mode inferido = OBSERVED
      - Session note incluye la nota del checkpoint del hook
    """

def test_observed_flow_multiple_hooks_register(tmp_repo_with_cortex):
    """
    Setup: hook instalado.
    Acción: 3 commits sucesivos.
    Assert: 3 checkpoints registrados.
    """

def test_observed_hook_failure_does_not_block_commit(tmp_repo_with_cortex):
    """
    Setup: hook instalado pero Cortex no disponible (mock).
    Acción: git commit.
    Assert: el commit pasa OK. El hook falló silenciosamente (log only).
    """
```

---

### T3.12 — Doctor extensions

**Archivos a modificar:**
- `cortex/doctor.py`

**Nuevas validaciones:**

```
[autopilot]
  Mode: assist
  Policy config: ok
  Hooks installed:
    ✓ claude-code (project)
    ✗ cursor (not installed)
    ✗ pi (Pi not detected on system — n/a)

[sessions / hooks]
  Detected event sources in active sessions: 12 checkpoints from ide-hook
```

---

### T3.13 — Documentación

**Archivos a modificar:**
- `C:\Cortex\README.md` — sección Observed mode actualizada.
- `C:\Cortex\docs\autopilot/` — actualizar las docs ahí para reflejar que Autopilot ahora es capa sobre Sessions.
- `C:\Cortex\docs\architecture\session-primitive.md` — agregar sección sobre hooks.
- `C:\Cortex\docs\pluggable-middle\README.md` — marcar Fase 03 ✅.

**Contenido nuevo importante en README:**

Agregar tabla resumen de hooks IDE soportados:

```markdown
## IDE Hooks (Observed Mode)

| IDE | Soporte | Mecanismo |
|---|---|---|
| Claude Code | ✓ Nativo | Hooks JSON in settings |
| Cursor / VSCode | ✓ Vía git hooks | post-commit |
| Pi Coding Agent | ✓ Nativo | just recipes |
| Codex | ❌ Sin hooks (modo legacy YAML) | — |
| opencode | ⏳ Roadmap | — |

Instalar:
```bash
cortex session hooks install --ide claude-code
```
```

---

## 5. Cross-cutting concerns

### 5.1 Compatibilidad

- Comandos `cortex autopilot ...` siguen funcionando.
- Si alguien tenía un script que invocaba la API Python directa de `AutopilotService` (viejo), la nueva API mantiene los métodos clave (`start`, `checkpoint`, `finish`, `status`). Signatures pueden cambiar; documentar el cambio en CHANGELOG.

### 5.2 Eliminación de duplicación

Esta fase **elimina** archivos:
- `cortex/autopilot/state_store.py`
- `cortex/autopilot/session_builder.py`
- `cortex/autopilot/session_writer.py`
- Posiblemente `cortex/autopilot/lifecycle.py` (depende de la auditoría T3.1).

Cada eliminación debe:
1. Verificar que nadie más en el repo importa el archivo (Grep).
2. Si alguien lo importa, redirigir el import al equivalente nuevo.
3. Commit aparte con mensaje claro: `chore(autopilot): remove deprecated state_store (replaced by SessionStorage)`.

### 5.3 Performance

- Hooks IDE deben ser **rápidos** (< 100ms idealmente). El hook checkpoint dispara una CLI invocation; OK porque es asíncrono respecto al usuario.
- Si el hook tarda más de 500ms, considerar fire-and-forget en background.

### 5.4 Seguridad

- Los hooks IDE ejecutan commands en el contexto del usuario. NO meter secrets o credenciales en los scripts instalados.
- El installer NO debe escribir a paths fuera del workspace/user config sin permiso explícito.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests
pytest tests/unit/autopilot/ -v
pytest tests/unit/session/hooks/ -v
pytest tests/integration/autopilot/ -v
pytest tests/e2e/test_observed_flow.py -v
pytest tests/e2e/test_managed_flow.py -v     # Fase 02 no regresión
pytest tests/e2e/test_byo_flow.py -v         # Fase 01 no regresión
# all green

# 2. Type checking
mypy --strict cortex/autopilot/ cortex/session/hooks/
# clean

# 3. Lint
ruff check cortex/autopilot/ cortex/session/hooks/ tests/
ruff format --check cortex/autopilot/ cortex/session/hooks/ tests/
# clean

# 4. Smoke test del adapter Claude Code (en directorio temporal):
cortex session hooks install --ide claude-code --target project
# expected: settings.json modificado

cortex session hooks status
# expected: tabla con claude-code instalado

cortex session hooks uninstall --ide claude-code
# expected: settings.json revertido

# 5. Smoke del flow Observed completo:
# (necesita un IDE real o mock)
# Crear spec → install hook git → modificar y commitear → finish-session
# Verificar que session tiene checkpoint con source=ide-hook
```

---

## 7. Handoff to next phase

Al cerrar Fase 03:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Autopilot refactorizado | `cortex/autopilot/` |
| Policies consolidadas | `cortex/autopilot/policies.py` |
| Hooks installer system | `cortex/session/hooks/` |
| 3 adapters IDE | `cortex/session/hooks/adapters/` |
| CLI `cortex session hooks ...` | `cortex/cli/session.py` |
| Tests E2E Observed | `tests/e2e/test_observed_flow.py` |
| Docs actualizadas | `docs/autopilot/`, `README.md`, `docs/architecture/session-primitive.md` |

### Lo que la Fase 04 puede asumir

1. Los tres modos (Managed, Observed, BYO) están funcionales y testeados.
2. La arquitectura está completa funcionalmente.
3. Autopilot es una thin layer sobre Sessions.
4. Hooks IDE existen para los 3 IDEs principales.

### Lo que falta para cerrar el proyecto

- Modo interactive del documenter (UX para detectar errores/desvíos).
- Polish final de docs.
- Eliminación opcional del modo Legacy YAML.
- Validación E2E del scenario interactive.

---

## 8. Progress Log

- [ ] T3.1 — Auditar módulo autopilot (mapeo)
- [ ] T3.2 — Crear `cortex/autopilot/policies.py` consolidado
- [ ] T3.3 — Reescribir `service.py` sobre Sessions
- [ ] T3.4 — Actualizar CLI Autopilot
- [ ] T3.5 — Actualizar MCP tools Autopilot
- [ ] T3.6 — Hooks installer system
- [ ] T3.7 — Adapter Claude Code
- [ ] T3.8 — Adapter Cursor (git hooks)
- [ ] T3.9 — Adapter Pi
- [ ] T3.10 — CLI `session hooks ...`
- [ ] T3.11 — Tests E2E Observed
- [ ] T3.12 — Doctor extensions
- [ ] T3.13 — Documentación
- [ ] Completion Verification Commands pasan
- [ ] Tabla `../README.md` actualizada ✅
- [ ] Commit final

---

## 9. Notas para el agente ejecutor

- **Empezá por T3.1 (auditoría).** Sin auditoría, el refactor es caos. La auditoría no es opcional.
- **Eliminar código es bueno.** Si un archivo del módulo Autopilot ya no aporta, borrarlo (con commits trazables). No mantener código zombie "por las dudas".
- **Hooks IDE: investigar primero.** Antes de codear el adapter de Claude Code, leer su doc oficial vía WebFetch. Antes de codear el de Cursor, validar que git hooks es la estrategia correcta para el target del usuario.
- **No expandir el alcance.** Esta fase NO agrega soporte a opencode, Codex, VSCode-puro, JetBrains. Solo los 3 mencionados. Cualquier expansión es Fase 04+ o post-MVP.
- **Performance de hooks importa.** Un hook lento es un hook abandonado por el usuario.
