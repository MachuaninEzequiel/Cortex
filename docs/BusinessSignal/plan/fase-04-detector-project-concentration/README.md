# Fase 4 - Detector Project Concentration

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Implementa el primer detector MVP y el motor de deteccion. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Usa el contrato `BusinessSignalDetector` del plan global seccion 7.2.
- Usa el modelo `BusinessSignal` de la seccion 8.5.
- No toques CLI, MCP ni enricher en esta fase.
- El detector debe ser independiente y testeable.

## Archivos a crear

```text
cortex/business_signal/detectors/__init__.py
cortex/business_signal/detectors/base.py
cortex/business_signal/detectors/project_concentration.py
cortex/business_signal/engine.py
cortex/business_signal/scoring.py
tests/unit/business_signal/test_engine.py
tests/unit/business_signal/test_project_concentration.py
tests/unit/business_signal/test_scoring.py
```

## Detalle: detectors/base.py

```python
"""Base contract for BusinessSignal detectors."""
from typing import Protocol
from cortex.business_signal.models import BusinessSignal, DetectorInput

class BusinessSignalDetector(Protocol):
    name: str
    version: str

    def evaluate(self, input: DetectorInput) -> list[BusinessSignal]: ...

class DetectorInput(BaseModel):
    trajectory: ProjectTrajectory
    historical_trajectories: list[ProjectTrajectory] = []
    config: dict[str, Any] = {}
```

## Detalle: project_concentration.py

El detector MVP. Detecta cuando un porcentaje significativo del contexto viene de un mismo proyecto historico.

**Umbrales iniciales (configurables):**
- Minimo 8 eventos de enrichment.
- Minimo 5 work items distintos (si hay work_item_ids).
- Un proyecto historico concentra mas del 45% del score ponderado.
- Al menos 3 estrategias distintas encontraron hits relacionados.

**Algoritmo:**
1. Verificar que trajectory.enrichment_events_count >= min_events.
2. Para cada proyecto en historical_project_weighted_scores:
   a. Calcular porcentaje del score total.
   b. Si supera threshold (45%), crear senal candidata.
3. Recopilar evidencia: top hits del proyecto historico.
4. Calcular score compuesto usando scoring.py.
5. Asignar confidence basada en cantidad de evidencia.
6. Retornar senales con status "active".

**Ejemplo de senal generada:**

```text
BusinessSignal(
    type="project_concentration",
    title="Historical Project Analogy",
    summary="El proyecto actual recupero 68% del contexto desde client-portal-v1",
    severity="advisory",
    confidence="high",
    recommended_actions=[
        "Revisar ADR-004 de client-portal-v1",
        "Verificar incident-2025-09-auth-refresh",
    ],
)
```

## Detalle: engine.py

```python
"""PatternRadarEngine — runs all detectors against trajectories."""

class PatternRadarEngine:
    def __init__(self, registry: DetectorRegistry, config: BusinessSignalConfig):
        self.registry = registry
        self.config = config

    def evaluate(self, trajectory: ProjectTrajectory,
                 historical: list[ProjectTrajectory] = []) -> list[BusinessSignal]:
        """Run all registered detectors and collect signals."""
        input = DetectorInput(
            trajectory=trajectory,
            historical_trajectories=historical,
        )
        all_signals = []
        for detector in self.registry.list_detectors():
            try:
                signals = detector.evaluate(input)
                all_signals.extend(signals)
            except Exception as exc:
                logger.warning("Detector %s failed: %s", detector.name, exc)
        # Deduplicate by related_project_id + type
        # Sort by score descending
        # Limit to max_active_signals
        return self._deduplicate_and_limit(all_signals)
```

## Detalle: scoring.py

```python
"""Composable scoring for BusinessSignal."""

def calculate_signal_score(
    concentration: float,
    continuity: float,
    evidence_quality: float,
    sequence: float,
    domain: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate weighted signal score. All inputs 0.0-1.0."""
    w = weights or DEFAULT_WEIGHTS
    return (
        concentration * w.get("concentration", 0.35) +
        continuity * w.get("continuity", 0.20) +
        evidence_quality * w.get("evidence_quality", 0.20) +
        sequence * w.get("sequence", 0.15) +
        domain * w.get("domain", 0.10)
    )

def determine_confidence(score: float, event_count: int, strategy_count: int) -> str:
    if score >= 0.7 and event_count >= 15 and strategy_count >= 3:
        return "high"
    if score >= 0.4 and event_count >= 8:
        return "medium"
    return "low"
```

## Checklist

- [ ] `BusinessSignalDetector` protocol definido en base.py.
- [ ] `ProjectConcentrationDetector` implementa el protocol.
- [ ] Detector usa umbrales configurables.
- [ ] Detector genera EvidencePointer para cada hit relevante.
- [ ] `PatternRadarEngine` ejecuta todos los detectores registrados.
- [ ] Engine deduplica senales del mismo proyecto historico.
- [ ] Engine captura excepciones de detectores sin fallar.
- [ ] `calculate_signal_score()` produce scores 0.0-1.0.
- [ ] `determine_confidence()` asigna confidence correctamente.
- [ ] `score_breakdown` se incluye en cada senal generada.
- [ ] Tests con trayectorias sinteticas verifican deteccion.
- [ ] Test verifica que con <8 eventos no se emite senal.
- [ ] Test verifica que con >45% concentracion si se emite senal.

## Gate de salida

- `pytest tests/unit/business_signal/test_project_concentration.py` pasa.
- `pytest tests/unit/business_signal/test_engine.py` pasa.
- Cortex detecta analogias historicas fuertes con datos sinteticos.

---
