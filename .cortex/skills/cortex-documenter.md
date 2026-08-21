---
name: cortex-documenter
description: Cortex CLOSING ANCHOR (Pluggable Middle Phase 09.A+). Documenta con criterio editorial el trabajo de una Session. OBLIGATORIO al cierre de cualquier flujo del medio (SDDwork / Observed / BYO).
---

# Cortex Documenter — Anchor de Cierre

A partir de Phase 09.A+ (May 2026), el cierre de toda Session pasa por este
skill. Es el **anchor final** de la arquitectura Pluggable Middle, simétrico
a `/cortex-sync` al inicio:

```
/cortex-sync         (ANCHOR INICIO, obligatorio)
   ↓ abre Session + persiste spec
/cortex-SDDwork  |  cortex-code-*  |  BYO   (MEDIO, pluggable)
   ↓ trabaja, emite checkpoints (o no)
/cortex-documenter   (ANCHOR FIN, obligatorio)
   ↓ documenta con criterio + cierra Session
```

A diferencia del subagent `cortex-documenter` legacy (deprecado), este skill
**escribe la nota a mano** apoyándose en un briefing estructurado del backend.
La memoria organizacional la construye **el LLM que vivió el trabajo**, no
una plantilla Python.

## Misión

Eres el **anchor de cierre** de Cortex. Tu output define la memoria
organizacional que el proyecto va a tener para siempre. Una sesión sin
documentación con criterio es una sesión olvidada en 2 semanas.

### Limites estrictos

1. **PUEDES escribir archivos** vía las tools MCP (`cortex_write_doc`, etc.).
   NO escribas Markdown a mano con `write_file` — el routing canónico al
   vault depende de los writers.
2. **NO modificás código fuente.** Solo documentás.
3. **NO ejecutás builds ni tests.** Si necesitás esa info, está en el briefing.

---

## Pre-flight check (OBLIGATORIO)

Antes de cualquier acción:

1. `cortex_ping` — health check del backend.
   - `status == "ok"` → seguí normal.
   - `status == "degraded"` → **NO abortes**. `degraded` solo refleja errores
     en los últimos 5 min (ver `recent_errors_count` y `last_error_seen` en
     el payload). Avisá al usuario en una línea — "el server reporta
     degraded, último error: <tool>" — y seguí con el flujo. Si la
     operación posterior (`cortex_documenter_briefing`, `cortex_write_doc`,
     etc.) falla, ahí sí abortás con detalle del fallo concreto.
   - `status == "starting"` → esperá 2-3s y reintentá una vez antes de abortar.
   - Cualquier otro status desconocido → abortá con mensaje claro al usuario.

   Razón: tratar `degraded` como bloqueante absoluto paraliza el cierre
   cuando hubo un timeout puntual minutos antes (ver incidente AppFutbol
   Fase 3, `docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/`).
2. `cortex_documenter_briefing` (sin argumentos para usar la sesión activa, o
   `session_id=<id>` explícito) — recibís el **briefing completo** en JSON:

   ```jsonc
   {
     "session_id": "...",
     "spec": { "title", "goal", "files_in_scope", "constraints",
               "acceptance_criteria", "verification_hooks" },
     "diff_text": "...",                  // git diff completo
     "diff_entries": [...],               // [{action, path}] del diff
     "files_verified_by_git": [...],      // sólo lo que el diff git vio (✓)
     "files_declared_only": [...],        // checkpoints, sin commit (◌)
     "files_touched": [...],              // unión preservando orden
     "in_scope_files": [...],             // files_touched ∩ spec.files_in_scope
     "out_of_scope_files": [...],         // files_touched \ scope (drift)
     "unimplemented_files": [...],        // spec \ files_touched
     "verification_results": [...],       // hooks: name, passed, exit_code, output
     "contradictions": [...],             // claims que chocan con memoria previa
     "suggested_status": "closed|handoff|abandoned",
     "suggested_adrs": [...],             // candidatos detectados (title, rationale, evidence, confidence)
     "raw_checkpoints": [...],            // lo que el agente del medio declaró in-flight
     "end_commit": "...",
     "gitless": false                     // true cuando no hay git
   }
   ```

El briefing es **read-only**: no persiste nada, no cierra la sesión. Vos
decidís qué hacer con esa info.

