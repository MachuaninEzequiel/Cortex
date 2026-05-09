# Fase 7.1 - Pi Autopilot Adapter

**Fuente:** Extension del plan `docs/autopilot/README.md` y de la Fase 7 ya realizada  
**Estado:** Pendiente de ejecucion  
**Ubicacion:** `docs/autopilot/fase-07-1-pi-autopilot-adapter/`  
**Motivo:** Pi es el CLI recomendado por Cortex y debe participar antes de Budget, Evals y Packaging

---

## Introduccion de la fase

En esta fase se implementa un adapter exclusivo para **Pi Coding Agent**, alineado con el contrato de Hook Adapters ya definido en la Fase 7, pero respetando la arquitectura propia de Pi.

Pi no debe tratarse como Cursor, Claude Code, OpenCode o Codex. Pi ya vive como entorno project-local en `cortex-pi/` y usa:

- `.pi/settings.json`
- `.pi/mcp.json`
- `.pi/extensions/*.ts`
- `.pi/agents/*.md`
- `.pi/skills/*`
- `justfile`

Por eso, el objetivo no es crear un hook generico externo, sino instalar una extension Pi propia que conecte el ciclo de vida de Pi con `cortex autopilot`.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir:

- que se implemento;
- archivos creados/modificados;
- decisiones tomadas;
- tests ejecutados y resultado;
- desviaciones respecto de este plan;
- riesgos residuales;
- proximos pasos.

---

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global y las adapta a Pi. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- Pi debe ser un adapter **project-local**. No escribas configuracion global en home del usuario.
- No dupliques logica de memoria en TypeScript. La extension Pi debe llamar al CLI `cortex autopilot ... --json`.
- No reemplaces `.pi/settings.json`; hace merge preservando extensiones, skills, agents, theme, model y tools existentes.
- No reemplaces `cortex-pi/` completo ni modifiques el adapter IDE `cortex/ide/adapters/pi.py` salvo que este plan lo indique explicitamente.
- No cambies la Fase 7 ya realizada. Esta fase es incremental.
- No cambies el contrato general de adapters salvo para registrar `pi`.
- Si Pi no expone un evento equivalente a `session_finish`, documenta la degradacion y deja `session_start` funcionando. No inventes eventos.
- Si no hay `.pi/`, el adapter debe crear solo lo minimo necesario o devolver error claro segun el comando de instalacion. No debe borrar nada.

---

## Objetivo

Agregar soporte Autopilot para Pi Coding Agent mediante un adapter dedicado que:

1. detecte instalaciones Pi project-local;
2. instale una extension Pi `cortex-autopilot.ts`;
3. agregue esa extension a `.pi/settings.json` sin pisar configuracion existente;
4. instale la meta-skill `using-cortex-autopilot` en formato compatible con Pi;
5. conecte eventos de sesion de Pi con el CLI `cortex autopilot`;
6. sea reversible mediante uninstall;
7. quede cubierto por tests unitarios;
8. quede preparado para las fases 8, 11 y 12.

---

## Contexto tecnico existente

### Pi como entorno recomendado

El repo ya contiene `cortex-pi/`, documentado como entorno recomendado por Cortex:

```text
cortex-pi/
  AGENTS.md
  justfile
  .pi/
    settings.json
    mcp.json
    system.md
    agents/
    skills/
    extensions/
    themes/
```

### Adapter IDE Pi existente

Existe `cortex/ide/adapters/pi.py`, que copia `cortex-pi/` al proyecto:

```text
cortex/ide/adapters/pi.py
```

Ese adapter pertenece a la instalacion IDE/manual. Esta fase no debe reemplazarlo. El nuevo adapter vive en:

```text
cortex/autopilot/adapters/pi.py
```

### Hook adapters Autopilot existentes

