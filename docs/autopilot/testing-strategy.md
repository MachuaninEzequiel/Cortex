# Cortex Autopilot — Estrategia de Testing

**Fecha:** 2026-05-09  
**Alcance:** Todas las fases del plan Autopilot  
**Principio:** Cada archivo de runtime tiene tests unitarios; cada fase tiene un gate de salida.

---

## 1. Pirámide de Tests

```
        /
       /  \        E2E / Evals (fase 11)
      /____\
     /      \      Integration (fases 5, 7, 9)
    /________\
   /          \   Unitarios (todas las fases)
  /____________\
```

| Nivel | Responsabilidad | Cuándo ejecutar |
|-------|-----------------|-----------------|
| **Unitario** | Contratos, serialización, lógica pura, registries | En cada cambio de código (`pytest tests/unit/autopilot`) |
| **Integración** | CLI + servicio, MCP + servicio, adapter + filesystem | En gates de fase y CI |
| **E2E / Evals** | Escenarios completos con memoria fake | En milestones y releases |

---

## 2. Estructura de Directorios de Test

```
tests/
  unit/
    autopilot/
      test_models.py          # Fase 1
      test_state_store.py     # Fase 1
      test_registry.py        # Fase 1
      test_service.py         # Fase 2
      test_detectors.py       # Fase 2
      test_policies.py        # Fase 2
      test_cli.py             # Fase 3
      test_session_builder.py # Fase 4
      test_renderers.py       # Fase 4
      test_mcp_tools.py       # Fase 5
      test_skills_assets.py   # Fase 6
      test_adapters.py        # Fase 7
      test_platform_detect.py # Fase 7
      test_context_budget.py  # Fase 8
      test_doctor.py          # Fase 10
    cli/
      test_main.py            # Regresión CLI histórico
  integration/
    autopilot/
      test_service_memory.py  # Servicio + AgentMemory fake
    mcp/
      test_server.py          # MCP server completo (existente)
  e2e/
    scenarios/
      test_autopilot_basic.py     # Fase 11
      test_autopilot_finish.py    # Fase 11
      test_autopilot_budget.py    # Fase 11
```

---

## 3. Reglas por Tipo de Test

### 3.1 Tests Unitarios

- **Sin I/O real**: usar `tmp_path` de pytest para filesystem.
- **Sin Chroma/ONNX real**: mocks de `AgentMemory`, `ContextEnricher` y `RetrievalResult`.
- **Sin Typer real**: probar funciones puras; el CLI se testea con `CliRunner` de Typer solo en Fase 3+.
- **Sin variables de entorno reales**: `monkeypatch` para `os.environ`.

#### Patrón de mock para `AgentMemory`

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def fake_memory():
    mem = MagicMock(spec=AgentMemory)
    mem.retrieve.return_value = MagicMock(unified_hits=[])
    mem.sync_vault.return_value = 0
    return mem
```

#### Patrón de test para `StateStore`

```python
def test_state_store_roundtrip(tmp_path):
    from cortex.autopilot.state_store import StateStore
    from cortex.autopilot.models import AutopilotSessionState

    store = StateStore(tmp_path)
    state = AutopilotSessionState(project_root=str(tmp_path), workspace_root=str(tmp_path))
    store.save_state(state)
    loaded = store.load_state(state.session_id)
    assert loaded is not None
    assert loaded.session_id == state.session_id
