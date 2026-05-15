# Hallazgos inesperados durante Fase 0 — y cambios realizados

**Fecha:** 2026-05-15
**Contexto:** Durante la ejecucion de Fase 0 aparecieron descubrimientos arquitecturales que el plan original no contemplaba. El creador instruyo: "tenes que escribirles una seccion en el plan, e instantaneamente realizar esos cambios". Este documento registra ambos.

**Directiva del creador:** "lo que tiene que estan bien hecho es todo lo que esta en `cortex/`, que son los archivos que realmente inyectan en la instalacion del usuario". Esta directiva es la **regla de oro de reconciliacion** que se aplica a todos los hallazgos de este documento.

---

## Hallazgo H-1: La SSoT real esta en codigo Python, no en `.cortex/`

### Descripcion

El plan original asumia que `.cortex/subagents/*.md` y `.cortex/skills/*.md` eran la **Single Source of Truth** de los prompts canonicos. La realidad es mas precisa:

**La SSoT real** son las funciones `render_*` en `cortex/setup/cortex_workspace.py`:

| Render function | Linea | Genera |
|---|---|---|
| `render_system_prompt()` | 24 | `.cortex/system-prompt.md` (o equivalente) |
| `render_agent_overview()` | 51 | overview content |
| `render_cortex_sync_skill()` | 71 | `.cortex/skills/cortex-sync.md` |
| `render_cortex_sddwork_skill()` | 186 | `.cortex/skills/cortex-SDDwork.md` |
| `render_subagent_explorer()` | 312 | `.cortex/subagents/cortex-code-explorer.md` |
| `render_subagent_implementer()` | 397 | `.cortex/subagents/cortex-code-implementer.md` |
| `render_subagent_documenter()` | 492 | `.cortex/subagents/cortex-documenter.md` |

Los archivos en `.cortex/subagents/`, `.cortex/skills/` y `cortex-pi/.pi/agents/` son **outputs** del setup. Si difieren del render, estan desactualizados — el render es la verdad.

### Implicancia para el plan

- **Fase 4** debe redefinirse con esta nueva claridad: la SSoT no es un archivo de markdown — es codigo Python. Los adapters de IDE deben:
  1. Llamar al render correspondiente (no leer `.cortex/subagents/<name>.md` directamente).
  2. Aplicar la traduccion de tools/frontmatter por IDE.
  3. Escribir el archivo en el path que el IDE espera.

  Los archivos en `.cortex/subagents/` se vuelven una **cache local** que el setup escribe para inspeccion del adopter, pero NO son la fuente.

- **Fase 5** debe tocar PRIMERO los renders en `cortex_workspace.py` y solo despues regenerar los archivos en disco. La advertencia del INVENTARIO seccion 5.6 sobre `cortex_workspace.py:249-250` se generaliza a todos los renders.

- **`cortex-SDDwork-cursor.md`** (el archivo problematico) NO tiene render en `cortex_workspace.py`. Es una skill que el adapter de cursor lee con `get_skill_prompt(project_root, "cortex-SDDwork-cursor")` (`cortex/ide/prompts.py:149`). Es contenido manual sin SSoT en codigo. Fase 4 debe eliminarlo o moverlo a render.

### Decision firmada

Aplicada la directiva "lo que esta en `cortex/` es la fuente": cualquier discrepancia entre render y archivo en disco se resuelve **regenerando el archivo desde el render**. Nunca al reves.

---

## Hallazgo H-2: `.cortex/subagents/cortex-documenter.md` estaba drifted del render

### Descripcion

Comparacion sistemica de los 5 archivos generados por render vs el contenido en disco:

| Archivo | sha render | sha disco (LF-canonical) | Estado |
|---|---|---|---|
| `.cortex/subagents/cortex-code-explorer.md` | `33490745915946fa` | `33490745915946fa` | OK |
| `.cortex/subagents/cortex-code-implementer.md` | `3bb57ad1806723dd` | `3bb57ad1806723dd` | OK |
| `.cortex/subagents/cortex-documenter.md` | `9433167051972cc3` | `1a81a5c1383cfdc3` | **DRIFT** |
| `.cortex/skills/cortex-sync.md` | `1b8dde229a530fd0` | `1b8dde229a530fd0` | OK |
| `.cortex/skills/cortex-SDDwork.md` | `4724da1f7cdc3436` | `4724da1f7cdc3436` | OK |

