<div align="center">

# Contribuir a Cortex

¡Gracias por tu interés! Somos un proyecto open-source enfocado en **DevSecDocOps Governance para AI Agents** con soporte **Enterprise Memory Productization**. Esta guía cubre todo lo que necesitás saber para contribuir efectivamente.

</div>

---

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Setup de Desarrollo](#setup-de-desarrollo)
- [Arquitectura del Proyecto](#arquitectura-del-proyecto)
- [Estándares de Código](#estándares-de-código)
- [Flujo de Trabajo Git](#flujo-de-trabajo-git)
- [Testing](#testing)
- [Áreas de Contribución](#áreas-de-contribución)
- [Comunidad y Soporte](#comunidad-y-soporte)

---

## Código de Conducta

Esperamos **profesionalismo, empatía y respeto** en todas las interacciones. Bienvenimos devs de todos los niveles. El feedback debe ser directo pero constructivo, y admitir errores es fuerza, no debilidad.

**Zero tolerance para:** acoso, discriminación, spam, comportamiento tóxico en PRs/issues, o intentos de introducir código malicioso. Reportar violaciones directamente a los maintainers.

---

## Setup de Desarrollo

**Prerrequisitos:** Python 3.10+, Git 2.30+, pip 22.0+

```bash
# 1. Fork el repo en GitHub, luego clonar TU fork
git clone https://github.com/TU-USUARIO/cortex.git
cd cortex
git remote add upstream https://github.com/MachuaninEzequiel/Cortex.git

# 2. Crear entorno virtual e instalar en modo desarrollo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

pip install -e ".[dev]"

# 3. Instalar pre-commit hooks (obligatorio)
pre-commit install

# 4. Verificar que todo funciona
ruff check .
pytest
mypy cortex/

# 5. (Opcional) Setup enterprise para contribuir a módulos enterprise
cortex setup enterprise --preset small-company --non-interactive
```

Si los tres checks pasan sin errores, estás listo.

---

## Arquitectura del Proyecto

Cortex sigue una arquitectura modular en capas con una capa enterprise superpuesta:

```text
┌─────────────────────────────────────┐
│         CLI Layer (Typer)           │  ← 30+ comandos, subcomandos
├─────────────────────────────────────┤
│   Facade Orchestrator & Services    │  ← core.py (Facade) + services/
├──────────────┬──────────────────────┤
│   Episodic   │   Semantic Memory    │  ← Capas de memoria
│  (ChromaDB)  │  (Markdown Vault)    │
├──────────────┴──────────────────────┤
│  Retrieval Engine (Adaptive RRF)    │  ← Fusión inteligente de resultados
├─────────────────────────────────────┤
│  Enterprise Memory Layer            │  ← org.yaml, promotion, reporting
│  (Multi-level retrieval + CI Gov)   │
├──────────────┬──────────────────────┤
│ Embedder     │  Async Context       │  ← Carga perezosa + Concurrencia
│ Factory      │  Enricher            │
├──────────────┴──────────────────────┤
│      MCP Server + WebGraph          │  ← IDE Bridge + Knowledge Graphs
└─────────────────────────────────────┘
```

**Módulos clave y su responsabilidad:**

| Módulo | Responsabilidad |
| --- | --- |
| `core.py` | Fachada principal (`AgentMemory`). Solo delega a servicios. |
| `services/` | Lógica de negocio (spec, session, pr). |
| `enterprise/config.py` | Carga y validación de `.cortex/org.yaml`. |
| `enterprise/models.py` | Modelos Pydantic de topología enterprise. |
| `enterprise/retrieval_service.py` | Retrieval multi-nivel (local + enterprise). |
| `enterprise/knowledge_promotion.py` | Pipeline de promoción auditable. |
| `enterprise/reporting.py` | Observabilidad y reporting enterprise. |
| `pipeline/` | Abstracciones formales para CI/CD y DevSecDocOps. |
| `episodic/memory_store.py` | Interfaz con ChromaDB para eventos. |
| `semantic/vault_reader.py` | Lee archivos Markdown del Vault. |
| `retrieval/hybrid_search.py` | Búsqueda adaptativa RRF con pesos dinámicos. |
| `retrieval/intent.py` | Detección de intención de búsqueda. |
| `embedders/factory.py` | Instanciación perezosa de backends. |
| `context_enricher/` | Resolución asíncrona concurrente de contexto. |
| `setup/orchestrator.py` | Orquestador de setup (Agent/Pipeline/Full/Enterprise/WebGraph). |
| `setup/enterprise_wizard.py` | Wizard interactivo para setup enterprise. |
| `webgraph/service.py` | Grafos de conocimiento + nodos enterprise. |
| `webgraph/federation.py` | Federación multi-proyecto con filtro por scope. |

---

## Estándares de Código

Usamos **Ruff** para linting/formateo y **Mypy** para type checking. Los pre-commit hooks corren esto automáticamente.

**Reglas de oro:**

- **Type hints siempre.** Toda función pública debe tener tipos explícitos.
- **Docstrings en Google Style** para funciones públicas. Incluir Args, Returns, Raises.
- **Pydantic para datos.** No usar dicts sin tipado para configuración o modelos.
- **Logging, no prints.** Usar `logger = logging.getLogger(__name__)` para debug.
- **Excepciones específicas.** Nunca capturar `Exception` a secas sin re-lanzar o loggear.
- **Comentarios que explican el _por qué_, no el _qué_.**

**Convenciones de nomenclatura:**

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Funciones/variables | `snake_case` | `retrieve_memory()` |
| Clases | `PascalCase` | `AgentMemory` |
| Constantes | `UPPER_SNAKE` | `DEFAULT_TOP_K` |
| Archivos | `snake_case` | `hybrid_search.py` |
| Tests | `test_<modulo>_<comportamiento>` | `test_retrieval_fuses_both_sources` |

**Reglas Enterprise adicionales:**

- Los modelos enterprise van en `cortex/enterprise/models.py` o `promotion_models.py`.
- Toda configuración enterprise se lee via `cortex/enterprise/config.py`, no directamente.
- Los presets se definen en `cortex/setup/enterprise_presets.py`.

---

## Flujo de Trabajo Git

```bash
# Siempre crear una rama desde main actualizado
git checkout main
git pull upstream main
git checkout -b feat/nombre-descriptivo   # o fix/, docs/, test/, refactor/
```

**Commits:** seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(retrieval): add BM25 fallback when vector search returns empty
fix(episodic): restore timestamp in memory retrieval
docs(readme): update CLI reference with new commands
test(enricher): add coverage for graph expansion strategy
feat(enterprise): add regulated-organization preset
fix(promotion): handle duplicate fingerprints in review
```

Un commit = un cambio lógico. PRs pequeños y enfocados siempre ganan.

---

## Testing

**Objetivo de coverage: >85%.** Nunca hacer merge de un PR que lo baje.

```bash
pytest                                          # Suite completa
pytest --cov=cortex --cov-report=term-missing  # Con coverage
pytest tests/unit/retrieval/ -v                # Un módulo específico
pytest -k "rrf"                                # Por nombre de test
pytest -k "enterprise"                         # Tests enterprise
```

Nuestra suite está dividida en `tests/unit/`, `tests/integration/` y `tests/e2e/`. Usamos *Hypothesis* para property-based testing en algoritmos complejos.

**Qué hace un buen test:**

- Sigue el patrón **Arrange / Act / Assert**
- Tiene nombre descriptivo: `test_hybrid_search_fuses_results_from_both_sources`
- Incluye docstring si el caso no es obvio (especialmente para regresiones)
- Usa los fixtures de `conftest.py`, no crea dependencias ad-hoc

---

## Áreas de Contribución

### Good First Issues _(para empezar)_

Buscá el label `good-first-issue` en los issues: pequeños bug fixes, mejoras en docs, tests adicionales, o mejoras en mensajes de error.

### Help Wanted (Contributors Experimentados)

| Área | Feature | Complejidad |
| --- | --- | --- |
| **Enterprise** | Mejoras en presets por industria (healthcare, fintech) | Media |
| **Retrieval** | Optimización de pesos RRF multi-nivel | Media-Alta |
| **WebGraph** | Enriquecimiento de nodos enterprise en visualización | Media |
| **Observabilidad** | Dashboard HTML/UI para `memory-report` | Media-Alta |
| **Integraciones** | Plugins para Azure DevOps, Linear, GitHub Issues | Media |
| **Migration** | Herramientas de migración desde setups legacy | Baja-Media |

### Estado del Roadmap: Enterprise Memory Productization

```text
✅ Onda 1: Fundación (Completada)
  - E1: Modelo organizacional enterprise (.cortex/org.yaml)
  - E2: Retrieval multi-nivel base (Local + Corporate)

✅ Onda 2: Operabilidad (Completada)
  - E3: Promotion pipeline de conocimiento (Manual/CI-driven)
  - E4: Gobernanza y CI enterprise (Políticas automáticas)

✅ Onda 3: Productización (Completada)
  - E5: Setup enterprise interactivo (Wizard guiado)
  - E6: Observabilidad y Reporting de salud de memoria

✅ Onda 4: Hardening (Completada)
  - E7: Presets, documentación, hardening y adopción

🔮 Siguiente: Integraciones avanzadas, dashboards visuales, plugins de terceros
```

---

## Comunidad y Soporte

**¿Necesitás ayuda?** Antes de abrir un issue, revisá el README y buscá en issues existentes. Para preguntas generales usá **Discussions**.

**Para reportar un bug**, incluí: descripción del problema, pasos para reproducirlo, comportamiento esperado vs actual, y tu entorno (OS, Python version, Cortex version). Adjuntá logs o error traces si los tenés.

**Para proponer una feature**, describí el problema que resuelve, la solución que imaginás, y si consideraste alternativas.

---

<div align="center">

Al contribuir, acordás que tus aportes serán licenciados bajo la **MIT License** de este repositorio.

_Contribuir a open-source es un acto de generosidad. Valoramos calidad sobre cantidad, PRs pequeños y enfocados, preguntas sobre suposiciones, y empatía con usuarios y otros devs._

**Gracias por ser parte de Cortex.**

</div>