```

### 3.2 Tests de Integración

- **CLI + servicio**: usar `typer.testing.CliRunner` con ` isolated_filesystem()`.
- **MCP + servicio**: invocar handlers directamente sin levantar stdio server.
- **Adapter + filesystem**: crear estructura temporal de proyecto y verificar archivos escritos.

### 3.3 Tests E2E / Evals

- **Memoria fake**: fixture que reemplaza `AgentMemory` por implementación en memoria con diccionarios.
- **Escenarios concretos**:
  1. Pregunta simple → sin spec, sin session note.
  2. Cambio simple → Fast Track, session auto generada.
  3. Docs-only → renderer docs-only.
  4. Tarea compleja → Deep Track sugerido.
  5. Cierre sin datos → draft seguro (`auto-draft`).
  6. Tool failure → warning, sin invención.
  7. Uninstall → config limpia.

### 3.4 Métricas de Evals

| Métrica | Objetivo |
|---------|----------|
| Session note creada cuando corresponde | 100% de escenarios positivos |
| No session note cuando no corresponde | 100% de escenarios negativos |
| Chars de contexto | Tope definido por profile |
| Cantidad de retrievals | ≤ 1 por fase de preflight |
| Subagentes spawn | 0 en fast, ≤ 1 en deep |
| Tiempo de startup | < 100 ms (sin ONNX) |
| Archivos tocados por install | Solo skills + hooks nuevos |

---

## 4. Gates de Salida por Fase

| Fase | Gate de salida |
|------|----------------|
| 0 | Documentación completa; sin contradicciones con `WorkspaceLayout`. |
| 1 | `pytest tests/unit/autopilot/test_models.py` y `test_state_store.py` pasan. |
| 2 | `pytest tests/unit/autopilot/test_service.py`, `test_detectors.py`, `test_policies.py` pasan. |
| 3 | `pytest tests/unit/autopilot/test_cli.py` + `pytest tests/unit/cli/test_main.py` pasan. |
| 4 | `pytest tests/unit/autopilot/test_session_builder.py` y `test_renderers.py` pasan; self-review detecta placeholders. |
| 5 | `pytest tests/unit/autopilot/test_mcp_tools.py` + `pytest tests/integration/mcp/test_server.py` pasan. |
| 6 | `pytest tests/unit/autopilot/test_skills_assets.py` pasa; setup normal sin Autopilot no cambia. |
| 7 | `pytest tests/unit/autopilot/test_adapters.py` + `test_platform_detect.py` pasan. |
| 8 | `pytest tests/unit/autopilot/test_context_budget.py` pasa. |
| 9 | Sin tests nuevos de runtime (solo reconciliación de skills); gate de coherencia. |
| 10 | `pytest tests/unit/autopilot/test_doctor.py` pasa. |
| 11 | Evals documentados y reproducibles. |
| 12 | Instalación limpia y desinstalación limpia validadas manualmente. |

---

## 5. Fixtures Compartidos (propuesta)

```python
# tests/unit/autopilot/conftest.py
import pytest
from pathlib import Path
from cortex.autopilot.state_store import StateStore
from cortex.autopilot.models import AutopilotSessionState

@pytest.fixture
def tmp_workspace(tmp_path):
    """Crea un workspace temporal con estructura mínima."""
    (tmp_path / ".cortex").mkdir()
    (tmp_path / ".cortex" / "workspace.yaml").write_text("layout_version: 2\n")
    return tmp_path

@pytest.fixture
def state_store(tmp_workspace):
    return StateStore(tmp_workspace / ".cortex")

@pytest.fixture
def sample_state(tmp_workspace):
    return AutopilotSessionState(
        project_root=str(tmp_workspace),
        workspace_root=str(tmp_workspace / ".cortex"),
    )
```

---

## 6. Regresión del CLI Histórico

- **Comando**: `pytest tests/unit/cli/test_main.py -q`
- **Frecuencia**: en cada fase que toque `cortex/cli/main.py` (Fase 3 y 5).
- **Regla**: si un test del CLI histórico falla, la fase no está completa.

---

## 7. Cobertura Mínima

| Módulo | Cobertura mínima esperada |
|--------|---------------------------|
| `cortex/autopilot/models.py` | 100% |
| `cortex/autopilot/state_store.py` | 100% |
| `cortex/autopilot/registry.py` | 100% |
| `cortex/autopilot/service.py` | ≥ 90% |
| `cortex/autopilot/detectors/*.py` | ≥ 85% |
| `cortex/autopilot/policies/*.py` | ≥ 85% |
| `cortex/autopilot/session_builder.py` | ≥ 85% |
| `cortex/autopilot/cli.py` | ≥ 80% |
| `cortex/autopilot/mcp_tools.py` | ≥ 80% |
| `cortex/autopilot/adapters/*.py` | ≥ 75% |

---

## 8. Herramientas

- **pytest** (ya en uso).
- **pytest-cov** para cobertura (opcional, no agregar si no está).
- **freezegun** o `time_machine` para tests determinísticos de timestamp (opcional).
- **Monkeypatch** de pytest para entorno y filesystem.

---

*Fin de la estrategia de testing.*
