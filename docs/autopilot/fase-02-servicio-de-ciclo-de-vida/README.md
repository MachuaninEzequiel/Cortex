# Fase 2 - Servicio de Ciclo de Vida

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 2 - Servicio de Ciclo de Vida`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- El servicio debe ser la unica API de negocio para hooks, CLI y MCP futuros.
- No registres comandos CLI todavia; eso pertenece a la Fase 3.
- No toques el MCP server; eso pertenece a la Fase 5.
- Toda decision automatica debe quedar como evento persistente.

## Plan operativo original

## Fase 2 - Servicio de Ciclo de Vida

### Objetivo

Crear `AutopilotService` como unica API de negocio.

### Archivos a crear

```text
cortex/autopilot/service.py
cortex/autopilot/lifecycle.py
cortex/autopilot/detectors/base.py
cortex/autopilot/detectors/default.py
cortex/autopilot/detectors/ambiguous.py
cortex/autopilot/policies/base.py
cortex/autopilot/policies/default.py
cortex/autopilot/policies/auto_checkpoint.py
cortex/autopilot/context_budget.py
tests/unit/autopilot/test_service.py
tests/unit/autopilot/test_detectors.py
tests/unit/autopilot/test_policies.py
```

### API propuesta

```python
class AutopilotService:
    def start(self, request: StartRequest) -> StartResult: ...
    def preflight(self, request: PreflightRequest) -> PreflightResult: ...
    def checkpoint(self, request: CheckpointRequest) -> CheckpointResult: ...
    def finish(self, request: FinishRequest) -> FinishResult: ...
    def status(self, session_id: str | None = None) -> StatusResult: ...
```

### Reglas

- `start()` crea estado, no busca memoria pesada.
- `preflight()` decide si necesita contexto.
- `checkpoint()` solo agrega informacion observada.
- `finish()` decide si guardar session note.
- Todas las decisiones deben dejar evento.

### Detectors obligatorios (referencia del plan global §7.1)

Los detectores usan los contratos `DetectionRequest` y `DetectionResult` de `models.py`. El implementador debe crear al menos:

- `CodeChangeDetector`
- `DocsOnlyDetector`
- `QuestionOnlyDetector`
- `AmbiguousRequestDetector` (ver §7.1.1 del plan global — heuristicas obligatorias)
- `NoopDetector`

**DetectorRegistry — logica de resolucion (§7.1.2):**

1. Ejecutar todos los detectores registrados.
2. Filtrar los que retornaron `confidence > 0.3`.
3. Si `SecuritySensitiveDetector` tiene confianza > 0.5, toma prioridad.
4. Si `AmbiguousRequestDetector` tiene confianza > 0.6, bloquea antes de cualquier otro.
5. En caso contrario, usar el detector con mayor `confidence`.
6. Si hay empate, preferir el mas conservador.

### Policies obligatorias (referencia del plan global §7.2)

Las policies usan el contrato `PolicyDecision` de `models.py`. El implementador debe crear al menos:

- `BudgetPolicy`
- `DocumentationRequiredPolicy`
- `AutoCheckpointPolicy` (ver §7.2.1 del plan global — umbrales: 5 archivos o 10 minutos)

### Checklist

- [ ] `start()` no carga ONNX.
- [ ] `preflight()` puede operar sin user_request y dejar warning.
- [ ] `checkpoint()` agrega archivos, comandos, tools y resumen.
- [ ] `finish(auto=True)` genera draft si falta documentacion.
- [ ] Policies pueden bloquear o degradar modo.
- [ ] `AmbiguousRequestDetector` detecta requests vagos correctamente.
- [ ] `AutoCheckpointPolicy` fuerza checkpoint tras 5 archivos sin registrar.
- [ ] `DetectorRegistry` resuelve conflictos entre detectores segun prioridad.

### Gate de salida

- Servicio testeado con memoria fake.
- Ningun test de esta fase requiere Chroma real.
- Detectors y policies tienen tests unitarios independientes.

---


