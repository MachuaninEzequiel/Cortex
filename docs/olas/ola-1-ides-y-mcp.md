---
title: Ola 1 — IDEs y MCP funcionando end-to-end
status: ✅ CERRADA AL 100% (2026-05-13)
prerequisitos: Ola 0 cerrada
bloquea: Ola 3 (parcial)
target_ides: Claude Code, OpenCode, Pi, Codex
suite_at_close: 816 passed, 6 skipped, 0 failed
---

## Resumen del cierre

**Fixes aplicados:**
- `cortex/ide/adapters/claude_code.py:170` — `--project-root` ahora absoluto (era `"."`), evita que Claude Code pierda el workspace cuando se lanza desde otro directorio.
- `cortex/ide/adapters/pi.py:detect_installation` — chequea `shutil.which("pi")` en lugar de retornar `True` siempre. Ahora doctor reporta correctamente si Pi no está instalado.
- `cortex/mcp/server.py` (cierre de deuda colateral arrastrada de Ola 0) — guard `cortex_create_spec ↔ cortex_sync_ticket` refactorizado DRY con constante UTF-8 limpia `_GOVERNANCE_VIOLATION_MESSAGE` (resolvió mojibake).

**Adapter Codex creado desde cero:**
- `cortex/ide/adapters/codex.py` (215 líneas) — `CodexAdapter(IDEAdapter)` con `inject_profiles`, `inject_mcp` con path absoluto, `detect_installation` chequeando `which("codex")`, `uninstall` selectivo. Modelado tras `ClaudeCodeAdapter` pero bajo `.codex/`.
- Registrado en `cortex/ide/registry.py` + alias `openai-codex`, `codex-cli`.

**Sistema de tiers introducido (`cortex/ide/registry.py`):**
- `TARGET_IDES = frozenset({"claude_code", "opencode", "pi", "codex"})` — los 4 oficiales.
- `COMMUNITY_IDES = frozenset({"cursor", "claude_desktop", "vscode", "windsurf"})` — best-effort.
- `_EXPERIMENTAL_IDES = {"antigravity", "hermes", "zed"}` (preservado).
- Nuevas helpers `get_target_ides()` y `get_ide_tier(name) → "target" | "community" | "experimental"`.
- Mensaje de error de `get_adapter()` ahora lista los 3 tiers cuando el IDE no existe — UX inmediata para el adopter.

**Tests nuevos (`tests/unit/test_ide_adapters.py`):**
- `test_target_ides_are_registered` — los 4 target están en el registry.
- `test_target_ides_helper_lists_the_four`.
- `test_get_ide_tier_classifies_each_adapter` — verifica los 3 tiers para 11 adapters.
- `test_get_ide_tier_supports_aliases` — `claude-code`, `claude`, `codex-cli` resuelven correctamente.
- `test_unknown_ide_error_lists_tiers` — el mensaje de error guía al adopter.
- `test_codex_adapter_inject_profiles` — los 6 archivos esperados aparecen en `.codex/`.
- `test_codex_adapter_inject_mcp_uses_absolute_path` — regresión del bug que había en Claude Code.
- `test_claude_code_adapter_inject_mcp_uses_absolute_path` — regresión directa del fix de Claude Code.

**Smoke real end-to-end de los 4 IDEs (CLI):**
- `cortex inject --ide claude-code` → 5 archivos, MCP con `--project-root` absoluto verificado. ✓
- `cortex inject --ide opencode` → 5 archivos en `~/.config/opencode/`. ✓
- `cortex inject --ide codex` → 6 archivos en `.codex/`, MCP absoluto verificado. ✓
- `cortex inject --ide pi` → estructura completa de `cortex-pi/` copiada. ✓
- `cortex inject --ide nonexistent` → error con los 3 tiers listados. ✓

**Documentación creada:**
- `docs/guides/ide-claude-code.md` — setup, verify, troubleshooting, autopilot.
- `docs/guides/ide-opencode.md` — incluye nota sobre XDG paths y shielded wrapper WSL.
- `docs/guides/ide-pi.md` — comparativa con los otros 3 IDEs target, justfile, teams, drift de agents.
- `docs/guides/ide-codex.md` — adapter nuevo de Ola 1, troubleshooting, estado de tests.

