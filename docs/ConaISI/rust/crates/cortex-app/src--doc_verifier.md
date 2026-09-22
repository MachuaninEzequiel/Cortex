# src/doc_verifier.rs

## Qué tiene adentro

Detecta si un PR trae docs de agente dentro del vault. Modo local (`git diff`) y modo CI (lista de files).

`DocVerificationResult`, `DocVerifier`.

`vault_files` es la UNIÓN; particiones new/modified/deleted mutuamente excluyentes y cubren todo `vault_files`. Paths fuera del vault se descartan.

Mensaje git: replica Python `check_output` sin stderr → `"git status failed: None"`.

## Para qué sirve

Decidir si hace falta el generador fallback.

## Relaciones

### Recibe de

- git status/diff o lista CI; raíz del vault.

### Envía a

- `PRService.generate_pr_docs`.

### Notas de implementación observadas en el código

Ola 4 fix: unión + particiones exhaustivas.
