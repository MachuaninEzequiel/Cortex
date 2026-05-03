# Cortex Enterprise — Informe de Revisión Arquitectónica

**Fecha:** 2026-05-03  
**Alcance:** Análisis exhaustivo del proyecto Cortex v3.0 Enterprise  
**Autor:** Análisis automatizado de revisión de software  

---

## 1. Introducción al Proyecto

### 1.1 ¿Qué es Cortex?

Cortex es un **sistema de memoria cognitiva híbrida para agentes de IA**, diseñado como una plataforma de gobernanza empresarial que combate la "Amnesia de Sesión" inherente a los LLMs. Combina tres capas de memoria:

- **Capa Episódica** — ChromaDB con embeddings ONNX (<1ms latencia) para recuerdos de corto plazo
- **Capa Semántica** — Vault Markdown compatible con Obsidian para conocimiento persistente
- **Capa Enterprise** — Vault corporativo con pipelines de promoción, retrieval multi-nivel y gobernanza CI

### 1.2 Visión General del Sistema

```mermaid
graph TB
    subgraph "Entrada del Usuario"
        CLI[CLI Typer<br/>30+ comandos]
        IDE[Adaptadores IDE<br/>Cursor/VSCode/Claude/Pi/etc.]
        MCP[MCP Server<br/>stdio transport]
    end

    subgraph "Fachada Principal"
        CORE[AgentMemory<br/>core.py]
    end

    subgraph "Memoria Híbrida"
        EPI[Memoria Episódica<br/>ChromaDB + ONNX]
        SEM[Memoria Semántica<br/>VaultReader + Embeddings]
        ENT[Memoria Enterprise<br/>Retrieval Multi-nivel]
    end

    subgraph "Servicios de Dominio"
        SPEC[SpecService]
        SESS[SessionService]
        PRS[PRService]
        PROM[KnowledgePromotion]
        WIS[WorkItemService]
    end

    subgraph "Motor de Retrieval"
        RRF[HybridSearch<br/>RRF Fusión Adaptativa]
        CE[ContextEnricher<br/>Multi-estrategia]
    end

    subgraph "Pipeline DevSecDocOps"
        PO[PipelineOrchestrator]
        SEC[SecurityStage]
        LINT[LintStage]
        TEST[TestStage]
        DOC[DocumentationStage]
    end

    subgraph "Infraestructura Enterprise"
        ECFG[EnterpriseConfig<br/>org.yaml]
        EVAULT[Vault Enterprise<br/>promotion pipeline]
        EREP[Reporting Service]
    end

    CLI --> CORE
    IDE --> MCP --> CORE
    CORE --> EPI
    CORE --> SEM
    CORE --> ENT
    CORE --> SPEC
    CORE --> SESS
    CORE --> PRS
    CORE --> WIS
    SPEC --> SEM
    SESS --> SEM
    PRS --> EPI
    ENT --> ECFG
    ENT --> EVAULT
    ENT --> EREP
    EPI --> RRF
    SEM --> RRF
    RRF --> CE
    CORE --> PO
    PO --> SEC & LINT & TEST & DOC
    PROM --> EVAULT

    style CORE fill:#4a90d9,stroke:#2c5ea0,color:#fff
    style RRF fill:#e67e22,stroke:#d35400,color:#fff
    style EPI fill:#27ae60,stroke:#1e8449,color:#fff
    style SEM fill:#8e44ad,stroke:#6c3483,color:#fff
    style ENT fill:#2c3e50,stroke:#1a252f,color:#fff
```

### 1.3 Cantidad de Archivos y Módulos

| Categoría | Archivos | Descripción |
|-----------|---------|-------------|
| Núcleo Python (`cortex/`) | ~80 | Motor principal del sistema |
| Tests (`tests/`) | ~35 | Unit, integration, e2e |
| IDE Adapters (`cortex/ide/adapters/`) | 9 | Cursor, VSCode, Claude, Pi, etc. |
| Pi Environment (`cortex-pi/`) | ~20 | Agentes, skills, extensiones |
| Docs & Vault | ~30 | Guías, enterprise plans, refact specs |
| CI/CD (`.github/workflows/`) | 4 | PR, enterprise, security, release |
| Total aprox. | ~180+ | Excluyendo `.git`, `.venv`, caches |

### 1.4 Stack Tecnológico

- **Lenguaje:** Python 3.10+
- **Framework CLI:** Typer
- **Validación:** Pydantic v2
- **Vector Store:** ChromaDB (embeddings ONNX por defecto)
- **Protocolo:** MCP (Model Context Protocol) v1.2+
- **Web UI:** Flask (WebGraph)
- **Tests:** pytest + Hypothesis (property-based)
- **Linting:** Ruff
- **Type Checking:** mypy