# Cortex BusinessSignal - Plan por Fases

**Fecha:** 2026-05-09
**Estado:** Propuesta tecnica para planificacion
**Alcance:** Nuevo modulo de inteligencia de negocio basado en telemetria de enrichment
**Principio rector:** senales basadas en evidencia, bajo consumo de tokens, explicabilidad total

---

## 1. Resumen Ejecutivo

Cortex ya detecta memoria similar cuando enriquece contexto. Si durante un proyecto actual aparecen repetidamente memorias de un mismo proyecto historico, esa repeticion es una senal de negocio que hoy se pierde dentro del prompt del agente.

BusinessSignal convierte esa telemetria pasiva en inteligencia de negocio explicable. No predice el futuro; detecta analogos historicos fuertes y avisa al equipo.

La propuesta es construir `Cortex BusinessSignal` como modulo lateral:

```text
cortex/
  business_signal/
    __init__.py
    models.py
    config.py
    telemetry.py
    aggregation.py
    engine.py
    registry.py
    scoring.py
    reporting.py
    stores/
      jsonl_store.py
      aggregate_store.py
    detectors/
      base.py
      project_concentration.py
      risk_echo.py
      sequence_similarity.py
    surfaces/
      cli.py
      mcp_tools.py
      autopilot_advisory.py
```

El CLI existente queda intacto. Solo se agrega un grupo nuevo:

```bash
cortex signals ...
```

BusinessSignal debe ser opt-in y no invasivo.

---

## 2. Objetivos

### Objetivo principal

Crear una capa de inteligencia de negocio que detecte patrones entre proyectos actuales e historicos, basandose exclusivamente en la telemetria de enrichment que Cortex ya produce.

### Objetivos funcionales

1. Capturar telemetria liviana de cada enrichment sin duplicar contenido del vault.
2. Agregar eventos por proyecto, HU, dominio y ventana temporal.
3. Detectar analogias historicas fuertes entre proyecto actual y proyectos previos.
4. Detectar ecos de riesgo basados en incidentes, ADRs y retrabajo historico.
5. Exponer senales en CLI, MCP y Autopilot.
6. Permitir feedback humano y de agentes para calibrar senales.
7. Mantener bajo consumo de tokens usando metadata y referencias en lugar de contenido completo.
8. Permitir futuras extensiones por adicion de archivos de detector.

### Objetivos de arquitectura

1. BusinessSignal debe ser independiente del ContextEnricher como modulo.
2. La integracion con el enricher debe ser por callback/evento, no por dependencia fuerte.
3. Cada detector nuevo debe poder agregarse creando un archivo y registrandolo.
4. Ningun detector debe escribir archivos directamente al vault.
5. Ningun detector debe llamar servicios de memoria a mano.
6. La telemetria debe ser persistente en disco usando JSONL.
7. El modulo debe poder importarse sin inicializar Chroma ni ONNX.

---

## 3. No Objetivos

BusinessSignal no debe:

1. Reemplazar `ContextEnricher` ni modificar el pipeline de retrieval.
2. Predecir el futuro como certeza. Es advisory, no profecia.
3. Guardar prompts completos, contenido de documentos ni datos sensibles.
4. Forzar senales a usuarios que no las pidieron.
5. Requerir bases de datos externas para el MVP.
6. Agregar dependencias pesadas o servicios externos obligatorios.
7. Bloquear CI por defecto. Las senales son advisory.
8. Inferir identidad de cliente desde texto libre sin confirmacion.
9. Saturar al agente con senales en cada enrichment.
10. Duplicar la funcionalidad de `feedback_loop.py` existente; debe integrarse con ella.

---

## 4. Filosofia de Diseno

### 4.1 Senales, no opiniones

Cada insight debe poder responder:

- Que patron se detecto.
- En que evidencia historica se basa.
- Que tan fuerte es la similitud.
- Que documentos conviene revisar.
- Que accion humana recomienda.
- Que nivel de confianza tiene.

Si no hay evidencia suficiente, no se emite senal.

### 4.2 Extension por archivo

Agregar un detector nuevo debe implicar:

1. Crear archivo en `cortex/business_signal/detectors/`.
2. Implementar el contrato base.
3. Registrarlo en el registry.
4. Agregar tests.

