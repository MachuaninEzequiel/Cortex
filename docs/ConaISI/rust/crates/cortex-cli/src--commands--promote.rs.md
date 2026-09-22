# rust/crates/cortex-cli/src/commands/promote.rs

## Qué tiene adentro

`promote-knowledge`: dry-run por default, `--apply` ejecuta. `--actor`, `--json`. Llama servicio de promoción enterprise.

## Para qué sirve

Promover candidatos revisados al vault enterprise.

## Relaciones

### Recibe de

- `cortex_enterprise` knowledge_promotion.
- org.yaml + vault.

### Envía a

- records.jsonl / notas promovidas; stdout plan.

### Notas de implementación observadas en el código

`--dry-run` default true, overridden by `--apply`.