La Fase 7 ya creo:

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
```

Pi debe integrarse a ese contrato sin romperlo.

---

## Decision arquitectonica

### Decision

Implementar Pi como adapter Autopilot dedicado, project-local, basado en extension TypeScript.

### Justificacion

Pi opera con extensiones TypeScript y configuracion `.pi/settings.json`. Intentar instalarlo como hook Markdown o config global seria inconsistente con su arquitectura.

### Consecuencia

El adapter Pi tendra dos capas:

1. **Python adapter**: instala/desinstala archivos y registra el adapter.
2. **TypeScript extension**: se ejecuta dentro de Pi y llama el CLI Autopilot.

---

## Alcance

### Dentro de alcance

- Crear `cortex/autopilot/adapters/pi.py`.
- Registrar `pi` en `cortex/autopilot/adapters/registry.py`.
- Agregar `PI_PLUGIN_ROOT` y/o deteccion `.pi/` en `platform_detect.py`.
- Crear template de extension Pi:
  - `cortex/autopilot/pi/extensions/cortex-autopilot.ts`
- Crear template de skill Pi:
  - `cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md`
- Instalar extension en `.pi/extensions/cortex-autopilot.ts`.
- Instalar skill en `.pi/skills/using-cortex-autopilot/SKILL.md`.
- Merge seguro de `.pi/settings.json`.
- Tests unitarios para adapter, detection y merge.
- Actualizar docs de la fase con `REALIZACION.md`.

### Fuera de alcance

- Cambiar runtime interno de Pi.
- Cambiar el paquete `@mariozechner/pi-coding-agent`.
- Rehacer `cortex-pi/`.
- Reescribir `cortex/ide/adapters/pi.py`.
- Agregar nuevas tools de memoria en TypeScript que dupliquen MCP.
- Cambiar Fase 8, 11 o 12 en esta misma implementacion.
- Hacer packaging marketplace de Pi en esta fase.

---

## Archivos a crear

```text
cortex/autopilot/adapters/pi.py
cortex/autopilot/pi/extensions/cortex-autopilot.ts
cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md
tests/unit/autopilot/test_pi_adapter.py
```

---

## Archivos a modificar

```text
cortex/autopilot/adapters/registry.py
cortex/autopilot/adapters/platform_detect.py
tests/unit/autopilot/test_platform_detect.py
docs/autopilot/fase-07-1-pi-autopilot-adapter/REALIZACION.md
```

### Condicion sobre archivos existentes

No modificar estos archivos salvo que un test demuestre que es imprescindible y se documente en `REALIZACION.md`:

```text
cortex/ide/adapters/pi.py
cortex-pi/README.md
cortex-pi/AGENTS.md
cortex-pi/.pi/settings.json
cortex-pi/.pi/mcp.json
```

El adapter debe instalar desde templates propios del modulo Autopilot, no editar directamente el template `cortex-pi/` en esta fase.

---

## Contrato del adapter Python

### Clase esperada

Archivo:

```text
cortex/autopilot/adapters/pi.py
```

Clase:

```python
class PiAutopilotAdapter:
    name = "pi"
    supported_events = {"session_start", "session_finish"}

    def install(self, project_root: Path) -> list[Path]:
        ...

    def uninstall(self, project_root: Path) -> list[Path]:
        ...

    def emit_session_start(
        self,
        state: AutopilotSessionState,
        bootstrap: str,
    ) -> str:
        ...
