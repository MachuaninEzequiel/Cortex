# FASE 6 — REALIZACION

**Fecha de ejecucion:** 2026-05-15
**Output formal:** Helper compartido `cortex/cli/_setup_helpers.py` + `setup_agent` y `setup_full` refactorizados para invocarlo + tests dedicados.
**Estado:** Completada. **734 tests verdes** (16 nuevos de Fase 6 + 718 preexistentes). Linter ruff verde sobre archivos Fase 6.

---

## 1. Tasks ejecutadas en orden

| Task | Descripcion | Archivo principal |
|---|---|---|
| 6.1 | Crear helper `select_ide_interactive` | `cortex/cli/_setup_helpers.py` (nuevo) |
| 6.2 | Refactor `setup_agent` para usar el helper + agregar `--non-interactive` | `cortex/cli/main.py` |
| 6.3 | Agregar seleccion interactiva a `setup_full` | `cortex/cli/main.py` |
| 6.4 | Tests del helper (10) + tests integracion CLI (6) | `tests/unit/cli/test_setup_helpers.py`, `tests/unit/cli/test_setup_commands_phase6.py` |
| 6.5 | REALIZACION + actualizar README plan | (este documento) |

---

## 2. Decisiones tomadas durante la realizacion

### 2.1 Helper en `cortex/cli/_setup_helpers.py` (no en `cortex/setup/`)

**Decision:** colocar el helper en `cortex/cli/`, no en `cortex/setup/orchestrator.py` ni en un modulo de `cortex/ide/`.

**Razon:**
- El helper usa `typer.prompt` y `typer.echo` — son CLI concerns, no setup concerns.
- Mantenerlo en `cortex/cli/` evita acoplar `cortex.setup` con `typer`.
- El nombre `_setup_helpers` (con prefijo underscore) marca claramente que es **modulo privado de la CLI** — los demas adapters/subsistemas no deben importarlo.

### 2.2 `--ide` tiene precedencia sobre `--non-interactive`

**Decision:** si el usuario pasa AMBOS `--ide claude_code --non-interactive`, devolver `claude_code` (no None).

**Razon:**
- `--ide` es un input EXPLICITO del usuario; respetarlo es mas predecible que ignorarlo.
- `--non-interactive` significa "no me preguntes nada" — no implica "no configures IDE". Si pidieron explicitamente un IDE, configuralo.
- Patron consistente con otros CLI tools (--config wins over --no-config).

Validado con tests `test_provided_ide_returned_as_is_noninteractive_mode`.

### 2.3 `--non-interactive` sin `--ide` -> `None` (sin prompt)

**Decision:** en CI sin IDE explicito, devolver `None` (skip IDE) en lugar de elegir un default.

**Razon:**
- Un default arbitrario (ej. "claude_code") seria sorpresivo en CI: el adopter no recordaria por que aparecio una config de Claude Code.
- `None` es honesto: "no me dijiste cual IDE, no asumi nada".
- El adopter siempre puede correr `cortex setup agent --ide X` despues si quiere.

Validado con test `test_noninteractive_without_ide_returns_none_no_prompt`.

### 2.4 `setup_agent` ahora soporta `--non-interactive` (paridad con `setup_full`)

**Decision:** agregar la flag `--non-interactive` a `setup_agent` (antes solo la tenian `setup_full` y `setup_pipeline`).

**Razon:**
- Sin esta flag, un script CI que quiera ejecutar SOLO `setup agent` no podia evitar el prompt de `git_depth` ni el menu de IDE.
- Paridad de flags entre los 3 comandos `setup_*` (agent / pipeline / full) reduce sorpresas.
- El comportamiento por default sigue igual: si NO se pasa `--non-interactive`, `setup_agent` prompt-ea como siempre.

Validado con test `test_setup_agent_now_supports_non_interactive_flag`.

### 2.5 Mensajes de prompt sin emojis en el helper

**Decision:** el helper imprime `"\nSelect IDE to configure:"` (sin emoji), aunque la version vieja en `setup_agent` usaba `"\n🔧 Select IDE to configure:"`.

