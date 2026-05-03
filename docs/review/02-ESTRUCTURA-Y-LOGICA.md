# Estructura y Lógica del Sistema

## 2. Arquitectura por Capas

Cortex sigue una **arquitectura hexagonal con fachada central** (`AgentMemory`):

```mermaid
graph TD
    subgraph "Capa de Presentación"
        CLI2[CLI<br/>cortex/cli/main.py]
        MCP2[MCP Server<br/>cortex/mcp/server.py]
        IDE2[IDE Adapters<br/>cortex/ide/]
        TUI[Tutor Engine<br/>cortex/tutor/]
    end

    subgraph "Fachada (Hexagonal Core)"
        AM[AgentMemory<br/>cortex/core.py]
        RTXC[RuntimeContext<br/>cortex/runtime_context.py]
        MDLS[Models & Config<br/>cortex/models.py<br/>cortex/core.py Pydantic]
    end

    subgraph "Capa de Dominio (Services)"
        SPS[SpecService]
        SES[SessionService]
        PRS2[PRService]
        WIS2[WorkItemService]
        KPS[KnowledgePromotion]
        REP[EnterpriseReporting]
    end

    subgraph "Capa de Infraestructura"
        EPI2[EpisodicMemoryStore<br/>cortex/episodic/]
        VW2[VaultReader<br/>cortex/semantic/]
        EBD[Embedder Factory<br/>cortex/embedders/]
        RRF2[HybridSearch<br/>cortex/retrieval/]
        CE2[ContextEnricher<br/>cortex/context_enricher/]
    end

    subgraph "Capa Enterprise"
        EC2[EnterpriseConfig<br/>cortex/enterprise/config.py]
        EM2[Enterprise Models<br/>cortex/enterprise/models.py]
        ERS[EnterpriseRetrievalService]
    end

    subgraph "Capa de Integración"
        SETP[Setup Orchestrator<br/>cortex/setup/]
        DOCC[Doctor<br/>cortex/doctor.py]
        PIN[Pipeline Orchestrator<br/>cortex/pipeline/]
        WEBG[WebGraph<br/>cortex/webgraph/]
    end

    CLI2 --> AM
    MCP2 --> AM
    IDE2 --> AM
    CLI2 --> DOCC & SETP
    AM --> EPI2 & VW2 & RRF2
    AM --> SPS & SES & PRS2 & WIS2 & KPS
    AM --> EC2 & EM2 & ERS
    EPI2 --> EBD
    VW2 --> EBD
    RRF2 --> CE2

    style AM fill:#3498db,stroke:#2980b9,color:#fff
    style EPI2 fill:#2ecc71,stroke:#27ae60,color:#fff
    style VW2 fill:#9b59b6,stroke:#8e44ad,color:#fff
    style EC2 fill:#e74c3c,stroke:#c0392b,color:#fff
```

## 3. Flujo de Datos Principal

### 3.1 Flujo de Búsqueda Híbrida (Retrieval)

```mermaid
sequenceDiagram
    participant U as Usuario/Agente
    participant C as CLI/MCP
    participant AM as AgentMemory
    participant RRF as HybridSearch
    participant ID as IntentDetector
    participant EPI as EpisodicStore
    participant SEM as VaultReader
    participant ENT as EnterpriseRetrieval

    U->>C: cortex search "login bug"
    C->>AM: retrieve(query, scope)
    AM->>RRF: search(query, top_k)
    RRF->>ID: detect_intent(query)
    ID-->>RRF: episodic_intent → boost epi_weight

    par Búsqueda Paralela
        RRF->>EPI: query_chroma(query, top_k)
        EPI-->>RRF: episodic_hits[]
    and
        RRF->>SEM: search(query, top_k)
        SEM-->>RRF: semantic_hits[]
    end

    RRF->>RRF: RRF Fusion(adaptive_weights)
    RRF-->>AM: RetrievalResult{unified_hits[]}

    opt scope == enterprise || all
        AM->>ENT: search(query, scope)
        ENT-->>AM: enterprise_hits[]
    end

    AM-->>C: RetrievalResult
    C-->>U: Resultados formateados
```

### 3.2 Flujo de Setup (Orchestrator)

