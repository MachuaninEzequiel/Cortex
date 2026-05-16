# Pluggable Middle Architecture

Esta carpeta contiene la propuesta arquitectónica para reformular el modelo tripartito de Cortex.

## Contenido

| Archivo | Contenido |
|---|---|
| [`ARQUITECTURA-PLUGGABLE-MIDDLE.md`](ARQUITECTURA-PLUGGABLE-MIDDLE.md) | **Documento maestro.** Diseño completo de la arquitectura, principios, diagramas, decisiones. |
| [`fases/`](fases/) | **Plan de implementación.** Desglose por fases secuenciales con detalle ejecutable. |

## Cómo navegar esta documentación

### Si nunca leíste nada: empezá por la arquitectura

1. Leé `ARQUITECTURA-PLUGGABLE-MIDDLE.md` completa.
2. Después leé `fases/README.md`.
3. Después abrí la fase que corresponda según el estado actual.

### Si vas a implementar (agente autónomo)

1. Leé `fases/README.md` (Quality Charter + Context Loading Protocol).
2. Identificá la fase actual ejecutando los chequeos descritos en `fases/README.md`.
3. Leé la fase correspondiente (ej. `fases/00-FOUNDATIONS.md`).
4. Seguí el flujo definido en esa fase.

### Si querés revisar una decisión histórica

- Las decisiones de diseño viven en `ARQUITECTURA-PLUGGABLE-MIDDLE.md` §12 (Decisiones tomadas).
- El razonamiento de prioridades/dependencias entre fases vive en `fases/README.md`.

## Estado actual

- **Diseño:** consolidado (v1.0).
- **Implementación:** no iniciada.

> Cuando una fase quede completa, este README debe actualizarse en la tabla de **Estado actual** marcando la fase como ✅. Es la única fuente de verdad sobre el progreso global de la implementación.

## Tabla de progreso

| Fase | Nombre | Estado | Output |
|---|---|---|---|
| 00 | Foundations (Session primitive) | ⏸ Pendiente | — |
| 01 | Documenter Reconstruction Mode (BYO) | ⏸ Pendiente | — |
| 02 | SDDwork Migration (Managed unified) | ⏸ Pendiente | — |
| 03 | Autopilot Fusion + Observed Mode | ⏸ Pendiente | — |
| 04 | Interactive Mode + Final Polish | ⏸ Pendiente | — |

> Leyenda: ⏸ Pendiente · 🟡 En progreso · ✅ Completa · ⚠️ Bloqueada
