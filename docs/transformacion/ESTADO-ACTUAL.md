# ESTADO ACTUAL DEL PROGRAMA

> **ACTUALIZADO 2026-08-26 (cierre OBRA 07 — post T2-cola/T4/T6-b, oráculo 2552 verde).**
> Obra 07 (migración total a Rust): **P0–P12 ✅ COMPLETADAS Y GATEADAS ·
> CIERRE COMPLETO**. Los motores Y el CLI nativo clap están wireados; el
> passthrough del `cortex-cli` quedó reducido al rollback `CORTEX_PY=1` más
> deuda documentada (session task/hooks, ide, docs validate/restore,
> webgraph serve/doctor, autopilot doctor/install/uninstall). Suite Python
> ORÁCULO: **2552 passed, 21 skipped, 0 failed, 0 errors**.
> Handoff activo para agentes: `HANDOFF.md` §"HANDOFF ACTIVO".

## Estado consolidado al cierre

### Completado y verificado con paridad byte-a-byte vs Python

| Fase | Alcance | Gate |
|---|---|---|
| P0 | crates cortex-config/cortex-app + harness `bench/parity/` | doctor.txt · next_stats.json PASS |
| P1 | CortexConfig completa en serde | dumps idénticos ×2 fixtures |
| P2 | vault + embeddings ort + hybrid search | BM25 100/100 · semántico 100/100 rankings |
| P3 | episódica nativa (lectura) + exportador chroma→JSONL | round-trip 12/12 · vector 6/6 · keyword/entity ✓ |
| P4 | Session primitive + storage YAML + verification + gates | dumps 4/4 · hooks 5/5 · gates 6/6 · infer_mode 4/4 |
| P5 | reconstructor gitless/git-aware + DocumenterPersister | dump idéntico · note_body byte-parity |
| P6 🅰 | crate cortex-actions (ActionEngine+FeedbackStore) | 16/16 salidas `next` byte-a-byte |
| P7 🅰 | módulo context en cortex-app (Enricher+budget) | 3 bundles --json byte-a-byte |
| P8 🅱 | cortex-setup: minijinja+YAML réplica+writers+11 IDE+hooks | YAML 138/138+fuzz · renders/writers idénticos · ide 33/33 · hooks 38/38 |
| P9 🅱 | cortex-mcp (rmcp): catálogo+ruteo congelados | list_tools byte-a-byte · ping golden |
| P10 | branding + TUI ratatui + logo | snapshot <50ms · tests del stream |
| P11-ci 🅰 | plugin CI + SessionService completo | 23/23 comandos `cortex ci` byte-a-byte |

Verificación integral post-cierre (esta sesión): workspace tests +
clippy/fmt limpios, todos los oráculos golden re-verificados, suite Python
ORÁCULO **2552 passed, 21 skipped, 0 failed, 0 errors** (primera vez 100%
verde desde la recatorización; T5 `f6fb828`). Gates del cierre: T1
`cierre_mcp_golden` (51 escenarios), T2 `cierre_cli_golden` (39 casos + MCP
stdio bounded), T3 `cierre_autopilot_golden` (236 líneas) + `cierre_autopilot_check`, T4 `pipeline_golden_p12b` (3 casos Documentation + A-D), T6/T6-b
`sessions_screen` (5) + `t6b_session_watch` (3).

### Bugs reales descubiertos/corregidos durante la migración

1. OOM del kernel ×2 (`bench/int8_probe.py`) → fix + lección de memoria.
2. Keyword bypass episódico roto con chromadb moderno → filtro `$contains`.
3. `lstrip("./")` anulaba exención de artefactos procesales en quality_gates.
4. Glob patterns tratados como literales en claude_code uninstall (atrapado
   por el gate P8d antes del commit — stream B).
5. Test `blit_copia_solo_lo_opaco` de branding con fixture imposible
   (introducido por commit de banner post-P10) → fixture corregido
   (`dded2da`). Único fallo del workspace en la verificación final.

### Lo que TODAVÍA depende de Python (deuda residual documentada)

Tras el cierre de la Obra 07, el passthrough de `cortex-cli` se redujo al
rollback `CORTEX_PY=1` más los siguientes leaves fuera del inventario T2-cola
(brief prohibió expandir sin requisito vinculante). Son deuda abierta, no
falla del cierre:

- `session task {list,done,in-progress,skip,block}` y
  `session hooks {list,install,uninstall,status}`
- `ide {list,setup,remove,status}`
- `docs {validate,restore,list-backups,routing-table}` (solo search/migrate
  están en el inventario)
- `hu import` (traceback Python no portable; list/show ya nativos)
- `{remember,forget,init,inject,sync-enterprise-vault,sync-ide,
  verify-docs,validate-docs,index-docs}`
- `webgraph {serve,doctor}` (el cálculo ya es nativo)
- `autopilot doctor/install/uninstall` (delegan por diseño documentado)

Lo nativo en esta Obra (P0–P12 + cierre T1–T7): motores híbridos
(vault/embeddings/context/session/documenter/persister), CLI clap
(search/context/stats/session ×9/next/hu ×2/pr-context ×5/docs ×2/
ci ×4/setup ×5/mcp-serve/reindex), MCP handlers no-sesión (T1), autopilot
service+cli+mcp×5 (T3-paralelo), pipeline stage Documentation (T4), pantalla
ratatui sesiones + integración `session watch/tui` (T6/T6-b). Auditoría
exhaustiva pre-cierre: `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md`
§9.2; registro de la propia sesión: `progreso-cierre.md` y
`progreso-cierre-paralelo.md`.

### Próximos pasos (post-cierre — baja definitiva de Python)

La Obra 07 (P0–P12 + cierre T1–T7) está completa. El paso siguiente,
**fuera de esta Obra**, es la baja definitiva de Python:

1. Baja leaves residuales documentados arriba (session task/hooks, ide,
   docs validate/restore, hu import, remember/forget, webgraph serve/doctor)
   — o confirmarlos como deuda aceptada permanente.
2. `CORTEX_PY=1` pasa a rollback histórico; wheels solo-Rust; README a
   binarios; goldens archivados.
3. Limpiezas: untracked + deprecaciones runtime.

Hasta ahí llegó esta Obra. Los pasos 2-3 son un **paquete separado** (ver
definición de hecho en `PROMPT-CIERRE-OBRA07.md` §"Definición de hecho").

## Reglas operativas vigentes

1. Suite Python completa = oráculo hasta la baja final; verificar Rust
   SIEMPRE por crate (`cargo test -p …`).
2. Paridad antes que velocidad; drift visible ⇒ revert.
3. Memoria: un modelo residente por vez · batches ≤64 · sin `/tmp` como caché.
4. Commits atómicos un-gate-por-commit · suite verde antes de commitear.
5. Dual-stream CERRADO: las reglas §4b de coordinación quedan históricas;
   el refresco documental vuelve a ser parte del flujo normal.
