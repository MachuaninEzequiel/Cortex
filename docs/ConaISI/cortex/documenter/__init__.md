# cortex/documenter/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/__init__.py` (60 líneas).
- **Módulo Python:** `cortex.documenter`.
- **Docstring del módulo:** cortex.documenter — Documenter Reconstruction Mode (Phase 01).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.documenter — Documenter Reconstruction Mode (Phase 01).

This package implements the **Documenter Reconstruction Mode** introduced
by the Pluggable Middle architecture (Phase 01). Given a closed-but-not-
yet-documented :class:`SessionRecord`, the reconstructor:

1. Loads the spec the session was anchored on.
2. Computes the diff from ``start_commit`` to HEAD.
3. Runs the verification hooks declared by the spec.
4. Cross-checks ``files_in_scope`` against the actually-touched files.
5. (Optionally) searches memory for contradictions.
6. Builds a synthetic :class:`cortex.handoff.AgentHandoff`.
7. Decides the suggested status (closed / handoff / abandoned).
8. Surfaces ADR candidates from checkpoint notes.

The output of step 8 is consumed by :class:`DocumenterPersister`
(Phase 01 / T1.5) to write the session note and any ADRs.

See: ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §7.

## Relaciones

### Recibe de

- `cortex.documenter.adr_evaluator` (ADRSuggestion, suggest_adrs)
- `cortex.documenter.contradiction_detector` (ContradictionDetector, ContradictionFinding, NoOpContradictionDetector)
- `cortex.documenter.diff_parser` (DiffEntry, parse_name_status)
- `cortex.documenter.persistence` (DocumenterPersister, FinishOverrides, FinishSessionResult)
- `cortex.documenter.reconstruction` (ReconstructionInput, ReconstructionOutput, Reconstructor)
- `cortex.documenter.spec_loader` (LoadedSpec, load_spec)
- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 60.
Reexportes observados:
- cortex.documenter.adr_evaluator: ADRSuggestion, suggest_adrs
- cortex.documenter.contradiction_detector: ContradictionDetector, ContradictionFinding, NoOpContradictionDetector
- cortex.documenter.diff_parser: DiffEntry, parse_name_status
- cortex.documenter.persistence: DocumenterPersister, FinishOverrides, FinishSessionResult
- cortex.documenter.reconstruction: ReconstructionInput, ReconstructionOutput, Reconstructor
- cortex.documenter.spec_loader: LoadedSpec, load_spec

---
Fuente: código de `cortex/documenter/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
