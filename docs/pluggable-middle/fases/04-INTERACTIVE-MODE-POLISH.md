# Fase 04 — Interactive Mode + Final Polish

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 03 · **Bloquea:** Nada (fase final) · **Esfuerzo estimado:** ~1 semana

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 04 |
| Nombre | Interactive Mode + Final Polish |
| Versión del plan | 1.0 |
| Dependencias | Fase 03 cerrada (los 3 modos operativos) |
| Output principal | Modo interactivo del documenter, documentación final, doctor exhaustivo, evaluación opcional de eliminación del modo Legacy YAML. |
| Breaking changes | Mínimos. Si se decide eliminar el modo Legacy YAML, sí (pero es opcional). |

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md):
  - §7.3 (Documenter: dos modos),
  - §7.4 (Modo interactivo UX mockup),
  - §12 Q3 (decisión sobre modos).
- Fases anteriores §7.

### 1.2 Código existente que vas a tocar

Leé enteros:

- `cortex/documenter/reconstruction.py` (Fase 01) — para entender el flujo.
- `cortex/documenter/persistence.py` (Fase 01) — donde vas a sumar `FinishOverrides`.
- `cortex/cli/session.py` y `cortex/cli/main.py` — para agregar el flag `--interactive`.
- `cortex/mcp/server.py` — para extender `cortex_finish_session` con modo interactive.
- `cortex/handoff.py` — si se decide eliminar (T4.8 opcional).
- `.cortex/subagents/cortex-documenter.md` — para actualizar el contrato con modo interactive.

Leé bajo demanda:

- Tests previos para no romperlos.
- Librerías de prompts CLI: `rich`, `prompt_toolkit`, `questionary` — investigar cuál ya está en el repo.

### 1.3 Documentación externa

- `rich` prompts: https://rich.readthedocs.io/en/stable/prompt.html
- `questionary` (si se decide usarlo): https://questionary.readthedocs.io/
- Best practices de CLI UX (lecturas opcionales): https://clig.dev/

---

## 2. Goal

Al finalizar esta fase:

1. **El documenter tiene modo interactivo funcional.** Cuando se invoca `cortex finish-session --interactive`, muestra:
   - Draft del session note.
   - ADRs sugeridos con justificación de criterios 3/3.
   - Discrepancias detectadas.
   - Scope drift.
   - Opciones: Aprobar / Editar / Handoff / Cancelar.
2. **Existe configuración `documenter.default_mode`** en `.cortex/config.yaml` que permite `auto` o `interactive` como default.
3. **El doctor está completo.** Valida toda la infraestructura del Pluggable Middle (sessions, hooks, policies, verification, documenter).
4. **README + Manifiesto actualizados** para reflejar la arquitectura final.
5. **Tests E2E** del modo interactive validan happy path + cada opción del prompt.
6. **(Opcional) Decisión sobre Legacy YAML:** evaluar si se elimina del documenter. Si sí, se elimina la rama de código + se actualizan los skills externos (Codex AGENTS.md, opencode).
7. **Migration guide** documenta lo que cambió desde el modelo tripartito original (aunque no hay usuarios reales, para futuros adoptantes).

**Lo que se considera "fase final":**

- No quedan tareas posteriores planeadas dentro de este roadmap.
- Si surgen mejoras (post-MVP, integraciones, mejoras de UX), van a un roadmap nuevo.

---

## 3. Decisiones de diseño clave

### 3.1 Modo interactivo: ¿librería usar?

**Decisión:** **`rich`** (ya en el repo).

Razones:
- Ya es dependencia.
- Soporta tablas, syntax highlighting de código, prompts simples.
- Para inputs más complejos (editar texto multilinea), invocar el editor del usuario via `click.edit()` o equivalente.

Lo que NO usamos:
- `questionary`: agregaría dependencia.
- `prompt_toolkit` standalone: overkill.

### 3.2 ¿Qué es editable en modo interactivo?

