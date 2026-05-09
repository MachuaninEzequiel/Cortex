# BusinessSignal Data Model

## Objetivo Del Modelo

El modelo de datos debe permitir responder preguntas como:

- Que memorias historicas se repiten en el proyecto actual.
- De que proyecto, vault o fuente vienen esas memorias.
- En que HU, sesiones o dominios se repitieron.
- Que tan fuerte y sostenida es la similitud.
- Que evidencia puede revisar una persona.

Debe hacerlo sin guardar prompts completos ni duplicar contenido del vault.

## EnrichmentEvent

Evento crudo emitido por cada enriquecimiento relevante.

```text
EnrichmentEvent
  event_id: str
  timestamp: datetime
  session_id: str | None
  current_project_id: str
  current_client_id: str | None
  current_work_item_id: str | None
  current_sprint_id: str | None
  source: git_diff | pr | manual | autopilot | mcp
  detected_domain: str | None
  domain_confidence: float
  changed_files: list[str]
  keywords: list[str]
  search_queries: list[str]
  total_searches: int
  total_raw_hits: int
  total_items: int
  total_chars: int
  within_budget: bool
  hits: list[EnrichmentHitRef]
```

## EnrichmentHitRef

Referencia liviana a cada item recuperado.

```text
EnrichmentHitRef
  source: episodic | semantic
  source_id: str
  title: str
  score: float
  enriched_score: float
  matched_by: list[str]
  files_mentioned: list[str]
  tags: list[str]
  memory_type: str | None
  date: datetime | None
  origin_scope: local | enterprise | unknown
  origin_project_id: str | None
  origin_vault: str | None
  vault_path: str | None
```

Regla importante: `content` no debe guardarse por defecto.

## ProjectTrajectory

Agregado que representa el comportamiento reciente de un proyecto actual.

```text
ProjectTrajectory
  current_project_id: str
  window_start: datetime
  window_end: datetime
  work_items_count: int
  enrichment_events_count: int
  total_hits: int
  historical_project_distribution: dict[str, int]
  historical_project_weighted_scores: dict[str, float]
  domain_distribution: dict[str, int]
  memory_type_distribution: dict[str, int]
  risk_document_hits: list[EvidencePointer]
  sequence_fingerprint: list[TrajectoryStep]
```

## TrajectoryStep

Representa una unidad del avance del proyecto.

```text
TrajectoryStep
  order: int
  work_item_id: str | None
  detected_domain: str | None
  top_historical_project_id: str | None
  top_memory_types: list[str]
  top_tags: list[str]
  changed_components: list[str]
```

Esto permite comparar secuencias entre proyectos.

## BusinessSignal

Salida principal del modulo.

```text
BusinessSignal
  signal_id: str
  type: str
  title: str
  summary: str
  current_project_id: str
  related_project_id: str | None
  severity: info | advisory | warning | critical
  confidence: low | medium | high
  score: float
  created_at: datetime
  updated_at: datetime
  status: active | acknowledged | archived | dismissed
  evidence: list[EvidencePointer]
  recommended_actions: list[str]
  metrics: dict[str, float | int | str]
```

## EvidencePointer

Toda senal debe tener evidencia navegable.

```text
EvidencePointer
  kind: session | hu | adr | incident | changelog | security | doc | memory
  title: str
  path: str | None
  memory_id: str | None
  origin_project_id: str | None
  origin_scope: local | enterprise | unknown
  score: float
  reason: str
```

## SignalFeedback

Para que Cortex aprenda si las senales fueron utiles.

```text
SignalFeedback
  signal_id: str
  timestamp: datetime
  actor: human | agent | ci
  feedback: useful | not_useful | false_positive | acted_on | ignored
  note: str | None
```

Esto puede integrarse luego con `feedback_loop.py`.

## Datos Que No Deben Guardarse Por Defecto

- Prompts completos del usuario.
- Contenido completo de documentos recuperados.
- Datos sensibles del cliente si no son necesarios.
- Conversaciones completas.
- Credenciales, secretos o diffs grandes.

BusinessSignal debe guardar referencias y metadata. El contenido se consulta bajo demanda desde el vault.