No debe requerir modificar el motor principal.

### 4.3 Bajo consumo primero

- Telemetria liviana: metadata y referencias, nunca contenido completo.
- Agregacion incremental, no recalculo total.
- Scoring descomponible sin LLM.
- Deteccion por umbrales configurables.

### 4.4 Compatibilidad total

BusinessSignal no debe romper:

- `ContextEnricher` ni su pipeline.
- CLI clasico ni comandos existentes.
- Autopilot ni sus policies.
- Enterprise retrieval ni org.yaml.
- MCP server ni tools existentes.

---

## 5. Diagnostico del Estado Actual

### 5.1 Componentes existentes reutilizables

| Area | Archivo actual | Uso en BusinessSignal |
|---|---|---|
| Enricher | `cortex/context_enricher/enricher.py` | Punto de captura de telemetria |
| WorkContext | `cortex/models.py` | Provee changed_files, keywords, domain |
| EnrichedContext | `cortex/models.py` | Provee hits, scores, estrategias |
| EnrichedItem | `cortex/models.py` | Item individual con score y matched_by |
| EpisodicHit | `cortex/models.py` | Tiene origin_scope, origin_project_id |
| SemanticDocument | `cortex/models.py` | Tiene origin_scope, origin_project_id |
| UnifiedHit | `cortex/models.py` | Hit fusionado RRF |
| Feedback Loop | `cortex/feedback_loop.py` | Base para SignalFeedback |
| Domain Detector | `cortex/context_enricher/domain_detector.py` | Provee dominio detectado |
| CLI | `cortex/cli/main.py` | Agregar subcomando signals aislado |
| MCP | `cortex/mcp/server.py` | Exponer tools BusinessSignal |
| Workspace | `cortex/workspace/layout.py` | Resolver paths |
| Config | `cortex/context_enricher/config.py` | Patron de config Pydantic |
| Enterprise | `cortex/enterprise/` | Scopes, org.yaml, reporting |
| Autopilot | `cortex/autopilot/` | Consumidor de senales |

### 5.2 Brechas criticas

1. **`EnrichedItem` no preserva origin metadata.** Hoy no tiene `origin_scope`, `origin_project_id`, `origin_vault` ni `memory_type`. Los modelos fuente (`EpisodicHit`, `SemanticDocument`) si los tienen, pero se pierden en la conversion. Esto es un BLOCKER para la Fase 2.

2. **No hay `project_id` formalizado.** Cortex infiere el proyecto del directorio de trabajo, pero no existe un campo explicito en config.yaml ni en WorkContext.

3. **No hay telemetria de enrichment.** `ContextEnricher.enrich()` devuelve `EnrichedContext` pero no emite eventos.

4. **No hay grupo `cortex signals`.** No existe subcomando CLI.

5. **No hay politica de retencion para JSONL.** Sin rotacion, los archivos crecen sin limite.

---

## 6. Arquitectura Objetivo

### 6.1 Vista de alto nivel

```text
ContextEnricher.enrich()
    |
    | emite EnrichmentEvent via TelemetrySink
    v
EnrichmentTelemetryStore (JSONL)
    |
    | agrega eventos por proyecto, HU, dominio
    v
AggregationService -> ProjectTrajectory
    |
    | ejecuta detectores modulares
    v
PatternRadarEngine
    |
    | genera senales con evidencia
    v
BusinessSignalRegistry
    |
    | persiste senales activas
    v
Surfaces
    +-- cortex signals (CLI)
    +-- cortex_business_signals (MCP)
    +-- Autopilot advisory injection
    +-- vault/signals/ (notas opcionales)
    +-- Enterprise reports
```

### 6.2 Flowchart de decision

```text
Enrichment ocurre
    |
    v
TelemetrySink habilitado? --No--> fin (sin overhead)
    |Yes
    v
Capturar EnrichmentEvent liviano (metadata, no contenido)
    |
    v
Acumular en JSONL
    |
    v
Umbral de re-evaluacion alcanzado? --No--> fin
    |Yes (cada N eventos o M minutos)
    v
AggregationService.aggregate(project_id, window)
    |
    v
PatternRadarEngine.evaluate(trajectory)
    |
    +-- ProjectConcentrationDetector
    +-- RiskEchoDetector
    +-- SequenceSimilarityDetector
    +-- (detectores futuros)
    |
    v
Senales nuevas o actualizadas?
    |Yes
    v
BusinessSignalRegistry.upsert(signals)
    |
    v
Notificar surfaces si hay senales high confidence
```