| Elemento | Editable | Cómo |
|---|---|---|
| Título del session note | ✓ | Inline prompt |
| Cuerpo del session note | ✓ | Editor externo (`$EDITOR`) |
| ADRs sugeridos | ✓ (aprobar/rechazar individual) | Prompt yes/no por cada uno |
| Status final (closed vs handoff) | ✓ | Hotkey [H] |
| Verification results | ✗ (read-only) | Solo display |
| Discrepancias | ✗ (read-only) | Solo display |

### 3.3 Default mode: ¿auto o interactive?

**Decisión:** **auto por default**, **interactive opt-in via `--interactive` flag o config**.

Razones:
- Usuario que no conoce el framework prefiere "just works".
- Usuario que quiere control activa explícitamente.
- Coherente con la filosofía de Cortex: hacer lo correcto silencioso, dar control cuando se pide.

### 3.4 Eliminación del modo Legacy YAML: ¿hacerla?

**Esta es una decisión que el ejecutor de Fase 04 debe re-evaluar al empezar.**

**Argumentos para eliminar:**
- Reduce código.
- Reduce dos paths de mantenimiento en el documenter.
- Cortex 100% sobre Sessions, simple.

**Argumentos para mantener:**
- Codex (sin subagent support) lo usa.
- Skills externos pueden depender de él.

**Decisión sugerida:** **mantenerlo**, pero:
- Etiquetarlo `@deprecated` en docstrings y subagent.
- Documentar que en una versión mayor futura puede removerse.
- Si Codex agrega soporte de hooks/MCP en su roadmap, re-evaluar.

Si el ejecutor decide eliminar: hacerlo en T4.8 (tarea opcional).

### 3.5 Doctor completo

El doctor de Fase 04 valida exhaustivamente la integridad del Pluggable Middle:

1. WorkspaceLayout v2 correcto.
2. `.cortex/sessions/` writable, sin sesiones corruptas.
3. `cortex.session` module healthy (puede listar, abrir, cerrar).
4. MCP server healthy (tools registradas).
5. Autopilot policies cargadas correctamente.
6. Hooks IDE: estado por adapter, version match.
7. Documenter: ambos modos invocables.
8. Verification hooks: muestra un summary de los hooks de la sesión activa.

---

## 4. Task Breakdown

### T4.1 — Modo interactive en `cortex/documenter/`

**Objetivo:** UI interactiva del documenter.

**Archivos a crear:**
- `cortex/documenter/interactive.py`
- `tests/unit/documenter/test_interactive.py`

**Archivos a modificar:**
- `cortex/documenter/persistence.py` — agregar `FinishOverrides`.

**API esperada:**

```python
@dataclass
class FinishOverrides:
    approved_adrs: list[int] | None = None  # índices de ADRSuggestion aprobados; None=todos
    edited_note_title: str | None = None
    edited_note_body: str | None = None
    forced_status: SessionStatus | None = None  # override del suggested_status

class InteractiveSession:
    """Presenta el resultado de reconstrucción y captura inputs del usuario."""

    def __init__(self, console: rich.Console) -> None: ...

    def prompt(self, reconstruction: ReconstructionOutput) -> FinishOverrides | InteractiveCancellation:
        """
        Renderiza el draft + ADRs + discrepancias.
        Presenta opciones: [A]probar / [E]ditar / [H]andoff / [C]ancelar.
        Retorna FinishOverrides o InteractiveCancellation.
        """
```

**Layout visual (referencia: mockup en §7.4 de arquitectura):**

Renderizar con `rich`:

1. Header: `📋 Resumen de la sesión <id>`
2. Tabla con: Spec, Diff resumen, Tests, Duration.
3. Panel "DRAFT SESSION NOTE": render markdown.
4. Panel "ADRs SUGERIDOS": cada uno con criterios 3/3.
5. Panel "ACCIONES": hotkeys.
6. Loop de prompts hasta confirmación o cancelación.

**Manejo de inputs:**

- `[A]probar` → retorna `FinishOverrides` con default (todos los ADRs sugeridos aprobados).
- `[E]ditar` → 
  - Sub-menu: editar título, editar cuerpo (via `$EDITOR`), aprobar/rechazar ADRs uno por uno.
  - Después del editing, volver al loop principal con el draft actualizado.