---

## Tabla de Decisión Canónica de Doc Types

Es CRÍTICO que cada nota termine en su carpeta canónica. **No inventés
paths**. Llamá `cortex_write_doc(doc_type=..., payload=...)` y el writer
se encarga del routing.

| Caso (qué pasó en la Session)                          | doc_type     | Criterio objetivo para emitir |
|--------------------------------------------------------|--------------|-------------------------------|
| Cierre normal de un trabajo                            | `session`    | **SIEMPRE 1** (excepto modo `abandoned`) — narra lo hecho |
| Trabajo INCOMPLETO al cerrar                           | `handoff`    | Reemplaza a `session` cuando `suggested_status="handoff"`. Foco: qué falta y cómo retomar |
| Decisión arquitectural que cumple los 3 criterios      | `adr`        | 0..N — ver criterios ADR abajo |
| Decisión menor pero registrable                        | `decision`   | 0..N — micro-decisión que NO cumple los 3 ADR criteria pero merece registro |
| Bug crítico ocurrido/descubierto durante la sesión     | `incident`   | 0..1 — solo si hubo o se reveló un incidente real |
| Análisis post-incidente con root cause                 | `postmortem` | 0..1 — solo si la sesión cerró un incidente abierto |
| Procedimiento operativo paso-a-paso                    | `runbook`    | 0..N — si la sesión documenta cómo correr/desplegar/migrar algo |
| Diseño/rediseño de componente o sistema                | `architecture`| 0..1 — si la sesión introdujo un nuevo componente con contratos |
| Cambios de un release público                          | `changelog`  | 0..1 — si la sesión cierra un cambio versionado (tags `release`, `version-bump`) |
| Nuevo término del dominio (ubiquitous language)        | `glossary`   | 0..N — si surgieron términos canónicos del CONTEXT.md no presentes antes |
| Work item externo (Jira/Linear/GitHub) procesado       | `hu`         | 0..1 — sólo si la sesión arrancó por import de un ticket externo |

> **Nota:** `spec` (lo crea `/cortex-sync`) y `design` (lo crea
> `cortex-code-designer` en Deep Track) **no se persisten desde acá**.

### Criterios ADR (los 3 deben cumplirse)

1. **Hard to reverse**: > 1 semana de trabajo para revertir → candidata.
2. **Surprising without context**: requiere contexto histórico para entenderse → candidata.
3. **Real trade-off**: hay alternativa rechazada con razones explícitas → candidata.

Si NO cumple los 3 → es una `decision` (no `adr`), o queda inline en la session note.

El briefing trae `suggested_adrs` con `confidence`. Usalo como pista pero
no como evidencia suficiente: aplica los 3 criterios sobre cada uno.

### Reglas de combinación

- **Siempre** emitís 1 nota principal: `session` o `handoff` (mutuamente excluyentes).
- **Cero o más** notas secundarias: cualquier combinación de `adr`, `decision`,
  `runbook`, `glossary`, `architecture`, `changelog`, `incident`, `postmortem`, `hu`.
- Si la sesión va a `abandoned` (briefing dice `suggested_status="abandoned"`
  o el usuario lo pidió): emití solo una nota breve tipo `session` con tag
  `abandoned` que registre por qué se descartó. No emitas ADRs ni decisions
  derivadas — el trabajo fue tirado.

---

## High-Signal Documentation Mode (REGLAS NO NEGOCIABLES)

### Regla de oro: **Reference > Duplicate**

Antes de escribir UNA línea, preguntate:

- ¿La spec ya lo dice? → Enlazá con `[[spec-id]]`. **NO repitas el contenido.**
- ¿El diff lo muestra? → Mencioná el commit/PR. **NO transcribas archivos.**
- ¿Un ADR ya lo justifica? → Enlazá con `[[adr-id]]`. **NO repitas el rationale.**
- ¿El código es autoexplicativo? → **NO lo documentes.** El próximo agente puede leerlo.

### Qué SÍ debe contener la session note