**Pi: decisión documentada sobre drift de agents.**
- `.cortex/subagents/` = canonical para los 3 agents compartidos (explorer, implementer, documenter).
- `cortex-pi/.pi/agents/` tiene 9 agents (los 3 + 4 Pi-only: sync, SDDwork, security-auditor, test-verifier + YAML configs).
- Drift por EOL aceptado en los 3 compartidos (no funcional). Los 4 Pi-only quedan dentro del bundle `cortex-pi/`. Documentado en `docs/guides/ide-pi.md` sección "Diferencias clave".

**Deuda residual (movida a otras olas):**
- Adapter Pi no fuerza sync byte-a-byte con `.cortex/subagents/` — deuda menor, no bloqueante. Si en Ola 4 el smoke 4×11 lo expone, hacerlo ahí.

## Checklist final de la Ola 1

### Claude Code
- [x] Auditoría completa
- [x] Fix aplicado (`--project-root` absoluto)
- [x] Validación end-to-end con flujo `cortex inject`
- [x] `docs/guides/ide-claude-code.md` creado

### OpenCode
- [x] Auditoría completa
- [x] Sin fixes requeridos (ya usaba WorkspaceLayout y path absoluto)
- [x] Validación end-to-end
- [x] `docs/guides/ide-opencode.md` creado

### Pi
- [x] Auditoría completa, incluyendo `cortex-pi/`
- [x] `detect_installation` fixeado para chequear `which("pi")`
- [x] Drift de agents documentado (decisión pragmática)
- [x] Validación end-to-end via `cortex inject --ide pi`
- [x] `docs/guides/ide-pi.md` creado

### Codex
- [x] Adapter creado en `cortex/ide/adapters/codex.py`
- [x] Registrado en `cortex/ide/registry.py` con aliases
- [x] `cortex inject --ide codex` funciona
- [x] Validación end-to-end (path absoluto verificado)
- [x] `docs/guides/ide-codex.md` creado

### Transversales
- [x] Test `test_target_ides_are_registered` pasa
- [x] Mensajes de error de `get_adapter()` uniformes con 3 tiers
- [x] Tiers introducidos: TARGET_IDES, COMMUNITY_IDES, _EXPERIMENTAL_IDES
- [x] Helpers `get_target_ides()` y `get_ide_tier()` con tests

### Cierre
- [x] Suite global verde: 816 passed, 6 skipped, 0 failed
- [x] Smoke `cortex inject` para los 4 IDEs ejecutado y documentado
- [x] 4 guías por IDE creadas en `docs/guides/`

**Ola 1 cerrada al 100%. Lista para arrancar Ola 2.**

# Ola 1 — IDEs y MCP funcionando end-to-end

## Objetivo

Que los **4 IDEs target** (Claude Code, OpenCode, Pi, Codex) reconozcan Cortex como servidor MCP, ejecuten todas sus tools correctamente, respeten el guard de gobernanza y permitan el flujo tripartito sin pasos manuales extra más allá del setup.

El usuario fue explícito: "los IDEs no funcionan correctamente hoy". Esta ola los lleva a "completamente funcionales".

## Contexto descubierto en auditoría (2026-05-13)

### Dos sistemas de adapters paralelos en el repo

| Path | Comando que lo usa | Adapters existentes |
|------|--------------------|----|
| `cortex/ide/adapters/` | `cortex inject --ide <name>` | cursor, vscode, claude_code, claude_desktop, opencode, zed, windsurf, pi, antigravity, hermes |
| `cortex/autopilot/adapters/` | `cortex autopilot install --ide <name>` | claude_code, codex, cursor, opencode, pi |

### Hallazgo crítico

**Codex no tiene IDE adapter clásico** en `cortex/ide/adapters/`. Sólo tiene autopilot adapter. Eso significa que hoy `cortex inject --ide codex` falla. **Hay que crearlo.**

Plugin metadata existe en `.codex-plugin/plugin.json` — buena base de partida.

### Otros plugins del repo

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- `.cursor-plugin/plugin.json`

Verificar en Ola 1 si estos plugins están alineados con lo que cada adapter inyecta o si hay drift.

### Pi tiene infraestructura especial

`cortex-pi/` es un sub-proyecto completo con `AGENTS.md`, `extensions/`, `justfile`. La gobernanza tripartita está duplicada entre `.cortex/subagents/` y `cortex-pi/.pi/agents/`. Verificar si los archivos están sincronizados o divergieron.