- `[H]andoff` → `forced_status=HANDOFF`, pedir reason inline, confirmar.
- `[C]ancelar` → `InteractiveCancellation()`. La sesión queda abierta sin cambios.

**Tests obligatorios:**
- Mock de inputs del usuario (rich permite testing via `console.input` mock).
- Test approve happy path.
- Test edit body via $EDITOR (mockear el editor).
- Test handoff path con reason.
- Test cancel deja session intacta.
- Test ADR approve/reject individual.

**Definition of Done T4.1:**
- Tests passing.
- UX renderiza correctamente (test manual con un repo de prueba).
- Sin errores con caracteres unicode/ANSI.

---

### T4.2 — Flag `--interactive` en CLI/MCP

**Archivos a modificar:**
- `cortex/cli/main.py` y `cortex/cli/session.py` — agregar flag en `finish-session` y `session close`.
- `cortex/mcp/server.py` — agregar param `interactive: bool = False` en `cortex_finish_session`.

**Comportamiento:**

```bash
cortex finish-session --interactive
# o
cortex session close --interactive

cortex finish-session                # auto (default)
cortex finish-session --interactive  # interactive
```

Si en config.yaml está `documenter.default_mode: interactive`, el default invierte.

**Tests:**
- Flag respetado.
- Config override respetado.
- CLI override de config: `--no-interactive` fuerza auto.

---

### T4.3 — Configuración `documenter.default_mode`

**Archivos a modificar:**
- `cortex/setup/` — agregar campo al config inicial.
- `cortex/services/` o donde se cargue `config.yaml` — leer el campo.

**Config schema:**

```yaml
# .cortex/config.yaml
documenter:
  default_mode: auto    # auto | interactive
  # ... otros campos ...
```

**Validación:** valor válido o error claro.

**Tests:**
- Default es `auto`.
- Config interactive activa el modo.
- Setup respeta el flag al inicializar (opcional: agregar prompt en `cortex setup agent`).

---

### T4.4 — Doctor completo

**Archivos a modificar:**
- `cortex/doctor.py` — agregar sección "Pluggable Middle Health".

**Validaciones a agregar:**

```python
def check_pluggable_middle_health(layout, services) -> list[DoctorCheck]:
    checks = []

    # 1. WorkspaceLayout v2
    checks.append(verify_v2_layout(layout))

    # 2. Sessions infrastructure
    checks.append(verify_sessions_dir(layout))
    checks.append(verify_no_corrupted_sessions(layout))
    checks.append(verify_active_session_pointer(layout))

    # 3. MCP tools registered
    checks.append(verify_mcp_tools_registered(["cortex_session_open", "cortex_session_checkpoint", ...]))

    # 4. Documenter modes
    checks.append(verify_documenter_reconstruction_invocable())
    checks.append(verify_documenter_legacy_yaml_invocable())  # si aún existe

    # 5. Autopilot policies
    checks.append(verify_autopilot_policy_config(layout))

    # 6. Hooks IDE
    for adapter_name in ["claude-code", "cursor", "pi"]:
        checks.append(verify_hook_adapter_status(adapter_name, layout))

    # 7. Verification hooks runner
    checks.append(verify_verification_runner_invocable())

    return checks
```

**Output ejemplo:**

```
🏥 Cortex Doctor

[workspace]
  ✓ Layout v2 detected at .cortex/

[sessions]
  ✓ Directory writable
  ✓ Active session: 2026-05-16_auth-jwt-refresh
  ✓ 12 sessions on disk parsed correctly
  ✓ No invariant violations

[mcp]
  ✓ 14 tools registered (incluye 6 session_*)

[documenter]
  ✓ Reconstruction mode invocable
  ✓ Legacy YAML mode invocable (deprecated)

[autopilot]
  Mode: assist
  ✓ Policy config valid
  Hooks:
    ✓ claude-code (project, version 1.0)
    ✗ cursor (not installed)
    n/a pi (Pi not detected)

[verification]
  ✓ Verification runner invocable
  Active session hooks: 3 declared (last run: 5m ago, all passed)

Overall: ✅ Healthy
```

**Tests:** mockear escenarios degraded.

---

### T4.5 — README y Manifiesto

