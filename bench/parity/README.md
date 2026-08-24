# Parity Harness — Obra 07 (migración total Python→Rust)

Contrato definido en `docs/transformacion/08-MIGRACION-TOTAL-RUST.md` §3.2:
**paridad-como-contrato**. Cada componente que migra de Python a Rust debe
producir salidas byte-a-byte idénticas a las del CLI Python sobre entradas
deterministas. Este directorio contiene la maquinaria de ese contrato.

## Cómo funciona

```text
make_fixture_project.py <dir>     # genera proyecto Cortex determinista
capture_golden.py --fixture <dir>             # captura golden/*.out
capture_golden.py --fixture <dir> --verify    # re-captura y compara; exit 1 si difiere
```

- **Fixture**: `config.yaml` + `vault/nota-a.md` + `vault/note-b.md`, sin git,
  sin chroma, sin estado externo. Regenerarlo desde cero produce los mismos
  goldens (probado).
- **Normalización**: la ruta absoluta del fixture → `{{ROOT}}`; un único `\n`
  final. **Todo lo demás es byte-parity**, incluido el ORDEN de las claves JSON.
- **rc esperados por comando** declarados en `COMANDOS` (`doctor` sale 1 con
  FAILs legítimos sobre el fixture incompleto — fijamos la salida, no el código).

## Comandos cubiertos hoy (pilotos P0)

| Golden | Comando | Formato |
|---|---|---|
| `doctor.txt` | `cortex doctor` | texto normalizado |
| `next_stats.json` | `cortex next --stats` | JSON crudo normalizado |

## Cómo lo consume Rust

Cada fase que porte un comando agrega una prueba de integración que:
1. genera el fixture en un tmpdir,
2. corre la implementación Rust,
3. normaliza igual (`{{ROOT}}`),
4. compara contra `golden/<cmd>.out`.

Referencia viva: `rust/crates/cortex-cli/tests/passthrough.rs` (patrón G6).
Los comandos se van agregando a `COMANDOS` a medida que avanzan las fases
(P1 config, P2 search, P6 next…), nunca todos juntos.

## Requisitos del entorno de captura

`.venv` del repo con extras dev+webgraph+fastembed instalados (los checks
`pm_*`/`webgraph_*` de doctor dependen de imports disponibles). Sin red, sin
modelos: los pilotos no cargan embedders.
