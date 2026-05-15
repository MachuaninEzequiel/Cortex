---
title: Roadmap post-early-adopters — 5 ítems para Cortex 0.5.x
date: 2026-05-13
target_release: 0.5.0
status: planificado
audience: Agente Cortex / dev humano que retome el desarrollo después de la reunión con los early adopters
prerequisitos: Cortex 0.4.0 desplegado y validado con los dos primeros adopters
---

# Roadmap post-early-adopters — 5 ítems para 0.5.x

Estos 5 items son la deuda **archivada** durante Olas 0-4 porque no eran bloqueantes para la reunión con los dos primeros early adopters el 2026-05-XX, pero **deben** atacarse antes del segundo onboarding masivo. Cada item está desarrollado al mismo nivel que los planes de `docs/olas/` para que el próximo agente lo pueda ejecutar sin contexto.

## Cómo usar este documento

1. Leer la sección "Contexto operativo" al final.
2. Elegir uno de los 5 items según prioridad técnica (sugerido: orden listado abajo).
3. Crear una rama feature `feature/0.5.x-roadmap-<slug>` y ejecutar la sección "Plan técnico" del item elegido.
4. Marcar checklist al final del item.
5. Mover el item resuelto a un archivo de historial (`docs/roadmap/closed/`) para mantener este doc limpio.

## Índice