### 6.3 Persistencia

```text
.cortex/business-signal/
    enrichment-events.jsonl
    aggregates/
        project-trajectories.jsonl
    signals/
        active-signals.jsonl
        archived-signals.jsonl
    feedback/
        signal-feedback.jsonl
    reports/
```

No se recomienda base externa para el MVP. Usar `WorkspaceLayout` para resolver paths.

### 6.4 Integracion con ContextEnricher

La integracion debe ser por callback opcional, no por dependencia fuerte:

```python
# En ContextEnricher.enrich(), al final:
if self._telemetry_sink is not None:
    self._telemetry_sink.record(
        EnrichmentEvent.from_enriched_context(enriched_context, work)
    )
```

El enricher no debe saber que existe cada detector. Solo emite un evento estructurado. El sink es opcional y configurable.

---

## 7. Contratos Modulares

### 7.1 TelemetrySink

```python
class TelemetrySink(Protocol):
    def record(self, event: EnrichmentEvent) -> None: ...
    def query(self, filter: EventFilter) -> list[EnrichmentEvent]: ...
```

Implementacion MVP: `JsonlTelemetrySink`.

### 7.2 Detector

Los detectores clasifican trayectorias y emiten senales.

```python
class BusinessSignalDetector(Protocol):
    name: str
    version: str

    def evaluate(self, input: DetectorInput) -> list[BusinessSignal]: ...
```

```python
class DetectorInput(BaseModel):
    trajectory: ProjectTrajectory
    historical_trajectories: list[ProjectTrajectory] = []
    config: DetectorConfig | None = None
```

Cada detector debe ser independiente, testeable y registrable.

Detectores iniciales (MVP):

- `ProjectConcentrationDetector` — detecta concentracion de hits en un proyecto historico
- `RiskEchoDetector` — detecta ecos de incidentes, ADRs y retrabajo
- `SequenceSimilarityDetector` — compara secuencias de avance entre proyectos

Detectores futuros:

- `ScopeDriftDetector`
- `KnowledgeGapDetector`
- `ClientBehaviorDetector`
- `ComplianceEchoDetector`
- `DeliveryFrictionDetector`
- `ArchitectureDecisionRecurrenceDetector`

### 7.3 DetectorRegistry

Cuando multiples detectores retornan senales:

1. Ejecutar todos los detectores registrados.
2. Filtrar senales con confidence < low.
3. Si hay senales critical de RiskEcho, priorizarlas.
4. Deduplicar senales sobre el mismo proyecto historico.
5. Ordenar por score descendente.
6. Limitar a max_active_signals configurable.

### 7.4 Scoring

Las senales no dependen de una sola metrica. El score final combina:

```python
signal_score = (
    concentration_score * 0.35 +
    continuity_score * 0.20 +
    evidence_quality_score * 0.20 +
    sequence_score * 0.15 +
    domain_score * 0.10
)
```

Los pesos deben ser configurables en `business_signal.yaml`.

### 7.5 SignalLifecycle

Transiciones validas:

```text
active -> acknowledged   (por: human, agent)
active -> dismissed      (por: human)
acknowledged -> archived (por: human, agent, auto-expire)
active -> archived       (auto: tras N dias sin interaccion)
dismissed -> active      (por: re-deteccion con score mas alto)
```

---

## 8. Modelo de Datos Consolidado

### 8.1 EnrichmentEvent

```python
class EnrichmentEvent(BaseModel):
    event_id: str
    timestamp: datetime
    session_id: str | None = None
    current_project_id: str
    current_client_id: str | None = None
    current_work_item_id: str | None = None
    current_sprint_id: str | None = None
    source: Literal["git_diff", "pr", "manual", "autopilot", "mcp"]
    detected_domain: str | None = None
    domain_confidence: float = 0.0
    changed_files: list[str] = []
    keywords: list[str] = []
    search_queries: list[str] = []
    total_searches: int = 0
    total_raw_hits: int = 0
    total_items: int = 0
    total_chars: int = 0
    within_budget: bool = True
    hits: list[EnrichmentHitRef] = []
```

