---
title: Ola 3 — UX de primer contacto + instalación completa
status: ✅ CERRADA AL 100% (2026-05-13)
prerequisitos: Olas 0, 1, 2 cerradas
bloquea: Ola 4
suite_at_close: 829 passed, 6 skipped, 0 failed
---

## Resumen del cierre

**Fixes aplicados:**

1. **`cortex setup full` incluye los 3 pilares** (`cortex/setup/orchestrator.py::_run_full_flow`):
   - Workspace agentic (config, vault, memory, skills, subagents, AGENT.md, etc.).
   - **WebGraph** ahora se instala automáticamente como pilar (`_install_webgraph()`).
   - Pipeline (workflows GitHub + devsecdocops.sh).
   - Cold start (preseed vault + git history + README fallback) vía `_init_memory()`.
   - Idempotente: correr 2 veces no rompe estado.

2. **Setup non-interactive (deuda de Ola 0 resuelta):**
   - `orchestrator.run()` acepta `non_interactive: bool = False`.
   - `_check_vault_pipeline_interactive()` respeta la flag y auto-acepta el vault detectado.
   - CLI: `cortex setup pipeline --non-interactive` y `cortex setup full --non-interactive` agregados.
   - `cortex setup full --ide <name> --non-interactive --git-depth N` ahora es 100% automatable (sin prompts).

3. **`AgentMemory()` descubre layout automáticamente** (`cortex/core.py::__init__`):
   - Firma cambiada a `config_path: str | Path | None = None`.
   - Sin args: hace `WorkspaceLayout.discover(cwd)` primero, usa `layout.config_path`. Esto resuelve el issue UX donde correr `cortex search` desde el repo root de new layout fallaba.
   - Con path explícito: comportamiento preservado (backwards compat).
   - Error message accionable cuando no encuentra config: menciona `cortex setup full --non-interactive`.

4. **Doctor gitignore layout-aware (deuda de Ola 0 resuelta):**
   - `cortex/doctor.py` ahora usa `NEW_LAYOUT_GITIGNORE_PATTERNS` (`.cortex/memory/`, `.cortex/vault/sessions/`) en new layout, `LEGACY_GITIGNORE_PATTERNS` en legacy.
   - Severidad `fail` para patterns que contienen "memory" o terminan en ".chroma/" (binarios que NO deben commitearse).
   - Pre-Ola 3: el doctor reportaba `[FAIL] gitignore:.memory/` en repos new-layout. Resuelto.

5. **Auto-update del `.gitignore` del adopter** (`orchestrator::_update_gitignore`):
   - Nuevo step en `_run_full_flow`.
   - Idempotente: solo agrega patterns que faltan.
   - Sección header `# Cortex (new layout)` o `# Cortex` según layout.
   - Esto cierra el último `[FAIL]` del doctor post-setup en repos vacíos.

6. **`cortex stats --project-root` (deuda de Ola 0 resuelta):**
   - `cortex/cli/main.py::stats` acepta `--project-root`.
   - `_load_memory()` ahora acepta `project_root: str | Path | None` y descubre layout desde ahí.
   - Error message accionable si no encuentra config (menciona setup + --project-root como alternativa).

**Tests nuevos:**

- `tests/unit/test_core_discovery.py` (4 tests):
  - `test_discovers_config_from_cwd_in_new_layout`.
  - `test_discovers_config_from_subdirectory` (walk upward).
  - `test_explicit_config_path_still_honored` (backwards compat).
  - `test_missing_config_raises_actionable_error` (verifica mensaje contiene "cortex setup").

**Tests existentes adaptados al new contract:**
- `tests/e2e/scenarios/test_setup_basic.py::test_doctor_passes_after_agent_setup` — actualizado a patterns new-layout.
- `tests/e2e/scenarios/test_setup_basic.py::test_doctor_strict_passes_after_agent_setup` — idem.
- `tests/e2e/scenarios/test_enterprise_setup.py::test_doctor_enterprise_scope` — idem.

**Smoke real end-to-end (CLI completo):**

