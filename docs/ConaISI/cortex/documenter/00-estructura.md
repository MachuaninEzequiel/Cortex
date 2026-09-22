# Estructura — `cortex/documenter`

## Para qué existe esta carpeta

cortex.documenter — Documenter Reconstruction Mode (Phase 01).

## Árbol interno (código, sin `__pycache__`)

```
documenter/
├── __init__.py
├── adr_evaluator.py
├── contradiction_detector.py
├── diff_parser.py
├── interactive.py
├── persistence.py
├── reconstruction.py
└── spec_loader.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/documenter/__init__.py` | 60 | cortex.documenter — Documenter Reconstruction Mode (Phase 01). |
| `cortex/documenter/adr_evaluator.py` | 115 | cortex.documenter.adr_evaluator — Surface ADR candidates from checkpoints. |
| `cortex/documenter/contradiction_detector.py` | 93 | cortex.documenter.contradiction_detector — Pluggable memory-search. |
| `cortex/documenter/diff_parser.py` | 77 | cortex.documenter.diff_parser — Parse ``git diff --name-status`` output. |
| `cortex/documenter/interactive.py` | 343 | cortex.documenter.interactive — Interactive prompt UX for ``finish-session``. |
| `cortex/documenter/persistence.py` | 482 | cortex.documenter.persistence — Persist a ReconstructionOutput. |
| `cortex/documenter/reconstruction.py` | 487 | cortex.documenter.reconstruction — Documenter reconstruction algorithm. |
| `cortex/documenter/spec_loader.py` | 133 | cortex.documenter.spec_loader — Read a spec back from disk. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation.common`
- `cortex.documentation.data`
- `cortex.documentation.writers`
- `cortex.documenter.adr_evaluator`
- `cortex.documenter.contradiction_detector`
- `cortex.documenter.diff_parser`
- `cortex.documenter.persistence`
- `cortex.documenter.reconstruction`
- `cortex.documenter.spec_loader`
- `cortex.handoff`
- `cortex.services.note_service`
- `cortex.session`
- `cortex.session.models`
- `cortex.session.service`
- `cortex.session.verification`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.ci.result`
- `cortex.ci.validator`
- `cortex.documenter`
- `cortex.documenter.persistence`
- `cortex.documenter.reconstruction`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
