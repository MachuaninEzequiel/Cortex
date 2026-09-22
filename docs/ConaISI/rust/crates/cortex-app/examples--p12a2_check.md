# examples/p12a2_check.rs

## Qué tiene adentro

`p12a2_check <fixtures_dir> <golden_dir>`. Escenarios S01–S09 de `p12a2_golden.py` sobre `WorkItemService`. Prefija excepciones Python (`KeyError/...`) a los `Result<String>`.

## Para qué sirve

Paridad P12A-2.

## Relaciones

### Recibe de

- `workitems` + writer HU.

### Envía a

- `golden_p12a2.txt`.

### Notas de implementación observadas en el código

Mensajes de error son contrato.
