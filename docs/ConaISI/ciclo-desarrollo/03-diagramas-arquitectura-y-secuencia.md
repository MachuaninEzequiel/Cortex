# Diagramas de Arquitectura y Secuencia de Cortex

Este documento presenta dos gráficos formales de ingeniería:
1. **Diagrama de Secuencia Temporal End-to-End**: La cronología exacta de llamadas y respuestas en una sesión de desarrollo completa.
2. **Diagrama de Bloques de Arquitectura Global de Sistemas**: La estructura por capas del sistema Cortex, interconectando usuarios, CLIs de agentes, modelos locales y remotos, micro-decisiones de SystemOne y el almacenamiento persistente.

---

## 1. Diagrama de Secuencia Temporal End-to-End

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Desarrollador (Humano)
    participant Host as Host IDE / CLI (Antigravity / Pi / Claude)
    participant Gate as Utterance Gate (SystemOne)
    participant MCP as Servidor MCP (cortex-mcp v2.2)
    participant Router as Model Router (SystemOne)
    participant LLM as Subagente Asignado (LLM Remoto / Local)
    participant Mem as Motor Híbrido RRF (cortex-core / embed)
    participant Doc as Documenter Engine (cortex-app)
    participant Disk as Almacén Local (.cortex/)

    %% Paso 1: Arranque y Detección
    Dev->>Host: Abre CLI/IDE en el proyecto
    Host->>Disk: WorkspaceLayout::discover()
    Host->>Host: HostDetector::detect_host() & Escudo de Políticas ToS
    Host->>Disk: CLI Model Discovery (lectura pasiva de modelos)
    Host->>MCP: Lanza cortex-mcp (stdio rmcp v2.2)
    MCP-->>Host: Server ready (32 tools catalogadas)

    %% Paso 2: Entrada del Dev y Utterance Gate
    Dev->>Host: Prompt: "Implementar validación de tokens JWT en el middleware"
    Host->>Gate: classify_utterance(prompt)
    Note over Gate: Micro-decisión sub-10ms:<br/>Choice work: implement<br/>needs_session: alto<br/>worth_remembering: alto
    Gate-->>Host: Resultado: implement (Disparar apertura de sesión)

    %% Paso 3: Top del Sandwich - Sync y Apertura
    Host->>MCP: cortex_session_open(spec_id="jwt-auth", summary="...")
    MCP->>Disk: Escribe .cortex/sessions/<session_id>.yaml (start_commit=HEAD)
    MCP-->>Host: SessionRecord creado

    %% Paso 4: Rebuild the Menu y Ruteo de Modelo
    Host->>MCP: cortex_session_status()
    MCP->>Router: rebuild_specialist_menu(checkpoints=0)
    Note over Router: Sin checkpoints previos:<br/>Especialista recomendado: Architect (cortex-code-designer)
    Router-->>MCP: available_specialists=[Architect(rec), Implementer, ...]
    MCP-->>Host: Estado vivo de sesión + menú dinámico

    Host->>Router: evaluate_model_routing(role="architect", candidates)
    Note over Router: Selección de modelo autorizada por Host Policy:<br/>Google Antigravity hacia google:gemini-2.5-pro<br/>Pi hacia openrouter:anthropic/claude-3.5-sonnet
    Router-->>Host: Decision: model_id seleccionado (confidence >= 0.85)

    %% Paso 5: Recuperación Híbrida y Squeeze
    Host->>MCP: cortex_context(query="JWT middleware security")
    MCP->>Mem: Búsqueda Semántica (BM25 en Vault) + Vectorial (vectors.v3.bin)
    Note over Mem: Fusión RRF (k=60):<br/>Docs 'tier: archive' atenuados al 20%<br/>Search Squeeze poda ruido
    Mem-->>MCP: UnifiedHits compactados y libres de distracción
    MCP-->>Host: ContextPack estructurado con punteros canónicos

    %% Paso 6: Implementación y Checkpoints
    Host->>LLM: Generar código y tests unitarios con el contexto
    LLM-->>Host: Modificaciones en src/auth.rs y tests/auth_test.rs
    Host->>Dev: Propuesta / diff de código generado
    Dev->>Host: Aprueba y ejecuta tests locales

    Host->>MCP: cortex_session_checkpoint(claims=["JWT signature validated", "Expiry check enforced"], touched=["src/auth.rs"])
    MCP->>Disk: Actualiza checkpoints en el SessionRecord YAML
    MCP-->>Host: Checkpoint registrado

    %% Paso 7: Auditoría y Verification Gate
    Host->>MCP: cortex_verify_session_claims(session_id)
    MCP->>Doc: VerificationGate::verify(git_diff, test_results)
    Doc-->>MCP: Claims verificados exitosamente
    MCP-->>Host: Claims confirmados (confidence=verified)

    %% Paso 8: Bottom del Sandwich - Documenter y Cierre
    Dev->>Host: "Listo, cerremos el ticket"
    Host->>Gate: classify_utterance("Listo, cerremos el ticket")
    Gate-->>Host: Resultado: done (Disparar Documenter)

    Host->>MCP: cortex_finish_session(session_id)
    MCP->>Doc: Reconstruct(start_commit, HEAD, checkpoints)
    Doc->>Disk: Chequeo de contradicciones contra ADRs existentes
    Doc->>MCP: Genera notas de sesión y borrador de nuevo ADR
    
    MCP->>Disk: cortex_write_doc(doc_type="adr", payload={...})
    MCP->>Disk: cortex_write_doc(doc_type="session", payload={...})

    MCP->>Gate: evaluate_worth_remembering(learnings)
    Note over Gate: Filtro de ruido:<br/>Solo aprendizajes y soluciones reales persisten
    Gate-->>MCP: allow_remember = true

    MCP->>Disk: Escribe en .cortex/memory/ (JSONL) y actualiza vectors.v3.bin
    MCP->>Disk: cortex_session_close(status="closed", end_commit=HEAD)
    MCP-->>Host: Sesión sellada con éxito

    Host-->>Dev: Resumen final: Código integrado, tests verdes, ADR y Memoria actualizados
