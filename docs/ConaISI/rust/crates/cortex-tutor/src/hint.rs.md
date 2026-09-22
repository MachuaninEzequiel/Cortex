# rust/crates/cortex-tutor/src/hint.rs

## Qué tiene adentro

Puerto de `cortex.tutor.hint`: ProjectState + HintEngine con cadena de prioridad L0..L7 (primer match gana; L7 interpola conteos como el f-string de Python).
Archivo de 172 líneas.
Símbolos públicos observados:
- `pub struct Hint`
- `pub struct ProjectState`
- `pub fn get_hint(state: &ProjectState) -> Hint`

## Para qué sirve

Puerto de `cortex.tutor.hint`: ProjectState + HintEngine con cadena de prioridad L0..L7 (primer match gana; L7 interpola conteos como el f-string de Python).

## Relaciones

### Recibe de

- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-tutor`: cortex-workspace, content/*.txt

### Envía a

- Crate `cortex-tutor` envía hacia: cortex-cli tutor, cortex-actions learn.topic (tópicos estáticos)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tutor/src/hint.rs`.
