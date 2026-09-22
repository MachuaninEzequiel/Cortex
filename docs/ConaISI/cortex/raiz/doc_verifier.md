# cortex/doc_verifier.py

## Qué tiene adentro

- `DocVerificationResult`: flags `has_agent_docs`, listas new/modified/deleted/valid/invalid.
- `DocVerifier(vault_path, root)`:
  - `verify_from_diff(base_branch)` — `git diff` local.
  - Modo CI: lista de archivos del payload (resto del archivo).

## Para qué sirve

Decidir si un PR ya trae docs de agente (entonces indexar) o hay que caer a `DocGenerator`.

## Relaciones

### Recibe de

- `git diff` o lista de paths CI.
- Directorio vault.

### Envía a

- CLI `verify-docs`, pipeline `DocumentationStage`.

---
Fuente: lectura de `cortex/doc_verifier.py`. No se usó documentación previa.