```

---

## 2. Diagrama de Bloques de Arquitectura Global de Sistemas

```mermaid
flowchart TD
    %% Capa 1: Usuario
    subgraph L1["Capa 1: Interacción Humana"]
        DEV["Desarrollador de Software"]
        TUI_USER["Usuario TUI Terminal"]
        BRAIN_USER["Usuario Desktop App"]
    end

    %% Capa 2: Entornos Host y CLIs de Agentes
    subgraph L2["Capa 2: Entornos Host y Agentes de Código"]
        HOST_AGY["Google Antigravity CLI / IDE"]
        HOST_PI["Pi Coding Agent (pi.dev)"]
        HOST_CLAUDE["Claude Code CLI (Anthropic)"]
        HOST_CURSOR["Cursor IDE / Codex CLI / OpenCode"]
    end

    %% Capa 3: Superficies de Cortex
    subgraph L3["Capa 3: Superficies y Puntos de Entrada de Cortex"]
        CLI_BIN["cortex-cli (Clap CLI Nativo 0.1.0)"]
        MCP_SERVER["cortex-mcp (rmcp 2.2 Stdio - 32 Tools)"]
        BRAIN_APP["cortex-brain-app (Tauri + React brain-ui)"]
        COMPANION_APP["cortex-companion (Ratatui TUI + HERDR)"]
        WEBGRAPH_HTTP["cortex-webgraph-server (Axum HTTP)"]
    end

    %% Capa 4: Inteligencia Híbrida y Motores de Inferencia
    subgraph L4["Capa 4: Motores de Inteligencia y Modelos de Lenguaje"]
        subgraph SYSTEM_ONE["SystemOne: Micro-Decisiones Cognitivas (cortex-judgement)"]
            SO_GATE["Utterance Gate (<10ms)"]
            SO_ROUTER["Model Router (Roles & Políticas)"]
            SO_SCORE["Primitiva Score (0.0..2.0)"]
            SO_SQUEEZE["Search Squeeze (Noul)"]
            SO_COMPACT["Session Compact (Poda)"]
            SO_WORTH["Filtro worth_remembering"]
        end

        subgraph CLOUD_MODELS["Modelos Remotos de Frontera"]
            REMOTE_PRO["Modelos Profundos: Gemini 2.5 Pro / Claude 3.5 Sonnet"]
            REMOTE_FAST["Modelos Ágiles: Gemini 2.5 Flash / Claude 3.5 Haiku"]
        end

        subgraph LOCAL_MODELS["Modelos Locales Soberanos"]
            LOCAL_GGUF["Modelos GGUF (llama.cpp) en ~/.cache/cortex/models/"]
            LOCAL_ROUTER["Router Determinista (Protocolo TOOL + Diálogo de Aprobación)"]
        end
    end

    %% Capa 5: Núcleo de Aplicación y Servicios Rust
    subgraph L5["Capa 5: Servicios y Dominio de Negocio (22 Crates Rust)"]
        SRV_SETUP["cortex-setup (Adapters, HostDetector, CLIDiscovery)"]
        SRV_APP["cortex-app (Session, Documenter, Episodic, Semantic)"]
        SRV_SERVICES["cortex-services (SpecService, NoteService, Migrate)"]
        SRV_AUTOPILOT["cortex-autopilot (State Machine, Preflight, Detectors)"]
        SRV_ACTIONS["cortex-actions (ActionEngine, cortex next)"]
        SRV_DOCTOR["cortex-doctor (Diagnósticos y Chequeos de Salud)"]
    end

    %% Capa 6: Motor de Memoria Híbrida y Fusión
    subgraph L6["Capa 6: Memoria Cognitiva Híbrida"]
        RRF_FUSION["Fusión Híbrida RRF (k=60)"]
        TIERED_FILTER["Tiered Memory Router (Primaria: 1.0 vs Archivo: 0.2)"]
        BM25_LEXICAL["Índice BM25 Léxico Substring (cortex-core)"]
        VECTOR_STORE["Almacén Vectorial V3 (cortex-embed Mean-Pool L2)"]
        ENRICHER_PIPELINE["Context Enricher Pipeline"]
    end

    %% Capa 7: Persistencia Física en Disco
    subgraph L7["Capa 7: Persistencia en Disco (.cortex/ Layout Canónico)"]
        FILE_CONFIG["config.yaml (Ajustes de Sistema y Model Router)"]
        FILE_SESSIONS[".cortex/sessions/*.yaml (Trazabilidad de Sesiones)"]
        FILE_VAULT[".cortex/vault/**/*.md (Vault Markdown Obsidian)"]
        FILE_MEMORY[".cortex/memory/*.jsonl (Registros de Memoria Episódica)"]
        FILE_VECTORS[".cortex/vectors.v3.bin (Vectores Binarios CCTXV3)"]
    end

    %% Capa 8: Capa Corporativa Enterprise
    subgraph L8["Capa 8: Gobernanza y Memoria Organizacional"]
        ENT_CONFIG[".cortex/org.yaml (Reglas de Promoción y Políticas)"]
        ENT_ENGINE["PromotionRulesEngine (cortex-enterprise)"]
        ENT_VAULT["Vault Central Corporativo (Conocimiento Compartido)"]
    end

    %% Conexiones Lógicas Limpias y Directas
    DEV --> L2
    TUI_USER --> CLI_BIN
    TUI_USER --> COMPANION_APP
    BRAIN_USER --> BRAIN_APP

    L2 --> MCP_SERVER
    L2 --> CLI_BIN

    CLI_BIN --> L5
    MCP_SERVER --> L5
    BRAIN_APP --> LOCAL_MODELS
    BRAIN_APP --> L5
    COMPANION_APP --> L5
    WEBGRAPH_HTTP --> L5

    L5 --> SYSTEM_ONE
    L5 --> L6
    L2 --> CLOUD_MODELS

    SYSTEM_ONE -. "Micro-Decisiones" .-> L2
    SYSTEM_ONE -. "Ruteo de Modelos" .-> CLOUD_MODELS

    L6 --> L7
    L5 --> L7

    L7 --> ENT_ENGINE
    ENT_CONFIG --> ENT_ENGINE
    ENT_ENGINE --> ENT_VAULT