**Archivos a modificar:**
- `C:\Cortex\README.md` — sección "Modelo de Ejecución" final.
- `C:\Cortex\CHANGELOG.md` — entrada Pluggable Middle.

**Cambios en README:**

1. Reemplazar la sección "El Modelo de Ejecución Tripartito" por "Modelo Pluggable Middle".
2. Actualizar tabla de comandos: agregar todos los `cortex session ...`, `cortex finish-session`.
3. Actualizar la sección "Novedades Recientes" mencionando la arquitectura nueva.
4. Agregar enlace destacado a `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`.

**Cambios en CHANGELOG.md:**

Entrada major:

```markdown
## [Unreleased] - Pluggable Middle Architecture

### Added
- **Session primitive** (`cortex.session`): tracking lifecycle from spec creation to documentation persistence.
- **Three operating modes:**
  - Managed: `cortex-SDDwork` (recomended for beginners).
  - Observed: bring your own agent + IDE hooks emit checkpoints automatically.
  - BYO: develop with anything, Cortex reconstructs from diff.
- **Verification hooks** (mandatory in specs): executable commands that prove work is done.
- **CLI:** `cortex session list/show/diff/switch/abandon/...`
- **CLI:** `cortex finish-session` (replaces direct documenter invocation).
- **CLI:** `cortex session hooks install --ide claude-code|cursor|pi`
- **MCP tools:** `cortex_session_*` (5), `cortex_finish_session`.
- **Documenter interactive mode** (`--interactive` flag).

### Changed
- `cortex-SDDwork` now emits checkpoints instead of YAML handoffs.
- Subagents `cortex-code-explorer` and `cortex-code-implementer` emit checkpoints.
- Spec template now requires `verification_hooks`.
- `cortex/services/session_service.py` renamed to `note_service.py` (alias kept for compat).
- Autopilot reescrito como thin layer sobre Sessions.

### Deprecated
- `cortex_validate_handoff` MCP tool (kept for legacy YAML mode).
- Legacy YAML inline handoffs between subagents.

### Removed
- `cortex/autopilot/state_store.py` (Sessions handles persistence).
- `cortex/autopilot/session_builder.py`, `session_writer.py` (Documenter handles persistence).
```

---

### T4.6 — Migration guide

**Archivos a crear:**
- `C:\Cortex\docs\pluggable-middle\MIGRATION-FROM-TRIPARTITO.md`

**Contenido:**

```markdown
# Migration Guide: Tripartito → Pluggable Middle

## TL;DR

Si venías usando Cortex con el modelo tripartito obligatorio (sync → SDDwork → documenter), la arquitectura nueva mantiene ese flujo intacto bajo el modo **Managed**. No tenés que cambiar nada.

Si querés aprovechar la nueva libertad: leé este doc.

## Mapping de conceptos

| Antes | Después |
|---|---|
| Flujo obligatorio sync→SDDwork→documenter | Modo Managed (uno de tres) |
| `cortex save-session` directo | `cortex finish-session` |
| YAML handoffs entre subagents | Checkpoints en la Session |
| Autopilot lifecycle separado | Sessions como base + Autopilot policies encima |

## Comandos: qué cambió

(tabla detallada)

## Flujos de trabajo: ejemplos antes/después

(ejemplos lado a lado)
```

---

### T4.7 — Tests E2E del modo interactive

**Archivos a crear:**
- `tests/e2e/test_interactive_flow.py`

**Escenarios:**

```python
def test_interactive_approve_default(tmp_repo_with_cortex, mock_console):
    """
    Setup: spec + manual changes + finish-session --interactive.
    Acción simulada: usuario teclea [A].
    Assert: session note persiste con default body, ADRs sugeridos aceptados.
    """

def test_interactive_edit_body(tmp_repo_with_cortex, mock_console, mock_editor):
    """
    Acción: usuario teclea [E] → editor abre → escribe nuevo cuerpo → cierra.
    Assert: session note tiene el cuerpo editado.
    """

def test_interactive_handoff(tmp_repo_with_cortex, mock_console):
    """
    Acción: usuario teclea [H] → reason → confirma.
    Assert: status=HANDOFF, blockers en session note.
    """

def test_interactive_cancel(tmp_repo_with_cortex, mock_console):
    """
    Acción: usuario teclea [C].
    Assert: session sigue OPEN, no se persistió nada.
    """

def test_interactive_reject_adr(tmp_repo_with_cortex, mock_console):
    """
    Acción: usuario teclea [E] → ADR submenu → reject uno → [A]probar.
    Assert: session note creada, pero ese ADR NO existe en vault/adrs/.
    """
```

