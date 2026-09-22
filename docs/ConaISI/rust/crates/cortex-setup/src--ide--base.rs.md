# rust/crates/cortex-setup/src/ide/base.rs

## Qué tiene adentro

Marcadores `BEGIN/END CORTEX SECTION`. `generate_autogen_header`, `backup_file`, `deep_merge_dict`, `append_to_markdown`, marker extract/strip/upsert, `is_cortex_owned_file`, `is_content_identical_to_bundle`, `json_dump_ascii`/`utf8`, `is_wsl`, `is_new_layout`.

## Para qué sirve

Helpers compartidos byte-a-byte con `cortex/ide/base.py`.

## Relaciones

### Recibe de

- IdeCtx + archivos destino.

### Envía a

- Todos los adapters y skills_bundle (upsert composed).

### Notas de implementación observadas en el código

Header empieza con `\n`. Backup `*.cortex_backup_%Y%m%d_%H%M%S`.