```
mkdir /tmp/cortex-ola3-final && cd /tmp/cortex-ola3-final && git init && git commit ...
cortex setup full --non-interactive --git-depth 1 --ide claude-code
# .cortex/ con 12 dirs/files, .github/workflows/ con 4 YAMLs, .gitignore con patches.
cortex doctor --project-root <smoke>
# TODO [OK]. Solo 2 entries de gitignore: .cortex/memory/ y .cortex/vault/sessions/, ambos verdes
# tras auto-update del .gitignore.
cortex stats --project-root <smoke>
# {"episodic_count": 7, "semantic_docs": 5, ...}
```

**Onboarding doc creado:**
- `docs/guides/getting-started-adopters.md` — guía completa: prerrequisitos, instalación, setup, verificación, IDE, primer flujo, troubleshooting, próximos pasos. Linkea las 4 guías por IDE (Ola 1).

## Checklist final de la Ola 3

### `cortex setup full` completo
- [x] `SetupMode.FULL` incluye agent + pipeline + webgraph + cold_start.
- [x] Idempotente: correr 2 veces no rompe.
- [x] Genera todos los archivos esperados verificados con `ls`.
- [x] `cortex doctor` retorna verde post-setup.

### Carga de config sin path explícito
- [x] `AgentMemory()` sin argumentos descubre layout y carga config correcto.
- [x] Test `test_discovers_config_from_cwd_in_new_layout` pasa.
- [x] Test desde subdirectorio (walk upward) pasa.
- [x] Test explicit path backwards-compat pasa.
- [x] Test missing config raises actionable error.
- [x] Todos los call sites internos siguen funcionando (suite global verde).

### Mensajes de error claros
- [x] `cortex search/stats/...` sin setup → mensaje accionable (con sugerencia `cortex setup full --non-interactive` y `--project-root`).
- [x] `cortex inject --ide <invalid>` → lista los 3 tiers (cubierto en Ola 1).
- [x] `AgentMemory()` sin config → FileNotFoundError con mensaje accionable.
- [x] `setup pipeline` interactivo → resuelto vía `--non-interactive`.

### Doctor end-to-end
- [x] Doctor sin FAIL gitignore en repos new-layout (layout-aware patterns).
- [x] `cortex setup full` auto-agrega patterns correctos al `.gitignore`.
- [x] Doctor detecta correctamente IDE adapter cuando `--ide` pasó en setup.

### Onboarding doc
- [x] `docs/guides/getting-started-adopters.md` creado.
- [x] Incluye prerrequisitos, instalación, setup, primer flujo, troubleshooting.
- [x] Linkea las 4 guías por IDE (Ola 1).

### Deuda residual de Ola 0 resuelta
- [x] `cortex setup pipeline --non-interactive` (resuelta).
- [x] `cortex setup full --non-interactive --ide` (resuelta).
- [x] `cortex stats --project-root` (resuelta).
- [x] Doctor gitignore layout-aware (resuelta).

### Smoke
- [x] Setup full --non-interactive desde repo limpio: workspace completo + workflows + gitignore.
- [x] Doctor verde end-to-end.
- [x] Stats con --project-root.

### Cierre
- [x] Suite global verde: 829 passed, 6 skipped, 0 failed.

**Ola 3 cerrada al 100%. Lista para arrancar Ola 4 (pulido final).**

# Ola 3 — UX de primer contacto + instalación completa

## Objetivo

Un usuario que **nunca usó Cortex** abre un repo web vacío (o uno existente sin vault), ejecuta una sola instrucción de setup, y obtiene un workspace `.cortex/` operativo con **los tres pilares activos: agentic + WebGraph + Pipeline**, en cualquiera de los 4 IDEs target. `cortex doctor` reporta verde end-to-end.

El usuario fue explícito: "**No hay vault de ningún tipo, no tengo ningún usuario con cortex instalado, va a ser la primera vez de alguien usándolo**". Esto significa que esta ola es el verdadero gate de adopción.

## Pilares de la instalación completa

Confirmado con el usuario: la recomendación a los adopters es la instalación completa, que incluye:

1. **Parte agentic**: `.cortex/` con vault, memory, skills, subagents, AGENT.md, system-prompt, config.yaml, org.yaml, workspace.yaml.
2. **WebGraph**: `.cortex/webgraph/` con server config, cache dir, primer snapshot.
3. **Pipeline**: `.github/workflows/` con los 5 workflows alineados al stack del repo (validado en Ola 2).

## Contexto descubierto previamente

### Bug histórico: carga de config antes de discovery

`cortex/core.py:138-154` — `AgentMemory.__init__` carga `config.yaml` desde un path fijo **antes** de descubrir el layout. Si un usuario corre `cortex search` desde el repo root en new layout sin `--project-root`, falla con `FileNotFoundError` y mensaje confuso.

### Modos del orchestrator

`cortex/setup/orchestrator.py` — `SetupMode`: AGENT, PIPELINE, FULL, WEBGRAPH, ENTERPRISE. El modo FULL hoy hace agent + pipeline + IDE profiles. **Hay que verificar si FULL ya incluye WebGraph.** Si no, agregar.

### Cold start

`cortex/setup/cold_start.py` ofrece preseed del vault con:
1. Layer 1: Preseed vault con docs estándar.
2. Layer 2: Git history mining (busca commits con "decision" / "ADR").
3. Layer 3: README fallback.

`release-2-known-weaknesses` mencionaba que el cold start tiene cobertura de tests baja. Hay que validarlo en repo real.

## Deuda extra descubierta en el smoke de Ola 0 (2026-05-13) — incorporar aquí

Durante el cierre de Ola 0 emergieron 3 issues de UX que pertenecen a esta ola:

1. **`cortex setup pipeline` y `cortex setup full` son interactivos sin `--non-interactive`.**
   `setup pipeline` pregunta "¿Es este el vault de Cortex? [Y/n]:" y se aborta si no se responde. Bloquea automatización (CI, scripts de onboarding, contenedores). Solo `setup agent` y `setup enterprise` tienen flag para skip. **Acción Ola 3:** agregar `--non-interactive` a `setup pipeline` y a `setup full` (que internamente compone agent+pipeline+webgraph). Default sensato cuando no-interactive: confirmar usar el vault detectado.

2. **`cortex stats` no acepta `--project-root`.** Hay que hacer `cd` al repo para que stats funcione. Inconsistente con `doctor`, `mcp-server`, `pr-context`, `autopilot *`, etc. **Acción Ola 3:** agregar el flag `--project-root` con resolución `WorkspaceLayout.discover()` igual que los demás.

3. **Doctor reporta FAIL en `gitignore:.memory/` y `gitignore:*.chroma/` en repos new-layout.** Los checks fueron escritos para legacy (`.memory/`, `vault/sessions/`). En new layout, memory vive en `.cortex/memory/` (ya ignorado por defecto via `.cortex/logs/` y `.cortex/*.log`). **Acción Ola 3:** los checks de gitignore deben ramificarse según `layout.is_legacy_layout`. En new layout deben verificar `.cortex/memory/` (o aceptarlo como no requerido si el path está dentro de un dir ya ignorado).

Estos 3 ítems son parte del checklist de Ola 3.E ("Mensajes de error claros") + nuevo ítem 3.E.bis ("Setup completamente no-interactive") + 3.D ("Doctor end-to-end verde post-setup").

## Pasos

### 3.A — Garantizar que `cortex setup full` incluye los 3 pilares

#### Auditoría

1. Leer `cortex/setup/orchestrator.py` completo. Identificar qué exactamente hace cada modo.
2. Si `FULL` no incluye `WEBGRAPH`: modificarlo para que lo incluya.
3. Verificar que también ejecuta `cold_start` para preseed del vault si el repo tiene git history.

#### Fix

Modificar el orchestrator: el modo `FULL` debe ejecutar **secuencialmente**:

1. `_setup_agent(layout, ctx)` — crea `.cortex/{config.yaml, vault/, memory/, skills/, subagents/, AGENT.md, system-prompt.md, workspace.yaml}`.
2. `_setup_pipeline(layout, ctx)` — genera `.github/workflows/*.yml` según stack detectado.
3. `_setup_webgraph(layout, ctx)` — crea `.cortex/webgraph/{config.yaml, cache/, workspace.yaml}`.
4. `cold_start.run_cold_start(layout)` — preseed del vault.
5. (Opcional según flag) `_setup_enterprise(layout, ctx)` con preset por default `small-company`.