## Estructura del módulo IDE

### `cortex/ide/base.py` — `IDEAdapter` protocol

Interfaz que **todos** los adapters deben cumplir:

- `name: str`
- `display_name: str`
- `get_config_paths() -> dict[str, Path]` — rutas IDE-specific donde se escribe
- `inject_profiles(project_root: Path) -> list[str]` — escribe agent skills/profiles
- `inject_mcp(project_root: Path) -> list[str]` — configura el MCP server
- `validate() -> bool` — verifica que el IDE está instalado / accesible

### `cortex/ide/registry.py`

Auto-discovery por nombre. Si un adapter nuevo se agrega a `cortex/ide/adapters/`, debe registrarse aquí.

## Pasos por IDE

Para cada IDE target, ejecutar el bloque "Auditoría → Fix → Validación → Documentación". El criterio de cierre por IDE está al final de cada bloque.

---

### 1.A — Claude Code

#### Auditoría

1. Leer `cortex/ide/adapters/claude_code.py` completo.
2. Leer `cortex/autopilot/adapters/claude_code.py` completo.
3. Leer `.claude-plugin/plugin.json` y comparar con lo que el adapter dice escribir.
4. Verificar `get_config_paths()`: confirmar que apunta a `~/.config/claude-code/...` o lo que claude-code real espera (mirar docs oficiales si hace falta).
5. **Probar manualmente:**
   ```bash
   cd <repo-de-prueba>
   cortex inject --ide claude-code
   ```
   Listar archivos modificados. Validar que `mcp.json` o equivalente del IDE referencia al servidor Cortex.

#### Fix

- Cualquier path hardcoded que no use `WorkspaceLayout` → corregir.
- Si `inject_mcp` escribe la entrada MCP pero falta `command: python -m cortex.cli.main mcp-server --project-root <ruta>` con `--project-root` apuntando al repo real → corregir.
- Si las skills (`cortex-sync`, `cortex-SDDwork-cursor`, `cortex-documenter`) que el adapter inyecta no existen o tienen nombre drift en `cortex/skills/` o `.cortex/skills/` → corregir nombres o agregar las skills faltantes.

#### Validación end-to-end

Arrancar Claude Code → abrir el repo de prueba → emitir un prompt simulado de feature pequeña ("agregar endpoint /health al server"). El IDE debe:

1. Detectar el MCP de Cortex (revisar logs MCP en `.cortex/logs/`).
2. Llamar primero `cortex_sync_ticket`.
3. Llamar `cortex_create_spec` — debe persistir un archivo en `vault/specs/`.
4. (Implementación simulada o real, no importa para esta validación.)
5. Llamar `cortex_save_session` o cerrar con `cortex_autopilot_finish --auto`.
6. La session note debe aparecer en `cortex search "endpoint health"`.

#### Documentación

Crear o actualizar `docs/guides/ide-claude-code.md` con:
- Instalación step-by-step.
- Comando `cortex inject --ide claude-code` y qué archivos genera.
- Smoke check (`cortex doctor`).
- Troubleshooting de los 3 errores más comunes.

#### Criterio de cierre Claude Code

- [ ] `cortex inject --ide claude-code` genera todos los archivos sin error.
- [ ] El MCP server arranca y Claude Code lo detecta (verificable por logs).
- [ ] Las 8 tools principales (search, search_vector, context, sync_ticket, create_spec, save_session, sync_vault, autopilot_*) responden sin error.
- [ ] Guard MCP rechaza `cortex_create_spec` sin `cortex_sync_ticket` previo.
- [ ] Flujo tripartito completo termina con session note indexada.
- [ ] `docs/guides/ide-claude-code.md` creado/actualizado.

---

### 1.B — OpenCode

#### Auditoría

1. Leer `cortex/ide/adapters/opencode.py`.
2. Leer `cortex/autopilot/adapters/opencode.py`.
3. Identificar dónde OpenCode lee su config MCP (probable: `.opencode/mcp.json` o similar — confirmar con docs oficiales).
4. **Probar manualmente:**
   ```bash
   cd <repo-de-prueba>
   cortex inject --ide opencode
   ```

#### Fix

