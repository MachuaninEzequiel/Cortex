---
title: Triadic Agent Model
status: stable
introduced_in: Phase 09.A+ (May 2026)
---

# Triadic Agent Model

> **TL;DR.** Cortex se estructura en tres skills invocables con `/`:
> `/cortex-sync` (anchor inicio, OBLIGATORIO), un middle pluggable
> (`/cortex-SDDwork` o BYO), y `/cortex-documenter` (anchor cierre,
> OBLIGATORIO). Los dos anchors construyen la memoria organizacional;
> el middle ejecuta el trabajo.

## El modelo

```
┌─────────────────────────────────────────────────────────────────┐
│  /cortex-sync                     ANCHOR INICIO (obligatorio)   │
│  • Carga contexto histórico (ONNX/hybrid RRF)                   │
│  • Emite propuesta interactiva (cortex_emit_proposal)           │
│  • Persiste spec (write_spec_note_canonical)                    │
│  • Abre Session                                                 │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│  MIDDLE (pluggable)                                             │
│  ─────────────────                                              │
│  /cortex-SDDwork   o   cortex-code-* (Deep Track)  o  BYO       │
│  • Implementa el trabajo                                        │
│  • Emite checkpoints (Managed/Observed) o no (BYO)              │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│  /cortex-documenter               ANCHOR CIERRE (obligatorio)   │
│  • cortex_documenter_briefing → contexto del cierre              │
│  • Decide doc_type(s) por criterios objetivos                   │
│  • Escribe la nota A MANO (criterio editorial del LLM)          │
│  • cortex_write_doc por cada nota (routing canónico al vault)   │
│  • cortex_self_review_note (opcional) — auto-crítica            │
│  • cortex_close_session — termina la Session                    │
└─────────────────────────────────────────────────────────────────┘
```

## Por qué triádico

La arquitectura previa hacía toda la documentación con un pipeline Python
(`Reconstructor` + `DocumenterPersister`). El resultado era una nota
estructurada generada por template Jinja a partir de checkpoints. **Cumplía
la forma pero perdía la voz**: el LLM que vivió el trabajo no escribía la
documentación; un template juntaba sus checkpoints.

El pilar fundacional de Cortex es que **el que hizo el trabajo es el que
documenta** — porque sólo él tiene las sorpresas, las micro-decisiones
in-flight, y el contexto de por qué algo es no-obvio. Phase 09.A+ restaura
este pilar sin tirar lo que el pipeline Python sí hacía bien (objetividad
del diff, ejecución determinista de hooks, heurísticas de ADR).

## Contratos entre los tres anchors

### sync → middle

`cortex-sync` deja persistido un **spec** en el vault y una **Session OPEN**
con `start_commit`/`start_branch` del repo (o sentinel `gitless` si no hay
git). El middle resuelve el spec contra el código real.

### middle → documenter

El middle declara su trabajo via `cortex_session_checkpoint`. Cada checkpoint
contiene:
- `verified_claims`: hechos comprobables (tests pasados, archivos leídos)
- `unverified_claims`: supuestos no probados
- `artifacts_touched`: paths tocados (no necesariamente committed)
- `note`: prosa breve con la intención

El documenter recibe esos checkpoints + diff git + verification hooks en su
**briefing**, y elige qué surfacar en la nota.

### documenter → memoria organizacional

El documenter persiste 1 nota principal (`session` o `handoff`) + 0..N
notas secundarias (`adr`, `decision`, `runbook`, `incident`, etc.). Cada
escritura va por el writer canónico de su `doc_type`, que rutea al folder
canónico del vault. La nota se indexa en semantic (ONNX) + episódica.

## La tabla canónica de doc types

El skill `/cortex-documenter` decide qué notas emitir aplicando criterios
objetivos. La tabla completa:

| `doc_type` | Folder | Cuándo emitirla | Cantidad |
|---|---|---|---|
| `session` | `vault/sessions/` | Cierre normal de trabajo (NO handoff) | 0..1 (excluye `handoff`) |
| `handoff` | `vault/handoffs/` | Trabajo INCOMPLETO al cerrar | 0..1 (excluye `session`) |
| `adr` | `vault/decisions/` (prefix `ADR-N-`) | Decisión que cumple los 3 criterios (hard-to-reverse + surprising + real trade-off) | 0..N |
| `decision` | `vault/decisions/` | Decisión menor pero registrable (no cumple los 3 criterios ADR) | 0..N |
| `incident` | `vault/incidents/` | Bug crítico ocurrido/descubierto durante la sesión | 0..1 |
| `postmortem` | `vault/postmortems/` | Análisis post-incidente con root cause | 0..1 |
| `runbook` | `vault/runbooks/` | Procedimiento operativo paso a paso | 0..N |
| `architecture` | `vault/architecture/` | Diseño/rediseño de componente o sistema | 0..1 |
| `changelog` | `vault/changelog/` | Cambios de un release público | 0..1 |
| `glossary` | `vault/glossary/` | Nuevo término del ubiquitous language | 0..N |
| `hu` | `vault/hu/` | Work item externo procesado (Jira/Linear/GitHub) | 0..1 |

> `spec` lo crea `/cortex-sync`, no el documenter.
> `design` lo crea `cortex-code-designer` en Deep Track.

## MCP tools del closing anchor

| Tool | Función |
|---|---|
| `cortex_documenter_briefing` | Read-only reconstruction. Devuelve JSON con spec, diff (`text` + `entries`), `files_verified_by_git`, `files_declared_only`, hooks, scope, ADR candidates, contradictions, `raw_checkpoints`, `gitless`. |
| `cortex_self_review_note` | Pure inspection. Detecta placeholder tokens + hollow success claims. Informacional, nunca bloquea. |
| `cortex_write_doc` | Dispatch genérico por `doc_type` sobre los 11 writers canónicos. |
| `cortex_close_session` | Termina la Session sin re-reconstruir. Recibe el `final_status`, `session_note_path`, `adrs_created`. |

## Modo BYO

Si el middle fue BYO (sin checkpoints), el briefing trae `raw_checkpoints: []`.
El documenter se apoya más en `diff_text` + `verification_results` + `spec`
para reconstruir la prosa. Sigue produciendo notas válidas — solo pierde la
"voz" del agente que trabajó porque no la registró.

## Modo Gitless

Si no hay git en el workspace, el briefing trae `gitless: true`,
`diff_text` vacío, `files_verified_by_git` vacío, y `files_declared_only`
con todos los archivos referenciados por checkpoints. El template canónico
de session note ya tiene un bloque `## ⚠ Gitless Session` que se renderea
cuando `payload.gitless == true` al llamar `cortex_write_doc`.

## File provenance (Phase 09.A+ / May 2026)

Los `files_touched` del briefing se construyen como la unión de:

- `files_verified_by_git`: lo que el diff git mostró (✓ objetivo)
- `files_declared_only`: lo que checkpoints declararon pero NO está en el
  diff (◌ declarado, no committed)

El documenter surfacea esa procedencia en la session note:

```
## Files Touched
- ✓ src/auth.py
- ✓ tests/auth/test_login.py
- ◌ docs/AUTH.md
```

Y, si hay declared-only, agrega un next_step recordando commit-or-revert.

## Migración desde el subagent legacy

El subagent `cortex-documenter.md` (en `.cortex/subagents/`) sigue
existiendo y es funcional para IDEs single-agent que no soporten
slash-skills (Codex via cortex-pi). En esos casos:

- El subagent se invoca via Task tool de su orquestador
- Internamente usa `cortex_finish_session` (auto-persist con template Python)
- La salida es la session note "estructural" del modelo viejo

Para IDEs con slash-skills (Claude Code, opencode):

- **No usar el subagent.** Invocar `/cortex-documenter` directamente
- El skill produce notas con criterio editorial del LLM

Cuando todos los IDEs targeted soporten slash dispatch nativo, el subagent
se elimina (no es backward-compat permanente).

## CLI alternative

Para flujos sin LLM en el loop (CI, scripting, smoke tests):

```bash
cortex finish-session [--handoff --reason "..."] [--abandon --reason "..."]
```

Este comando:
- Corre `Reconstructor` (Python)
- Corre verification hooks
- Persiste la session note via `DocumenterPersister` (template Jinja)
- Cierra la Session

Es la **misma** ruta que el subagent legacy en modo Reconstruction.
Coexiste con el skill como fallback. La CLI imprime un tip al cierre
recordando que `/cortex-documenter` produce notas de mayor señal cuando
hay LLM disponible.