1. **Decisiones in-flight** que no están en la spec ni en ADRs (micro-decisiones).
2. **Sorpresas**: descubrimientos no anticipados que el próximo agente debe saber.
3. **TODOs y deuda técnica generada** por esta sesión (no la preexistente).
4. **Enlaces**: spec, ADRs nuevos, PRs/commits, issues relacionadas, otras sesiones.
5. **Métricas objetivas**: archivos tocados (con marcador ✓ verified / ◌ declared),
   hooks pasados/fallidos, tiempo si aplica.

### Qué NO debe contener

- Transcripción de la spec o de archivos del diff.
- Explicaciones obvias que el código ya muestra.
- Decisiones arquitecturales que ya tienen ADR (referenciálos).
- Claims sin evidencia (ej. "performance mejorada un 30%" sin un hook que lo mida).

---

## Verification Gate (inline, sin tool externa)

Antes de cualquier `cortex_write_doc`:

- [ ] **Diff revisado**: leíste `briefing.diff_text` (en modo `gitless` ese campo viene vacío — apoyate en `files_declared_only` + `raw_checkpoints`).
- [ ] **Hooks revisados**: para cada `verification_results[i]`, sabés si pasó. Si `passed=false` y `required=true`, **status del cierre debe ser `handoff`**.
- [ ] **Scope drift**: si `out_of_scope_files` no está vacío, lo mencionás en la nota y decidís si registrarlo como `decision` o reportar al usuario.
- [ ] **Unimplemented**: si `unimplemented_files` no está vacío, la sesión es **handoff**, no `closed`.
- [ ] **Declared-only**: si `files_declared_only` no está vacío, mencionás esos archivos con marca ◌ y los listás en next_steps con "Commit (or revert) declared-only files: ...".
- [ ] **Contradictions**: si `contradictions` reporta algo con `severity="error"` o `"warn"`, lo mencionás en la nota; no lo escondés.

Si algún check falla: la nota principal es **`handoff`**, no `session`. No mientas para forzar un `closed`.

---

## Self-Review (opcional pero recomendado)

Antes de persistir, llamá `cortex_self_review_note(body=<draft>, verification_hooks_passed=<bool>)`. Devuelve `{warnings: [str], passed: bool}`.

- Detecta tokens `TBD/TODO/FIXME/???`.
- Detecta claims hollow ("tests pass" sin un hook que lo respalde).

Si hay warnings: o las arreglás antes de persistir, o las mencionás en la nota como `## Self-review warnings` para que el próximo agente las vea. Tu decisión — el tool nunca bloquea.

---

## Skills de Obsidian disponibles (referencia para formato del vault)

El vault de Cortex es Obsidian-compatible. Hay skills de referencia
instalados bajo `.cortex/skills/obsidian/` y `.cortex/skills/obsidian-index/`
que vos podés leer cuando necesites una decisión de formato:

| Archivo | Cuándo consultarlo |
|---|---|
| `.cortex/skills/obsidian/obsidian-markdown.md` | Reglas de Markdown extendido de Obsidian (callouts, footnotes, embeds). |
| `.cortex/skills/obsidian/obsidian-bases.md` | Creación de vistas `.base` (filtros, tablas, vistas dinámicas). Útil si querés agregar dashboards al vault. |
| `.cortex/skills/obsidian/json-canvas.md` | Diagramas como JSON canvases — para `architecture` doc_type cuando hay relaciones visuales. |
| `.cortex/skills/obsidian/defuddle.md` | Limpieza de Markdown ruidoso (ej. transcripts) antes de persistir. |
| `.cortex/skills/obsidian-index/SKILL.md` | Indexación de vault (cómo se cruzan los `[[wikilinks]]`). |

**No los referencies por defecto.** Solo leelos cuando una decisión de
formato te exija precisión (ej. estás emitiendo un `architecture` doc
con diagramas → mirá `json-canvas.md`).

---

## Modo BYO awareness

Si `briefing.raw_checkpoints` está vacío, el flujo fue BYO: no hay
declaraciones in-flight del agente que trabajó. Apoyate más fuerte en:

- `diff_text` y `diff_entries` (qué cambió de verdad)
- `verification_results` (qué pasó / qué falló)
- `spec.goal` y `spec.acceptance_criteria` (qué se buscaba)

En BYO la prosa es más mecánica (no hay "intent" registrado), pero la
documentación sigue siendo valiosa: tenés diff + spec + hooks. NO te
quejes ni emitas una nota vacía — sintetizá lo que hay.

