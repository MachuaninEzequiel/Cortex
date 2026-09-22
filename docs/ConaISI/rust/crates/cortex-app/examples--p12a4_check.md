# examples/p12a4_check.rs

## Qué tiene adentro

`p12a4_check <golden_dir>`. S01–S14 generator+validator+verifier + PRService. Reloj fijo 2026-06-01. YAML error → `{{YAML_ERR}}`.

## Para qué sirve

Paridad P12A-4.

## Relaciones

### Recibe de

- `doc_generator`, `doc_validator`, `doc_verifier`, `pr`.

### Envía a

- `golden_p12a4.txt`.

### Notas de implementación observadas en el código

Mismo monkeypatch de fecha que el oráculo.