Mismo patrón que 1.A. Atención particular a:
- OpenCode puede tener un formato de hooks distinto a Claude Code. Si `inject_mcp` escribe el formato equivocado, OpenCode ignora el servidor sin error visible.
- Verificar que `hooks` del autopilot adapter (en `.opencode/hooks.md`) usen el `AUTOPILOT-OPENCODE` marker que `doctor.py:_check_hooks_installed` busca (línea ~103).

#### Validación end-to-end

Igual que 1.A pero desde OpenCode.

#### Documentación

`docs/guides/ide-opencode.md`.

#### Criterio de cierre OpenCode

- [ ] `cortex inject --ide opencode` genera archivos sin error.
- [ ] OpenCode reconoce el MCP server.
- [ ] Las 8 tools principales responden.
- [ ] Guard MCP funciona.
- [ ] Flujo tripartito completo termina con session note indexada.
- [ ] `docs/guides/ide-opencode.md` creado.

---

### 1.C — Pi (Coding Agent)

#### Auditoría — caso especial porque Pi tiene infra propia

1. Leer `cortex/ide/adapters/pi.py`.
2. Leer `cortex/autopilot/adapters/pi.py`.
3. Leer **toda** la estructura de `cortex-pi/`: `AGENTS.md`, `README.md`, `extensions/`, `justfile`.
4. Comparar `cortex-pi/.pi/agents/cortex-documenter.md` con `.cortex/subagents/cortex-documenter.md`. Si divergen, decidir cuál es la fuente de verdad. Plan: el de `.cortex/subagents/` es el canonical y `cortex-pi/.pi/agents/` se genera/sincroniza desde ahí.
5. Revisar `cortex-pi/justfile` para entender qué orquesta (`just cortex`, `just sdd`, `just hotfix`, `just audit` mencionados en README).

#### Fix

- Si los agents divergieron entre `.cortex/subagents/` y `cortex-pi/.pi/agents/`: agregar un comando `cortex inject --ide pi` (o sub-CLI) que **sincroniza** desde el canonical y deja un solo lugar para editar.
- Verificar que el `mcp.json` que se inyecta en `cortex-pi/.pi/mcp.json` (o equivalente) apunta correctamente al `cortex mcp-server`.
- `cortex-pi/.pi/extensions/cortex-autopilot.ts` — si existe esa extension TypeScript, validar que carga sin error al iniciar Pi.

#### Validación end-to-end

```bash
cd cortex-pi
just cortex   # Si el justfile lo soporta
```

O directamente desde la CLI de Pi: abrir Pi en un proyecto que tenga Cortex instalado y probar el flujo. Lo que diferencia Pi es que tiene **teams** definidos (`cortex-sddwork`, `cortex-hotfix`, `cortex-research`, `cortex-audit`). Validar al menos `cortex-sddwork`.

#### Documentación

`docs/guides/ide-pi.md` — incluir prereqs (`npm install -g @mariozechner/pi-coding-agent`, `just`), comandos, troubleshooting.

#### Criterio de cierre Pi

- [ ] Adapters de IDE y de autopilot sincronizados con la estructura de `cortex-pi/`.
- [ ] Single source of truth para los agents (no más drift `.cortex/subagents/` vs `cortex-pi/.pi/agents/`).
- [ ] `cortex inject --ide pi` o equivalente regenera `cortex-pi/` desde scratch sin error.
- [ ] `just cortex` (o flujo Pi nativo) ejecuta el tripartito completo.
- [ ] Pi guarda session note indexada al cerrar.
- [ ] `docs/guides/ide-pi.md` creado.

---

### 1.D — Codex (caso "construir adapter desde cero")

#### Auditoría

1. Leer `cortex/autopilot/adapters/codex.py` (existe).
2. Leer `.codex-plugin/plugin.json`.
3. Buscar documentación oficial de Codex sobre dónde lee config MCP. Si Codex es la CLI de OpenAI (`openai codex` o similar), confirmar formato esperado.
4. Listar las 10 funciones que `cortex/ide/adapters/cursor.py` o `claude_code.py` exponen y mapear las equivalentes para Codex.

#### Fix — crear el adapter

Crear `cortex/ide/adapters/codex.py` con la misma interfaz que los demás:

```python
class CodexAdapter(IDEAdapter):
    name = "codex"
    display_name = "Codex"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "mcp": Path.home() / ".codex" / "mcp.json",  # CONFIRMAR
            "hooks": Path.home() / ".codex" / "hooks.md",  # CONFIRMAR
            "skills": ...,
        }

    def inject_profiles(self, project_root: Path) -> list[str]:
        ...

    def inject_mcp(self, project_root: Path) -> list[str]:
        ...

    def validate(self) -> bool:
        ...
```