El unico drift estaba en `cortex-documenter.md`. El diff exacto:

```diff
-| Que se hizo en una sesion de trabajo | session | write_session_note         |
+| Que se hizo en una sesion de trabajo | session | write_session_note_canonical |
-| Especificacion previa al desarrollo  | spec    | write_spec_note            |
+| Especificacion previa al desarrollo  | spec    | write_spec_note_canonical  |
```

El render usaba los nombres correctos (`write_session_note_canonical`, `write_spec_note_canonical` — funciones que existen en `cortex/documentation/writers.py:590,609`); el archivo en disco tenia los nombres viejos sin sufijo `_canonical` (que **no existen** en el codigo). La copia espejo en `cortex-pi/.pi/agents/cortex-documenter.md` estaba alineada con el render (`9433167051972cc3`), pero la SSoT en `.cortex/subagents/` quedo congelada con la version anterior al rename.

Causa probable: alguien hizo el rename a `_canonical` en `cortex/setup/cortex_workspace.py` Y en `cortex-pi/.pi/agents/cortex-documenter.md` (manualmente o con `pi adapter sync_canonical_subagents`), pero `.cortex/subagents/cortex-documenter.md` no se regenero corriendo el setup despues del rename.

### Cambio realizado (instantaneo, antes de cerrar Fase 0)

**Acción:** regenerar `.cortex/subagents/cortex-documenter.md` invocando `render_subagent_documenter()` y sobrescribiendo el archivo.

**Comando equivalente:**

```python
from cortex.setup.cortex_workspace import render_subagent_documenter
from pathlib import Path
Path('.cortex/subagents/cortex-documenter.md').write_text(
    render_subagent_documenter(), encoding='utf-8', newline='\n'
)
```

**Verificacion post-cambio:**

```
.cortex/subagents/cortex-documenter.md (LF)        sha: 9433167051972cc3
render_subagent_documenter()                       sha: 9433167051972cc3
Aligned with render: True
```

**Diff resultante en git:**

```diff
- | session | write_session_note         |
+ | session | write_session_note_canonical |
- | spec    | write_spec_note            |
+ | spec    | write_spec_note_canonical  |
```

Solo esas 2 lineas cambiaron. Ningun otro contenido del archivo se altero.

**Impacto en alcance:** ninguno. El archivo ya era output del setup; regenerarlo manualmente equivale a haber corrido `cortex setup agent` justo antes de la Fase 1. No introduce funcionalidad nueva ni elimina nada.

---

## Hallazgo H-3: `.cortex/skills/cortex-SDDwork-cursor.md` no tiene render — viola principio rector

### Descripcion

El archivo `.cortex/skills/cortex-SDDwork-cursor.md`:
- NO tiene funcion `render_*` correspondiente en `cortex/setup/cortex_workspace.py`.
- Es leido por `cortex/ide/prompts.py:149` (`build_cursor_prompts`) usando `get_skill_prompt(project_root, "cortex-SDDwork-cursor")` — busca el archivo en `.cortex/skills/`.
- Es una variante de skill especifica por IDE (cursor), lo cual **viola el principio rector #1** del plan ("Cortex se comporta igual en todos los IDEs").

### Por que NO se cambia en Fase 0

Eliminar el archivo o convertirlo en render requiere:
1. Refactorizar `build_cursor_prompts()` para que use `render_cortex_sddwork_skill()` (la canonica) y deje al adapter de cursor traducirlo.
2. Eliminar el adapter cursor "hibrido" que embebe explorer + implementer en el SDDwork-cursor.
3. Hacer que cursor delegue como cualquier otro IDE.

Esto es **alcance completo de Fase 4** (adapters SSoT). No corresponde anticiparlo en Fase 0.

### Cambio realizado en Fase 0

**Ninguno.** Solo documentacion.

### Accion para Fase 4

Listar `cortex-SDDwork-cursor.md` como archivo a eliminar tras refactorizar `cursor.py`. Crear render unico canonico (ya existe: `render_cortex_sddwork_skill()`) y dejar que el adapter de cursor lo consuma como cualquier otro adapter.

---

## Hallazgo H-4: Archivos huerfanos en `cortex-pi/.pi/agents/` sin render

