# Progress

## Status
In Progress

## Tasks

## Files Changed

## Notes

### Exploración documental (subagente 01-filosofia)
- Reporte de filosofía/narrativa completo escrito en /tmp/cortex-explore/01-filosofia.md
- Fuentes: README en/es, CHANGELOG, CONTRIBUTING, config.yaml, docs/transformacion/{README,ESTADO-ACTUAL,HANDOFF,03,08,09,12,PROMPT-BAJA-FISICA}, ADR-001, docs/vision, git log
- Hallazgos clave: Cortex = memoria híbrida + gobernanza para agentes; Obra 07 completó la migración total a Rust 100% nativo (passthrough eliminado); Python sobrevive solo como oráculo de paridad congelado en CI (2552 passed); deudas: hu import http(s) nativo, reindex real, tutor, borrado físico de Python (decisión dueño)

### Exploración núcleo de dominio (subagente 04-nucleo-dominio)
- Reporte completo escrito en /tmp/cortex-explore/04-nucleo-dominio.md (SOLO LECTURA, sin cambios de código)
- Domínio: cortex-core (scoring Neumaier, store vectors.v3.bin, BM25 substring, webgraph), cortex-app (semantic parser/routing 13 doc_types/chunker, episodic JSONL+entidades, session primitive+service+gates+hooks, documenter reconstructor), cortex-services (Spec/NoteService transaccionales), cortex-workspace (layout), cortex-config
- Hallazgos clave: paridad-como-contrato bit-a-bit (R5.2), dim siempre paramétrica, dominio puro sin pyo3, retrieval híbrido RRF k=60 + pesos por intención + per-language embeddings (es→multilingual-e5-large), cierre verificado = CLOSED solo si hooks OK y sin unimplemented

### Exploración periféricos Rust (subagente 05-brain-setup)
- Reporte completo escrito en /tmp/cortex-explore/05-brain-setup.md (SOLO LECTURA, sin cambios de código)
- Domínio: cortex-brain (asistente local read-only by design, router determinista 1:1 Python, tools READ/SAFE_ACTION vía CLI cortex, protocolo TOOL con confirmación, i18n ES/EN, backend llama.cpp/GGUF LFM2.5 opcional + DeterministicBackend default), cortex-embed (ONNX MiniLM ort, dim paramétrica, paridad cos=1.0 con chroma), cortex-py (fachada PyO3 LEGADO de transición, cortex_core._native, APIs batch R5.4), cortex-setup (11 IDE adapters + HookInstaller + canonical_tools + minijinja/yaml/slug/fingerprint réplica), cortex-autopilot (7 detectores + policy observe/assist/autopilot + Service sobre SessionService nativo), cortex-doctor (checks reales + stubs contractuales patrón P6/P9 + NativeDoctorBackend seam), cortex-pipeline (orquestador con gates + stages lint/security/test/documentation + GH Actions), cortex-enterprise (governance multi-tenant, knowledge promotion JSONL, reporting con DoctorBackend inyectable), cortex-webgraph-server (axum, guard X-Cortex-WebGraph, pyjson byte-parity, federación), cortex-tutor (7 topics + HintEngine L0..L7), cortex-branding (pura, half-block ANSI)
- Validación: cargo check -p (11 crates) limpio; cargo test -p brain/enterprise/doctor/pipeline/tutor → 70+ tests OK (no toqué setup por Cargo.lock/feature context, verificado por subagente 02)
- Hallazgo clave: cortex-py es código de transición (no el futuro de integración); el futuro es CLI nativo + MCP

### Exploración arquitectura workspace Rust (subagente 02-arquitectura)
- Reporte completo escrito en /tmp/cortex-explore/02-arquitectura.md (SOLO LECTURA, sin cambios de código)
- Mapé los 20 crates en 4 capas (base: core/config/embed/branding; infra: setup/workspace/py; dominio: app/services/actions/mcp/enterprise/autopilot/pipeline/tui; fachadas: doctor/webgraph-server/tutor/cli/brain) con ~94k LOC RosT totales
- Reglas: paridad-como-contrato, core dominio PURO sin pyo3, dim paramétrica, pyjson/PyVal para json.dumps, yaml/PyYAML réplica, backends inyectables, forbid(unsafe_code), fallo explícito P6/P9
- Originales pre-O7: core/embed/py (O3) + brain (O6); los 16 restantes son Obra 07
- Validación: cargo check --workspace y cargo clippy --workspace limpios (exit 0)
- Riesgos: app→setup acoplamiento de capa, features serde_json inconsistentes, pyjson×4 y yaml×2 duplicados, storage sesiones single-thread, suite Python oráculo 2552 como dependencia viva de CI, ort rc pre-release, hu import http(s) sin cliente HTTP nativo

## Subagente superficies (exploración)

- Reporte completo: /tmp/cortex-explore/03-superficies.md
- Inventario: 27 subárboles CLI top-level, 5 pantallas TUI, 32 tools MCP (rmcp stdio), Action Engine 10 acciones v1 con scheduler (impacto×frescura−costo × aprendido × señales), lote auto-ok en TUI.
- Comando sin args abre el Home TUI nativo; dispatch manual por primer token, rechazo Typer-like rc 2, baja física sin passthrough.

## Auditoría de estado/convenciones/metodología (subagente 06-estado)

- Obra 07 COMPLETA (P0–P12 + T1–T7) + BAJA DEFINITIVA ejecutada (RUTA 1 + RUTA 2 + FASE FÍSICA, commits a61122c..6007221). CLI nativo sin passthrough a Python; CORTEX_PY=1 = aviso histórico.
- Verificado en vivo: cargo test --workspace = 587 passed / 0 failed (85 binarios, incluye WIP P8d/TUI). Oráculo documentado: 2552/21/0/0 bajo lock (~120 s). Recolección pytest tests/unit+integration = 2473 items.
- Deuda residual no bloqueante: hu import http(s) sin cliente HTTP (ADR futura), reindex real rc 1 explícito, webgraph_dependencies no-op; borrado físico Python + wheels solo-Rust pendientes del dueño (paquete separado).
- Estado del árbol: branch feature/transformacion-2026-08 con WIP P8d (adapters IDE pi/claude_desktop/vscode/zed/codex) + TUI sesiones/branding sin commitear — riesgo de colisión entre agentes paralelos en cortex-setup/ide y cortex-tui.
- Salida completa: /tmp/cortex-explore/06-estado.md
