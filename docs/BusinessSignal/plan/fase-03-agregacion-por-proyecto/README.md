# Fase 3 - Agregacion por Proyecto

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Construye trayectorias de proyecto a partir de eventos de telemetria. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Usa `ProjectTrajectory` y `TrajectoryStep` exactos del plan global seccion 8.
- No toques el enricher, CLI ni MCP en esta fase.
- La agregacion debe ser incremental.
- Usar eventos sinteticos para tests.

## Archivos a crear

```text
cortex/business_signal/aggregation.py
cortex/business_signal/stores/aggregate_store.py
tests/unit/business_signal/test_aggregation.py
```

## Detalle: aggregation.py

`AggregationService` recibe `EnrichmentEventStore` y `AggregateStore`. Metodo principal:

```python
def aggregate(self, project_id: str, window_days: int = 30) -> ProjectTrajectory:
```

Algoritmo:
1. Cargar eventos para project_id dentro de la ventana.
2. Contar distribucion de `origin_project_id` en todos los hits.
3. Calcular weighted scores por proyecto historico (suma de enriched_score).
4. Construir domain_distribution y memory_type_distribution.
5. Colectar risk_document_hits (tipos: incident, security, adr, changelog; tags: scope-change, rework, blocked).
6. Construir sequence_fingerprint desde work_items ordenados.
7. Persistir trayectoria.

## Detalle: aggregate_store.py

```python
class AggregateStore:
    def save(self, trajectory: ProjectTrajectory) -> None: ...
    def load_latest(self, project_id: str) -> ProjectTrajectory | None: ...
    def load_all_projects(self) -> list[ProjectTrajectory]: ...
```

Usa `JsonlStore` bajo `.cortex/business-signal/aggregates/project-trajectories.jsonl`.

## Checklist

- [ ] `aggregate()` produce ProjectTrajectory valida.
- [ ] Distribucion historica cuenta por origin_project_id.
- [ ] Weighted scores suma enriched_score por proyecto.
- [ ] Risk documents filtra por tipos y tags riesgosos.
- [ ] Sequence fingerprint refleja orden temporal de work items.
- [ ] Ventana temporal filtra eventos viejos.
- [ ] Tests usan eventos sinteticos.

## Gate de salida

- `pytest tests/unit/business_signal/test_aggregation.py` pasa.
- Con 20 eventos sinteticos, la trayectoria muestra distribucion correcta.

---