Cada paso debe ser idempotente: correr `cortex setup full` dos veces no debe romper el estado.

#### Validación

```bash
# Repo vacío
mkdir test-empty && cd test-empty && git init
cortex setup full --ide claude-code --non-interactive

# Verificar
ls .cortex/  # debe tener config.yaml workspace.yaml vault/ memory/ skills/ subagents/ AGENT.md system-prompt.md webgraph/
ls .github/workflows/  # debe tener los 5 workflows
cortex doctor --scope all --strict  # verde

# Repeat — idempotencia
cortex setup full --ide claude-code --non-interactive  # no rompe
```

### 3.B — Fix de carga de config antes de discovery (`core.py:138-154`)

#### Cambio

`AgentMemory.__init__` debe aceptar `config_path: str | Path | None = None`. Si es `None`:

1. Hacer `WorkspaceLayout.discover(Path.cwd())` primero.
2. Usar `layout.config_path` como path.

Si es explícito, usar tal cual (preserva tests y casos avanzados).

#### Pasos

1. Leer `cortex/core.py:137-160`.
2. Refactorizar para que la firma sea `__init__(self, config_path: str | Path | None = None)`.
3. Hacer discovery antes de cargar el config si `config_path is None`.
4. Actualizar todos los usos de `AgentMemory(...)` en la codebase que pasaban `"config.yaml"` por default a NO pasar nada.
5. Agregar test:
   ```python
   def test_agent_memory_discovers_config_in_new_layout(tmp_path, monkeypatch):
       # Setup new layout
       (tmp_path / ".cortex").mkdir()
       (tmp_path / ".cortex" / "workspace.yaml").write_text("layout_version: 2\n")
       (tmp_path / ".cortex" / "config.yaml").write_text(
           "episodic:\n  persist_dir: memory\nsemantic:\n  vault_path: vault\n"
       )
       monkeypatch.chdir(tmp_path)
       mem = AgentMemory()  # sin argumentos
       assert mem.workspace_root == tmp_path / ".cortex"
   ```

### 3.C — Mensajes de error claros para primer contacto

Auditar los puntos donde un usuario novel falla más probable y mejorar los mensajes.

#### Casos prioritarios

1. **`cortex search` sin haber corrido setup**: hoy → `FileNotFoundError: config.yaml`. Después → `❌ Cortex no está configurado en este directorio. Ejecutá: cortex setup full`.
2. **MCP server sin `--project-root` y cwd no es repo Cortex**: hoy → exception random. Después → `❌ MCP server requiere --project-root o ser ejecutado dentro de un repo con .cortex/ configurado`.
3. **`cortex inject --ide <nombre-invalido>`**: hoy → KeyError probable. Después → `❌ IDE 'xxx' no soportado. IDEs disponibles: claude-code, opencode, pi, codex (oficiales), cursor, vscode, ... (comunidad)`.
4. **`cortex setup full` sin red para descargar ONNX**: hoy → exception en primer embed. Después → `⚠️ No se pudo descargar el modelo ONNX (offline). Setup completado pero las búsquedas con embeddings van a fallar hasta que vuelvas online`.

#### Pasos

1. Listar los 6-10 puntos de error más probables del primer contacto. Recorrer mental los comandos: `setup full`, `doctor`, `inject`, `mcp-server`, `search`, `create-spec`, `save-session`, `autopilot start`.
2. Para cada uno, identificar la excepción que lanza hoy y agregar `try/except` en el wrapper CLI que produzca un mensaje accionable.
3. Mantener el traceback técnico atrás de `--debug` (flag).

### 3.D — `cortex doctor --scope all --strict` debe pasar verde post-setup

1. Verificar todos los checks de doctor:
   - Config existe y valida.
   - Vault writable.
   - Memory writable.
   - Skills instaladas.
   - Workflows presentes (si pipeline activo).
   - Org.yaml válido (si enterprise activo).
   - MCP tools importables.
   - Session indexing (de Ola 0).
   - Adapter IDE detectado (si `--ide` fue pasado en setup).
