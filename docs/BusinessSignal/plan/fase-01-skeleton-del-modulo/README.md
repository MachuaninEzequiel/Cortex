# Fase 1 - Skeleton del Modulo

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se crea el paquete `cortex.business_signal` con modelos, configuracion, stores y registry, sin comportamiento invasivo.

Al terminar, documentar en `REALIZACION.md`.

## Nota obligatoria para agentes implementadores

### Reglas generales

- **No improvises.** Usa los modelos exactos de la seccion 8 del plan global.
- **No saltees tests.** Gate de salida obligatorio.
- **No toques el CLI existente** en esta fase.
- **No toques el MCP server** en esta fase.
- **No toques el ContextEnricher** en esta fase.
- **No importes `AgentMemory`** en esta fase.

### Aplicacion especifica

- Usa los modelos Pydantic exactos del plan global seccion 8.
- No inventes campos ni renombres clases.
- El modulo debe poder importarse sin inicializar Chroma ni ONNX.

## Referencia obligatoria: modelos de la seccion 8

El implementador debe crear los siguientes modelos en `cortex/business_signal/models.py` EXACTAMENTE como estan definidos en la seccion 8 del plan global:

- `EnrichmentEvent` (§8.1)
- `EnrichmentHitRef` (§8.2)
- `ProjectTrajectory` (§8.3)
- `TrajectoryStep` (§8.4)
- `BusinessSignal` (§8.5)
- `EvidencePointer` (§8.6)
- `SignalFeedback` (§8.7)
- `BusinessSignalConfig` (§8.8)

Ademas, crear un `EventFilter` para queries:

```python
class EventFilter(BaseModel):
    project_id: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    source: str | None = None
    min_hits: int | None = None
```

## Plan operativo

### Archivos a crear

```text
cortex/business_signal/__init__.py
cortex/business_signal/models.py
cortex/business_signal/config.py
cortex/business_signal/errors.py
cortex/business_signal/registry.py
cortex/business_signal/stores/__init__.py
cortex/business_signal/stores/jsonl_store.py
tests/unit/business_signal/__init__.py
tests/unit/business_signal/test_models.py
tests/unit/business_signal/test_jsonl_store.py
tests/unit/business_signal/test_config.py
```

### Responsabilidades

**`__init__.py`**
- Package marker. Exportar `BusinessSignalConfig` y version.

**`models.py`**
- Todos los modelos Pydantic de la seccion 8 del plan global.
- Importar solo `pydantic`, `datetime`, `typing`, `uuid`.
- NO importar nada de `cortex.models` ni de otros modulos cortex.

**`config.py`**
- Cargar config opcional desde `.cortex/business-signal.yaml`.
- Proveer defaults si no existe el archivo.
- Usar `WorkspaceLayout` para resolver path.

**`errors.py`**
- `BusinessSignalError(Exception)` — base.
- `SignalNotFoundError(BusinessSignalError)`.
- `StoreError(BusinessSignalError)`.
- `DetectorError(BusinessSignalError)`.

**`registry.py`**
- Registro de detectores con add/get/list.
- No importar detectores concretos todavia.

**`stores/jsonl_store.py`**
- Leer/escribir JSONL generico.
- Operaciones: append, load_all, load_filtered, count, rotate.
- Rotacion FIFO por max_events.
- Encoding UTF-8.

### Detalle de `stores/jsonl_store.py`

```python
class JsonlStore:
    """Generic JSONL append-only store with rotation."""

    def __init__(self, path: Path, max_lines: int = 5000) -> None:
        self.path = path
        self.max_lines = max_lines

    def append(self, data: BaseModel) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(data.model_dump_json() + "\n")

    def load_all(self, model_class: type[T]) -> list[T]:
        if not self.path.exists():
            return []
        results = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                results.append(model_class.model_validate_json(line))
        return results

    def count(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for line in self.path.read_text("utf-8").splitlines() if line.strip())

    def rotate(self) -> int:
        """Remove oldest entries if over max_lines. Returns removed count."""
        if not self.path.exists():
            return 0
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_lines:
            return 0
        removed = len(lines) - self.max_lines
        self.path.write_text(
            "\n".join(lines[removed:]) + "\n",
            encoding="utf-8",
        )
        return removed
```

### Checklist

- [ ] `models.py` contiene todos los modelos de la seccion 8.
- [ ] Todos los modelos serializan y deserializan correctamente.
- [ ] `BusinessSignalConfig` tiene defaults sensatos.
- [ ] `config.py` carga YAML si existe, usa defaults si no.
- [ ] `JsonlStore.append()` crea directorios padre.
- [ ] `JsonlStore.load_all()` retorna lista vacia si no existe archivo.
- [ ] `JsonlStore.rotate()` preserva las lineas mas recientes.
- [ ] `registry.py` permite add/get/list sin detectores concretos.
- [ ] Tests unitarios cubren serializacion, store y config.
- [ ] El modulo se importa sin Chroma ni ONNX.

### Gate de salida

- `pytest tests/unit/business_signal` pasa.
- `import cortex.business_signal` no falla y no inicializa dependencias pesadas.
- Todos los modelos del plan global estan implementados.

---
