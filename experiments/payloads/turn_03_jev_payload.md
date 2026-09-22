# Turn 3 JEV Search
Query: patrón de visualización del pipeline cognitivo desde prompt hasta LLM con bypass de gating

```text
## Context for: 'patrón de visualización del pipeline cognitivo desde prompt hasta LLM con bypass de gating'

- [SEMANTIC] **Cortex Product Spec** (/home/chucho/pruebas/exp-cortex-jev/.cortex/vault/CORTEX_PRODUCT_SPEC.md)
  > # Cortex: Cognitive Operating System for AI Coding Agents *Especificación Completa de Producto y Arquitectura para el Sitio Web Promocional*  ---  ## 1. Visión y Posicionamiento de Producto  ### El Problema de los Asistentes de Código Actuales Los agentes de IA generativa (Claude Code, Cursor, Gemin…
- [SEMANTIC] **Architecture** (/home/chucho/pruebas/exp-cortex-jev/.cortex/vault/architecture.md)
  > # Architecture Overview - Rate Limiter  Este módulo implementa el patrón Token Bucket concurrente para control de tráfico de APIs. Requiere soporte para invocaciones asíncronas seguras multi-hilo con Tokio. Parámetros clave: capacidad máxima de tokens (burst) y tasa de recarga por segundo (refill_ra…
- [SEMANTIC] **Glossary** (/home/chucho/pruebas/exp-cortex-jev/.cortex/vault/glossary.md)
  > # Ubiquitous Language  - **Token Bucket**: Algoritmo que acumula fichas hasta una capacidad máxima y descuenta al procesar solicitudes. - **Refill Rate**: Tasa constante de regeneración de fichas por unidad de tiempo. - **Burst Capacity**: Número máximo de operaciones toleradas en una ráfaga instant…
- [SEMANTIC] **Adr-001-Concurrency** (/home/chucho/pruebas/exp-cortex-jev/.cortex/vault/decisions/ADR-001-concurrency.md)
  > # ADR-001: Thread-Safety via Mutex vs AtomicU64  - **Status**: Accepted - **Decision**: Usar `std::sync::Mutex` o `tokio::sync::Mutex` para sincronizar el estado del bucket   cuando la recarga dependa de marcas de tiempo continuas (`Instant`). - **Consecuencias**: Garantiza monotonicidad estricta y …
- [SEMANTIC] **Zero-Dependency Tech Stack for Landing Platform** (/home/chucho/pruebas/exp-cortex-jev/.cortex/vault/local/adr/zero-dependency-tech-stack-for-landing-platform.md)
  > ## title  Zero-Dependency Tech Stack for Landing Platform  ## context  The landing platform must load in <50ms and demonstrate Cortex capabilities offline.  ## decision  Use vanilla HTML5, CSS3, and ES2022 Canvas without external npm packages.  ## status  accepted  ## tags  - architecture  - web  - …
```
