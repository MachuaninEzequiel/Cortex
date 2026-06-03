# HANDOFF — Codex MCP no conecta: causa raíz (trust gate) + fix mono-repo

> **Fecha:** 2026-05-30 → 2026-06-01
> **Branch:** `feature/nuevo-modo-autonomo`
> **Estado:** Implementación COMPLETA en código + tests verdes (1 fallo preexistente ajeno).
> **PENDIENTE crítico:** aplicar a un proyecto real y **verificar en vivo en Codex**, y
> **confirmar la sintaxis exacta del trust** contra la versión instalada de Codex.

---

## 0. TL;DR para el próximo agente

- **Síntoma:** al instalar Cortex en un proyecto para Codex, los **agentes/instrucciones
  entran** pero el **MCP server no conecta**.
- **Causa raíz CONFIRMADA (con evidencia de logs):** Cortex registra el MCP en el
  `config.toml` **del proyecto** (`<proyecto>/.codex/config.toml`), y **Codex descarta toda
  la capa project-local hasta que el proyecto esté "trusted"**. No es el archivo equivocado:
  es el **trust gate** de Codex.
- **Decisión de diseño (firmada con el usuario):** el harness es **mono-repo**
  (`cortex setup agent` por proyecto), así que el MCP debe seguir siendo **project-scoped**
  (NO global). **Se DESCARTÓ la "Opción A" de registrar en `~/.codex/config.toml` global**
  porque contradice mono-repo (aparecería en todos los proyectos, apuntando al repo
  equivocado).
- **Fix implementado:** mantener el registro project-scoped + que `inject_mcp` **también
  marque el proyecto como `trusted`** en el config global (merge quirúrgico) + **hardening**
  del bloque MCP. Modo elegido: **Auto-trust con aviso**, reversible en `uninstall`.
- **Qué falta:** correr `cortex inject --ide codex` en el proyecto real, reabrir Codex,
  confirmar que `cortex` aparece en `/mcp` sin el ERROR de trust, y **validar la sintaxis
  `trust_level = "trusted"`** (inferida, no 100% confirmada por docs).

---

## 1. El problema original (reportado por el usuario)

Instaló Cortex para Codex en un proyecto. Los agentes "entran correctamente" (creyó que se
migraban desde una carpeta `.claude` preexistente), **pero el MCP server no se conecta**, y
la instalación debería habilitarlo automáticamente.

Ref doc oficial Codex MCP: https://developers.openai.com/codex/mcp

---

## 2. Causa raíz — CONFIRMADA con evidencia directa

### 2.1 Evidencia de archivos (entorno real de la máquina del usuario)

| Hecho | Valor |
|---|---|
| Proyecto donde se instaló | **`C:\AppFutbol`** (de `~/.codex/.codex-global-state.json` → `active-workspace-roots`) |
| `C:\AppFutbol\.codex\config.toml` | **Contiene** `[mcp_servers.cortex]` (registro project-scoped) ✓ |
| `C:\AppFutbol\AGENTS.md` (raíz) | Existe, con sección `BEGIN CORTEX SECTION` → **por eso los agentes entran** |
| `~/.codex/config.toml` (global) | **NO contiene** `cortex`. Solo `[mcp_servers.node_repl]`, `marketplaces`, `plugins`, `[desktop]` |
| Tabla `[projects]`/trust en global | **NINGUNA** → el proyecto no está trusted |
| `.claude` en el proyecto | Existe (`agents`, `skills`, `settings.json`, `settings.local.json`) → de ahí la percepción de "migración", pero el AGENTS.md es template propio de Cortex |

### 2.2 LA PRUEBA DEFINITIVA — log de Codex

De `C:\Users\chuch\.codex\logs_2.sqlite`, tabla `logs`, `target = codex_app_server`
(`app-server/src/lib.rs:652`), nivel **ERROR**:

```
Project-local config, hooks, and exec policies are disabled in the following
folders until the project is trusted, but skills still load.
  1. C:\AppFutbol\.codex
     To load project-local config, hooks, and exec policies, add c:\appfutbol
     as a trusted project in C:\Users\chuch\.codex\config.toml.
```

Esto prueba TODO:
1. Codex **sí lee** `C:\AppFutbol\.codex\config.toml` (no es el archivo equivocado).
2. Lo **deshabilita** porque el proyecto **no es trusted**.
3. **"but skills still load"** → explica la asimetría: AGENTS.md/skills (raíz, fuera de
   `.codex/`) cargan; el MCP (capa project-local) no.
4. Codex mismo dice el fix: **agregar el proyecto como trusted en `~/.codex/config.toml`**.

