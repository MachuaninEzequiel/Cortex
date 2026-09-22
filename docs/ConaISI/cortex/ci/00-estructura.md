# Estructura — `cortex/ci`

## Para qué existe esta carpeta

cortex.ci — Phase 07 CI plugin (Pluggable Middle).

## Árbol interno (código, sin `__pycache__`)

```
ci/
├── __init__.py
├── diff_io.py
├── markdown_formatter.py
├── result.py
├── review_session.py
├── session_matcher.py
└── validator.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/ci/__init__.py` | 31 | cortex.ci — Phase 07 CI plugin (Pluggable Middle). |
| `cortex/ci/diff_io.py` | 84 | cortex.ci.diff_io — Resolve the diff text from CLI inputs. |
| `cortex/ci/markdown_formatter.py` | 121 | cortex.ci.markdown_formatter — Render a ``ValidationResult`` as Markdown for the Level 2 PR comment workflow. |
| `cortex/ci/result.py` | 104 | cortex.ci.result — Typed inputs and outputs for the CI validator. |
| `cortex/ci/review_session.py` | 157 | cortex.ci.review_session — CI-owned review-session helpers (Level 3). |
| `cortex/ci/session_matcher.py` | 49 | cortex.ci.session_matcher — find the Session matching a PR. |
| `cortex/ci/validator.py` | 264 | cortex.ci.validator — Validate a PR against its Session + spec. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.ci.markdown_formatter`
- `cortex.ci.result`
- `cortex.ci.validator`
- `cortex.documenter.reconstruction`
- `cortex.documenter.spec_loader`
- `cortex.session`
- `cortex.session.models`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.session.verification`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.ci`
- `cortex.ci.markdown_formatter`
- `cortex.ci.session_matcher`
- `cortex.ci.validator`
- `cortex.cli.ci`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