```mermaid
flowchart TD
    START[Usuario: cortex setup agent] --> DETECT[ProjectDetector.detect]
    DETECT --> CTX[ProjectContext<br/>stack + ci + env]
    CTX --> MODE{SetupMode?}

    MODE -->|AGENT| AGENT_FLOW[Agent Flow]
    MODE -->|PIPELINE| PIPE_FLOW[Pipeline Flow]
    MODE -->|FULL| FULL_FLOW[Full Flow]
    MODE -->|ENTERPRISE| ENT_FLOW[Enterprise Flow]
    MODE -->|WEBGRAPH| WG_FLOW[WebGraph Flow]

    AGENT_FLOW --> CREATE_DIRS[Crear Directorios<br/>.memory/, vault/, etc.]
    CREATE_DIRS --> CREATE_CFG[Crear config.yaml]
    CREATE_CFG --> CREATE_ORG[Crear .cortex/org.yaml]
    CREATE_ORG --> CREATE_VAULT[Crear Vault Docs]
    CREATE_VAULT --> CREATE_EVAULT[Crear Enterprise Vault]
    CREATE_EVAULT --> CREATE_AG[Crear Agent Guidelines]
    CREATE_AG --> INSTALL_SKILLS[Instalar Skills]
    INSTALL_SKILLS --> INIT_MEM[Init Memory + Cold Start]
    INIT_MEM --> INSTALL_IDE[Instalar IDE Profiles]

    PIPE_FLOW --> CREATE_CFG2[Crear config.yaml]
    CREATE_CFG2 --> CREATE_ORG2[Crear .cortex/org.yaml]
    CREATE_ORG2 --> CREATE_EVAULT2[Crear Enterprise Vault]
    CREATE_EVAULT2 --> CREATE_WF[Crear GitHub Workflows]
    CREATE_WF --> CREATE_SCRIPT[Crear scripts/devsecdocops.sh]

    ENT_FLOW --> CREATE_DIRS2[Crear Directorios]
    CREATE_DIRS2 --> CREATE_CFG3[Crear config.yaml]
    CREATE_CFG3 --> CREATE_ORG3[Crear org.yaml + Presets]
    CREATE_ORG3 --> CREATE_VAULT2[Crear Vault Docs]
    CREATE_VAULT2 --> CREATE_EVAULT3[Crear Enterprise Vault]
    CREATE_EVAULT3 --> CREATE_WF2[Crear Workflows]
    CREATE_WF2 --> CREATE_SCRIPT2[Crear scripts/]
    CREATE_SCRIPT2 --> CREATE_WS[Crear workspace.yaml]

    style START fill:#3498db,stroke:#2980b9,color:#fff
    style DETECT fill:#e67e22,stroke:#d35400,color:#fff
```

### 3.3 Flujo de Gobernanza (Pipeline DevSecDocOps)

```mermaid
flowchart LR
    subgraph "CI/CD Pipeline"
        SRC[Security Stage<br/>audit_level=high] --> LNT[Lint Stage<br/>ruff check]
        LNT --> TST[Test Stage<br/>pytest --cov]
        TST --> DOCST[Doc Stage<br/>verify-docs]
    end

    SRC -->|block_on_failure=true| X1[❌ FAIL]
    LNT -->|block_on_failure=true| X2[❌ FAIL]
    TST -->|block_on_failure=true| X3[❌ FAIL]
    DOCST -->|block_on_failure=false| WARN[⚠️ WARN]

    DOCST --> OK[✅ PASS]

    style SRC fill:#e74c3c,stroke:#c0392b,color:#fff
    style LNT fill:#e67e22,stroke:#d35400,color:#fff
    style TST fill:#3498db,stroke:#2980b9,color:#fff
    style DOCST fill:#2ecc71,stroke:#27ae60,color:#fff
```

## 4. Modelo de Datos Enterprise