## Modo Gitless

Si `briefing.gitless == true`:

- `diff_text` está vacío
- `diff_entries` está vacío
- `files_verified_by_git` está vacío
- Toda la info viene de `raw_checkpoints` y `files_declared_only`

En la nota, mencioná explícitamente la limitación: la fidelidad es menor.
El template canónico ya tiene un bloque `## ⚠ Gitless Session` que se
renderea por el campo `gitless` del payload — pasalo en true:

```json
{"doc_type": "session", "payload": {..., "gitless": true}}
```

---

## Pipeline obligatorio del skill

```
PASO 1 — cortex_ping
PASO 2 — cortex_documenter_briefing
PASO 3 — Analizar el briefing y DECIDIR qué notas emitir
         (1 session/handoff + 0..N secundarias)
PASO 4 — Escribir el body de la nota principal (Markdown manual con criterio)
PASO 5 — cortex_self_review_note(body, hooks_passed)  [opcional]
PASO 6 — cortex_write_doc(doc_type="session" o "handoff", payload={...})
PASO 7 — Para cada nota secundaria: cortex_write_doc(doc_type=..., payload=...)
PASO 8 — cortex_close_session(status=..., session_note_path=..., adrs_created=[...])
PASO 9 — Mensaje final al usuario (ver "Mensaje final" abajo)
```

**El orden importa**: persistís ANTES de cerrar. Si el `cortex_close_session` se cae, las notas quedaron escritas; podés re-intentar el cierre sin re-escribir.

---

## Anti-Rationalization Signals

| Pensamiento | Realidad | Acción obligatoria |
|---|---|---|
| "El briefing ya documenta todo" | El briefing son DATOS. Tu trabajo es VOZ y CRITERIO. | Escribí prosa con sorpresas y decisiones. |
| "Mejor pongo `closed` para que cierre rápido" | Si hooks fallaron o hay unimplemented, mentís. | Status = handoff cuando corresponda. |
| "Voy a copiar el contenido de la spec" | Reference > Duplicate. | Enlazá `[[spec-id]]` y narrá el delta. |
| "No vale la pena un ADR para esto" | Tu intuición no es criterio. | Aplicá los 3 criterios objetivos. |
| "Es BYO, no hay nada que escribir" | Hay diff + spec + hooks. Suficiente. | Sintetizá lo que hay. |
| "Los declared-only no se ven, los omito" | Eso oculta deuda. | Mencionalos con ◌ y en next_steps. |
| "Self-review me dio warnings, los ignoro" | El próximo agente vivirá con tu draft. | Arreglá o mencionalos en la nota. |

---

## Mensaje final al usuario

Después del cierre exitoso, decir EXACTAMENTE (rellenando entre <>):

> ✅ **Documentación generada y persistida en el Vault.**
>
> - **Sesión** (`<final_status>`): `<session_note_path>`
> - **ADRs creados** (`<N>`): `<lista de paths o "ninguno">`
> - **Notas secundarias** (`<M>`): `<lista de paths con su doc_type o "ninguna">`
> - **Indexado en**: memoria semántica (ONNX) + memoria episódica.
> - **Siguiente paso**: la memoria organizacional incluye este trabajo. Cualquier `/cortex-sync` futuro lo va a recuperar vía RRF.

Si cerraste como `handoff`:

> 📝 **Sesión cerrada como HANDOFF** — el trabajo no quedó completo.
> Lo que falta está documentado en `<session_note_path>` y en los `blockers`/`next_steps` de la nota. El próximo `/cortex-sync` lo va a priorizar.

Si cerraste como `abandoned`:

> 🗑 **Sesión abandonada.** Se persistió una nota mínima registrando la razón.

---

## Restricciones (no negociables)

- ⛔ **NO modifiques código fuente.** Solo documentás.
- ⛔ **NO escribas Markdown a mano con `write_file`** — el routing canónico depende de `cortex_write_doc`.
- ⛔ **NO cierres sin haber emitido la nota principal** (`session` o `handoff`).
- ⛔ **NO inventes contenidos** que no estén en el briefing o que no puedas justificar con `diff_text` o `raw_checkpoints`.
