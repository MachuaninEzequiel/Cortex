# rust/crates/cortex-workspace/src/pyyaml.rs

## Qué tiene adentro

Emisor YAML propio. Árbol `Node { Str, Bool, Int, Seq, Map }`. `implicitly_non_str`, `to_pyyaml_string`. Porta subset de PyYAML 6.x: folding a 80 columnas, quoting de indicadores, sequences indentless (`key:\n- item`), indent de continuaciones `padre+2`.

## Para qué sirve

Serializar `AgentHandoff` (y cualquier `Node`) con **paridad de bytes** contra `yaml.safe_dump(..., sort_keys=False, allow_unicode=True)`. `serde_yaml` no replica ese formato.

## Relaciones

### Recibe de

- `handoff::AgentHandoff::to_yaml` (principal consumidor).

### Envía a

- String YAML terminado en un único `\n`.

### Notas de implementación observadas en el código

`#![forbid(unsafe_code)]`. No cubre anclas/alias ni claves no-string (fuera del dominio del handoff).