| # | Item | Severidad | Esfuerzo |
|---|------|-----------|----------|
| 1 | Empty-query transport pattern fix (ex weakness #2) | Media-alta | 1-2 días |
| 2 | `EmbedderFactory` adoption + remove dup en runtime | Media | 2-3 días |
| 3 | Domain detection extensible por config | Baja-media | 1 día |
| 4 | CLI monolithic split (`cli/main.py` → módulos) | Media | 2-3 días |
| 5a | ~~Pi sync mechanism~~ | ✅ CERRADO en Tripartita Refinada (Plan 05) | — |
| 5b | Smoke suite real (tests/smoke/scenarios + workflow CI nightly) | Media | 1-2 días |

Total estimado restante: ~7-10 días de trabajo focal de un agente.

## Cerrados en 0.5.x (Tripartita Refinada)

| # | Item | Fecha | Referencia |
|---|------|-------|------------|
| 5a | Pi sync mechanism (`PiAdapter.sync_canonical_subagents` + CLI flag `--sync-canonical`) | 2026-05-14 | `docs/agents/implementacion/05-ide-pi.md` |

---

## 1. Empty-query transport pattern fix

### Objetivo

Eliminar el patrón `episodic.search("", top_k=N)` que se usa hoy para aproximar "listar todas las memorias" en el ContextEnricher. El embedder rechaza el string vacío con excepción, la excepción se traga con `try/except` ancho, y los grafos de co-occurrence + typed-graph quedan **silenciosamente vacíos** — el ranking pierde una estrategia entera sin que nadie se entere.

### Contexto y por qué se postpuso

Detectado en `docs/architecture/release-2-known-weaknesses.md` weakness #2 (release 2). Durante Olas 0-4 se evaluó:
- **Impacto real:** el enricher sigue funcionando con las otras 4 estrategias (topic, files, keywords, pr_title). Para sesiones cortas de adopters early no se nota. El graph boost solo destaca cuando hay >50 memorias acumuladas.
- **Costo del fix:** requiere agregar **una API nueva** al store episódico (`list_all`), conectarla en 2 puntos del enricher, agregar tests que verifiquen que con N memorias guardadas el typed graph tiene N nodos. Es trabajo de un release minor.

Decisión Ola 4: scoped out, archivado acá. Fix entra en 0.5.0 como primer item porque desbloquea quality de retrieval para adopters con >2 semanas de uso.

### Archivos a tocar

- `cortex/episodic/memory_store.py` — agregar método público `list_all`.
- `cortex/context_enricher/co_occurrence.py` — `_build_co_occurrence` consume `list_all`.
- `cortex/context_enricher/enricher.py` — `_build_typed_graph` consume `list_all`.
- `tests/unit/episodic/test_memory_store.py` — test del nuevo método.
- `tests/unit/context_enricher/test_enricher.py` (o `test_co_occurrence.py` si existe) — tests del graph populated.

### Plan técnico

**Paso 1 — Agregar `EpisodicMemoryStore.list_all`** (`cortex/episodic/memory_store.py`):

Firma propuesta:
```python
def list_all(
    self,
    *,
    branch: str | None = None,
    memory_type: str | None = None,
    limit: int | None = None,
) -> list[MemoryEntry]:
    """Return all stored episodic memories without an embedding query.

    Read directly from the Chroma collection via ``self._collection.get()``,
    bypassing the embedder entirely. Filters apply via ``where=`` clauses.
    """
```

Implementación: usar `self._collection.get(where=..., limit=limit, include=["documents", "metadatas"])` y mapear con `_deserialize_metadata`.

Cubrir 3 path:
- Sin filtros → todas las memorias.
- Con `branch="main"` → filtra por `metadata.branch`.
- Con `memory_type="session"` → filtra por `metadata.memory_type`.

**Paso 2 — Reemplazar uso en co_occurrence**:

Buscar en `cortex/context_enricher/enricher.py` y `cortex/context_enricher/co_occurrence.py` cualquier `self.episodic.search("", ...)` y reemplazar con `self.episodic.list_all(limit=...)`.

Eliminar los `try/except Exception` que tragaban el error del embedder. Si `list_all` falla (problema real de Chroma), debe propagarse — el agente puede recuperarse.

**Paso 3 — Tests del path activo**:

```python
def test_typed_graph_populates_with_real_memories(episodic_store, ...):
    # Agregar 10 memorias con co-occurrence files
    for i in range(10):
        episodic_store.add(content=f"x{i}", files=["a.py", "b.py"])

    enricher = ContextEnricher(episodic=episodic_store, semantic=...)
    work = WorkContext(changed_files=["a.py"])
    result = enricher.enrich(work)

    # Antes del fix: graph vacío, sin co-occurrence boost.
    # Después del fix: items boosted por co-occurrence.
    boosted = [item for item in result.items if "co_occurrence" in item.matched_by]
    assert boosted, "co-occurrence boost no se aplica con memorias reales"
```

**Paso 4 — Actualizar known-weaknesses**:

En `docs/architecture/release-2-known-weaknesses.md`, mover el item #2 de "SCOPED OUT" a "RESOLVED" con referencia al PR.

### Criterio de cierre

- [ ] `EpisodicMemoryStore.list_all` implementado con 3 paths (sin filtro / por branch / por memory_type).
- [ ] Tests del método nuevo: 3+ casos verdes.
- [ ] `_build_co_occurrence` y `_build_typed_graph` consumen `list_all`; ya no usan `search("")`.
- [ ] Test que verifica boost activo con N memorias reales (no mocked).
- [ ] `release-2-known-weaknesses.md` #2 marcado RESOLVED.
- [ ] Suite global verde.

### Esfuerzo estimado

1-2 días. La API es simple, los puntos de uso son 2, los tests requeridos son ~5.

---

## 2. `EmbedderFactory` adoption en runtime — eliminar duplicación de embedder

### Objetivo

Migrar `EpisodicMemoryStore` y `VaultReader` para que reciban un `EmbedderProtocol` en lugar de strings (`embedding_model`, `embedding_backend`). Adoptar el factory paralelo (`cortex/embedders/`) que ya existe pero **no se usa** en runtime principal. Eliminar `cortex/episodic/embedder.py` o convertirlo en wrapper deprecated.

### Contexto y por qué se postpuso

Documentado en `docs/review/cortex-save-state.md` §11.2. Hay **dos sistemas de embedders paralelos** hoy:

- `cortex/episodic/embedder.py` — `Embedder` clase concreta, usada por `EpisodicMemoryStore` y `VaultReader` directamente (instanciando desde strings).
- `cortex/embedders/` — Factory + Protocol + 3 backends concretos (ONNX, local, OpenAI), bien diseñado pero **no se invoca en runtime principal**.

La coexistencia es intencional para garantizar que episodic + semantic compartan el mismo vector space (mismo modelo, mismo backend, mismas dimensiones). Pero deja deuda visible: dos clases que hacen lo mismo, una usada y otra preparada-pero-no-adoptada.

Decisión Ola 4: el refactor de adopción es trabajo grande (3 clases públicas afectadas, tests de fixtures, eventual cleanup de un archivo entero). No entró en Olas 0-4. Va a 0.5.0 porque es deuda visible para cualquier dev externo que mire el codebase.

### Archivos a tocar

- `cortex/embedders/__init__.py` — asegurar que `EmbedderFactory.create()` es la API canónica.
- `cortex/embedders/base.py` — `EmbedderProtocol` ya existe.
- `cortex/episodic/memory_store.py` — `__init__` recibe `embedder: EmbedderProtocol` en lugar de `embedding_model`/`embedding_backend`.
- `cortex/semantic/vault_reader.py` — idem.
- `cortex/core.py` — `AgentMemory.__init__` construye el embedder via `EmbedderFactory` y lo pasa a los dos stores.
- `cortex/episodic/embedder.py` — convertir en wrapper deprecated o eliminar (decisión: deprecated wrapper con `DeprecationWarning` para evitar breakage de consumidores externos).
- `tests/unit/episodic/test_memory_store.py` — fixture `episodic_store` recibe embedder mockeado.
- `tests/unit/semantic/test_vault_reader.py` — idem.
- `tests/unit/embedders/test_embedder_contract.py` — ya verifica el contrato; agregar test de integración que confirma que `AgentMemory` construye un solo embedder y lo comparte.

### Plan técnico

**Paso 1 — Confirmar `EmbedderFactory` listo**:

Auditar `cortex/embedders/factory.py`:
- `EmbedderFactory.create(model_name, backend) -> EmbedderProtocol` retorna instancia.
- Registry tiene `onnx`, `local`, `openai`.
- Backend `onnx` por default.

**Paso 2 — Migrar `EpisodicMemoryStore`**:

Antes:
```python
def __init__(self, persist_dir, embedding_model, embedding_backend, collection_name):
    self.embedder = Embedder(model_name=embedding_model, backend=embedding_backend)
    ...
```

Después:
```python
def __init__(
    self,
    persist_dir: str,
    embedder: EmbedderProtocol,
    collection_name: str = "cortex_episodic",
):
    self.embedder = embedder
    ...
```

Eliminar import de `cortex.episodic.embedder.Embedder`.

**Paso 3 — Migrar `VaultReader`** análogamente.

**Paso 4 — Construir el embedder en `AgentMemory.__init__`**:

```python
from cortex.embedders import EmbedderFactory

self.embedder = EmbedderFactory.create(
    model_name=self.config.episodic.embedding_model,
    backend=self.config.episodic.embedding_backend,
)
self.episodic = EpisodicMemoryStore(
    persist_dir=str(self._runtime_episodic_dir),
    embedder=self.embedder,
    collection_name=self.config.episodic.collection_name,
)
self.semantic = VaultReader(
    vault_path=str(self._vault_path_resolved),
    embedder=self.embedder,
)
```

Resultado: un solo embedder instanciado, compartido. Vector space garantizado sin acoplar a la implementación.

**Paso 5 — Decisión sobre `cortex/episodic/embedder.py`**:

Opciones:
- **A (limpio):** eliminar el archivo. Cualquier consumidor externo se rompe; documentar en CHANGELOG breaking change.
- **B (compat):** convertir el archivo en un wrapper que importa desde `cortex.embedders` y emite `DeprecationWarning`. Menos invasivo, deja path de migración.

Sugiero **B** para 0.5.0 (no romper API pública sin warning). Eliminación dura en 0.6.0.

**Paso 6 — Tests**:

- Modificar `tests/conftest.py` fixture `episodic_store` para usar `EmbedderFactory.create` o un `MockEmbedder` que cumple `EmbedderProtocol`.
- Agregar test en `tests/unit/embedders/test_embedder_contract.py`:
  ```python
  def test_agent_memory_shares_single_embedder(tmp_path):
      """AgentMemory must construct ONE embedder and share it across stores."""
      _make_workspace(tmp_path)
      mem = AgentMemory(config_path=tmp_path / ".cortex" / "config.yaml")
      assert mem.episodic.embedder is mem.semantic._embedder
  ```

### Criterio de cierre

- [ ] `EpisodicMemoryStore.__init__` recibe `embedder: EmbedderProtocol`.
- [ ] `VaultReader.__init__` recibe `embedder: EmbedderProtocol`.
- [ ] `AgentMemory.__init__` instancia el embedder una sola vez via `EmbedderFactory` y lo pasa a ambos stores.
- [ ] `cortex/episodic/embedder.py` convertido en wrapper deprecated con `DeprecationWarning`.
- [ ] Test "shared embedder" verde.
- [ ] Tests existentes (fixtures `episodic_store`, `vault_reader`) adaptados al nuevo contrato.
- [ ] CHANGELOG documenta el cambio como breaking (firma de los dos stores).
- [ ] Suite global verde.

### Esfuerzo estimado

2-3 días. Cambio de superficie en 3 clases públicas + adaptación de ~10 tests + CHANGELOG.

---

## 3. Domain detection extensible por config

### Objetivo

Permitir que adopters extiendan `cortex/context_enricher/domain_detector.py` con sus propios dominios (fintech, healthcare, agro, edtech, etc.) vía `config.yaml`, sin tocar código.

### Contexto y por qué se postpuso

Hoy `DOMAIN_RULES` es un dict hardcoded con 12 dominios genéricos (auth, database, api, security, payments, ui, testing, infrastructure, data, i18n, logging, configuration). Para verticals específicas:
- **Fintech:** transactions, ledger, KYC, AML, settlement.
- **Healthcare:** patient, ICD-10, HIPAA, EHR, prescription.
- **Agro:** lote, cultivo, agroquimico, cosecha.

Estos dominios no aparecen en la lista, por lo que el detector cae al embedding fallback con confidence baja. Resultado: enricher trata el código vertical-specific como "no domain detected" y pierde una señal de retrieval.

No bloquea adopters generales (web/SaaS). Sí bloquea adopters en verticals específicas — y los segundos onboarders después de la reunión inicial probable que vengan de algún vertical.

### Archivos a tocar

- `cortex/context_enricher/config.py` — agregar campo `custom_domains` a `ContextEnricherConfig`.
- `cortex/context_enricher/domain_detector.py` — `DomainDetector.__init__` acepta `custom_domains` y los mergea con `DOMAIN_RULES`.
- `cortex/core.py::_get_enricher_config` — leer `context_enricher.custom_domains` del config raw.
- `cortex/setup/templates.py::render_config_yaml` — agregar comentario en el template indicando cómo extender.
- `tests/unit/context_enricher/test_domain_detector.py` — tests del merge + detect con custom domain.
- `docs/guides/configuration-reference.md` — documentar la opción.

### Plan técnico

**Paso 1 — Schema del custom_domains**:

```yaml
# config.yaml
context_enricher:
  custom_domains:
    fintech:
      file_patterns: [transaction, ledger, settlement, kyc, aml]
      keywords: [debit, credit, balance, transfer, fee, fraud, chargeback]
    healthcare:
      file_patterns: [patient, ehr, prescription, hipaa]
      keywords: [diagnosis, medication, dose, allergy, comorbidity]
```

**Paso 2 — Modelo Pydantic**:

```python
# cortex/context_enricher/config.py
class CustomDomainRule(BaseModel):
    file_patterns: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

class ContextEnricherConfig(BaseModel):
    ...
    custom_domains: dict[str, CustomDomainRule] = Field(default_factory=dict)
```

**Paso 3 — Merge en `DomainDetector`**:

```python
class DomainDetector:
    def __init__(self, custom_domains: dict[str, CustomDomainRule] | None = None):
        self.rules = dict(DOMAIN_RULES)  # base
        if custom_domains:
            for name, rule in custom_domains.items():
                self.rules[name] = {
                    "file_patterns": rule.file_patterns,
                    "keywords": rule.keywords,
                }
```

**Paso 4 — Cablear en `core.py`**:

`_get_enricher_config` ya construye `ContextEnricherConfig` desde raw YAML — el `custom_domains` viene por default.

**Paso 5 — Tests**:

```python
def test_custom_domain_detected():
    detector = DomainDetector(custom_domains={
        "fintech": CustomDomainRule(
            file_patterns=["transaction", "ledger"],
            keywords=["debit", "credit"],
        )
    })
    match = detector.detect(
        files=["src/transactions/transfer.py"],
        keywords=["debit", "balance"],
    )
    assert match.domain == "fintech"
    assert match.confidence > 0.5

def test_custom_overrides_base_with_same_name():
    """User can override a built-in domain by re-defining it."""
    detector = DomainDetector(custom_domains={
        "payments": CustomDomainRule(
            file_patterns=["custom-payments"],
            keywords=["specific-token"],
        )
    })
    # User's rule replaces the base 'payments' rule.
    assert detector.rules["payments"]["keywords"] == ["specific-token"]
```

### Criterio de cierre

- [ ] `CustomDomainRule` agregado a `cortex/context_enricher/config.py`.
- [ ] `ContextEnricherConfig.custom_domains` añadido al schema.
- [ ] `DomainDetector` acepta y mergea custom domains.
- [ ] 3 tests pasan: detect con custom, override de built-in, sin custom (base preservado).
- [ ] Template `render_config_yaml` incluye comentario de cómo extender.
- [ ] `docs/guides/configuration-reference.md` documenta el feature.
- [ ] Suite global verde.

### Esfuerzo estimado

1 día. Cambio acotado (1 modelo Pydantic + 1 modificación de DomainDetector + tests + doc).

---

## 4. CLI monolithic split (`cli/main.py` → módulos)

### Objetivo

Romper `cortex/cli/main.py` (1738 líneas, 30+ comandos top-level + 4 sub-apps embebidos) en 5-7 módulos especializados por área. **Sin cambiar la API pública** (el set de comandos visibles para el usuario es idéntico).

### Contexto y por qué se postpuso

Documentado en `docs/review/cortex-save-state.md` §11.8. El archivo es difícil de navegar (1738 líneas), las regresiones cuestan diagnosticar, y los reviewers no leen el monolito entero. Sub-apps ya existen como pattern (`webgraph_app`, `autopilot_app`, `pr_context_app`, `hu_app`) — solo hay que extender ese pattern a los comandos top-level.

No bloquea adopters (la CLI funciona perfectamente). Sí bloquea a colaboradores nuevos: la barrera de entrada para tocar un comando es leer el monolito.

Decisión Ola 4: refactor mecánico pero invasivo. No entró en Olas 0-4 porque no agrega features ni resuelve bugs. Va a 0.5.0 como mantenibilidad.

### Archivos a tocar (final state)

Estructura propuesta:
```
cortex/cli/
├── __init__.py
├── main.py              ← entrypoint, solo bootstrap + add_typer de cada sub-app
├── setup_cli.py         ← cortex setup {agent,pipeline,full,webgraph,enterprise}
├── memory.py            ← search, context, remember, forget, stats, sync-vault
├── workflow.py          ← create-spec, save-session, agent-guidelines
├── docs_pipeline.py     ← verify-docs, validate-docs, index-docs
├── enterprise.py        ← org-config, promote-knowledge, review-knowledge, sync-enterprise-vault, memory-report
├── doctor_cli.py        ← doctor command
├── ide.py               ← inject, sync-ide, install-skills, install-ide, mcp-server, mcp-serve
```

Sub-apps existentes (`autopilot`, `webgraph`, `pr-context`, `hu`) se mantienen donde están.

### Plan técnico

**Paso 1 — Auditoría inicial**:

Listar los 30+ `@app.command()` en `cli/main.py` y mapearlos a los módulos propuestos. Confirmar:
- Imports compartidos (yaml, json, typer, AgentMemory, WorkspaceLayout, etc.).
- Helpers privados compartidos (`_load_memory`, `_get_staged_files`, etc.) → moverlos a `cortex/cli/_helpers.py`.
- `_DEFAULT_CONFIG` constante → mover a `cortex/cli/_helpers.py`.

**Paso 2 — Extract refactor por módulo, uno a la vez**:

Por cada módulo, en orden de cohesión más simple a más compleja:
1. `cortex/cli/setup_cli.py` (5 comandos cohesivos, ya tienen una sub-typer-app interna).
2. `cortex/cli/ide.py` (5 comandos, todos invocan `cortex.ide.inject`).
3. `cortex/cli/workflow.py` (3 comandos).
4. `cortex/cli/docs_pipeline.py` (3 comandos).
5. `cortex/cli/memory.py` (6 comandos).
6. `cortex/cli/enterprise.py` (5 comandos).
7. `cortex/cli/doctor_cli.py` (1 comando).

Cada módulo expone un `app: typer.Typer` (Typer "command group" embebido) que el `main.py` importa y agrega via `app.add_typer(module.app, name=None)` — `name=None` hace que los comandos aparezcan como top-level, manteniendo la API pública.

**Paso 3 — `main.py` final reducido**:

```python
# cortex/cli/main.py — solo bootstrap + add_typer
import typer
from cortex.cli.setup_cli import app as setup_app
from cortex.cli.memory import app as memory_app
from cortex.cli.workflow import app as workflow_app
# ... etc

app = typer.Typer(name="cortex", help="...")
app.callback()(_root_callback)
app.add_typer(setup_app, name="setup")
app.add_typer(memory_app)  # commands appear at top level
app.add_typer(workflow_app)
app.add_typer(docs_pipeline_app)
app.add_typer(enterprise_app)
app.add_typer(doctor_app)
app.add_typer(ide_app)
app.add_typer(webgraph_app, name="webgraph")
app.add_typer(autopilot_app, name="autopilot")
# ... pr-context, hu sub-apps preservados
```

Target final: `main.py` < 150 líneas.

**Paso 4 — Tests existentes intactos**:

Toda la suite de `tests/unit/cli/test_main.py` y `tests/unit/cli/test_context.py` debe seguir verde sin tocar — el split es semántico equivalente.

Agregar un test de smoke al final que verifica que **todos** los comandos siguen registrados:

```python
def test_all_top_level_commands_registered():
    """Smoke test post-split: la API pública sigue intacta."""
    from cortex.cli.main import app
    expected = {
        "setup", "init", "doctor", "context", "save-session", "create-spec",
        "verify-docs", "validate-docs", "index-docs", "search", "remember",
        "forget", "stats", "sync-vault", "inject", "sync-ide", "mcp-server",
        "mcp-serve", "install-ide", "install-skills", "memory-report",
        "org-config", "promote-knowledge", "review-knowledge",
        "sync-enterprise-vault", "agent-guidelines",
        # sub-apps
        "webgraph", "autopilot", "pr-context", "hu",
    }
    registered = (
        {c.name or c.callback.__name__.replace("_", "-") for c in app.registered_commands}
        | {g.name for g in app.registered_groups if g.name}
    )
    missing = expected - registered
    assert not missing, f"Comandos perdidos en el split: {missing}"
```

**Paso 5 — Actualizar docstring de `main.py`**:

El docstring de Ola 4 listando 35+ comandos sigue válido pero se mueve mayoritariamente a `__init__.py` del módulo cli para que sea visible al hacer `python -c "import cortex.cli; help(cortex.cli)"`.

### Criterio de cierre

- [ ] `cli/main.py` reducido a < 150 líneas (solo bootstrap + add_typer).
- [ ] 7 módulos especializados creados con sus comandos.
- [ ] `_helpers.py` con helpers privados compartidos.
- [ ] Test `test_all_top_level_commands_registered` pasa.
- [ ] Suite global verde, sin modificar tests existentes.
- [ ] `--help` muestra los mismos comandos que antes.
- [ ] CHANGELOG documenta el refactor (no-breaking).

### Esfuerzo estimado

2-3 días. Refactor mecánico pero requiere cuidado con imports cruzados y helpers compartidos. Idealmente hacer **un solo PR grande** (no 7 chicos) para que el split sea reviewable como atomic operation.

---

## 5b. Smoke suite real (post-Pi-sync)

> **NOTA — split desde Item #5 original:** la parte de "Pi sync mechanism" se cerró durante Tripartita Refinada (Plan 05). Lo que sigue describe **solamente** la parte de smoke suite real, que sigue abierta. Para Pi sync ver `docs/agents/implementacion/05-ide-pi.md`.

### Objetivo

Llenar `tests/smoke/` con scenarios reales del flujo demo. Independiente del Pi sync (ya cerrado).

### Contexto y por qué se postpuso

**Smoke suite real:** `tests/smoke/` tiene infraestructura (Dockerfile, entrypoint.sh, README) pero **cero tests activos**. El roadmap original pedía smoke nightly. Durante Olas 0-4 se ejecutaron smokes manuales en `/tmp/` y se documentaron — funciona pero no es repetible automáticamente. Tripartita Refinada (Plan 07 §2) entregó tests cross-IDE como **unit parametrizados** (rápidos, sin subprocess). El smoke real con subprocess + repo limpio + setup full sigue pendiente.

### Archivos a tocar

- `tests/smoke/Dockerfile.smoke` — ya existe; verificar que tenga Python 3.11 + pipx + git.
- `tests/smoke/entrypoint.sh` — ya existe; convertir en orquestador de scenarios.
- `tests/smoke/scenarios/test_setup_full_smoke.py` — NUEVO.
- `tests/smoke/scenarios/test_mcp_server_smoke.py` — NUEVO.
- `tests/smoke/scenarios/test_autopilot_smoke.py` — NUEVO.
- `tests/smoke/scenarios/test_search_smoke.py` — NUEVO.
- `.github/workflows/ci-smoke-nightly.yml` — NUEVO workflow scheduled.

### Plan técnico

**Paso 1 — Smoke suite estructura**:

Cada test es un scenario end-to-end que:
1. Crea un repo limpio bajo `/tmp` (o `tmpfs` en Docker).
2. Corre `cortex setup full --non-interactive`.
3. Ejecuta el flujo a verificar.
4. Verifica side effects (archivos, doctor, search).
5. Limpia.

Ejemplo `test_setup_full_smoke.py`:
```python
import subprocess
from pathlib import Path

import pytest


@pytest.mark.smoke
def test_setup_full_creates_three_pillars(tmp_path: Path) -> None:
    """End-to-end: setup full en repo vacío crea los 3 pilares."""
    repo = tmp_path / "smoke-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("# smoke")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=repo,
        check=True,
        env={"GIT_AUTHOR_NAME": "smoke", "GIT_AUTHOR_EMAIL": "smoke@cortex"},
    )

    r = subprocess.run(
        ["cortex", "setup", "full", "--non-interactive", "--git-depth", "1"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr

    cortex_dir = repo / ".cortex"
    assert (cortex_dir / "config.yaml").exists()
    assert (cortex_dir / "vault").is_dir()
    assert (cortex_dir / "memory").is_dir()
    assert (cortex_dir / "webgraph" / "config.yaml").exists()
    assert (repo / ".github" / "workflows").is_dir()
    assert len(list((repo / ".github" / "workflows").glob("*.yml"))) >= 4
```

Análogos para MCP, autopilot, search.

**Paso 2 — Workflow CI nightly**:

```yaml
# .github/workflows/ci-smoke-nightly.yml
name: CI - Smoke Nightly

on:
  schedule:
    - cron: '0 4 * * *'  # 04:00 UTC daily
  workflow_dispatch:

jobs:
  smoke:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/smoke -m smoke --tb=short -v
```

**Paso 3 — Tests**:

Smoke tests: ver Paso 1. La parte de Pi sync (originalmente en este item) ya está cubierta — ver `tests/unit/test_ide_adapters.py::TestPiSyncCanonicalSubagents` (Plan 05).

### Criterio de cierre

- [ ] 4 smoke tests escritos (setup full, MCP, autopilot, search).
- [ ] Marcador `smoke` registrado en `pyproject.toml::tool.pytest.ini_options.markers` (ya está).
- [ ] `.github/workflows/ci-smoke-nightly.yml` creado con matrix de 3 versiones de Python.
- [ ] CHANGELOG documenta el feature.
- [ ] Suite global verde.

### Esfuerzo estimado

1-2 días. Solo smoke suite + CI yaml; Pi sync ya cerrado en Tripartita Refinada (Plan 05).

---

## Contexto operativo

Para el agente que retome este roadmap en una sesión futura:

1. Releé `docs/review/cortex-save-state.md` primero para recuperar el mapa mental del repo.
2. Leé `docs/olas/README.md` para entender la narrativa de cómo se llegó hasta 0.4.0.
3. Asumí Cortex 0.4.0 ya desplegado: 4 olas cerradas, 835 tests verdes, los dos primeros adopters ya tuvieron su reunión y posiblemente generaron feedback. **Antes de empezar 0.5.x, leer el feedback recopilado de los adopters** (deberá estar en `vault/sessions/` con tag `early-adopters`).
4. La regla operativa permanente del proyecto: **"dejar las cosas terminadas sin deuda técnica"**. Si arrancás un item, cerralo al 100% antes de pasar al siguiente. Si descubrís deuda nueva, agregala acá; no la dejes flotando.
5. Convención de commits: Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`). PRs pequeños y enfocados.
6. Antes de cerrar cualquier item, correr la suite completa: `python -m pytest tests/unit tests/integration tests/e2e --no-cov`. Cero failures.
7. Si en el medio del trabajo cambia el contexto de negocio (más adopters, feedback urgente, decisión estratégica), **priorizar lo que el usuario diga sobre este roadmap**. Este doc es un commitment técnico, no una orden inviolable.

## Convención para items resueltos

Cuando se cierre un item:

1. Mover su sección a `docs/roadmap/closed/0.5.x-item-<N>-<slug>.md` con un header de cierre (fecha + PR link).
2. Reducir la entrada en `docs/roadmap/post-adopters.md` a una línea en una tabla "Cerrados":

```markdown
## Cerrados en 0.5.x

| # | Item | Fecha | PR |
|---|------|-------|----|
| 1 | Empty-query transport pattern fix | 2026-MM-DD | #XX |
```

Esto mantiene el archivo activo limpio y el historial preservado.