### 8.2 EnrichmentHitRef

```python
class EnrichmentHitRef(BaseModel):
    source: Literal["episodic", "semantic"]
    source_id: str
    title: str
    score: float
    enriched_score: float
    matched_by: list[str] = []
    files_mentioned: list[str] = []
    tags: list[str] = []
    memory_type: str | None = None
    date: datetime | None = None
    origin_scope: Literal["local", "enterprise", "unknown"] = "unknown"
    origin_project_id: str | None = None
    origin_vault: str | None = None
    vault_path: str | None = None
```

Regla: `content` no debe guardarse por defecto.

### 8.3 ProjectTrajectory

```python
class ProjectTrajectory(BaseModel):
    current_project_id: str
    window_start: datetime
    window_end: datetime
    work_items_count: int = 0
    enrichment_events_count: int = 0
    total_hits: int = 0
    historical_project_distribution: dict[str, int] = {}
    historical_project_weighted_scores: dict[str, float] = {}
    domain_distribution: dict[str, int] = {}
    memory_type_distribution: dict[str, int] = {}
    risk_document_hits: list[EvidencePointer] = []
    sequence_fingerprint: list[TrajectoryStep] = []
```

### 8.4 TrajectoryStep

```python
class TrajectoryStep(BaseModel):
    order: int
    work_item_id: str | None = None
    detected_domain: str | None = None
    top_historical_project_id: str | None = None
    top_memory_types: list[str] = []
    top_tags: list[str] = []
    changed_components: list[str] = []
```

### 8.5 BusinessSignal

```python
class BusinessSignal(BaseModel):
    signal_id: str
    type: str
    title: str
    summary: str
    current_project_id: str
    related_project_id: str | None = None
    severity: Literal["info", "advisory", "warning", "critical"]
    confidence: Literal["low", "medium", "high"]
    score: float
    created_at: datetime
    updated_at: datetime
    version: int = 1
    status: Literal["active", "acknowledged", "archived", "dismissed"]
    evidence: list[EvidencePointer] = []
    recommended_actions: list[str] = []
    metrics: dict[str, float | int | str] = {}
    score_breakdown: dict[str, float] = {}
```

### 8.6 EvidencePointer

```python
class EvidencePointer(BaseModel):
    kind: Literal[
        "session", "hu", "adr", "incident",
        "changelog", "security", "doc", "memory"
    ]
    title: str
    path: str | None = None
    memory_id: str | None = None
    origin_project_id: str | None = None
    origin_scope: Literal["local", "enterprise", "unknown"] = "unknown"
    score: float = 0.0
    reason: str = ""
```

### 8.7 SignalFeedback

```python
class SignalFeedback(BaseModel):
    signal_id: str
    timestamp: datetime
    actor: Literal["human", "agent", "ci"]
    feedback: Literal[
        "useful", "not_useful", "false_positive", "acted_on", "ignored"
    ]
    note: str | None = None
```

### 8.8 BusinessSignalConfig

```python
class BusinessSignalConfig(BaseModel):
    enabled: bool = False
    project_id: str | None = None
    client_id: str | None = None
    telemetry_enabled: bool = True
    max_events: int = 5000
    retention_days: int = 180
    rotation_strategy: Literal["fifo", "time_window"] = "fifo"
    aggregation_mode: Literal["incremental", "full"] = "incremental"
    snapshot_interval: int = 50
    max_active_signals: int = 20
    re_evaluation_interval: int = 10
    scoring_weights: dict[str, float] = {
        "concentration": 0.35,
        "continuity": 0.20,
        "evidence_quality": 0.20,
        "sequence": 0.15,
        "domain": 0.10,
    }
    detector_thresholds: dict[str, dict[str, float]] = {}
```

---

## 9. Diseno del CLI

### 9.1 Nuevo grupo

Crear `cortex/business_signal/cli.py` y en `cortex/cli/main.py` solo:

```python
from cortex.business_signal.cli import app as signals_app
app.add_typer(signals_app, name="signals")
```

### 9.2 Comandos propuestos