```

### Reglas de `install()`

`install(project_root)` debe:

1. Resolver `project_root`.
2. Buscar `.pi/settings.json`.
3. Si `.pi/` no existe:
   - crear `.pi/extensions/` y `.pi/skills/using-cortex-autopilot/`;
   - crear `.pi/settings.json` minimo, solo si no existe;
   - dejar warning documentable si el adapter no puede saber si Pi esta instalado.
4. Copiar template:
   - origen: `cortex/autopilot/pi/extensions/cortex-autopilot.ts`
   - destino: `<project_root>/.pi/extensions/cortex-autopilot.ts`
5. Copiar template:
   - origen: `cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md`
   - destino: `<project_root>/.pi/skills/using-cortex-autopilot/SKILL.md`
6. Hacer backup de `.pi/settings.json` antes de modificarlo:
   - usar la utilidad existente `_write_with_backup()` si encaja;
   - o crear backup `settings.json.autopilot-backup`.
7. Mergear `.pi/settings.json` preservando:
   - `model`
   - `theme`
   - `defaultExtensions`
   - `skills`
   - `agents`
   - `defaultAgent`
   - `compaction`
   - `tools`
8. Agregar `.pi/extensions/cortex-autopilot.ts` a la lista correcta de extensiones.
9. Agregar `.pi/skills/using-cortex-autopilot/SKILL.md` a `skills` si esa lista existe.
10. No duplicar entradas si ya existen.
11. Devolver lista de paths escritos/modificados.

### Reglas de `uninstall()`

`uninstall(project_root)` debe:

1. Remover `.pi/extensions/cortex-autopilot.ts` si existe.
2. Remover `.pi/skills/using-cortex-autopilot/` si existe.
3. Remover entradas Autopilot de `.pi/settings.json`:
   - `.pi/extensions/cortex-autopilot.ts`
   - `.pi/skills/using-cortex-autopilot/SKILL.md`
4. Preservar todas las demas entradas.
5. Si existe backup y el archivo actual solo contiene cambios Autopilot, puede restaurar backup.
6. No borrar `.pi/`, `AGENTS.md`, `justfile`, agents ni extensiones existentes.
7. Devolver lista de paths eliminados/modificados.

### Reglas de `emit_session_start()`

Debe reutilizar:

```python
format_session_start_output(state, bootstrap, "pi")
```

Si `format_session_start_output()` no contempla `pi`, el formato default actual debe servir:

```json
{"additionalContext": "<payload_json>"}
```

No crear un formato especial salvo que haya evidencia de que Pi requiere otra estructura.

---

## Deteccion de plataforma

### Modificar enum

Archivo:

```text
cortex/autopilot/adapters/platform_detect.py
```

Agregar:

```python
class Platform(Enum):
    ...
    PI = "pi"
```

### Reglas de deteccion

`detect_platform()` debe detectar Pi por variables de entorno si existen:

```python
if os.environ.get("PI_PLUGIN_ROOT"):
    return Platform.PI
if os.environ.get("PI_CODING_AGENT"):
    return Platform.PI
```

### No depender solo de filesystem en `detect_platform()`

`detect_platform()` hoy no recibe `project_root`, por eso no debe intentar buscar `.pi/settings.json` desde ahi. La deteccion por filesystem debe quedar en el adapter:

```python
def is_project_configured(project_root: Path) -> bool:
    return (project_root / ".pi" / "settings.json").exists()
```

### Tests requeridos

Actualizar:

```text
tests/unit/autopilot/test_platform_detect.py
```

Agregar casos:

- `PI_PLUGIN_ROOT` detecta `Platform.PI`.
- `PI_CODING_AGENT` detecta `Platform.PI`.
- prioridad: si `CURSOR_PLUGIN_ROOT` y `PI_PLUGIN_ROOT` estan seteados, mantener prioridad definida.

### Prioridad recomendada

Mantener Pi despues de Codex/OpenCode si solo se usa env var generica. Si Pi define env var propia, puede ir antes de `UNKNOWN` sin afectar otros harnesses:

```python
if os.environ.get("PI_PLUGIN_ROOT"):
    return Platform.PI
if os.environ.get("PI_CODING_AGENT"):
    return Platform.PI
