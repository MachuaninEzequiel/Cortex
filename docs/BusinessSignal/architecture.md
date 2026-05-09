# BusinessSignal Architecture

## Vision Tecnica

BusinessSignal debe ser un modulo lateral de Cortex. No debe estar incrustado dentro de `ContextEnricher` como logica de negocio, porque el enricher tiene una responsabilidad clara: recuperar contexto util para el agente.

La separacion correcta es:

- `ContextEnricher`: recupera contexto.
- `BusinessSignal`: analiza patrones derivados del contexto recuperado.

Esto evita que cada mejora de analitica contamine el pipeline de retrieval y permite agregar detectores nuevos sin modificar el core.

## Componentes Propuestos

```text
cortex/business_signal/
  __init__.py
  models.py
  telemetry.py
  aggregation.py
  engine.py
  registry.py
  scoring.py
  reporting.py
  config.py
  detectors/
    __init__.py
    base.py
    project_concentration.py
    sequence_similarity.py
    risk_echo.py
    priority_pattern.py
    scope_drift.py
  stores/
    __init__.py
    jsonl_store.py
    aggregate_store.py
  surfaces/
    __init__.py
    cli.py
    mcp_tools.py
    autopilot_advisory.py
```

## Flujo Principal

### 1. Captura de Telemetria

Cada vez que Cortex ejecuta un enrichment relevante, BusinessSignal recibe un evento liviano.

El evento no debe guardar todo el contenido recuperado. Debe guardar:

- Identidad de la sesion.
- Proyecto actual.
- HU o work item actual, si existe.
- Dominio detectado.
- Queries ejecutadas.
- Hits recuperados con scores.
- Origen de cada hit.
- Referencias al vault.
- Metadata minima para agrupar.

Esto permite analitica sin duplicar memoria ni consumir tokens.

### 2. Agregacion

Los eventos crudos se agrupan en ventanas:

- Por proyecto actual.
- Por sprint o periodo.
- Por HU / work item.
- Por dominio.
- Por modulo tecnico.
- Por cliente.
- Por product owner, si Cortex tiene esa metadata.

La agregacion produce trayectorias:

```text
ProjectTrajectory
  current_project_id
  time_window
  work_items_count
  enrichment_events_count
  historical_project_distribution
  domain_distribution
  risk_document_distribution
  sequence_fingerprint
```

### 3. Deteccion

El `PatternRadarEngine` ejecuta detectores independientes.

Cada detector recibe una trayectoria actual y, opcionalmente, datos historicos agregados. Devuelve cero o mas senales.

Contrato conceptual:

```text
DetectorInput -> list[BusinessSignal]
```

Cada detector debe ser independiente, testeable y registrable.

### 4. Scoring

Las senales no deben depender de una sola metrica. El score final puede combinar:

- Concentracion de hits en un proyecto historico.
- Repeticion a lo largo de varias HU.
- Diversidad de estrategias que encontraron la similitud.
- Calidad del origen: ADR, incident, session, HU.
- Recencia o vigencia del conocimiento.
- Coincidencia de dominio.
- Coincidencia de archivos o componentes.
- Coincidencia de secuencia.

Ejemplo de scoring inicial:

```text
signal_score =
  concentration_score * 0.35 +
  continuity_score * 0.20 +
  evidence_quality_score * 0.20 +
  sequence_score * 0.15 +
  domain_score * 0.10
```

Los pesos deben ser configurables.

### 5. Persistencia

La persistencia inicial debe ser simple:

```text
.cortex/business-signal/
  enrichment-events.jsonl
  aggregates/
    project-trajectories.jsonl
  signals/
    active-signals.jsonl
    archived-signals.jsonl
  reports/
```

No se recomienda una base externa para el MVP.

### 6. Superficies

BusinessSignal debe exponerse en varias superficies:

- CLI: reportes humanos y JSON.
- MCP: herramientas para que agentes consulten senales.
- Autopilot: avisos compactos cuando una senal sea relevante.
- Vault: notas de insight opcionales.
- Enterprise reports: salud y aprendizaje entre proyectos.

## Integracion Con ContextEnricher

La integracion ideal es por callback/evento, no por dependencia fuerte.

Opcion recomendada:

```text
ContextEnricher.enrich(...)
  -> EnrichedContext
  -> optional telemetry sink records EnrichmentEvent
```

El enricher no debe saber que existe cada detector. Solo debe emitir un evento estructurado.

## Integracion Con Enterprise Retrieval

Para que BusinessSignal sea realmente util, los hits deben preservar metadata de origen:

- `origin_scope`
- `origin_project_id`
- `origin_vault`
- `origin_persist_dir`

Hoy Cortex ya maneja esta metadata en modelos como `SemanticDocument`, `EpisodicHit` y `UnifiedHit`, pero el modelo `EnrichedItem` no la conserva completamente.

Recomendacion futura:

- Extender `EnrichedItem` con campos opcionales de origen.
- O crear una estructura paralela `EnrichedEvidenceRef` usada solo para telemetria.

La segunda opcion es mas conservadora porque no altera el formato de prompt.

## Principios De Diseno

- Bajo consumo: usar metadata primero, texto solo bajo demanda.
- Evidencia primero: toda senal debe tener links/referencias.
- Advisory por defecto: no bloquear flujos de trabajo.
- Modularidad extrema: agregar un detector debe ser agregar un archivo y registrarlo.
- Compatibilidad: no romper `ContextEnricher`, CLI clasico ni Autopilot.
- Explicabilidad: todo score debe poder descomponerse.
- Privacidad: no duplicar contenido sensible si alcanza con referencias.

