# Archivo de goldens de paridad — BAJA DEFINITIVA (fase física)

> Este directorio es el ARCHIVO HISTÓRICO de los oráculos de paridad de la
> migración Python→Rust (Obra 07). Se conservan LIVING (no se borran) como
> evidencia y para poder reactivar la verificación si algún día se quiere.

## Por qué se archivan

La BAJA DEFINITIVA (fase física, paquete `PROMPT-BAJA-FISICA.md`) eliminó el
passthrough a Python del CLI nativo: `CORTEX_PY=1` pasó a ser un aviso
histórico, el catch-all devolvió `No such command '<cmd>'.` rc 2 y el módulo
`fallback.rs` murió. Con **todo** lo que el oráculo expone wireado nativamente
ya no existe contraparte de desarrollo para estos gates: correrlos de nuevo
requeriría un oráculo Python, y eso es precisamente lo que la baja física
retira de la línea de vida.

Verificado: ningún workflow de CI corre estos scripts. `ci-gates.yml` ejecuta
pytest (suite Python viva, `cortex/cli/**`) + `cargo test` — no los goldens.

## Qué validaban

Cada `*_golden*.py` era un gate determinista `build/verify` que comparaba el
binario nativo `cortex-cli` contra el CLI Python REAL (`.venv/bin/cortex`)
sobre fixtures deterministas en tmp, con normalizaciones pactadas
(`{{ROOT}}`, `{{TS}}`, `{{FP}}`, …) y casos byte-parity / equivalencias.

| Fase | Goldens | Cubría |
|---|---|---|
| P5–P9 (pilotos) | `actions_golden_p6.py`, `capture_golden.py`, `capture_config_golden.py`, `ci_golden_p11.py`, `context_golden_p7.py`, `documenter_golden.py`, `episodic_golden.py`, `persister_golden.py`, `p9_ping_golden.py`, `search_golden.py`, `session_golden.py`, `verification_golden.py`, `p8_{hooks,ide,setup,writers}_golden.py` + `golden*`/`golden_*` | pilotos de paridad (config/search/session/next/docs/context/episodic/persister/ci/actions) |
| P12a | `p12a1_golden.py` … `p12a9_golden.py` + `golden_p12a*` | paridad por tarea P12a (A1..A9) |
| P12b / Stream B | `cli_golden_p12b.py`, `doctor_golden_p12b.py`, `enterprise_golden_p12b.py`, `pipeline_golden_p12b.py`, `tutor_golden_p12b.py`, `webgraph_golden_p12b.py`, `workspace_golden_p12b.py` + `.p12b-*` | CLI clap, doctor, enterprise, docs pipeline, tutor, webgraph, workspace |
| Cierre T3/T6 | `cierre_{autopilot,cli,leaves_a,leaves_b,leaves2_a,leaves2_b,mcp}_golden.py` + `.p12-cierre-*` | autopilot, cli/gates, leaves RUTA 1 (A/B), leaves RUTA 2 (A/B), MCP, sesiones |
| RUTA 1/2 (baja definitiva) | `cierre_leaves_a/b_golden.py`, `cierre_leaves2_a/b_golden.py` + `.p12b-cli/docs/leaves-b/webgraph` | session task/hooks, remember/forget, IDE, docs, autopilot doctor + rechazo install/uninstall, webgraph serve/doctor, hu import |

Los `*.txt` en los subdirectorios `.p12*` / `golden*` son los **bytes de
referencia** capturados del oráculo real en su momento; los `.work/` son los
fixtures de los gates.

## Cómo reactivarlos

Restaurar a `bench/parity/` (los `git mv` inversos) y correr con el entorno
de oráculo completo:

```sh
# 1) volver a la posición original
git mv bench/parity/archive/*_golden*.py bench/parity/
git mv bench/parity/archive/golden* bench/parity/
git mv bench/parity/archive/.p12b-* bench/parity/
git mv bench/parity/archive/.p12-* bench/parity/

# 2) patrón house build/verify (igual que en su vida)
.venv/bin/python bench/parity/<gate>.py build --out /tmp/pg-build
.venv/bin/python bench/parity/<gate>.py verify --out /tmp/pg-build
```

Requisitos de entorno (los de siempre): `.venv` con extras
dev+webgraph+fastembed, binario nativo `cortex-cli` en PATH, sin red ni
modelos (los gates no cargan embedders).

> Nota post-baja: los gates de rollback (`CORTEX_PY=1` delega byte-idéntico)
> ya NO son reproducibles — el passthrough fue eliminado por diseño. Si se
> reactiva un golden con ese caso, hay que retirar/adaptar el bloque de
> rollback.

## Decisión de borrado físico

La eliminación física de `cortex/`+`tests/`+`pyproject.toml` queda FUERA de
este paquete y pertenece al dueño (quedará el oráculo Python como suite CI
viva mientras exista; este archivo se puede borrar cuando se decida).