---

### T4.8 (OPCIONAL) — Decisión sobre Legacy YAML

**Solo ejecutar si se decide eliminar.** Re-evaluar en §3.4.

**Si se elimina:**

**Archivos a modificar:**
- `cortex/handoff.py` — marcar deprecated o eliminar.
- `cortex/mcp/server.py` — quitar `cortex_validate_handoff`.
- `.cortex/subagents/cortex-documenter.md` — eliminar sección "Modo Legacy YAML".
- `cortex/agent_guidelines.md` — actualizar references.
- Cualquier doc que mencione legacy YAML.

**Tests:** asegurar que ningún test depende del legacy.

**Si NO se elimina:**

Solo agregar pruebas adicionales de deprecation warnings y documentar claramente en el subagent que es legacy/deprecated.

---

### T4.9 — Documentación final

**Archivos a modificar:**
- `C:\Cortex\docs\pluggable-middle\README.md` — marcar Fase 04 ✅; agregar sección "Implementation complete" con fecha.
- `C:\Cortex\docs\architecture\session-primitive.md` — versión final con toda la info.
- `C:\Cortex\docs\architecture\pluggable-middle-overview.md` (nuevo) — versión corta del documento maestro para quien no quiere leer las 800 líneas.
- `C:\Cortex\docs\autopilot/` — verificar que todos los docs reflejen el modelo nuevo.

---

### T4.10 — Validación final exhaustiva

**Objetivo:** correr toda la batería de tests del proyecto + smokes manuales para confirmar el estado final.

**Acciones:**

1. `pytest tests/` completo, con `--cov`.
2. `mypy --strict cortex/`.
3. `ruff check . && ruff format --check .`.
4. Manual smoke de los 3 modos:
   - **BYO:** crear spec, picar a mano, finish.
   - **Managed:** crear spec, simular checkpoint de SDDwork, finish.
   - **Observed:** crear spec, instalar hook git, commit, finish.
5. Manual smoke del modo interactive: finish-session --interactive, probar las 4 acciones.
6. `cortex doctor` retorna `✅ Healthy`.

**Definition of Done T4.10:**
- Todo verde.
- 0 warnings inesperados.
- 0 deuda técnica nueva introducida.

---

## 5. Cross-cutting concerns

### 5.1 Backward compatibility final

- Mantener aliases CLI (`cortex autopilot ...`, `cortex save-session`).
- Mantener MCP tools deprecadas con warnings.
- Si se elimina Legacy YAML, **es un breaking change major**. Documentar prominentemente en CHANGELOG.

### 5.2 Calidad de UX

El modo interactivo es **lo que el usuario va a sentir** del framework. Calidad de wording, colores legibles, prompts claros.

Reglas:
- Mensajes en español (consistente con el resto del proyecto).
- Hotkeys con feedback inmediato.
- Cancel siempre disponible y sin consecuencias.
- Mensajes de error con sugerencia accionable.

### 5.3 Documentación coherente

Al cierre de esta fase, todos los docs deben hablar del mismo modelo. Hacer un audit final:

```bash
grep -ri "modelo tripartito" docs/    # ¿hay referencias viejas?
grep -ri "Tripartita Refinada" docs/  # idem
```

Si quedan referencias viejas, actualizarlas.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Full test suite
pytest tests/ -v --cov=cortex --cov-report=term-missing
# all green; coverage > 85% global

# 2. Type checking total
mypy --strict cortex/
# clean

# 3. Lint total
ruff check . && ruff format --check .
# clean

# 4. Doctor
cortex doctor
# expected: Overall: ✅ Healthy

# 5. Modo BYO smoke
# (en repo temp)
cortex create-spec --title "byo final smoke" \
  --goal "..." \
  --verification-hook 'name=t;command=test -f f.txt'
