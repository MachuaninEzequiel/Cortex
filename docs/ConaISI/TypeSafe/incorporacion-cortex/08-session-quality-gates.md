# Session quality gates

Módulo: `cortex/session/quality_gates.py`. MCP `cortex_review_checkpoint`. Lo invoca el orquestador SDDwork después de cada checkpoint de subagente en Deep Track.

## Qué se queda en código (stage 1)

- `artifacts_touched ⊆ spec.files_in_scope` (scope vacío = wildcard).
- Checkpoint reporta *algo* (`verified_claims` o `artifacts_touched` no vacíos).
- `_is_process_artifact` (prefijos canónicos Cortex, no in-scope).

Eso es teoría de conjuntos. Jev no aporta. Si stage 1 falla → `redelegate`, sin modelo.

## Qué está hueco (stage 2)

- Placeholders `TBD` / `FIXME` / `???` en `note`.
- Si claims mencionan tests/build/lint/check/CI, al menos uno > 10 chars.

Un subagente puede escribir “ran the full integration suite against staging, all green” sin haber corrido nada. El gate actual lo acepta. `VerificationRunner` es la evidencia real cuando la spec declara hooks; muchos checkpoints no los tienen.

Literales de salida que **no se cambian**: `accept | redelegate | warn`. El orquestador ya ramifica en esos tres.

## TypeSafe en stage 2 (y solo si stage 1 pasó)

State:

```json
{
  "spec_goal": "...",
  "files_in_scope": ["..."],
  "checkpoint": {
    "note": "...",
    "verified_claims": ["..."],
    "unverified_claims": ["..."],
    "artifacts_touched": ["..."]
  },
  "diff_slice": "<name-status + hunks de artifacts_touched, no del repo entero>"
}
```

Questions (un call):

```text
Noul claims_supported_by_diff
  "Are the verified_claims actually supported by diff_slice (not merely asserted)?"

Noul note_matches_diff
  "Does checkpoint.note describe the same work as diff_slice, without claiming extra files or extra outcomes?"

Noul placeholders_or_vacuous
  "Is the note or claims vacuous, templated, or still containing unresolved placeholders?"

Score evidence_quality
  0: No evidence; claims are slogans
  1: Some concrete artifacts or commands, but outcomes are vague
  2: Concrete artifacts, commands, and outcomes that match the diff

Choice action
  accept: spec-compliant and evidence is sufficient to proceed
  warn: spec-compliant but evidence is weak; proceed and copy reason into unverified_claims
  redelegate: the work does not match the spec or the claims are unsupported
```

Código:

1. Si `placeholders_or_vacuous.noul` alto **o** el regex de TBD sigue matcheando → no hace falta Jev para el placeholder; el regex es más barato. Jev cubre “vacuous without TBD”.
2. Si `claims_supported_by_diff.noul < 0.5` y el checkpoint **afirma** tests/build → `warn` o `redelegate` según si stage 1 (scope) pasó. Scope OK + evidencia mentirosa = `warn` (el contrato actual: quality failed but spec compliance passed).
3. Si `action.confidence < 0.5` (Choice) → `warn`, no `redelegate`. No adivinar un loop de subagente.
4. El Choice `action` no es la autoridad si contradice stage 1. Stage 1 gana siempre.

Cookbook equivalente: citation_check (claim vs fuente). Acá la fuente es el diff.

## Verification hooks

Siguen siendo la gold evidence. Si `VerificationRunner` dice `passed=False`, quality gates no necesitan a Jev para fallar. Si `passed=True`, Jev puede igual `warn` si la nota afirma cosas que el hook no midió (cobertura, “all browsers”, “no regressions”).

## Mejora

Deep Track deja de aceptar checkpoints teatrales. El orquestador ya sabe `redelegate`. Lo que faltaba era un juez del *contenido* del claim. Eso baja el número de sessions `verified` falsas que después envenenan retrieval.
