# PROGRAMA DE TRANSFORMACIÓN CORTEX — Plan Maestro

> Estado: ACTIVO · Creado: 2026-08-21 · Origen: deep-review 2026-08 (docs/reviews/2026-08-deep-review/)
> Objetivo final: una versión superadora de Cortex — más eficiente, mejores resultados de retrieval,
> más simple de usar — administrada por tramos documentales que permiten cambiar de sesión sin perder contexto.

> **Obra activa (2026-08-29):** [17 · Producto: el experto al lado](17-PRODUCTO-EXPERTO-AL-LADO.md).
> Eso es **lo que se construye**. El [16](16-DEUDA-REAL-Y-NORTE-DE-PULIDO.md)
> manda sobre *qué es teatro* en el árbol; su deuda residual está diferida.
> Rama `feature/transformacion-2026-08`, commits locales, sin push.

## Reglas de administración documental (obligatorias)

1. Cada obra vive en su documento (`01..17`). Toda decisión se registra ahí, no en chat.
2. Toda tarea ejecutable lleva checkbox `[ ]`; se marca `[x]` recién verificada. Nada "hecho" sin evidencia (comando + salida).
3. Cada obra define **criterio de entrada** (pre-requisitos) y **criterio de salida** (gates). Un tramo no empieza sin entrada cumplida ni se cierra sin salida verificada.
4. Cambio de sesión: leer este README + **el documento 17** (producto) y el 16 si hace falta honestidad del árbol. `ESTADO-ACTUAL.md` y `HANDOFF.md` son historia de 07/08.
5. Los subagentes trabajan con scopes disjuntos y entregan incrementalmente (archivos escritos temprano y por secciones, o mensajes cortos encadenados).

## Los 5 obras (workstreams)

| Doc | Obra | Resumen |
|---|---|---|
| [01](01-PODA-Y-LIMPIEZA.md) | Podado y limpieza total | Inventario completo de código muerto/viejo/mal hecho; eliminar todo lo no usado; suite verde como base |
| [02](02-ESTANDAR-UNICO-IDE-CLI.md) | Estándar único de CLIs/IDEs | UN contrato para todas las CLIs: mismos comandos, misma instalación, inyección con marcadores, uninstall seguro |
| [03](03-MIGRACION-RUST.md) | Migración a Rust | Estrategia honesta e incremental para rendimiento/eficiencia (batería); benchmarks primero, porteo después |
| [04](04-VECTORIZACION-E-IDIOMA.md) | Vectorización + configuración por idioma | Investigación de modelos nuevos; config por idioma (ES/EN/multilingüe); corregir bugs silenciosos del stack vectorial |
| [05](05-UX-TUI-ACTIONENGINE.md) | UX simplificada + ActionEngine | TUIs simples, comandos consolidados, motor de acciones que automatiza el aprendizaje (el usuario solo elige de vez en cuando) |
| [06](06-INTELIGENCIA-LOCAL-LFM.md) | Inteligencia local LFM2.5 [FUTURO] | LLM edge local (Liquid) como reranker/summarizer/cerebro del ActionEngine — investigación profunda pendiente antes de implementar |

Obras posteriores (historia 07/08 + pulido activo):

| Doc | Obra | Estado |
|---|---|---|
| [07](07-AUDITORIA-2026-08-24.md)–[12](12-AUDITORIA-PYTHON-RESIDUAL.md) | Migración total a Rust + baja del passthrough | Historia. Núcleo nativo REAL. |
| [13](13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md)–[14](14-HERDR-COMPANION.md) | COMPOSED + Companion Herdr | Dominio y máquina ELM REAL. Superficie diaria incompleta. |
| [15](15-REBRANDING-TUI-HERDR-STATUS.md) | Rebrand + 3 modos Herdr | Relato del agente. Crítica §3–§4 vigente; §2 no describir el árbol. |
| [16](16-DEUDA-REAL-Y-NORTE-DE-PULIDO.md) | Deuda real (honestidad del árbol) | Autoridad de *qué es teatro*. Residual **diferido**. |
| **[17](17-PRODUCTO-EXPERTO-AL-LADO.md)** | **Producto: experto al lado** | **Obra activa. HUD + Liquid on-demand + prompts copiables.** |

## Orden de tramos (con racional)

```
TRAMO 0: Línea base (parte de Obra 01)          ← bloqueante de todo
   └─ pin mcp<2 o migrar API; suite verde; gates en CI propios
TRAMO 1: Podado (Obra 01) + Estándar IDE (Obra 02)  ← en paralelo, scopes disjuntos
   └─ no se poda y estandariza ANTES de portear a Rust: nada de código muerto cruza el puente
TRAMO 2: Vectorización + idioma (Obra 04)
   └─ mejora resultados YA en Python; el diseño de config queda listo para el core Rust
TRAMO 3: Migración Rust incremental (Obra 03)
   └─ núcleo caliente primero (vector search, BM25, cache, parsing); fachada Python→Rust vía PyO3
TRAMO 4: UX/TUI/ActionEngine (Obra 05)
   └─ sobre la base ya limpia y rápida; el ActionEngine orquesta las primitivas estables
```

Racional del orden: podar antes de portear (no migrar basura), estandarizar la capa IDE antes de
reescribirla, mejorar el modelo de embeddings en Python mientras tanto (es independiente del lenguaje),
y hacer la UX al final sobre primitivas estables.

## Métricas de éxito del programa

- Rendimiento: benchmark antes/después (cold start, retrieve p50/p99, consumo de batería en workload estándar). Meta: ≥5× en rutas calientes.
- Calidad retrieval: suite de evaluación ES+EN (queries con relevancia esperada) — hoy NO existe; se crea en Obra 04.
- Limpieza: 0 código muerto detectable (vulture + revisión), 0 duplicaciones conocidas del review.
- Uniformidad: 1 solo contrato de IDE/CLI; mismos comandos para todos; uninstall nunca destructivo.
- Simplicidad: flujo nuevo usuario ≤3 comandos; ActionEngine reduce decisiones frecuentes a menús.

## Estado actual

Ver [ESTADO-ACTUAL.md](ESTADO-ACTUAL.md) — actualizado al cerrar cada sesión de trabajo.