### 2.3 Confirmación documental

developers.openai.com/codex/mcp (textual):
> *"By default this is `~/.codex/config.toml`, but you can also scope MCP servers to a
> project with `.codex/config.toml` **(trusted projects only)**."*

---

## 3. La decisión de diseño (debate cerrado con el usuario)

### 3.1 Mono-repo (el usuario tiene razón)
Cortex se instala por proyecto (`cortex setup agent` con selector de IDE). El MCP es
inherentemente project-scoped (sirve el vault/sessions/memory de ESE repo). Por lo tanto el
MCP debe estar disponible **solo donde se corrió setup agent**. El `.codex/config.toml` del
proyecto **ya es** el mecanismo mono-repo correcto.

### 3.2 Por qué se DESCARTÓ la "Opción A" (registro global)
Poner `[mcp_servers.cortex]` en `~/.codex/config.toml` lo haría visible en **todos** los
proyectos de Codex (es global), y con `--project-root` fijo apuntaría siempre al mismo repo.
Eso **contradice mono-repo** y es estrictamente peor. **NO hacer esto.**

### 3.3 Trust temporal/revertible: NO sirve (pregunta del usuario, respondida)
El trust **no se consume durante la instalación** (que solo escribe archivos). Se evalúa
cuando **Codex** carga el proyecto, y **en cada arranque**. Es un gate **persistente por
sesión**, no un desbloqueo de una sola vez. Si se revierte a no-trust, la próxima vez que
Codex cargue el proyecto el MCP se vuelve a deshabilitar. → **El trust debe persistir**
mientras Cortex esté instalado.

### 3.4 Modo elegido: **Auto-trust con aviso**
`cortex setup agent --ide codex` agrega el trust automáticamente (UX instantánea que el
usuario quería) **e imprime un aviso explícito** de qué marcó y qué implica. La reversión
ocurre en **`uninstall`** (no post-install), ownership-aware.

### 3.5 Caveat de seguridad (documentado, aceptado)
Marcar trusted habilita TODA la capa project-local de Codex (config/hooks/exec policies), no
solo el MCP. Codex la gatea a propósito. Como el usuario corre setup en su propio repo de
forma deliberada, es razonable, pero es una expansión de superficie hecha en su nombre.

---

## 4. Qué se implementó (código)

Todo en **`cortex/ide/adapters/codex.py`** salvo el fixture de tests.

### 4.1 Hardening del bloque MCP project-scoped
`_build_cortex_toml_block()` (codex.py:248) + `_resolve_cortex_command()` (codex.py:236):
- `command` = **ruta absoluta** a `cortex.exe` vía `shutil.which("cortex")` (fallback al
  nombre pelado). Razón: Codex Desktop no garantiza el PATH de la shell del usuario.
- `startup_timeout_sec = 60`. Razón: el server Python es pesado; el default de Codex (10 s)
  lo mata. El propio `node_repl` de OpenAI usa **120 s** en el config global del usuario.
- `env`: agrega `PYTHONIOENCODING = "utf-8"` y `PYTHONUNBUFFERED = "1"` (stdio JSON-RPC
  limpio en Windows), además del `PYTHONWARNINGS = "ignore"` que ya estaba.

Bloque resultante:
```toml
# BEGIN CORTEX MCP (auto-generated, do not edit)
[mcp_servers.cortex]
command = "C:\\Users\\...\\Scripts\\cortex.exe"
args = ["mcp-server", "--stdio", "--project-root", "C:\\AppFutbol"]
startup_timeout_sec = 60
enabled = true

[mcp_servers.cortex.env]
PYTHONWARNINGS = "ignore"
PYTHONIOENCODING = "utf-8"
PYTHONUNBUFFERED = "1"
# END CORTEX MCP
```

### 4.2 Auto-trust en el config global (merge no-destructivo)
Nuevos helpers en codex.py:
- `_codex_global_config_path()` (codex.py:314) — resuelve `~/.codex/config.toml`,
  **respetando `CODEX_HOME`** (misma env var que respeta Codex; los tests la usan para
  aislamiento).
- `_trust_markers(project_root)` (codex.py:327) — marcadores **específicos del path**:
  `# BEGIN CORTEX TRUST [<path>] ...` / `# END CORTEX TRUST [<path>]`. Multi-repo safe:
  uninstall remueve solo el del proyecto.
- `_build_cortex_trust_block()` (codex.py:336) — genera:
  ```toml
  [projects."<path>"]
  trust_level = "trusted"
  ```