```mermaid
erDiagram
    OrganizationConfig {
        string name
        string slug
        OrgProfile profile
    }

    MemoryConfig {
        string mode
        string enterprise_vault_path
        string enterprise_memory_path
        bool enterprise_semantic_enabled
        RetrievalScope retrieval_default_scope
        float retrieval_local_weight
        float retrieval_enterprise_weight
    }

    PromotionConfig {
        bool enabled
        list allowed_doc_types
        bool require_review
    }

    GovernanceConfig {
        GitPolicy git_policy
        CIProfile ci_profile
        bool version_sessions_in_git
    }

    EnterpriseOrgConfig {
        int schema_version
        OrganizationConfig organization
        MemoryConfig memory
        PromotionConfig promotion
        GovernanceConfig governance
    }

    CortexConfig {
        EpisodicConfig episodic
        SemanticConfig semantic
        RetrievalConfig retrieval
        LLMConfig llm
        IntegrationsConfig integrations
    }

    MemoryEntry {
        string id
        string content
        string memory_type
        list tags
        list files
        dict metadata
    }

    RetrievalResult {
        list episodic_hits
        list semantic_hits
        list unified_hits
    }

    EnterpriseOrgConfig ||--o{ OrganizationConfig : has
    EnterpriseOrgConfig ||--o{ MemoryConfig : has
    EnterpriseOrgConfig ||--o{ PromotionConfig : has
    EnterpriseOrgConfig ||--o{ GovernanceConfig : has
    CortexConfig ||--o{ EpisodicConfig : has
    CortexConfig ||--o{ SemanticConfig : has
```

## 5. Estructura del Workspace Actual (Legacy)

```
<repo-root>/
├── config.yaml                    # Configuración principal de Cortex
├── vault/                         # Vault de conocimiento (Markdown)
│   ├── architecture.md
│   ├── auth.md
│   ├── getting_started.md
│   ├── decisions/
│   ├── runbooks/
│   ├── sessions/
│   ├── incidents/
│   ├── hu/
│   └── specs/
├── vault-enterprise/              # Vault corporativo
│   ├── README.md
│   ├── decisions/
│   ├── runbooks/
│   ├── incidents/
│   └── hu/
├── .memory/                       # ChromaDB episódico (local)
│   └── chroma/
├── .cortex/                       # Workspace de Cortex
│   ├── AGENT.md
│   ├── system-prompt.md
│   ├── org.yaml                    # Config enterprise
│   ├── workspace.yaml
│   ├── skills/
│   │   ├── cortex-sync.md
│   │   ├── cortex-SDDwork.md
│   │   └── obsidian-*/
│   ├── subagents/
│   │   ├── cortex-code-explorer.md
│   │   ├── cortex-code-implementer.md
│   │   └── cortex-documenter.md
│   ├── logs/
│   └── webgraph/
│       ├── config.yaml
│       ├── workspace.yaml
│       └── cache/
├── scripts/
│   └── devsecdocops.sh
└── .github/
    └── workflows/
```

## 6. Modelo de Ejecución Tripartito (Agentes)

```mermaid
flowchart TD
    USER[Usuario/Desarrollador] --> SYNC[cortex-sync<br/>Analista / SpecWriter]
    SYNC --> |"Spec persistida"| SDD[cortex-SDDwork<br/>Orquestador]
    
    SDD --> |"Tarea simple"| FAST[🟢 Fast Track<br/>Implementación directa]
    SDD --> |"Tarea compleja"| DEEP[🔴 Deep Track<br/>Delegación a subagentes]
    
    DEEP --> EXP[cortex-code-explorer<br/>Análisis estático]
    DEEP --> IMP[cortex-code-implementer<br/>Implementación]
    
    FAST --> SEC[Security Check]
    DEEP --> SEC
    SEC --> TSTV[Test Verification]
    TSTV --> DOCER[cortex-documenter<br/>Guardian]
    
    DOCER --> |"save-session"| VAULT[Vault<br/>Persistencia]
    DOCER --> |"remember"| MEMORY[Memoria Episódica<br/>ChromaDB]

    style SYNC fill:#3498db,stroke:#2980b9,color:#fff
    style SDD fill:#e67e22,stroke:#d35400,color:#fff
    style DOCER fill:#2ecc71,stroke:#27ae60,color:#fff
```

### Gobernanza de la cadena de agentes

El flujo tripartito está **forzado por el MCP server** mediante validación de gobernabilidad:

1. `cortex-sync` **DEBE** llamar a `cortex_sync_ticket` como primer paso (inyección de contexto vía ONNX)
2. `cortex-SDDwork` decide el track (Fast/Deep) basándose en complejidad
3. `cortex-documenter` es el cierre **obligatorio** (definition of done = documentación persistida)
4. Si `cortex_create_spec` se invoca sin `cortex_sync_ticket` previo → **rechazo técnico**