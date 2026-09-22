# Documenter: contradicciones y ADRs

Módulos: `cortex/documenter/{contradiction_detector,adr_evaluator,reconstruction,persistence}.py`, `cortex-app/src/documenter/`, MCP `cortex_finish_session`, `cortex_documenter_briefing`, `cortex_self_review_note`. CLI `finish` / `finish-session`.

Este es el hueco más honesto de ConaISI: el Protocol existe porque “pure-Python cannot judge”; el CLI pasa NoOp.

## Reconstructor (no tocarlo)

8 pasos, stateless, no muta la Session (`DocumenterPersister` escribe). Carga spec, diff `start_commit`→HEAD, hooks, files_in_scope vs tocados, contradicciones opcionales, handoff sintético, status, ADRs.

`run_hooks=False` en briefing MCP para no timeout en `npm build`. TypeSafe no corre hooks.

## Contradicciones — implementar el Protocol

Firma actual (ficha): `find_contradictions(...)` → lista de `ContradictionFinding`.

Backend TypeSafe:

1. **Prefiltro en código** (obligatorio, jaggedness #5): `cortex_search` / HybridSearch con query = título+nota de los checkpoints + files tocados, intent SEMANTIC, top ADRs/decisions/specs (p. ej. 10). ACL enterprise si aplica.
2. **Un call** state = `{diff_name_status, diff_stat_or_sliced_hunks, checkpoints_notes, candidates: [{id, title, body_chunk}]}`.
3. Por candidato:

```text
Noul contradicts_{id}
  instructions: {
    question: "Does the current work contradict this prior decision?",
    compare: ["diff", "candidates[i].body_chunk"],
    focus: "A contradiction is a change that violates a still-binding decision, not a refinement or a documented supersession."
  }
  criteria:
    true: { what: "The diff does the opposite of what the decision requires", examples: ["ADR forbids ORM X; diff adds ORM X"] }
    false: { what: "Compatible, orthogonal, or the diff explicitly supersedes the decision", examples: ["New ADR replacing the old one in the same diff"] }

Noul still_binding_{id}
  "Is this prior decision still presented as current (not superseded, not contradicted, not expired) in its own text?"
```

4. Código:

```text
si contradicts.noul >= 0.7 y still_binding.noul >= 0.7 → ContradictionFinding (grave)
si contradicts.noul >= 0.7 y still_binding bajo → finding leve / “possible supersession”
si 0.4 < contradicts < 0.7 → finding con flag review (MemoryEntry.confidence = asserted)
si bajo → nada
```

5. Persistencia: el `confidence` tri-estado de `MemoryEntry` **nace acá**. Mapeo:

| Condición | `MemoryEntry.confidence` |
|---|---|
| Verification hooks passed y contradicciones vacías o noul bajo | `verified` |
| Hooks passed, contradicción media | `asserted` |
| Contradicción grave | `contradicted` (y el finding se persiste; no se borra el ADR viejo — eso es promote/humano) |

No hay que cambiar el enum. Hay que dejar de poner `verified` por default cuando el detector fue NoOp.

Si el state del diff es enorme: slice a files_in_scope (el reconstructor ya compara scope vs tocados). No mandar el diff del monorepo.

## ADRs — reemplazar `_DECISION_PATTERNS`

Tres criterios que **el propio código declara** y dice no poder juzgar:

```text
Noul hard_to_reverse
  "Would undoing this decision be costly (API break, data migration, public contract, security model)?"

Noul surprising_without_context
  "Would a future contributor be surprised by this choice without a written record?"

Noul real_tradeoff
  "Does the work choose between real alternatives with downsides, rather than mechanically following a spec?"
```

Composite en código (pesos del equipo, no del modelo):

```text
adr_score = 0.4 * hard + 0.3 * surprising + 0.3 * tradeoff
si adr_score >= 0.65 y min(confidence-equivalente) ...
```

Noul no tiene confidence: la incertidumbre *es* el noul cerca de 0.5. Si alguno de los tres ∈ (0.4, 0.6) → candidato débil, interactive mode (documenter `default_mode: auto | interactive` ya existe) pregunta al humano. Si los tres altos → `ADRSuggestion` con rationale = los tres noul (visible al reviewer, como exige la ficha).

State: checkpoints notes + diff summary (name-status + hunks de files que no son process artifacts). BYO mode sin checkpoints: la ficha dice no minar ADRs. Respetar eso. TypeSafe no inventa narrativa donde no hay.

Título del ADR: **no** lo genera Jev. `_title_from_note` se queda, o el writer Jinja, o el humano en interactive. Jaggedness #8.

## Self-review note

MCP `cortex_self_review_note`: lugar natural para un segundo call **solo si** el primero encontró contradicción media/alta o adr_score alto. Segunda call con state enriquecido (el ADR candidato completo, no el chunk). Esa sí es dependencia real (fetch). Si no hubo señal, no hay segunda call.

## Qué mejora

- Finish deja de escribir “verified” de mentira.
- El vault deja de acumular ADRs-keyword (“we decided to…” en un checkpoint de typo).
- El próximo retrieval (experimento 1) encuentra decisiones reales.
- El loop positivo de la tesis: documenter limpio → retrieval limpio → agentes que no contradicen ADRs → menos findings → más `verified` genuinos.

## Qué no hacer

- Un Noul `is_good_session`. Mezcla todo.
- Mandar el vault como candidatos. Prefiltrar.
- Generar el cuerpo del ADR.
- Correr esto en el briefing MCP con hooks de build. El reconstructor ya separa briefing (`run_hooks=False`) de finish.