- `_global_has_foreign_trust()` (codex.py:355) — detecta si ya existe un
  `[projects."<este path>"]` FUERA de nuestros marcadores (normaliza case/sep de Windows).
  Si el usuario ya confió el proyecto a mano, **NO** duplicamos la tabla (TOML prohíbe
  tablas duplicadas → invalidaría toda la config).
- `_merge_trust_into_global()` (codex.py:375) — merge idempotente: agrega/reemplaza solo
  nuestro bloque, preserva `marketplaces`/`plugins`/`node_repl`/`desktop`/otros proyectos.

Integración en `CodexAdapter.inject_mcp()` (codex.py:459): escribe el bloque project-scoped
**y** mergea el trust al global; si cambió, hace backup y escribe, y llama a
`_print_trust_notice()` (codex.py:507). Devuelve ambos paths.

### 4.3 Uninstall simétrico (reversión)
`CodexAdapter.uninstall()` (codex.py:525) — paso "2b": remueve la entrada de trust del global
**solo si está entre NUESTROS marcadores** para el path del cwd (ownership-aware). No toca
trust de otros proyectos ni el que el usuario puso a mano.

### 4.4 Bug latente arreglado (IMPORTANTE)
`re.sub` interpreta los backslashes de rutas Windows en el **string de reemplazo** como
escapes de regex (`\U`, `\p`…) → crasheaba en la 2ª inyección idempotente. Era un bug
**preexistente** en el merge del MCP que mi test destapó. Fix: replacement por **callable**
(`pattern.sub(lambda _m: bloque, existing)`) en los 3 merges: AGENTS.md
(`_replace_or_append_cortex_section`, codex.py:213), MCP
(`_replace_or_append_cortex_toml_block`, codex.py:293) y trust (`_merge_trust_into_global`).

---

## 5. Archivos modificados (lista completa)

**En el repo `C:\Cortex`:**
1. `cortex/ide/adapters/codex.py` — todo lo del punto 4 (núcleo del cambio).
2. `tests/conftest.py` — fixture autouse `_isolate_codex_home`: apunta `CODEX_HOME` a un
   temp por test para que **ningún test toque el `~/.codex` real**.
3. `tests/unit/test_ide_adapters.py` — actualizado `test_codex_adapter_inject_mcp_uses_absolute_path`
   (env endurecido + command por nombre + startup_timeout + trust global) + **nuevo**
   `test_codex_inject_mcp_global_trust_is_merge_safe_and_reversible` + `import os`.
4. `tests/unit/ide/test_adapters_phase4.py` — assert de `command` por nombre del ejecutable.
5. `tests/integration/test_smoke_multi_ide_phase7.py` — mismo ajuste de assert.
6. `tests/integration/test_cross_ide_smoke.py` — mismo ajuste de assert.

**Fuera del repo (memoria del agente, `~/.claude/projects/C--Cortex/memory/`):**
- `codex-mcp-trust-root-cause.md` (nuevo) + `MEMORY.md` (índice actualizado).

---

## 6. Estado de tests

```
136 passed, 1 failed
```
- **El único fallo es PREEXISTENTE y AJENO:**
  `tests/unit/ide/test_adapters_phase4.py::test_canonical_skill_files_in_disk_match_renders`
  → drift entre `.cortex/skills/cortex-documenter.md` (en disco) y su función de render.
  **Verificado con `git stash` de mis cambios: falla igual sin ellos.** No tocar como parte
  de esta tarea (es otro tema: re-sync de skills canónicos).
- Comando para re-correr:
  ```
  python -m pytest tests/unit/test_ide_adapters.py tests/unit/test_ide_module.py \
    tests/unit/ide/ tests/integration/test_smoke_multi_ide_phase7.py \
    tests/integration/test_cross_ide_smoke.py --no-cov -q
  ```

---

## 7. PENDIENTE — próximos pasos (en orden)

1. **Aplicar al proyecto real y verificar EN VIVO** (no se hizo; el código no toca el
   `~/.codex` real porque los tests usan `CODEX_HOME` aislado):
   - Correr en `C:\AppFutbol`: `cortex inject --ide codex` (o `cortex setup agent --ide codex`).
   - Confirmar que apareció `[projects."C:\\AppFutbol"] trust_level = "trusted"` en
     `~/.codex/config.toml` y que el bloque MCP del proyecto quedó endurecido.
   - **Reabrir Codex Desktop** (el trust se evalúa al cargar el proyecto).
   - Verificar en Codex: comando `/mcp` debe mostrar `cortex` con sus tools, **sin** el ERROR
     de trust en los logs.

