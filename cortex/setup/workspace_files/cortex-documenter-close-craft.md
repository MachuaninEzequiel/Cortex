---
name: cortex-documenter-close-craft
description: Craft on-demand del anchor de cierre — claims verificables, handoff útil, señales de ADR y auditoría final. Léelo SOLO al escribir la nota (PASO 4) y antes de persistir (PASO 8), no antes: es contexto on-demand, no carga permanente.
when-to-use: cortex-documenter, fase de escritura de la session note.
---

# Craft de cierre — escribir una nota que valga para siempre

## 1. Claims verificables (evidencia observable > opinión)

Toda afirmación de la nota debe tener **un ancla en el briefing**. Si no hay
ancla, no es una claim: es una opinión, y las opiniones van como contexto, no
como resultado.

| ❌ Opinión | ✅ Claim verificable |
|---|---|
| "Mejoramos la performance del search" | "El hook `bench-search` pasó (exit 0): cold query 20.8× vs baseline (ver `verification_results[0]`)" |
| "El refactor quedó bien" | "Los 3 archivos del diff (`src/retrieval.rs`, …) pasaron `cargo test -p cortex-core` (hook `test-core`, passed=true)" |
| "Quedó un tema de auth" | "`out_of_scope_files` incluye `src/auth.py`; el checkpoint 2 lo declaró como pendiente (◌, sin commit)" |

Anclas disponibles: `verification_results` (hooks: name/exit_code/output),
`files_verified_by_git` (✓) vs `files_declared_only` (◌), `diff_entries`,
`raw_checkpoints`, `contradictions`. Si una claim menciona test/build/lint/
check/ci, necesita un hook o archivo que la respalde — el quality gate la
rechaza con >10 chars triviales.

## 2. Placeholders prohibidos

`TBD`, `TODO`, `FIXME`, `???`, `xxx`, `fill me`, `[pendiente]` — el
self-review y los quality gates los marcan. Si uno queda en tu draft:

1. Arreglalo ahora con contenido real del briefing (hay diff + hooks: la
   información existe).
2. Si es deuda real pendiente, formulala como `next_step` verificable
   ("Falta el hook `docs-validate` en `ci.yml`", no "falta terminar docs").
3. Si no podés resolverlo: dejalo explícito en `## Self-review warnings` para
   el próximo agente — nunca silencio.

## 3. Handoff útil (context_for_next)

Una nota de `handoff` vale por lo que el próximo agente puede hacer SIN
rellenar huecos. El `next_steps`/`context_for_next` debe responder:

- **Qué falta, verificable**: archivos `unimplemented`/◌ y hooks fallidos
  (`"verification_results[2] failed: docs-validate"`), no "falta terminar".
- **Cómo retomar**: el comando exacto (`cortex session current` + el path de
  la nota, o re-correr el hook que falló).
- **Qué NO repetir**: decisiones ya tomadas (enlazá ADR/decision) y
  callejones ya explorados — ahorra una sesión.
- **Blocker vs pendiente**: distingüí lo que bloquea (hook requerido fallido)
  de lo que es deuda aceptada (declarada, con dueño implícito: la próxima
  sesión la prioriza).

## 4. Cuándo sugerir ADRs — señales que el documenter ya detecta

El briefing trae `suggested_adrs` con `confidence`. Detección por señales de
texto en checkpoints/notas (`decidimos`, `chose`, `instead of`, `trade-off`,
`vs`, `rejected`, `ADR` — 2+ señales ⇒ high confidence). No te detengas ahí:

- Aplicá los 3 criterios a CADA candidata: ¿hard to reverse >1 semana?
  ¿surprising sin contexto? ¿real trade-off con alternativa rechazada con
  razones? Los 3 ⇒ `adr`. Si no, es `decision` o queda inline.
- Una decisión sin alternativa rechazada NO es un trade-off; un gusto no es
  un criterio objetivo. Si el objetivo era for zar una decisión rápida, esa
  prisa es justo la señal de que necesita registro permanente.

## 5. Auditoría final antes de persistir (PASO 8)

Checklist de 60 segundos:

- [ ] Cada archivo tocado tiene marca: ✓ verified o ◌ declared-only (y los ◌ figuran en next_steps).
- [ ] Cada claim tiene ancla en el briefing (hook/archivo/checkpoint).
- [ ] Cero placeholders (`TBD/TODO/FIXME/???`).
- [ ] Los enlaces apuntan a ids reales (`[[spec-id]]`, `[[adr-id]]`, PR/commit).
- [ ] La nota cuenta la HISTORIA del delta: sorpresas + decisiones in-flight,
      no solo el diff.
- [ ] `contradictions` con severity ≥ warn están mencionadas, no escondidas.
- [ ] Si cerraste `handoff`: el lector puede retomar con solo leer la nota.
- [ ] El status no miente: hook requerido fallido o `unimplemented` ⇒ `handoff`.

## 6. Anti-Rationalization Signals

| Pensamiento | Realidad | Acción |
|---|---|---|
| "El briefing ya documenta todo" | Son DATOS; tu trabajo es VOZ y CRITERIO | Escribí prosa con sorpresas y decisiones |
| "Mejor `closed` para que cierre rápido" | Si hooks fallaron o hay unimplemented, mentís | Status = handoff cuando corresponda |
| "Voy a copiar el contenido de la spec" | Reference > Duplicate | Enlazá `[[spec-id]]`, narrá el delta |
| "No vale la pena un ADR para esto" | La intuición no es criterio | Aplicá los 3 criterios objetivos |
| "Es BYO, no hay nada que escribir" | Hay diff + spec + hooks | Sintetizá lo que hay |
| "Los declared-only no se ven, los omito" | Eso oculta deuda | Marcá ◌ y dejalo en next_steps |
| "Self-review me dio warnings, los ignoro" | El próximo agente vivirá con tu draft | Arreglá o mencioná en la nota |