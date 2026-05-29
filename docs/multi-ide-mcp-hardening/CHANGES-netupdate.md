# CHANGES.md — Cortex Pi Release 2.5+net

Diff conceptual entre la carpeta original `cortex-pi` (Release 2.5
pre-net) y esta versión rediseñada con cortex-net.

## Resumen

- **Filosofía adoptada**: modelo B′ (híbrido con sync afuera de la red).
- **Protocolo nuevo**: `cortex-net` peer-to-peer entre agentes del medio y el documenter.
- **Sync queda fuera**: por diseño, garantiza integridad del pre-flight.
- **Documenter pasa a ser observer**: escucha la red durante todo el trabajo, no solo lee briefing al final.
- **Limpieza de generaciones**: YAML AgentHandoff eliminado de security-auditor y test-verifier. agent-chain.yaml queda como **fallback** para IDEs sin subagents (Codex).

## Archivos NUEVOS

| Archivo | Propósito |
|---|---|
| `.pi/extensions/cortex-net.ts` | Implementa el protocolo peer-to-peer: 4 tools (`cortex_net_list`, `cortex_net_send`, `cortex_net_get`, `cortex_net_await`), hub auto-elected, gate de session_id, auto-reply implícita, heartbeats |
| `ADAPTER_CONTRACT.md` | Documento que vos llevás al adapter Python para que pueda regenerar esta carpeta |
| `CHANGES.md` | Este archivo |

## Archivos MODIFICADOS

| Archivo | Qué cambió |
|---|---|
| `.pi/system.md` | Menciona cortex-net en directivas + nuevo directive "Cortex-net hygiene" |
| `.pi/settings.json` | Agrega `cortex-net.ts` a `defaultExtensions` |
| `.pi/agents/cortex-sync.md` | Agrega sección "NO PARTICIPÁS DE CORTEX-NET" explícita (límite estricto #4) |
| `.pi/agents/cortex-SDDwork.md` | Reescritura sustancial: incorpora red en Deep Track, tabla "Cuándo USAR cortex-net" vs "Cuándo NO usar", anti-rationalization signals nuevos. Fast Track sin cambios funcionales |
| `.pi/agents/cortex-documenter.md` | Cambio mayor: dos modos (observer in-flight + closing anchor). Pre-flight ahora chequea `cortex_net_list`. Tabla de doc-types sin cambios |
| `.pi/agents/cortex-code-designer.md` | Frontmatter: agrega tools `cortex_net_*`. Sección nueva "Uso de cortex-net" |
| `.pi/agents/cortex-code-explorer.md` | Frontmatter: agrega tools `cortex_net_*`. Sección nueva "Uso de cortex-net" |
| `.pi/agents/cortex-code-implementer.md` | Frontmatter: agrega tools `cortex_net_*`. Sección nueva "Uso de cortex-net" |
| `.pi/agents/cortex-security-auditor.md` | Reescritura del output: ahora emite `cortex_session_checkpoint` en vez de YAML AgentHandoff. Agrega cortex-net tools y guía de uso |
| `.pi/agents/cortex-test-verifier.md` | Mismo patrón que security-auditor |
| `.pi/agents/teams.yaml` | Simplificado: ya no es pipeline, solo metadata para system-select. Nuevo team `cortex-byo` |
| `.pi/agents/agent-chain.yaml` | Marcado explícitamente como **fallback**. Eliminado `validate_handoff`, `expected_input_agent`, referencias a YAML. Steps actualizados a checkpoints |
| `justfile` | Recetas nuevas: `cortex` (con red), `cortex-solo` (sin red), `role-*` para multi-terminal |

## Archivos INTACTOS (sin cambios)

| Archivo | Razón |
|---|---|
| `.pi/extensions/cortex-tools.ts` | El bridge al CLI de Cortex no cambia |
| `.pi/extensions/cortex-mcp.ts` | El adaptador MCP no cambia |
| `.pi/extensions/system-select.ts` | El selector de agentes funciona igual |
| `.pi/extensions/damage-control.ts` | La auditoría runtime no cambia |
| `.pi/damage-control-rules.yaml` | Las reglas de seguridad no cambian |
| `.pi/mcp.json` | Config MCP no cambia |
| `.pi/themes/cortex-dark.json` | El tema no cambia |
| Todos los `.pi/skills/` | Las skills no cambian |
| `extensions/cortex-dashboard.ts` (premium) | UI no cambia |
| `extensions/cortex-memory-widget.ts` (premium) | UI no cambia |
| `extensions/cortex-spec-tracker.ts` (premium) | UI no cambia |
| `extensions/cortex-subagent-widget.ts` (premium) | UI no cambia |

## Lo que se ELIMINÓ

Nada se borra físicamente. `agent-chain.yaml` y la extensión
`agent-chain.ts` siguen existiendo, pero como **fallback documentado**
para IDEs sin red. Su uso primario en flujos normales queda obsoleto.

YAML AgentHandoff `agent: ... status: ... verified_claims:` queda
**deprecated en todos los agents**. El contrato real es
`cortex_session_checkpoint`. La función `cortex_validate_handoff` sigue
existiendo en MCP solo por compat con generaciones viejas — los agents
nuevos NO la deben llamar.

## Migration path para usuarios existentes

Si alguien tenía Cortex Pi pre-net corriendo y actualiza a esta versión:

1. Sus checkpoints existentes en sesiones abiertas siguen funcionando — el formato no cambió.
2. Si tenían pipelines de `agent-chain` configurados con `validate_handoff`, los pipelines siguen ejecutándose en modo fallback. NO necesitan migrar inmediatamente.
3. La primera vez que abran Pi después del update, verán la notificación de `cortex-net: registrado como "<rol>"` en la barra superior, lo cual confirma que la red está activa.
4. Para usar la red explícitamente desde varias terminales (estilo IndyDevDan video), tienen las recetas `just role-*`.

## Impacto en tokens

| Modo | Costo extra estimado |
|---|---|
| Fast Track | Cero (cortex-net no se usa) |
| Deep Track sin negociación | ~2-3% extra (overhead del system prompt mencionando inbounds vacíos) |
| Deep Track con 2-3 preguntas in-flight | ~10-15% extra, pero **mejor outcome** (decisiones registradas correctamente como ADRs) |
| Documenter en modo observer activo | ~20-30% extra en el agente documenter, pero **dramatically richer** session notes |

El trade-off es claro: gastás más tokens, pero la memoria organizacional que persiste vale **mucho** más que el costo marginal del Inferencia.

## Compatibilidad de versiones

- Pi v0.70+ (confirmado)
- Cortex backend Release 2.5+ (necesario para checkpoints + designer)
- bun 1.3.2+ (para jiti)
- Pipx + cortex-memory instalado vía pipx

## TODOs para vos antes de release

- [ ] Actualizar el adapter Python en `cortex/ide/adapters/pi.py` siguiendo `ADAPTER_CONTRACT.md`.
- [ ] Validar que `CORTEX_SESSION_ID` se pueda setear desde el CLI cuando se llama a Pi desde Cortex.
- [ ] Agregar smoke tests en `tests/test_adapter_pi.py` que verifiquen los 5 checks del contract.
- [ ] Decidir si la versión 2.0 del contract es backward-compatible con 1.5 (si alguien tiene v1.5 instalada).
- [ ] Documentar en el README principal de Cortex que el setup con Pi genera ahora la versión 2.5+net.
- [ ] Crear una vista en el Vault (`.base` file) que muestre las sessions notes con un campo nuevo: cantidad de inbounds observados por el documenter. Esto te da telemetría sobre cuánto se está usando la red.