### Descripcion

Los siguientes archivos viven en `cortex-pi/.pi/agents/` y NO tienen funcion `render_*` en `cortex/setup/cortex_workspace.py`:

- `cortex-SDDwork.md`
- `cortex-sync.md`
- `cortex-security-auditor.md`
- `cortex-test-verifier.md`
- `agent-chain.yaml`
- `teams.yaml`

Tampoco tienen contraparte en `.cortex/subagents/`. Son **bundle estatico de pi** — parte del repositorio que se copia tal cual al project root cuando el adopter corre `cortex setup --ide pi` (mecanismo: `cortex/ide/adapters/pi.py:115-126` con `shutil.copytree`).

Aplicando la directiva del creador ("lo que esta en `cortex/` es la fuente"): estos archivos NO estan en `cortex/`. No tienen SSoT en codigo. Son contenido manualmente mantenido del bundle de pi.

### Por que NO se cambia en Fase 0

Decidir si estos archivos deben:
- (a) Migrarse a renders en `cortex/setup/cortex_workspace.py` (volverlos generados como los otros).
- (b) Mantenerse como bundle estatico exclusivo de pi (porque pi tiene su propia identidad de agent set).
- (c) Migrar parte (los que tengan valor cross-IDE) y mantener parte (los que sean exclusivos de pi).

...es una **decision arquitectural del creador**, fuera del alcance de Fase 0 (read-only).

### Cambio realizado en Fase 0

**Ninguno.** Solo documentacion.

### Accion pendiente

Item para discusion con el creador en Fase 4 o como decision separada:

> Los archivos `cortex-pi/.pi/agents/cortex-{SDDwork,sync,security-auditor,test-verifier}.md` no tienen render en `cortex/`. ¿Migrarlos a renders (los volves cross-IDE) o consolidar pi como bundle "estatico de pi" cuyo contenido NO se rige por la SSoT cross-IDE?

---

## Hallazgo H-5: Bug colateral `cortex_search_vector` sin handler dispatch

### Descripcion

Ya documentado en `INVENTARIO.md` seccion 5.4. Resumen: el tool `cortex_search_vector` esta REGISTRADO en `handle_list_tools` (`cortex/mcp/server.py:113`) pero NO tiene branch en el dispatch (`handle_call_tool` lineas 519-636). Invocarlo devuelve error de tool no encontrado.

### Por que NO se cambia en Fase 0

Es un bug pre-existente sobre `cortex/mcp/server.py`. Tocarlo aqui invadiria Fase 1 (que refactoriza el server entero).

### Cambio realizado en Fase 0

**Ninguno.** Documentado como ARRASTRE-1 para que Fase 1 lo incluya en su alcance (decision pendiente del creador: ¿lo arregla Fase 1 mientras refactoriza, o se difiere a un plan separado?).

---

## Resumen de cambios materiales realizados durante Fase 0

| Archivo modificado | Origen del cambio | Verificacion |
|---|---|---|
| `.cortex/subagents/cortex-documenter.md` | Hallazgo H-2: regenerado desde `render_subagent_documenter()` | sha post-cambio = sha del render = `9433167051972cc3`. |

**Total: 1 archivo regenerado.** Cero archivos de codigo Python tocados. Cero tests modificados.

---

---

## Hallazgo H-6: 3 de 4 target adapters estan fundamentalmente incorrectos contra docs oficiales 2026

### Descripcion

Tras la directiva del creador del 2026-05-15 ("tenes la obligacion de buscar en las documentaciones oficiales (...) cada ide/cli tiene su forma de ser configurado"), se ejecuto investigacion exhaustiva via WebFetch a las docs oficiales de los 4 target IDEs. Resultado consolidado en `MATRIZ-NATIVA-IDES.md`.

**Resumen de divergencias detectadas:**

