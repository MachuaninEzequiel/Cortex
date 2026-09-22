# src/ci/review_session.rs

## Qué tiene adentro

Sesiones de revisión CI (L3). Usa la primitiva Session. Checkpoints `CheckpointSource::CiBot` ⇒ `infer_mode` CI_REVIEW.

`open_review_session`, `report_ci_checkpoint`, `close_review_session`.

NO promueven el puntero activo (CI corre junto a la sesión del developer).

## Para qué sirve

Auditoría del bot de CI sin pisar la sesión humana.

## Relaciones

### Recibe de

- `SessionService` / storage.

### Envía a

- YAML de sesión review; example `ci_check` flujo L3.

### Notas de implementación observadas en el código

Únicos bits nuevos: source CI_BOT y no tocar active pointer.