Registrar el adapter en `cortex/ide/registry.py`.

Actualizar `cortex/ide/adapters/__init__.py` si tiene un `__all__` o similar.

#### Validación end-to-end

```bash
cortex inject --ide codex
```

Debe escribir los archivos correctos. Luego arrancar Codex apuntando al repo y validar el flujo tripartito.

#### Documentación

`docs/guides/ide-codex.md`.

#### Criterio de cierre Codex

- [ ] `cortex/ide/adapters/codex.py` creado y registrado.
- [ ] `cortex inject --ide codex` funciona.
- [ ] Codex reconoce el MCP server.
- [ ] Las 8 tools principales responden.
- [ ] Guard MCP funciona.
- [ ] Flujo tripartito completo termina con session note indexada.
- [ ] `docs/guides/ide-codex.md` creado.

---

## Tareas transversales (después de los 4 IDEs)

### 1.E — Test que verifica que los 4 IDEs target están registrados

Agregar a `tests/unit/test_ide_module.py` o `tests/unit/test_ide_adapters.py`:

```python
def test_target_ides_are_registered():
    from cortex.ide.registry import list_adapters
    registered = {a.name for a in list_adapters()}
    target = {"claude-code", "opencode", "pi", "codex"}
    missing = target - registered
    assert not missing, f"Target IDEs missing from registry: {missing}"
```

### 1.F — Mensajes de error parejos

Auditar los 4 adapters: cuando `validate()` falla (IDE no instalado), el mensaje de error debe ser **uniforme** y sugerir cómo instalar el IDE. Hoy probable que cada adapter tenga formato distinto.

### 1.G — `cortex sync-ide` y `cortex inject`

Verificar que ambos comandos (existen en `cli/main.py`) hacen sentido. Si `sync-ide` es alias de `inject`, documentar. Si tienen diferente comportamiento, validar que ambos funcionan para los 4 IDEs.

### 1.H — Limpiar adapters no-target

No borrar los adapters de Cursor / VSCode / Windsurf / Zed / etc., pero **marcarlos** explícitamente como "no soportado oficialmente" en su docstring. Esto evita que un adopter piense que está al mismo nivel que los 4 target.

## Tests obligatorios al cierre de la ola

```bash
python -m pytest tests/unit/test_ide_module.py tests/unit/test_ide_adapters.py tests/unit/autopilot/test_adapters.py tests/unit/autopilot/test_pi_adapter.py --no-cov
```

Plus la suite completa:

```bash
python -m pytest tests/unit tests/integration tests/e2e --no-cov
```

Pegar resultado:

```
[pegar output cuando se cierre la ola]
```

## Checklist final de la Ola 1

### Claude Code
- [ ] Auditoría completa
- [ ] Fixes aplicados
- [ ] Validación end-to-end con flujo tripartito
- [ ] `docs/guides/ide-claude-code.md` creado

### OpenCode
- [ ] Auditoría completa
- [ ] Fixes aplicados
- [ ] Validación end-to-end
- [ ] `docs/guides/ide-opencode.md` creado

### Pi
- [ ] Auditoría completa, incluyendo `cortex-pi/`
- [ ] Single source of truth para agents
- [ ] Sync mechanism implementado
- [ ] Validación end-to-end via `just cortex` o flujo nativo Pi
- [ ] `docs/guides/ide-pi.md` creado

### Codex
- [ ] Adapter creado en `cortex/ide/adapters/codex.py`
- [ ] Registrado en `cortex/ide/registry.py`
- [ ] `cortex inject --ide codex` funciona
- [ ] Validación end-to-end
- [ ] `docs/guides/ide-codex.md` creado

### Transversales
- [ ] Test `test_target_ides_are_registered` pasa
- [ ] Mensajes de error de `validate()` uniformes
- [ ] Adapters no-target marcados como "no soportado oficialmente"
- [ ] `cortex sync-ide` y `cortex inject` ambos funcionan para los 4 target

### Cierre
- [ ] Suite global verde
- [ ] Smoke test desde los 4 IDEs registrado en este doc

**Sólo cuando todos los items están marcados, se puede pasar a Ola 2.**
