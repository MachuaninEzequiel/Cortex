# rust/crates/cortex-brain/src/tools.rs

## Qué tiene adentro

Catálogo ordenado (`BTreeMap`) de 7 tools:

| nombre | tier | hint |
|---|---|---|
| `memory.search` | Read | `<query> [top_k]` |
| `docs.related` | Read | `<tema> [precise\|fast]` |
| `cortex.health` | Read | |
| `vault.stats` | Read | |
| `session.current` | Read | |
| `webgraph.serve` | SafeAction | |
| `actions.propose` | Read | |

`dispatch`:

- `cortex.health` → `cortex doctor`
- `session.current` → `cortex context`
- `memory.search` / `docs.related` → `cortex search <args>` (query vacía: error o texto related)
- `vault.stats` → recorre `vault/**/*.md` nativo
- `webgraph.serve` → spawn detached `cortex webgraph serve --no-open`
- `actions.propose` → `cortex next --json`, formatea id/title; vacío = “nada pendiente”

`cortex_bin()` lee `CORTEX_BIN` o `"cortex"`. Tests: no hay tools mutadoras (`vault.reindex`, `session.checkpoint_now`, `setup.finish_bootstrap`).

## Para qué sirve

Única vía del brain hacia el resto de Cortex: invoca el CLI como un usuario. Mutaciones no son tools; `actions.propose` solo lista comandos.

## Relaciones

### Recibe de

- `i18n` (mensajes de error/ayuda)
- stdout/stderr del proceso `cortex`
- filesystem `vault/`
- env `CORTEX_BIN`

### Envía a

- proceso CLI `cortex` (args doctor/context/search/next/webgraph)
- texto usuario de vuelta a `chat::procesar_respuesta_modelo` / `DeterministicBackend`

### Notas de implementación observadas en el código

`webgraph.serve` es el único side-effect whitelisteado. Spawn con stdin/stdout/stderr a null para no atar el brain al servidor.