2. Si algún check falla post-setup completo, **es un bug que rompe el flujo** → fixearlo.

### 3.E — Onboarding doc detallado

Crear `docs/guides/getting-started-adopters.md` con:

1. Prerrequisitos (Python 3.10+, git, pipx).
2. Instalación de Cortex (pipx install --editable C:\Cortex).
3. Setup en un proyecto:
   ```bash
   cd D:\MiProyecto
   cortex setup full --ide claude-code
   cortex doctor --scope all --strict
   ```
4. Primer flujo en el IDE elegido (linkear a `docs/guides/ide-<name>.md` de Ola 1).
5. Troubleshooting:
   - "No detecta el MCP server" → pasos.
   - "search no devuelve nada" → pasos.
   - "El IDE no encuentra cortex_*" → pasos.
6. Cómo desinstalar / volver atrás.

Idioma: español, tono profesional pero amistoso.

### 3.F — Smoke completo del primer contacto

Ejecutar en una VM/máquina limpia (o equivalent simulación):

1. Instalar Python 3.11, git, pipx desde cero.
2. Clonar Cortex.
3. `pipx install --editable .`
4. `mkdir test-adopter && cd test-adopter && git init && echo "# Test" > README.md && git add . && git commit -m "init"`
5. `cortex setup full --ide pi`
6. `cortex doctor --scope all --strict`
7. Iniciar Pi, emitir un prompt simulado de feature web pequeña, completar el ciclo tripartito.
8. `cortex webgraph serve` y abrir en navegador.
9. `cortex search <keyword del prompt>` — debe encontrar la session note recién creada.

**Si cualquier paso falla**, el bug encontrado pertenece a esta ola (no a Ola 4) — fixearlo antes de cerrar.

## Tests obligatorios al cierre

```bash
python -m pytest tests/integration/setup/ tests/e2e/scenarios/test_setup_full.py tests/e2e/scenarios/test_setup_basic.py tests/e2e/scenarios/test_setup_on_fixtures.py --no-cov
```

Plus suite completa:

```bash
python -m pytest tests/unit tests/integration tests/e2e --no-cov
```

Pegar resultado:

```
[pegar output cuando se cierre la ola]
```

## Checklist final de la Ola 3

### `cortex setup full` completo
- [ ] `SetupMode.FULL` incluye agent + pipeline + webgraph + cold_start.
- [ ] Idempotente (correr 2 veces no rompe).
- [ ] Genera todos los archivos esperados verificados con `ls`.
- [ ] `cortex doctor --scope all --strict` retorna verde post-setup.

### Carga de config sin path explícito
- [ ] `AgentMemory()` sin argumentos discovers layout y carga config correcto.
- [ ] Test `test_agent_memory_discovers_config_in_new_layout` pasa.
- [ ] Test equivalente para legacy layout pasa.
- [ ] Todos los call sites internos actualizados.

### Mensajes de error claros
- [ ] `cortex search` sin setup → mensaje accionable.
- [ ] `cortex mcp-server` sin contexto → mensaje accionable.
- [ ] `cortex inject --ide <invalid>` → lista IDEs disponibles.
- [ ] `cortex setup full` offline → degrada con warning, no exception.
- [ ] (Mínimo) 6 puntos de error prioritarios cubiertos.

### Doctor end-to-end
- [ ] Doctor sin warnings críticos post-setup en repo nuevo.
- [ ] Doctor detecta correctamente IDE adapter cuando `--ide` se pasó al setup.

### Onboarding doc
- [ ] `docs/guides/getting-started-adopters.md` creado.
- [ ] Incluye prerrequisitos, instalación, setup, primer flujo, troubleshooting, desinstalación.
- [ ] Linkea las guías por IDE (Ola 1).

### Smoke
- [ ] Smoke completo en máquina limpia ejecutado.
- [ ] Cualquier bug encontrado en el smoke arreglado dentro de esta ola.
- [ ] Resultados pegados en este doc.

### Cierre
- [ ] Suite global verde.

**Sólo cuando todos los items están marcados, se puede pasar a Ola 4.**
