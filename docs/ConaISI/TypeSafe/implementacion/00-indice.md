# Implementación práctica — TypeSafe / Jev en Cortex

**Empezá por [HANDOFF.md](HANDOFF.md)** si venís sin contexto.

Principio rector: **Direct** (Jev off) es el Cortex de hoy, bit a bit. **JevDD** es Direct + portero Jev. Un binario. Fail-open. Key solo env/llavero.

Código: rama **`typesafe`** hasta terminar P0–P4. Ver [HANDOFF](HANDOFF.md).

01–06 = contrato original (crate, if, fail-open). Siguen vigentes en arquitectura. **UX de tracks y “el humano elige sync”** quedó superada por 08–09.

## Leer en este orden

| # | Archivo | Qué decide |
|---|---------|------------|
| H | [HANDOFF](HANDOFF.md) | Hecho vs falta; contexto justo; P0–P4 |
| 01 | [Dos modos](01-dos-modos.md) | Direct vs JevDD a nivel flags; fail-open |
| 02 | [Arquitectura](02-arquitectura-modular.md) | Trait, crate, adapters |
| 03 | [Archivos](03-archivos-a-crear.md) | Lista original; **parcialmente ya creado** (ver HANDOFF) |
| 04 | [UX](04-experiencia-de-usuario.md) | Setup/doctor; slash de agentes **obsoleto** como camino feliz → 09 |
| 05 | [Costo](05-modelo-de-costo.md) | Tokens / centavos |
| 06 | [Flujos](06-flujos-runtime.md) | Search y demás; el de “agente elige track” → 08 |
| 07 | [Enricher pack](07-enricher-pack.md) | Canónico + punteros; `context_pack` |
| 08 | [Direct y JevDD](08-direct-y-jevdd.md) | Sin Fast/Deep; enchufes no tracks |
| 09 | [Portero](09-portero.md) | Utterance → sesión / remember / finish |
| 10 | [SystemOne & Router](10-systemone-model-router-and-host-boundaries.md) | SystemOne core, Model Router, Score, Host Boundaries & Discovery |

## Resumen

```
Direct  = system_one off o sin key     → código actual
System1 = enabled + key + purpose on   → mismo código + if SystemOne

search_squeeze  → HECHO (cortex search)
promotion       → HECHO (ranking en Org Memory)
context_pack    → HECHO
utterance       → HECHO (portero de chat)
session_compact → HECHO (poda verbatim)
model_router    → SPEC 10 (Fase 0 y 1 en curso)
```

Nombres prohibidos en producto: Fast Track, Deep Track, marcas de metodologías o SDKs de terceros. No LangChain. Jev no llama MCP; el harness sí, cuando Jev clasifica.
