---
title: Reportes de Memoria Empresarial
description: Diagnóstico y métricas de salud de memoria con cortex memory-report.
---

El comando `cortex memory-report` genera informes exhaustivos sobre la **salud, volumen, fragmentación y cobertura de la memoria cognitiva** en repositorios individuales o a escala organizacional ([`cortex-enterprise`](file:///home/chucho/Cortex/rust/crates/cortex-enterprise)).

---

## Sintaxis

```bash
cortex memory-report [OPCIONES]
```

---

## Opciones Disponibles

```text
Usage: cortex memory-report [OPTIONS]

Options:
      --project-root <PATH>  Ruta al proyecto a auditar
      --json                 Emite el reporte en JSON estructurado
      --verbose              Incluye el desglose individual por nota y sesión
  -h, --help                 Muestra la ayuda
```

---

## Métricas Clave Reportadas

1. **Volumen y Distribución de Memoria:**
   * Total de notas en Vault por `doc_type` (`adr`, `spec`, `design`, `runbook`, etc.).
   * Número de eventos episódicos y checkpoints acumulados.
2. **Estado de Gobernanza:**
   * Cantidad de notas en borrador (`draft`) pendientes de revisión.
   * Porcentaje de notas con trazabilidad completa y enlaces validados.
3. **Salud de Índices:**
   * Sincronización entre archivos Markdown y vectores en caché.
   * Dimensión y tamaño del índice BM25.
4. **Higiene Temporal:**
   * Eventos episódicos que han superado el límite de retención (`retention_days`) y son candidatos para archivado o compresión.

---

## Ejemplo de Reporte

```bash
cortex memory-report
```

Salida:
```text
📊 Reporte de Salud de Memoria Cognitiva — Cortex Enterprise

[Vault Semántico]
  Notas Totales:        34
  - ADRs:               8 (7 accepted, 1 draft)
  - Specs:              12 (10 closed, 2 in-progress)
  - Designs:            6 (6 approved)
  - Runbooks:           4 (4 stable)
  - Handoffs:           4 (4 archived)

[Memoria Episódica]
  Eventos Totales:      1,420 registros
  Sesiones Totales:     48 (1 open, 45 closed, 2 handoff)
  Caché Vectorial:      384 dims (100% sincronizado)

[Gobernanza]
  Notas Pendientes:     1 nota en cola de revisión
  Audit Trail:          100% de operaciones firmadas
  Estado General:       🟢 SALUDABLE
```