echo "hi" > f.txt; git add f.txt; git commit -m "x"
cortex finish-session
# expected: closed OK

# 6. Modo Managed smoke
cortex create-spec --title "managed final smoke" \
  --goal "..." \
  --verification-hook 'name=t;command=test -f g.txt'
echo "hi" > g.txt; git add g.txt; git commit -m "y"
cortex session checkpoint --source cortex-SDDwork --note "managed"
cortex finish-session
# expected: closed OK, mode=managed

# 7. Modo Observed smoke
cortex session hooks install --ide cursor  # git post-commit
cortex create-spec --title "observed final smoke" \
  --goal "..." \
  --verification-hook 'name=t;command=test -f h.txt'
echo "hi" > h.txt; git add h.txt; git commit -m "z"
# hook debió emitir checkpoint
cortex finish-session
# expected: closed OK, mode=observed

# 8. Interactive smoke
cortex create-spec --title "interactive smoke" \
  --goal "..." \
  --verification-hook 'name=t;command=true'
cortex finish-session --interactive
# manual: probar [A], [E], [H], [C]

# 9. Verificación que NO quedó deuda
grep -r "TODO\|FIXME\|XXX" cortex/ | grep -v test
# expected: vacío o solo justified comments
```

---

## 7. Cierre del proyecto

Al cerrar Fase 04:

### Estado final esperado

- Los 3 modos funcionan E2E.
- El modo interactivo está disponible.
- El framework completo está documentado.
- El doctor valida toda la infra.
- Cero deuda técnica abierta en lo nuevo.
- README y Manifiesto reflejan el modelo final.
- CHANGELOG completo.

### Roadmap post-MVP (no incluido en este plan)

Ideas que pueden venir DESPUÉS (no parte de las 4 fases):

- Hooks IDE adicionales: opencode, JetBrains nativo, GitHub Codespaces.
- Web UI para visualizar Sessions en tiempo real.
- Integraciones cloud para checkpoints multi-dispositivo.
- Plugin para CI: validar PRs contra session notes.

### Hand-off al "después"

- Crear issue o doc roadmap nuevo con las ideas post-MVP.
- Limpiar `docs/pluggable-middle/fases/_internal/` (notas privadas de las fases).
- Considerar mover `docs/pluggable-middle/` a `docs/architecture/pluggable-middle/` (más permanente).
- Eliminar referencias a "Pluggable Middle como propuesta" → ahora es **el modelo de Cortex**.

---

## 8. Progress Log

- [ ] T4.1 — Modo interactive (`cortex/documenter/interactive.py`)
- [ ] T4.2 — Flag `--interactive` en CLI/MCP
- [ ] T4.3 — Configuración `documenter.default_mode`
- [ ] T4.4 — Doctor completo
- [ ] T4.5 — README + CHANGELOG
- [ ] T4.6 — Migration guide
- [ ] T4.7 — Tests E2E modo interactive
- [ ] T4.8 — (Opcional) Decisión Legacy YAML
- [ ] T4.9 — Documentación final
- [ ] T4.10 — Validación final exhaustiva
- [ ] Completion Verification Commands TODOS pasan
- [ ] Tabla en `../README.md` actualizada ✅
- [ ] Commit final con mensaje semántico

---

## 9. Notas para el agente ejecutor

- **Esta es la última fase. La calidad importa más que la velocidad.**
- **Modo interactivo:** probar UX manualmente, no alcanza con unit tests. Si "se siente raro", arreglar.
- **No agregues features fuera del plan.** Si surgen ideas, anotarlas en el roadmap post-MVP, no implementarlas acá.
- **Migration guide:** aunque no hay usuarios reales hoy, el doc es para mañana. Escribilo como si tuvieras 100 adoptantes esperándolo.
- **Validación exhaustiva (T4.10):** es el sello de calidad final. Si falla algo, no cerrar la fase. Arreglar y re-verificar.
- **Al final:** dejá el repo en un estado que vos mismo (en otra sesión, sin contexto) pudieras retomar entendiendo todo. Esa es la prueba última de la documentación.