- **Codex**: el adapter actual escribe a paths que Codex no lee (`.codex/AGENTS.md`, `.codex/agents/`, `.codex/skills/`, `.codex/mcp.json`). Codex lee `AGENTS.md` en project root, no soporta subagents personalizados, y usa `.codex/config.toml` (TOML) con clave `[mcp_servers.<name>]` para MCP — no JSON. **El adapter actual NO instala MCP en Codex.**
- **pi**: el adapter actual copia `cortex-pi/.pi/agents/*.md` al project root. Pi **no usa esa carpeta** — sus skills van en `.pi/skills/` y AGENTS.md en root. Pi tampoco soporta subagents (cita: *"No sub-agents"*) ni MCP (cita: *"No MCP"*). El bundle copiado a `.pi/agents/` es **invisible para pi**.
- **opencode**: el adapter declara MCP tools (`cortex_save_session`, `cortex_search`, etc.) en el campo `tools:` del agent profile. opencode **solo acepta nombres nativos lowercase** ahi (`read`, `edit`, `bash`, `task`, etc.). Los MCP tools se descubren dinamicamente, no se declaran a priori.
- **claude_code**: el unico relativamente correcto. Solo le falta inyectar el campo `tools` traducido en el frontmatter del subagent escrito (hoy lo deja en blanco, heredando todas las tools del padre — viola la restriccion declarada por el prompt canonico).

### Por que sucede

El mecanismo de Cortex de "tomar el prompt canonico y traducirlo via adapter" es CORRECTO en concepto, pero los adapters **fueron escritos asumiendo APIs antiguas o documentacion desactualizada de cada IDE**. Codex agrego `[mcp_servers]` en TOML; pi nunca soporto MCP/subagents; opencode evoluciono el modelo de tools/permission. Los adapters quedaron congelados en una version mental anterior.

### Implicancia para el plan

El alcance de Fase 4 (adapters SSoT) **se TRIPLICA**:

- claude_code: cambio acotado (1-2 lineas para inyectar tools).
- opencode: cleanup mediano del campo `tools`.
- codex: **rediseno completo** del adapter.
- pi: **rediseno completo** del adapter, mas decisiones arquitecturales sobre que features de Cortex son posibles en pi.

Tambien el principio rector #1 del plan necesita refinarse: el **comportamiento conceptual** de Cortex es uniforme, pero la **materializacion** difiere — algunos IDEs (Codex, pi) no soportan subagentes, y por lo tanto Cortex en esos IDEs es funcionalmente reducido (single-agent flow en lugar de tripartita refinada).

### Cambio realizado en Fase 0

**Ninguno de codigo.** Solo documentacion: el archivo `MATRIZ-NATIVA-IDES.md` consolida toda la matriz nativa real con citas literales a las docs oficiales y acciones correctivas precisas por adapter.

### Items de firma del creador — FIRMADOS 2026-05-15

Los 4 items pendientes recibieron firma del creador. Resumen y referencia:

1. **pi se mantiene como TARGET y el adapter NO se toca.** El creador confirmo que `cortex-pi/` tiene contribuciones de comunidad funcionales y respeta ese estado. (Decision 1 en `MATRIZ-NATIVA-IDES.md` seccion 4).
2. **Codex acepta single-agent secuencial.** Un agente unico ejecuta las 3 fases del flujo tripartito secuencialmente. (Decision 2).
3. **Cursor: usar los 3 subagents reales.** Se elimina el hibrido `cortex-SDDwork-cursor.md` y `build_cursor_prompts()`. Se usan los renders canonicos en `.cursor/agents/`. (Decision 3).
4. **Community/experimental marcados como NO VALIDADOS.** Foco del plan: claude_code, opencode, pi (sin tocar), codex, cursor. El resto se etiqueta como "no validado contra docs oficiales 2026" sin reescritura. (Decision 4).

Detalles en `MATRIZ-NATIVA-IDES.md` seccion 4 y alcance corregido de Fase 4 en seccion 5.

---

## Reglas de oro derivadas para fases siguientes

1. **La SSoT es codigo Python en `cortex/`.** Cualquier discrepancia entre disco y render se resuelve regenerando desde render.
2. **Antes de editar un prompt canonico, identificar su fuente.** Si tiene render en `cortex_workspace.py`, editar el render. Si NO tiene render, decidir si necesita uno (Fase 4) o queda como contenido manual del bundle (caso pi).
3. **Hallazgos imprevistos NO se incorporan silenciosamente.** Se documentan en este archivo (o uno equivalente por fase: `HALLAZGOS-INESPERADOS-FASE-N.md`) y se decide explicitamente si se actuan en la fase actual o se difieren. La regla del plan "cero deuda tecnica" prohibe el carry-on silencioso.