**Razon:**
- Consistencia con la regla del repositorio: solo usar emojis cuando el usuario los pide o cuando son intencionales para la UX especifica de un comando. El menu del helper es generico (compartido entre `setup_agent` y `setup_full`).
- Los emojis se mantienen en los mensajes top-level de cada comando (`"🧠 Cortex — Setting up..."`) que son specific a la accion.
- En console Windows el emoji 🔧 a veces no renderiza bien (cp1252).

### 2.6 Tests de comandos via `CliRunner` con orchestrator mockeado

**Decision:** los 6 tests de integracion en `test_setup_commands_phase6.py` mockean `SetupOrchestrator` para no ejecutar setup real (que tocaria disco).

**Razon:**
- El alcance de Fase 6 es validar el FLUJO de seleccion de IDE en la CLI, NO el comportamiento del orchestrator (eso ya esta cubierto por sus propios tests en `tests/integration/setup/`).
- Mockear `SetupOrchestrator` permite tests rapidos (<2s) y deterministas que validan EXACTAMENTE lo que Fase 6 introdujo: el helper se invoca y el orchestrator recibe el `ide` correcto.
- Helper local `_fake_summary()` provee el shape minimo que `format_summary` necesita (claves `project_name`, `language`, `package_manager`, etc.) sin tocar disco.

---

## 3. Cumplimiento del gate de cero deuda tecnica de Fase 6

| Item del gate | Estado |
|---|---|
| `cortex setup full` (sin flags) prompt-ea por IDE | OK — bloque interactivo via helper. Validado por tests. |
| `cortex setup full --non-interactive` no prompt-ea | OK — `test_setup_full_non_interactive_skips_ide_prompt` lo verifica. |
| `cortex setup full --ide X` no prompt-ea | OK — `test_setup_full_with_ide_flag_skips_prompt`. |
| `cortex setup agent` mantiene comportamiento (prompt si no `--ide`) | OK — el helper preserva la logica original. |
| Helper es la unica implementacion del menu | OK — `test_setup_agent_calls_select_ide_helper` y `test_setup_full_calls_select_ide_helper` validan via `mock_helper.assert_called_once()`. |
| Tests cubren los 4 paths del helper (flag, non-interactive, interactivo valido, interactivo invalido) | OK — 10 tests del helper + 6 de integracion = 16 tests. |
| CERO duplicacion entre `setup_agent` y `setup_full` para seleccion de IDE | OK — el bloque interactivo de 20 lineas en `setup_agent` fue reemplazado por una sola llamada al helper. |
| CERO referencias en docs a "vieja forma" (correr 2 comandos) | OK — docstring de `setup_full` actualizada. |
| El helper no tiene dependencias circulares con `cortex.ide` ni con `cortex.setup.orchestrator` | OK — solo depende de `typer` y `cortex.ide` (lectura de lista de IDEs). |
| Tests cubren caminos felices Y infelices (input invalido) | OK — `test_interactive_choice_invalid_number_returns_none`, `test_interactive_choice_invalid_name_returns_none`. |
| Linter ruff verde sobre archivos Fase 6 | OK (1 warning preexistente UP042 en `cortex/cli/main.py:173` — clase `DoctorScope` heredando de `str, Enum`. NO introducido por Fase 6). |
| CERO TODOs/FIXMEs nuevos | OK. |

---

## 4. Lista exhaustiva de archivos tocados

### Nuevos

- `cortex/cli/_setup_helpers.py` (~70 lineas) — helper `select_ide_interactive` con docstring exhaustiva.
- `tests/unit/cli/test_setup_helpers.py` (10 tests).
- `tests/unit/cli/test_setup_commands_phase6.py` (6 tests de integracion CLI).

### Modificados

- `cortex/cli/main.py`:
  - `setup_agent`: bloque interactivo de 20 lineas reemplazado por llamada al helper. Agregada flag `--non-interactive` (paridad con `setup_full`).
  - `setup_full`: agregada llamada al helper antes de pasar `ide` al orchestrator. Docstring actualizada para reflejar el nuevo flujo.

### NO tocados (intencionalmente)

- `cortex/setup/orchestrator.py` — no necesita cambios; recibe el `ide` ya resuelto desde la CLI.
- `cortex/cli/main.py:setup_pipeline` — ya tenia `--non-interactive`, no maneja IDE (es solo CI/CD profile).

---

## 5. Verificacion final

### Helper paths (tests/unit/cli/test_setup_helpers.py)