```bash
cortex signals                              # Lista senales activas
cortex signals --json                       # Salida JSON para CI/agentes
cortex signals explain <signal-id>          # Evidencia detallada
cortex signals report                       # Reporte Markdown
cortex signals report --window 30d          # Reporte con ventana temporal
cortex signals dismiss <signal-id> --reason "..."  # Descartar senal
cortex signals feedback <signal-id> --useful       # Registrar feedback
cortex signals doctor                       # Validar telemetria y detectores
cortex signals watch                        # Monitor en tiempo real (futuro)
```

### 9.3 Reglas CLI

1. Todos los comandos deben aceptar `--project-root`.
2. `cortex signals --json` es salida estable para CI.
3. Ningun comando debe preguntar interactivamente si recibe `--json`.
4. `doctor` no modifica archivos.
5. `dismiss` requiere `--reason` para trazabilidad.

---

## 10. Diseno MCP

### 10.1 Tools nuevas

- `cortex_business_signals` — senales activas compactas
- `cortex_explain_business_signal` — evidencia de una senal
- `cortex_record_signal_feedback` — registrar feedback

### 10.2 Contrato

Las MCP tools deben delegar a un service central, igual que el CLI. No deben duplicar logica.

### 10.3 Reglas de inyeccion en Autopilot

- En `question_only`: no inyectar senales.
- En `docs_only`: solo senales de documentacion faltante.
- En `fast_code`: maximo 1 advisory si es high confidence.
- En `deep_code`: hasta 3 senales compactas.
- En `finish_only`: registrar si la sesion confirma o contradice una senal.

---

## 11. Plan por Fases

### Fase 0 - Preparacion del Core

**Objetivo:** Resolver los blockers tecnicos antes de construir BusinessSignal.

**Archivos a tocar:**
- `cortex/models.py` — extender `EnrichedItem` con origin metadata
- `cortex/context_enricher/enricher.py` — propagar origin al crear EnrichedItem
- `config.yaml` schema — agregar `project.id` y `project.client_id`

**Gate:** EnrichedItem tiene origin_scope, origin_project_id, origin_vault, memory_type. Tests de regresion pasan.

---

### Fase 1 - Skeleton del Modulo

**Objetivo:** Crear paquete `cortex.business_signal` sin comportamiento invasivo.

**Archivos a crear:**
- `cortex/business_signal/__init__.py`
- `cortex/business_signal/models.py`
- `cortex/business_signal/config.py`
- `cortex/business_signal/errors.py`
- `cortex/business_signal/stores/jsonl_store.py`
- `cortex/business_signal/registry.py`
- Tests unitarios

**Gate:** `pytest tests/unit/business_signal` pasa. El modulo se importa sin Chroma ni ONNX.

---

### Fase 2 - Telemetria de Enrichment

**Objetivo:** Capturar eventos livianos de cada enrichment.

**Archivos a crear:**
- `cortex/business_signal/telemetry.py`
- `cortex/business_signal/stores/event_store.py`

**Archivos a tocar:**
- `cortex/context_enricher/enricher.py` — agregar telemetry sink opcional

**Gate:** Al ejecutar enrichment, queda un evento JSONL estructurado.

---

### Fase 3 - Agregacion por Proyecto

**Objetivo:** Construir trayectorias desde eventos.

**Archivos a crear:**
- `cortex/business_signal/aggregation.py`
- `cortex/business_signal/stores/aggregate_store.py`

**Gate:** Se puede calcular distribucion de proyectos historicos desde eventos.

---

### Fase 4 - Detector Project Concentration

**Objetivo:** Implementar el primer detector MVP.

**Archivos a crear:**
- `cortex/business_signal/detectors/base.py`
- `cortex/business_signal/detectors/project_concentration.py`
- `cortex/business_signal/engine.py`
- `cortex/business_signal/scoring.py`

**Gate:** Cortex detecta analogias historicas fuertes.

---

### Fase 5 - CLI Inicial

**Objetivo:** Exponer senales al usuario.

**Archivos a crear:**
- `cortex/business_signal/cli.py`
- Tocar `cortex/cli/main.py` solo para registrar subcomando

**Gate:** `cortex signals` y `cortex signals explain <id>` funcionan.

---

### Fase 6 - MCP Tools

**Objetivo:** Permitir que agentes consulten senales.

