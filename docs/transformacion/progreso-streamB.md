# Progreso STREAM B — Obra 07 (P8 cortex-setup + P9 cortex-mcp)

> Stream B del dual-stream P6+P7 ∥ P8+P9 (plan §4b). Este archivo es el
> único registro de progreso de este stream: NO actualiza ESTADO-ACTUAL.md
> ni HANDOFF.md.

## Nota de sesión 2026-08-24 (reanudación post-crash)

La sesión anterior cayó dejando WIP sin commitear: skeletons de los 11
adapters con `unimplemented!("P8d")`, stub en canonical_tools y scaffolding
muerto en base.rs. Esta sesión completó el porteos real (6 workers paralelos
disjuntos + claude_code/canonical_tools como patrón de referencia), limpió
los residuos y construyó el gate de paridad (`p8_ide_golden.py` +
tests/ide_parity.rs). El gate atrapó y corrigió un drift real antes de
commit: glob patterns tratados como literales en claude_code uninstall.

| Fase | Estado | Evidencia | Commit |
|---|---|---|---|
| P8a base (jinja minijinja + dumper YAML réplica PyYAML) | ✅ | `bench/parity/p8_yaml_diff.py` 138/138 casos + fuzz 800/800 byte-idénticos vs PyYAML real; plantillas embebidas verificadas contra disco | dc03184 |
| P8b writers canónicos (notas) | ✅ | byte-parity vs oráculo Python (`writers_parity.rs`) | 774e50e |
| P8c setup/templates renderers (config/workflows/docs/org) | ✅ | renders byte-parity sobre fixtures deterministas (`setup_parity.rs` + `golden_setup/setup/`) | df6628e |
| P8d 11 IDE adapters + canonical_tools + prompts | ✅ | `p8_ide_golden.py` 33/33 manifiestos (11 IDEs × fresh/existing/uninstall): árboles project+home byte-a-byte + reports normalizados; reloj congelado, HOME/CODEX_HOME redirigidos; verify reproducible; evidencia `bench/results/p8d-evidencia.json` | 15046fa |
| P8e session hooks install/uninstall | ✅ | `p8_hooks_golden.py` 38/38 manifiestos (4 adapters × 9 casos + 2 extras cursor); payloads asdict() completos + árboles byte-a-byte; evidencia `bench/results/p8e-evidencia.json` | 9cd894a |
| P9 crate cortex-mcp (rmcp) | ✅ | list_tools **byte-a-byte** vs golden Python (32 tools + server_version 2.2); routing table idéntica; mensajes congelados (desconocida/sync_vault); ping bare en paridad ({{UPTIME}}); transporte rmcp stdio funcional; evidencia `bench/results/p9-evidencia.json` | 7222d51 |

## Obra 07 STREAM B: ✅ COMPLETA (P8 + P9 verdes con evidencia)

Pendiente para sesión de integración: ESTADO-ACTUAL.md/HANDOFF.md (regla
§4b.5 — no los toca ningún stream); wire-format exacto de transporte MCP
(nulls explícitos vs omisión rmcp) diferido a P12.