```

---

## 3. Diagrama de Arquitectura UML Formal (Componentes, Bases de Datos y Estereotipos)

Este diagrama sigue el estándar formal de **Diagrama de Componentes y Despliegue UML 2.5**, utilizando la simbología canónica:
- **Actor UML**: `Dev` (Desarrollador Humano).
- **Cilindros de Base de Datos UML** (`[(BDD)]`): Representando las distintas estructuras de almacenamiento persistente (`.cortex/sessions`, `.cortex/vault`, `.cortex/vectors.v3.bin`, `.cortex/memory`, `org.yaml`).
- **Componentes con Estereotipos**: `<<host>>`, `<<mcp-server>>`, `<<system-one>>`, `<<llm>>`, `<<subagent>>`, `<<memory-engine>>`.
- **Interfaces y Puertos**: Puertos de entrada/salida (`rmcp 2.2 stdio`, `RRF k=60`, `BM25`, `JSON-RPC 2.0`).

```mermaid
flowchart TB
    %% Actor Humano
    DEV([👤 Actor: Desarrollador])

    %% Host IDE y Aislamiento de Entorno
    subgraph COMP_HOST ["<<host-environment>> Entornos de Desarrollo"]
        direction TB
        HOST_IDE["<<component>><br/><b>Host Agent IDE</b><br/>(Antigravity / Pi / Claude Code / Cursor)"]
        SHIELD["<<guard>><br/><b>HostPolicyShield</b><br/>(Aislamiento ToS Google vs OpenRouter)"]
        HOST_IDE --- SHIELD
    end

    %% Servidor Cortex MCP
    subgraph COMP_MCP ["<<mcp-server>> cortex-mcp v2.2"]
        direction TB
        MCP_CORE["<<component>><br/><b>Servidor rmcp (stdio)</b><br/>JSON-RPC 2.0 Protocol"]
        
        subgraph MCP_INTERFACES ["<<interfaces>> Catálogo de 32 Tools"]
            direction LR
            PORT_SYS["○ Sys / Ping (1)"]
            PORT_SEARCH["○ Search / Context (5)"]
            PORT_SESS["○ Sessions / Tasks (9)"]
            PORT_SPEC["○ Specs / HU (5)"]
            PORT_AUDIT["○ Audit / Claims (2)"]
            PORT_DOC["○ Documenter (5)"]
            PORT_AUTO["○ Autopilot (5)"]
        end
        MCP_CORE --> MCP_INTERFACES
    end

    %% Motor Cognitivo Rápido: SystemOne
    subgraph COMP_S1 ["<<system-one>> Motor Cognitivo Reflejo (cortex-judgement)"]
        direction TB
        S1_GATE["<<classifier>> Utterance Gate<br/>(<10ms, work_choice, needs_session)"]
        S1_ROUTER["<<router>> Model Router<br/>(Confidence >= 0.85, Roles: Arch/Impl/Doc)"]
        S1_SQUEEZE["<<filter>> Search Squeeze<br/>(Poda de Noul / Distractores)"]
        S1_COMPACT["<<reducer>> Session Compact<br/>(Compresión de Historial con JEV)"]
        S1_WORTH["<<gatekeeper>> worth_remembering<br/>(Guarda de Aprendizajes Clave)"]
    end

    %% Capa de Inteligencia Deliberativa: LLMs y Subagentes
    subgraph COMP_AI ["<<deliberative-intelligence>> Razonamiento y Modelos"]
        direction TB
        subgraph CLOUD_LLM ["<<llm-remote>> Modelos Remotos"]
            LLM_DEEP["Deep Reasoning:<br/>Gemini 2.5 Pro / Claude 3.5 Sonnet"]
            LLM_FAST["Fast Reflexive:<br/>Gemini 2.5 Flash / Haiku"]
        end

        subgraph LOCAL_LLM ["<<llm-sovereign>> Modelos Locales"]
            LLM_GGUF["Local GGUF llama.cpp<br/>(~/.cache/cortex/models/)"]
        end

        subgraph SUBAGENTS ["<<subagents>> Personas Especializadas"]
            SA_ARCH["cortex-code-designer<br/>(Arquitectura & SDD)"]
            SA_IMPL["implement-craft<br/>(Implementación & Tests)"]
            SA_DOC["cortex-documenter<br/>(ADRs & Cierre)"]
        end
    end

    %% Capa de Memoria Híbrida
    subgraph COMP_MEM ["<<memory-engine>> Motor de Recuperación Híbrida (cortex-core)"]
        direction TB
        RRF_FUSION["<<algorithm>> Fusión RRF (k=60)"]
        BM25_ENGINE["<<search-engine>> BM25 Lexical (Token Match)"]
        VEC_ENGINE["<<vector-engine>> Embeddings Cosine k-NN"]
        TIER_ROUTER["<<filter>> Tiered Router (Active: 1.0 vs Archive: 0.2)"]
        
        RRF_FUSION --> BM25_ENGINE
        RRF_FUSION --> VEC_ENGINE
        RRF_FUSION --> TIER_ROUTER
    end

    %% Bases de Datos y Almacenamiento Persistente (Cilindros UML)
    subgraph COMP_STORAGE ["<<persistence-layer>> Bases de Datos Físicas (.cortex/)"]
        direction TB
        DB_SESSIONS[("🛢️ BDD Episódica<br/><b>sessions/*.yaml</b><br/>session_events.jsonl")]
        DB_VAULT[("🛢️ BDD Semántica<br/><b>vault/**/*.md</b><br/>Specs, ADRs, Notes")]
        DB_VECTORS[("🛢️ BDD Vectorial V3<br/><b>vectors.v3.bin</b><br/>HNSW + L2 Embeddings")]
        DB_CONFIG[("🛢️ BDD Config<br/><b>workspace.toml</b><br/>config.yaml")]
        DB_ENTERPRISE[("🛢️ BDD Corporativa<br/><b>org.yaml</b><br/>Enterprise Central Vault")]
    end

    %% Relaciones y Flujos de Datos UML
    DEV -->|Prompt de Desarrollo| HOST_IDE
    HOST_IDE -->|JSON-RPC 2.0 (stdio)| MCP_CORE
    HOST_IDE -.->|Micro-evaluación <10ms| S1_GATE
    
    S1_ROUTER -.->|Asignación de Modelo| CLOUD_LLM
    HOST_IDE -->|Contexto Enriquecido| SUBAGENTS
    SUBAGENTS -->|Inferencia| CLOUD_LLM
    SUBAGENTS -->|Inferencia Soberana| LOCAL_LLM

    MCP_CORE -->|Consultas RRF / Context| RRF_FUSION
    MCP_CORE -->|Auditoría / Claims| S1_SQUEEZE
    MCP_CORE -->|Evaluación de Ruido| S1_WORTH

    BM25_ENGINE -->|Lectura Tokens| DB_VAULT
    VEC_ENGINE -->|Lectura Vectores k-NN| DB_VECTORS
    
    MCP_CORE -->|Escritura de Sesión & Checkpoints| DB_SESSIONS
    MCP_CORE -->|Escritura de ADRs & Specs| DB_VAULT
    MCP_CORE -->|Persistencia de Aprendizajes| DB_CONFIG
    DB_VAULT -.->|Reglas de Promoción| DB_ENTERPRISE
```

---

## 4. Síntesis Arquitectónica de la Interacción

1. **Separación de Responsabilidades**:
   - El **Desarrollador** define la intención y valida las decisiones.
   - El **Host CLI/IDE** provee el entorno de trabajo del agente y la conexión al modelo.
   - **SystemOne** actúa como el *Sistema 1 de Kahneman*: decisiones reflejas deterministas en $<10$ms (portero de intenciones, poda de ruido, ruteo de subagentes, calificación de impacto de ADRs).
   - Los **LLMs Remotos** actúan como el *Sistema 2 de Kahneman*: razonamiento deliberado, generación de código y resolución de problemas.
   - Los **Modelos Locales GGUF** en Cortex Brain operan con soberanía total para consultas rápidas de salud, estadísticas y grafos sin enviar telemetría a la nube.
   - Los **22 Crates de Rust de Cortex** garantizan paridad matemática, latencia nativa, tipado seguro e invariantes de memoria que persisten en `.cortex/`.