**Archivos a crear:**
- `cortex/business_signal/surfaces/mcp_tools.py`
- Tocar `cortex/mcp/server.py` para registrar tools

**Gate:** Agente puede consultar senales via MCP.

---

### Fase 7 - Feedback Loop

**Objetivo:** Aprender si las senales fueron utiles.

**Archivos a crear:**
- `cortex/business_signal/feedback.py`

**Gate:** Feedback se registra y ajusta scoring.

---

### Fase 8 - Integracion Autopilot

**Objetivo:** Hacer que Autopilot consuma senales de forma prudente.

**Gate:** Autopilot inyecta senales segun budget profile.

---

### Fase 9 - Risk Echo y Detectores Avanzados

**Objetivo:** Agregar detectores de riesgo y secuencia.

**Gate:** Cortex advierte ecos de riesgo historicos.

---

### Fase 10 - Reportes y Vault Notes

**Objetivo:** Generar reportes Markdown y notas opcionales en vault.

**Gate:** `cortex signals report` genera reporte accionable.

---

### Fase 11 - Doctor y Observabilidad

**Objetivo:** Diagnosticar estado de BusinessSignal.

**Gate:** `cortex signals doctor` valida telemetria y detectores.

---

### Fase 12 - Enterprise Dashboard

**Objetivo:** Visibilidad organizacional cross-project.

**Gate:** Reportes por proyecto, cliente, dominio y detector.

---

### Fase 13 - Politicas Gobernadas

**Objetivo:** Permitir reglas enterprise sobre senales.

**Gate:** Organizaciones pueden crear policies sobre senales criticas.

---

## 12. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| EnrichedItem sin origin metadata | Blocker | Fase 0 resuelve antes de empezar |
| project_id no formalizado | Alto | Fase 0 agrega a config.yaml |
| JSONL crece sin limite | Medio | Politica de retencion en config |
| Falsos positivos generan ruido | Alto | Feedback loop temprano (Fase 7), shadow mode |
| Telemetria degrada performance del enricher | Medio | Sink async/fire-and-forget |
| Romper CLI actual | Alto | Subcomando aislado y tests de regresion |
| Romper ContextEnricher | Alto | Sink opcional, null por defecto |
| Cold start sin datos suficientes | Medio | Umbrales minimos, estado warming_up |
| Privacidad cross-project en enterprise | Alto | Scopes de visibilidad en org.yaml |
| Autopilot aun en desarrollo | Medio | Priorizar CLI y MCP antes de Autopilot |

---

## 13. Decisiones Iniciales Recomendadas

1. BusinessSignal debe estar deshabilitado por defecto (`enabled: false`).
2. Primer detector debe ser Project Concentration (MVP mas seguro).
3. Telemetria no debe guardar contenido, solo metadata y referencias.
4. Los datos deben vivir en `.cortex/business-signal/`.
5. El grupo CLI debe ser `cortex signals`.
6. No agregar dependencias nuevas en MVP.
7. Feedback loop debe estar antes de Autopilot en el roadmap.
8. Shadow mode opcional antes de exponer senales al usuario.
9. Scoring con pesos configurables desde el primer dia.
10. Enterprise reports recien despues de MVP local probado.

---

## 14. Nota Final para Agentes Implementadores

Si sos un agente de IA leyendo este documento para implementar BusinessSignal, segui estas reglas:

1. **No improvises.** Usa los modelos exactos definidos en la seccion 8. No inventes campos ni renombres clases.
2. **No saltees tests.** Cada fase tiene un gate de salida con tests. Si los tests no pasan, la fase no esta completa.
3. **No toques el CLI existente** salvo la linea `app.add_typer(signals_app, name="signals")`.
4. **No toques el MCP server** hasta la Fase 6.
5. **No toques el ContextEnricher** hasta la Fase 2, y solo para agregar el sink opcional.
6. **Usa `WorkspaceLayout`** para resolver paths. No hardcodees `.cortex/` ni `config.yaml`.
7. **Cada archivo nuevo** debe tener su test unitario correspondiente.
8. **No guardes contenido** en EnrichmentEvent. Solo metadata y referencias.
9. **Si algo no esta claro**, pregunta antes de asumir.
10. **Verifica** que los tests existentes de ContextEnricher siguen pasando despues de cada cambio.
