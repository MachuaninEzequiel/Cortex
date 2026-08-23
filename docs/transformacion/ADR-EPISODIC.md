# ADR-003 — Store episódico: chromadb queda (Gate C1, T-DEC-1)

> Estado: ACEPPTADO — NO migrar por migrar · Fecha: 2026-08-24
> Contexto: docs/transformacion/03-MIGRACION-RUST.md §7-R3 y §8-C1/C2.

## Decisión

**`EpisodicMemoryStore` sigue sobre chromadb embebido. No se ejecuta C2
(migración a store propio) en este programa de transformación.** La ruta nativa
queda documentada como opción futura con criterios de re-evaluación explícitos.

## Evidencia del spike (números medidos hoy, misma máquina del baseline)

Vectores aleatorios normalizados dim=384, top-5, mediana de 20 queries:

| n vectores | chroma add | chroma query p50 | fuerza bruta numpy p50 |
|---|---|---|---|
| 1 000 | 100 ms | 0.53 ms | **0.047 ms** |
| 5 000 | 642 ms | **0.83 ms** | 1.61 ms |

Lectura:

- El motor HNSW de chroma recién gana por encima de ~2–3k vectores.
- La memoria episódica de Cortex crece LENTO (memorias de agente): el volumen
  típico por proyecto está muy lejos del régimen donde un ANN propio justifique
  una migración.
- Con G1 (`cortex-core::scoring`) ya existe la pieza de cómputo que usaría un
  store propio (sqlite + fuerza bruta/HNSW casero) — la migración es VIABLE pero
  su costo real está en la capa de persistencia/filtros/colecciones, no en el
  scoring.

## Por qué quedarse

1. **Riesgo/beneficio**: chromadb funciona y está testeado; migrarlo es XL
   (C2) sin win medible para los volúmenes actuales (<1 ms por query).
2. **Superficie usada**: add/query/get/delete + persistencia — todo cubierto;
   ningún síntoma de dolor actual (arranque, latencia, corrupción).
3. **Foco del programa**: los gates con win demostrado (G1-G4) están hechos;
   desviar esfuerzo a C2 diluiría el objetivo ≥5× ya alcanzado en las rutas
   calientes.

## Criterios de re-evaluación (disparan nueva decisión)

1. Volumen episódico >50k memorias por proyecto con queries >10 ms.
2. Necesidad de distribuir Cortex sin la dependencia chromadb (peso instalado).
3. Migración de Obra E ("eliminar Python del runtime") — ahí el store propio
   sobre sqlite sería prerequisito, reutilizando `cortex-core::scoring`.