2. **CONFIRMAR la sintaxis exacta del trust** ⚠️ — `[projects."<path>"] trust_level =
   "trusted"` fue **inferida** del mensaje de error de Codex + comportamiento conocido del
   CLI; **las docs públicas no la detallan**. Si tras reabrir Codex el ERROR persiste, este
   es el primer sospechoso. Alternativas a probar: dejar que Codex escriba el trust él mismo
   (aceptar su prompt de "trust this folder") y **leer cómo lo escribió** en
   `~/.codex/config.toml`, luego alinear nuestro `_build_cortex_trust_block()` a esa forma.

3. **Confirmar que el server arranca** una vez trusted — que `command` (ruta absoluta a
   `cortex.exe`) resuelve en el entorno con que Codex Desktop spawnea, y que 60 s alcanza. Si
   falla, mirar logs (ver §8).

4. **Casing del path** — Codex bajó a minúsculas `c:\appfutbol` en el hint; nuestra key usa
   el path con casing real `C:\AppFutbol`. En Windows debería matchear case-insensitive, pero
   si el trust no toma efecto, revisar esto.

5. **Decidir si aplicar también a `C:\AppFutbol`** quitando el bloque viejo: el proyecto ya
   tiene el bloque MCP project-scoped previo (sin hardening). `inject_mcp` lo **reemplaza**
   por marcadores, así que re-correr inject lo actualiza solo. OK.

---

## 8. Diagnósticos / recetas útiles (entorno del usuario)

### Datos del entorno
- **Codex = app Desktop (Electron)**, NO el CLI npm. Binario:
  `C:\Users\chuch\AppData\Local\OpenAI\Codex\bin\7dea4a003bc76627\codex.exe`
  (de `CODEX_CLI_PATH` en el env de `node_repl`). **`codex` NO está en el PATH de la shell** →
  por eso NO se puede usar `codex mcp add` ni `codex mcp list` desde la terminal.
- `cortex.exe`: `C:\Users\chuch\AppData\Roaming\Python\Python313\Scripts\cortex.exe` (SÍ en PATH).
- `python`: `C:\Python313\python.exe` (3.13.7).
- `CODEX_HOME` efectivo: `C:\Users\chuch\.codex`.

### Query a los logs de Codex (la que destapó la causa raíz)
Script reutilizable en `C:\Users\chuch\AppData\Local\Temp\cortex_codexlogs\analyze.py`
(copia `logs_2.sqlite` + `-wal`/`-shm` a temp y busca `cortex|mcp|AppFutbol|trust`). Para
re-correr tras aplicar el fix y ver si el ERROR de trust desapareció:
```powershell
# copiar DB (está con WAL activo) a temp y consultar con Python sqlite3
# tabla: logs(id, ts, level, target, feedback_log_body, file, line, ...)
# filtrar feedback_log_body por 'trust' / 'cortex' / 'mcp'
```

### Verificar el config global a mano
```powershell
Get-Content "$env:USERPROFILE\.codex\config.toml"   # ¿tiene [projects."C:\AppFutbol"]?
```

---

## 9. Referencias de código (codex.py, líneas actuales)

| Símbolo | Línea |
|---|---|
| `_CORTEX_TRUST_MARKER_OPEN_TPL` / `_CLOSE_TPL` | 68 / 69 |
| `_resolve_cortex_command()` | 236 |
| `_build_cortex_toml_block()` | 248 |
| `_replace_or_append_cortex_toml_block()` (fix re.sub) | 293 |
| `_codex_global_config_path()` (respeta CODEX_HOME) | 314 |
| `_trust_markers()` | 327 |
| `_build_cortex_trust_block()` | 336 |
| `_global_has_foreign_trust()` | 355 |
| `_merge_trust_into_global()` | 375 |
| `CodexAdapter.inject_mcp()` | 459 |
| `CodexAdapter._print_trust_notice()` | 507 |
| `CodexAdapter.uninstall()` (incl. paso 2b trust) | 525 |

Memoria relacionada: `~/.claude/projects/C--Cortex/memory/codex-mcp-trust-root-cause.md`.

---

## 10. Resumen de una línea para el próximo agente

> El código YA arregla el problema (MCP project-scoped mono-repo + auto-trust con aviso +
> hardening, merge no-destructivo, reversible). **Falta aplicarlo a `C:\AppFutbol`, reabrir
> Codex y verificar `/mcp` en vivo, confirmando de paso que `trust_level = "trusted"` es la
> sintaxis correcta.** Si el ERROR de trust persiste tras reabrir, el sospechoso #1 es la
> sintaxis exacta del trust (inferida, no confirmada por docs).