| Path | Test |
|---|---|
| `--ide X` (interactivo) -> X sin prompt | `test_provided_ide_returned_as_is_interactive_mode` |
| `--ide X --non-interactive` -> X sin prompt | `test_provided_ide_returned_as_is_noninteractive_mode` |
| `--non-interactive` (sin --ide) -> None sin prompt | `test_noninteractive_without_ide_returns_none_no_prompt` |
| Interactivo, choice = "0" -> None | `test_interactive_choice_zero_returns_none` |
| Interactivo, choice = "1" -> primer IDE | `test_interactive_choice_by_number` |
| Interactivo, choice = "opencode" -> opencode | `test_interactive_choice_by_name` |
| Interactivo, choice = "99" (fuera de rango) -> None | `test_interactive_choice_invalid_number_returns_none` |
| Interactivo, choice = "garbage" -> None | `test_interactive_choice_invalid_name_returns_none` |
| Interactivo, choice = N (last) -> ultimo IDE | `test_interactive_choice_last_index` |
| Menu lista TODOS los IDEs soportados | `test_interactive_mode_displays_full_supported_list` |

### Integracion CLI (tests/unit/cli/test_setup_commands_phase6.py)

| Comando | Verificacion |
|---|---|
| `setup full --non-interactive --git-depth 50` | NO prompt; orchestrator recibe `ide=None` |
| `setup full --ide claude_code --non-interactive --git-depth 50` | NO prompt; orchestrator recibe `ide=claude_code` |
| `setup agent --non-interactive --git-depth 50` | NO prompt; orchestrator recibe `ide=None` (paridad con full) |
| `setup agent --ide opencode --non-interactive --git-depth 50` | NO prompt; orchestrator recibe `ide=opencode` |
| Helper se invoca en `setup_agent` | `mock_helper.assert_called_once()` |
| Helper se invoca en `setup_full` | `mock_helper.assert_called_once()` |

---

## 6. Items para handoff a Fase 7

Fase 6 desbloquea Fase 7 (Validacion E2E). Items concretos:

- El smoke test E2E debe ejercitar `cortex setup full --ide claude_code --non-interactive --git-depth 50` y verificar que el proyecto queda completamente listo (sin necesitar `setup agent` adicional).
- Reproducir el incidente del 2026-05-15 con un proyecto fresh creado via `cortex setup full --ide claude-code` (single command).

### ARRASTRE-3 (deuda preexistente, fuera de alcance)

`UP042` en `cortex/cli/main.py:173` — clase `DoctorScope(str, Enum)` debe usar `enum.StrEnum` (Python 3.11+ syntax). NO introducida por Fase 6. Documentada para Fase 7 o plan futuro.

---

## 7. Handoff formal

```yaml
agent: fase-6-setup-full-interactivo
status: completed
artifacts_produced:
  - cortex/cli/_setup_helpers.py (~70 lineas, nuevo)
  - tests/unit/cli/test_setup_helpers.py (10 tests)
  - tests/unit/cli/test_setup_commands_phase6.py (6 tests)
  - docs/multi-ide-mcp-hardening/FASE-6-REALIZACION.md (este documento)
artifacts_modified:
  - cortex/cli/main.py (refactor setup_agent + ampliacion setup_full)
verified_claims:
  - "734 tests verdes (16 nuevos de Fase 6 + 718 preexistentes)"
  - "Helper select_ide_interactive es la unica implementacion del menu"
  - "Cero duplicacion entre setup_agent y setup_full"
  - "setup_agent ahora soporta --non-interactive (paridad con setup_full)"
  - "setup_full ahora prompt-ea por IDE en modo interactivo"
  - "Tests cubren los 4 paths del helper + integracion via CliRunner con orchestrator mockeado"
  - "Linter ruff verde sobre archivos Fase 6"
unverified_claims: []
contradicted_claims: []
arrastre:
  - "ARRASTRE-3: UP042 en cortex/cli/main.py:173 (DoctorScope debe usar StrEnum). NO introducido por Fase 6."
context_for_next:
  - "Fase 7 (validacion E2E) es la ultima fase del plan; ejercitara cortex setup full --ide X end-to-end + reproducira el incidente del 2026-05-15"
suggested_adr: false
```