return Platform.UNKNOWN
```

No alterar prioridades existentes salvo test explicito.

---

## Registro del adapter

Archivo:

```text
cortex/autopilot/adapters/registry.py
```

Agregar import:

```python
from cortex.autopilot.adapters.pi import PiAutopilotAdapter
```

Agregar entrada:

```python
_ADAPTERS: dict[str, type] = {
    ...
    "pi": PiAutopilotAdapter,
}
```

`list_adapters()` debe incluir `"pi"`.

`get_adapter("pi")` debe devolver `PiAutopilotAdapter`.

`get_adapter_for_current_platform()` debe funcionar cuando `detect_platform()` retorna `Platform.PI`.

---

## Template de extension Pi

### Archivo template

Crear:

```text
cortex/autopilot/pi/extensions/cortex-autopilot.ts
```

### Proposito

Esta extension corre dentro de Pi y conecta eventos de sesion con el CLI Autopilot.

### Reglas de la extension

1. No implementar memoria propia.
2. No leer ni escribir el vault.
3. No indexar documentos.
4. No duplicar MCP.
5. Resolver el binario `cortex` con una funcion local similar a `resolveCortexBin()` de `cortex-pi/.pi/extensions/cortex-tools.ts`, pero reducida.
6. Ejecutar comandos con `spawnSync` o API equivalente.
7. Usar `cwd` de Pi.
8. Pasar `--project-root <cwd>`.
9. Pasar `--json`.
10. Manejar errores con notificaciones claras.

### Eventos esperados

La extension debe intentar registrar:

```typescript
pi.on("session_start", async (_event, ctx) => { ... })
```

Y si Pi soporta cierre:

```typescript
pi.on("session_finish", async (_event, ctx) => { ... })
```

Si el evento real se llama distinto o no existe, el implementador debe:

1. revisar patrones en `cortex-pi/.pi/extensions/*.ts`;
2. usar el evento disponible mas cercano;
3. documentar la decision en `REALIZACION.md`;
4. mantener tests Python del adapter aunque no se compile TypeScript en esta fase.

### Comportamiento en `session_start`

Debe ejecutar:

```bash
cortex autopilot start --project-root <cwd> --mode assist --json
```

Resultado esperado:

- si OK:
  - guardar `session_id` en variable local de la extension;
  - notificar que Autopilot esta activo;
  - agregar contexto bootstrap si Pi ofrece API para contexto adicional;
  - si no hay API de contexto adicional, solo notificar y confiar en skill instalada.
- si falla:
  - notificar warning;
  - no bloquear Pi.

### Comportamiento en `session_finish`

Debe ejecutar:

```bash
cortex autopilot finish --project-root <cwd> --session-id <session_id> --auto --json
```

Si no hay `session_id`, debe:

- no ejecutar finish;
- notificar warning solo si esta en modo debug;
- no bloquear Pi.

### Comportamiento opcional de checkpoint

No implementar checkpoint automatico en esta fase salvo que sea trivial. Si se implementa, debe ser muy conservador:

```bash
cortex autopilot checkpoint --project-root <cwd> --session-id <session_id> --summary "Pi session checkpoint" --json
```

Pero el scope principal es start/finish.

### Output y notificaciones

La extension debe usar `ctx.ui.notify(...)` si esta disponible, siguiendo el patron de `cortex-tools.ts`.

Mensajes sugeridos:

- exito start:
  - `"Cortex Autopilot activo (session <id>)"`
- fallo start:
  - `"Cortex Autopilot no pudo iniciar: <error>"`
- exito finish:
  - `"Cortex Autopilot cerro la sesion: <path or status>"`
- fallo finish:
  - `"Cortex Autopilot no pudo cerrar la sesion: <error>"`

### Configuracion por env

La extension debe respetar:

```text
CORTEX_AUTOPILOT_MODE
CORTEX_BIN
```

Defaults:

```text
CORTEX_AUTOPILOT_MODE=assist
CORTEX_BIN=cortex
```

No agregar nuevas env vars salvo que sean documentadas.

---

## Template de skill Pi

### Archivo template

Crear:

```text
cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md
```

### Contenido esperado

Debe adaptar la meta-skill Autopilot al formato Pi.

Contenido minimo:

```markdown
---
name: using-cortex-autopilot
description: Bootstrap minimo para usar Cortex Autopilot en Pi sin cargar todo el workflow manual.
---

# Using Cortex Autopilot in Pi

Pi esta gobernado por Cortex Autopilot cuando esta skill esta instalada.

Reglas:

1. Usa solo herramientas Cortex (`cortex_*` o `cortex_autopilot_*`) para memoria.
2. No uses memoria externa (`engram_*`, `mem_*`, `save_memory`, `session_summary`).
3. Para tareas simples, favorece Fast Track.
4. Para tareas complejas, usa el pipeline Pi/Cortex existente.
5. No declares una tarea completa sin que Autopilot o `cortex-documenter` hayan persistido la sesion.
6. Mantene el contexto compacto: no cargues todo el vault si no hace falta.
7. Si Autopilot falla, informa el bloqueo y continua en modo manual Cortex.
```

### Regla de tamano

La skill no debe superar 1500 palabras.

### Relacion con skills existentes

No reemplaza:

- `.pi/skills/cortex-vault/SKILL.md`
- `.pi/skills/cortex-python/SKILL.md`
- `.pi/skills/cortex-testing/SKILL.md`

Solo se agrega como bootstrap.

---

## Merge de `.pi/settings.json`

### Entrada actual esperada

Ejemplo existente:

```json
{
  "model": "claude-sonnet-4-20250514",
  "theme": "cortex-dark",
  "defaultExtensions": ["extensions/cortex-dashboard.ts"],
  "skills": [
    ".pi/skills/cortex-vault.md",
    ".pi/skills/cortex-python.md",
    ".pi/skills/cortex-testing.md",
    ".pi/skills/obsidian-index.md"
  ],
  "agents": [
    ".pi/agents/cortex-sync.md",
    ".pi/agents/cortex-SDDwork.md"
  ],
  "defaultAgent": "cortex-sync",
  "compaction": {
    "strategy": "summarize",
    "triggerAt": 0.8,
    "preserveSystemPrompt": true
  },
  "tools": {
    "bash": true,
    "read": true,
    "write": true,
    "edit": true
  }
}
```

### Resultado esperado

Agregar sin duplicar:

```json
{
  "defaultExtensions": [
    "extensions/cortex-dashboard.ts",
    "extensions/cortex-autopilot.ts"
  ],
  "skills": [
    ".pi/skills/cortex-vault.md",
    ".pi/skills/cortex-python.md",
    ".pi/skills/cortex-testing.md",
    ".pi/skills/obsidian-index.md",
    ".pi/skills/using-cortex-autopilot/SKILL.md"
  ]
}
```

### Importante sobre rutas

Pi usa en el template actual rutas relativas mezcladas:

- `extensions/cortex-dashboard.ts` en `defaultExtensions`
- `.pi/skills/...` en `skills`

Mantener esa convencion:

```text
defaultExtensions: "extensions/cortex-autopilot.ts"
skills: ".pi/skills/using-cortex-autopilot/SKILL.md"
```

No usar paths absolutos.

---

## Helpers recomendados en `pi.py`

El adapter deberia incluir helpers chicos y testeables:

```python
def _pi_dir(project_root: Path) -> Path:
    return project_root / ".pi"

def _settings_path(project_root: Path) -> Path:
    return _pi_dir(project_root) / "settings.json"

def _extension_dest(project_root: Path) -> Path:
    return _pi_dir(project_root) / "extensions" / "cortex-autopilot.ts"

def _skill_dest(project_root: Path) -> Path:
    return _pi_dir(project_root) / "skills" / "using-cortex-autopilot" / "SKILL.md"

def _load_settings(path: Path) -> dict:
    ...

def _merge_settings(settings: dict) -> dict:
    ...

def _remove_settings_entries(settings: dict) -> dict:
    ...
```

### Reglas para `_load_settings`

- Si no existe, devolver config minima:

```python
{
    "defaultExtensions": [],
    "skills": [],
}
```

- Si existe pero JSON invalido:
  - no pisar el archivo;
  - levantar `ValueError` con mensaje claro;
  - `install()` debe propagar el error.

### Reglas para `_merge_settings`

- Si `defaultExtensions` no existe, crearlo como lista.
- Si `skills` no existe, crearlo como lista.
- Si existen pero no son listas, levantar `ValueError`.
- Agregar entradas Autopilot sin duplicar.
- Preservar el resto del dict.

### Reglas para `_remove_settings_entries`

- Remover solo entradas Autopilot.
- Preservar orden relativo del resto.
- No borrar claves vacias salvo que el plan lo indique. Mantener `defaultExtensions` y `skills` aunque queden vacias.

---

## Tests requeridos

### Archivo

```text
tests/unit/autopilot/test_pi_adapter.py
```

### Casos minimos

1. `install_creates_pi_files_when_missing`
   - Dado un `tmp_path` sin `.pi/`
   - Ejecuta `PiAutopilotAdapter().install(tmp_path)`
   - Verifica:
     - `.pi/extensions/cortex-autopilot.ts`
     - `.pi/skills/using-cortex-autopilot/SKILL.md`
     - `.pi/settings.json`

2. `install_merges_existing_settings`
   - Dado `.pi/settings.json` con model/theme/extensions/skills
   - Ejecuta install
   - Verifica que conserva claves existentes y agrega Autopilot.

3. `install_is_idempotent`
   - Ejecuta install dos veces
   - Verifica que no duplica entries.

4. `install_rejects_invalid_settings_json`
   - Dado `.pi/settings.json` invalido
   - Ejecuta install
   - Espera `ValueError`
   - Verifica que el archivo original no fue pisado.

5. `uninstall_removes_only_autopilot_files`
   - Dado `.pi/` con extension/skill Autopilot y otros archivos
   - Ejecuta uninstall
   - Verifica que borra solo Autopilot.

6. `uninstall_removes_settings_entries`
   - Verifica que `extensions/cortex-autopilot.ts` y `.pi/skills/using-cortex-autopilot/SKILL.md` salen de settings.

7. `uninstall_preserves_other_settings`
   - Verifica que no borra model/theme/agents/tools/otras extensiones.

8. `registry_includes_pi`
   - `list_adapters()` contiene `"pi"`.
   - `get_adapter("pi")` devuelve `PiAutopilotAdapter`.

9. `platform_detect_pi_plugin_root`
   - con `PI_PLUGIN_ROOT=1`, retorna `Platform.PI`.

10. `platform_detect_pi_coding_agent`
   - con `PI_CODING_AGENT=1`, retorna `Platform.PI`.

11. `emit_session_start_uses_default_json_shape`
   - Construye `AutopilotSessionState`
   - llama `emit_session_start`
   - verifica JSON top-level `additionalContext`.

12. `template_extension_mentions_autopilot_cli`
   - Lee template TS
   - verifica que contiene:
     - `autopilot`
     - `start`
     - `finish`
     - `--json`
     - `--project-root`

13. `template_skill_contains_memory_isolation`
   - Lee SKILL.md
   - verifica que prohibe memoria externa.

### Tests existentes a actualizar

```text
tests/unit/autopilot/test_platform_detect.py
tests/unit/autopilot/test_adapters.py
```

Si `test_adapters.py` tiene expectations de cantidad o lista exacta de adapters, agregar `"pi"`.

---

## Comandos de validacion

Ejecutar:

```bash
pytest tests/unit/autopilot/test_pi_adapter.py -q
pytest tests/unit/autopilot/test_platform_detect.py -q
pytest tests/unit/autopilot/test_adapters.py -q
pytest tests/unit/autopilot -q
```

Si el agente puede ejecutar suite mas amplia:

```bash
pytest tests/unit/cli/test_main.py -q
pytest tests/unit/test_ide_adapters.py -q
```

No es obligatorio ejecutar e2e en esta fase salvo que el entorno Pi este disponible.

---

## Gate de salida

La fase esta completa solo si:

- [ ] Existe `cortex/autopilot/adapters/pi.py`.
- [ ] Existe template `cortex/autopilot/pi/extensions/cortex-autopilot.ts`.
- [ ] Existe template `cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md`.
- [ ] `registry.py` registra `"pi"`.
- [ ] `platform_detect.py` reconoce Pi por env vars.
- [ ] `install()` crea/copiar extension y skill.
- [ ] `install()` mergea `.pi/settings.json` sin pisar configuracion existente.
- [ ] `install()` es idempotente.
- [ ] `uninstall()` remueve solo archivos/entries Autopilot.
- [ ] Tests unitarios de Pi pasan.
- [ ] Tests unitarios Autopilot pasan.
- [ ] `REALIZACION.md` documenta implementacion, decisiones, tests y riesgos.

---

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Pi no soporta `session_finish` | Medio | Implementar start; documentar degradacion; finish puede quedar manual o futuro |
| `.pi/settings.json` tiene schema no esperado | Alto | Merge conservador, validacion de listas, ValueError claro |
| Duplicar logica de memoria en TypeScript | Alto | Extension solo llama CLI Autopilot |
| Romper configuracion Pi existente | Alto | Backup + merge + tests de preservacion |
| Paths relativos incorrectos | Medio | Mantener convencion `extensions/...` y `.pi/skills/...` |
| Falta Python/cortex en PATH | Medio | Mensaje claro; respetar `CORTEX_BIN` |
| Adapter IDE Pi y Autopilot Pi divergen | Medio | No tocar `cortex/ide/adapters/pi.py`; documentar frontera |

---

## Criterios de calidad

### Modularidad

El soporte Pi debe poder eliminarse sin afectar otros adapters.

### Reversibilidad

Uninstall debe dejar el proyecto igual salvo backups explicitamente creados.

### Compatibilidad

No debe romper:

- Cursor adapter
- Claude Code adapter
- OpenCode adapter
- Codex adapter
- CLI manual
- MCP tools existentes
- Pi manual con `just cortex`

### Bajo consumo

La extension Pi no debe disparar retrieval por si misma. Solo inicia/cierra Autopilot. El presupuesto se gobierna en fases posteriores.

---

## Forma esperada de `REALIZACION.md`

Al terminar, crear:

```text
docs/autopilot/fase-07-1-pi-autopilot-adapter/REALIZACION.md
```

Con esta estructura:

```markdown
# Fase 7.1 - Pi Autopilot Adapter: Realizacion

## Fecha

## Resumen

## Archivos creados

## Archivos modificados

## Decisiones tomadas

## Detalles de implementacion

## Tests ejecutados

## Resultado de tests

## Desviaciones respecto del plan

## Riesgos residuales

## Proximos pasos
```

Si hay desviaciones, no ocultarlas. Documentarlas con motivo tecnico.

---

## Prompt corto para ejecutar esta fase

```text
Implementa exclusivamente `docs/autopilot/fase-07-1-pi-autopilot-adapter`.

Antes de tocar codigo:
1. Lee `docs/autopilot/README.md`.
2. Lee `docs/autopilot/fase-07-hook-adapters/README.md`.
3. Lee `docs/autopilot/fase-07-hook-adapters/REALIZACION.md`.
4. Lee completo `docs/autopilot/fase-07-1-pi-autopilot-adapter/README.md`.

No implementes otra fase. No toques MCP ni el CLI salvo que este README lo indique. No modifiques `cortex/ide/adapters/pi.py` ni `cortex-pi/` salvo que puedas justificarlo y documentarlo en REALIZACION.md.

Cumpli el gate de salida y documenta la realizacion en esta misma carpeta.
```

