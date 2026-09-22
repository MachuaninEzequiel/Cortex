# Ciclo de Desarrollo de Software con Cortex: Índice y Mapa Canónico

Esta carpeta documenta de forma molecular, exhaustiva y libre de abstracciones obsoletas el ciclo completo de ingeniería de software asistido por Cortex en su arquitectura 100% Rust y SystemOne.

---

## Documentos de la Sección

1. [01-ciclo-desarrollo-software-molecular.md](01-ciclo-desarrollo-software-molecular.md)
   - **Despliegue automático**: Qué ocurre cuando el desarrollador abre un IDE/CLI (`cortex-setup`, adaptadores, detección de entorno host y políticas de proveedor).
   - **Catálogo Exhaustivo de las 32 Tools MCP**: Detalle milimétrico de cada una de las 32 tools nativas del servidor MCP (`rmcp`), sus argumentos, sus backends nativos y su posición en el ciclo.
   - **El Ciclo de Vida del Software ("El Sandwich Canónico")**:
     - *Fase 0*: Utterance Gate (Portero SystemOne sub-10ms).
     - *Fase 1*: Sync & Apertura de Sesión (`cortex-sync`, Spec, SessionRecord).
     - *Fase 2*: Model Router y Asignación de Roles (`cortex-code-designer`, `cortex-code-implementer`, `cortex-documenter`, `review_checkpoint`).
     - *Fase 3*: Context Packaging & Search Squeeze (Fusión RRF $k=60$, Tiered Memory).
     - *Fase 4*: Implementación, Tareas y Checkpoints Vivos.
     - *Fase 5*: Auditoría, Verification Gates y Primitiva Score (0..2).
     - *Fase 6*: Documenter & Guardado de Memoria (Diff, notas, changelog, filtro `worth_remembering`).
     - *Fase 7*: Memoria Organizacional & Promoción Enterprise.
   - **Interacción con Modelos Locales y Remotos**: Cortex Brain (`llama.cpp`, GGUF, Tauri) vs Suscripciones de LLMs de proveedores autorizados.

2. [02-red-neuronal-conceptual.md](02-red-neuronal-conceptual.md)
   - **Red Neuronal Gráfica de Redes Conceptuales**: Diagrama conceptual masivo (`flowchart TD`) que mapea todos los nodos de decisión, almacenes, conectores, subagentes, herramientas y componentes de Cortex sin solapamientos.

3. [03-diagramas-arquitectura-y-secuencia.md](03-diagramas-arquitectura-y-secuencia.md)
   - **Diagrama de Secuencia Temporal End-to-End**: Interacción cronológica milimétrica desde el prompt inicial del desarrollador hasta la persistencia en el Vault y memoria episódica.
   - **Diagrama de Bloques de Arquitectura Global de Sistemas**: Topología de capas que interconecta el Humano, los IDE Hosts, LLMs Cloud, Modelos Locales GGUF (`cortex-brain`), SystemOne Micro-Decisiones, los 22 crates de Rust y la persistencia en disco (`.cortex/`).
