<div align="center">

# Contribuir a Cortex

¡Gracias por tu interés! Somos un proyecto open-source enfocado en **DevSecDocOps Governance para AI Agents**. Esta guía cubre todo lo que necesitás saber para contribuir efectivamente.

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
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Instalar pre-commit hooks (obligatorio)
pre-commit install
```

Para verificar que todo está bien:

```bash
ruff check .
pytest
mypy cortex/
```

Si los tres pasan sin errores, estás listo. 🎉

---

## Arquitectura del Proyecto

Cortex sigue una arquitectura modular en capas:

```
┌─────────────────────────────────────┐
│         CLI Layer (Typer)           │  ← Interfaz usuario
├─────────────────────────────────────┤
│       Core Orchestrator             │  ← AgentMemory (core.py)
├──────────────┬──────────────────────┤
│   Episodic   │   Semantic Memory    │  ← Capas de memoria
│  (ChromaDB)  │  (Markdown Vault)    │
├──────────────┴──────────────────────┤
│     Retrieval Engine (Hybrid RRF)   │  ← Fusión de resultados
├──────────────┬──────────────────────┤
│     ONNX     │   Context Enricher   │  ← Embeddings + Contexto
│   Embedder   │  (Proactive Inject)  │
├──────────────┴──────────────────────┤
│          MCP Server Layer           │  ← Integración IDE
└─────────────────────────────────────┘
```

**Módulos clave y su responsabilidad:**

| Módulo                         | Responsabilidad                                                              |
| ------------------------------ | ---------------------------------------------------------------------------- |
| `core.py`                      | Orquestador principal (`AgentMemory`). Solo delega, nunca lógica de negocio. |
| `episodic/memory_store.py`     | Interfaz con ChromaDB. Almacena eventos: CI logs, PR summaries.              |
| `semantic/vault_reader.py`     | Lee archivos Markdown del Vault (Obsidian-compatible).                       |
| `retrieval/hybrid_search.py`   | RRF cross-source: episódico y semántico compiten en ranking unificado.       |
| `embedders/onnx_embedder.py`   | Backend default (<1ms, sin deps pesadas).                                    |
| `enricher/context_enricher.py` | Analiza archivos modificados y sugiere contexto proactivamente.              |
| `cli/main.py`                  | App Typer. Lógica mínima aquí, delegar al core.                              |

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

| Elemento            | Convención                       | Ejemplo                             |
| ------------------- | -------------------------------- | ----------------------------------- |
| Funciones/variables | `snake_case`                     | `retrieve_memory()`                 |
| Clases              | `PascalCase`                     | `AgentMemory`                       |
| Constantes          | `UPPER_SNAKE`                    | `DEFAULT_TOP_K`                     |
| Archivos            | `snake_case`                     | `hybrid_search.py`                  |
| Tests               | `test_<modulo>_<comportamiento>` | `test_retrieval_fuses_both_sources` |

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
```

Un commit = un cambio lógico. PRs pequeños y enfocados siempre ganan.

---

## Testing

**Objetivo de coverage: >85%.** Nunca hacer merge de un PR que lo baje.

```bash
pytest                                          # Suite completa
pytest --cov=cortex --cov-report=term-missing  # Con coverage
pytest tests/test_retrieval/ -v                # Un módulo específico
pytest -k "rrf"                                # Por nombre de test
```

**Qué hace un buen test:**

- Sigue el patrón **Arrange / Act / Assert**
- Tiene nombre descriptivo: `test_hybrid_search_fuses_results_from_both_sources`
- Incluye docstring si el caso no es obvio (especialmente para regresiones)
- Usa los fixtures de `conftest.py`, no crea dependencias ad-hoc

---

## Áreas de Contribución

### Good First Issues _(para empezar)_

Buscá el label `good-first-issue` en los issues: pequeños bug fixes, mejoras en docs, tests adicionales, o mejoras en mensajes de error.

### Help Wanted _(contributors experimentados)_

| Área               | Feature                                              | Complejidad |
| ------------------ | ---------------------------------------------------- | ----------- |
| **Almacenamiento** | Backend Qdrant como alternativa a ChromaDB           | Media-Alta  |
| **Búsqueda**       | Hybrid Search mejorado (BM25 + Dense vectorial real) | Media       |
| **Visualización**  | WebGraph interactivo de conexiones entre memorias    | Alta        |
| **Ecosistema**     | Plugins nativos para CrewAI, LangChain, AutoGen      | Media       |
| **Performance**    | Suite oficial de benchmarks vs competidores          | Media-Baja  |

### Roadmap

```
Q2 2026: Stabilization — 90%+ coverage, Docker image, MkDocs site
Q3 2026: Ecosystem     — Qdrant, CrewAI/LangChain plugins, VS Code extension
Q4 2026: Enterprise    — Cortex Cloud beta, RBAC, audit logs, SSO/SAML
```

---

## Comunidad y Soporte

**¿Necesitás ayuda?** Antes de abrir un issue, revisá el README y buscá en issues existentes. Para preguntas generales usá **Discussions**.

**Para reportar un bug**, incluí: descripción del problema, pasos para reproducirlo, comportamiento esperado vs actual, y tu entorno (OS, Python version, Cortex version). Adjuntá logs o error traces si los tenés.

**Para proponer una feature**, describí el problema que resuelve, la solución que imaginás, y si consideraste alternativas.

---

---

<div align="center">

Al contribuir, acordás que tus aportes serán licenciados bajo la **MIT License** de este repositorio.

_Contribuir a open-source es un acto de generosidad. Valoramos calidad sobre cantidad, PRs pequeños y enfocados, preguntas sobre suposiciones, y empatía con usuarios y otros devs._

**Gracias por ser parte de Cortex.**

</div>

---

---
