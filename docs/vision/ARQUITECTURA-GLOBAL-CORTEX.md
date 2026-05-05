# 🧠 Cortex Enterprise — Arquitectura Global del Sistema

> **Documento para Patrocinadores** | Versión 0.3.0 (Alpha)  
> *Sistema de Gobernanza, Memoria Corporativa y DevSecDocOps para Organizaciones con Agentes de IA*

---

## 📋 Resumen Ejecutivo

**Cortex** es una plataforma de infraestructura cognitiva que transforma la memoria de sesión volátil de los agentes de IA en **memoria institucional persistente y auditable**. A diferencia de las soluciones aisladas por proyecto, Cortex opera como capa transversal empresarial donde el conocimiento fluye desde lo local (un desarrollador, un proyecto) hacia lo corporativo (toda la organización) mediante un pipeline de promoción gobernado.

La arquitectura está diseñada para ser **modular por instalación** (`agent`, `pipeline`, `full`, `webgraph`) pero **unificada en ejecución** gracias a un backbone de embeddings ONNX que permite la interoperabilidad semántica entre todas las partes sin depender de APIs externas ni GPUs.

---

## 🏛️ Visión Macro: Las 4 Partes Instalables

Cortex se instala de forma progresiva según la madurez de la organización. Cada parte es autónoma pero diseñada para componerse en el sistema integral.

```mermaid
graph TB
    subgraph "📦 Cortex Setup — Modos de Instalación"
        direction TB
        
        subgraph "🧩 Modos Individuales"
            A["<b>cortex setup agent</b><br/>Memoria + Vault + Skills + MCP"]
            P["<b>cortex setup pipeline</b><br/>CI/CD + Auditoría + Gates"]
            W["<b>cortex setup webgraph</b><br/>Visualización de Grafos + Federación"]
        end
        
        F["<b>cortex setup full</b><br/>Agent + Pipeline + Enterprise Foundation"]
        E["<b>cortex setup enterprise</b><br/>Topología Org + Vault Corporativo + Promotion Pipeline"]
    end
    
    A --> F
    P --> F
    F --> E
    W -.-> E
    
    style A fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style P fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style W fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style F fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    style E fill:#fce4ec,stroke:#880e4f,stroke-width:3px
```

| Modo | Propósito de Negocio | Quién lo instala |
|------|---------------------|------------------|
| **`setup agent`** | Habilita la memoria híbrida (episódica + semántica) en el proyecto local, conecta el IDE vía MCP y establece el vault de conocimiento. | Desarrollador individual |
| **`setup pipeline`** | Activa los GitHub Actions de gobernanza: Security, Lint, Test, Docs gates en cada PR. | DevOps / Tech Lead |
| **`setup full`** | Despliegue completo de gobernanza + memoria en un solo paso. Ideal para nuevos proyectos. | Tech Lead / Arquitecto |
| **`setup webgraph`** | Activa la visualización interactiva de grafos de conocimiento y federación entre workspaces. | Data Team / Arquitecto |
| **`setup enterprise`** | Escalado a nivel organizacional: vault corporativo, promoción de conocimiento y topología declarativa (`org.yaml`). | CTO / Enterprise Architect |

---

## 🔗 Arquitectura de Interconexión: El Backbone ONNX

El elemento diferenciador de Cortex es que **no es un monolito con acoplamiento fuerte**. Es un ecosistema de componentes distribuidos que se entienden entre sí porque comparten el mismo espacio vectorial semántico generado por ONNX Runtime.

```mermaid
graph LR
    subgraph "🧠 Backbone Neural Compartido — ONNX Runtime"
        direction TB
        ONNX["<b>ONNX Embedding Engine</b><br/>all-MiniLM-L6-v2<br/>384 dim | &lt;1ms latencia | ~50MB<br/>⚡ CPU-only, sin API keys"]
        
        subgraph "Espacio Vectorial Unificado"
            V1["Vector: spec-auth-jwt"]
            V2["Vector: decision-arquitectura"]
            V3["Vector: incident-seguridad"]
            V4["Vector: runbook-despliegue"]
            V5["Vector: session-PR-123"]
        end
    end
    
    subgraph "🖥️ Partes Locales del Sistema"
        direction TB
        AG["<b>Agent</b><br/>ChromaDB local<br/>Vault local<br/>Skills"]
        PL["<b>Pipeline</b><br/>GitHub Actions<br/>Security Gates<br/>Test Gates"]
        WG["<b>WebGraph</b><br/>Nodos de conocimiento<br/>Relaciones<br/>Federación"]
    end
    
    subgraph "🏢 Capa Enterprise"
        direction TB
        EV["<b>Enterprise Vault</b><br/>vault-enterprise/"]
        EM["<b>Enterprise Memory</b><br/>ChromaDB corporativa"]
        RP["<b>Promotion Pipeline</b><br/>candidate → reviewed → promoted"]
    end
    
    AG -->|"genera embeddings"| ONNX
    PL -->|"genera embeddings"| ONNX
    WG -->|"genera embeddings"| ONNX
    EV -->|"consulta semántica"| ONNX
    EM -->|"consulta semántica"| ONNX
    
    ONNX -.->|"vectores persistidos"| V1
    ONNX -.->|"vectores persistidos"| V2
    ONNX -.->|"vectores persistidos"| V3
    ONNX -.->|"vectores persistidos"| V4
    ONNX -.->|"vectores persistidos"| V5
    
    AG -->|"promueve conocimiento"| RP
    RP -->|"materia aprobada"| EV
    RP -->|"materia aprobada"| EM
    WG -->|"enriquece nodos"| EV
    PL -->|"genera incidentes/audits"| EM
    
    style ONNX fill:#ffeb3b,stroke:#f57f17,stroke-width:3px
    style AG fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style PL fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style WG fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style EV fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style EM fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style RP fill:#fce4ec,stroke:#880e4f,stroke-width:2px
```

### ¿Por qué ONNX es el pegamento arquitectónico?

| Característica | Valor para la Organización |
|---------------|---------------------------|
| **Modelo único compartido** (`all-MiniLM-L6-v2`) | Todos los componentes —agente, pipeline, webgraph, vault enterprise— "hablan el mismo idioma numérico". Un embedding generado en el proyecto A es comparable con uno generado en el proyecto B. |
| **Zero dependencies externas** | No requiere API keys de OpenAI, ni GPUs, ni conectividad a internet. El modelo corre 100% on-premise en CPU. |
| **Footprint mínimo** | ~50MB de RAM vs ~2.5GB de PyTorch. Se puede desplegar en cualquier runner de CI, laptop de desarrollador o servidor edge. |
| **Sub-milisegundo de latencia** | Búsquedas semánticas en tiempo real dentro del flujo de desarrollo sin fricción perceptible. |
| **Intercambio de contexto** | Gracias a que todos los componentes usan el mismo espacio vectorial, el contexto de una sesión de desarrollo local puede ser **inyectado automáticamente** en la búsqueda de otro proyecto o del vault enterprise. |

---

## 🏛️ Arquitectura Integral: Flujo de Datos y Contexto

Este diagrama muestra cómo fluye la información a través del sistema completo, desde que un desarrollador escribe código hasta que el conocimiento se convierte en activo corporativo.

```mermaid
flowchart TB
    subgraph "👤 Desarrollador / Agente de IA"
        IDE["IDE con MCP<br/>Cursor / VSCode / Pi / Claude"]
        GIT["Repositorio Git Local"]
    end
    
    subgraph "🧠 Cortex Local — Por Proyecto"
        direction TB
        CLI["CLI Cortex<br/>Typer + 30+ comandos"]
        FACADE["AgentMemory Façade<br/>Inyección de Servicios"]
        
        subgraph "Memoria Híbrida RRF"
            EP["Capa Episódica<br/>ChromaDB + ONNX<br/>Eventos, sesiones, PRs"]
            SEM["Capa Semántica<br/>Vault Markdown<br/>Specs, decisiones, runbooks"]
            RRF["Fusión RRF<br/>Reciprocal Rank Fusion<br/>pesos configurables"]
        end
        
        CE["Context Enricher<br/>Detección de dominio<br/>Co-occurrence boost"]
        VLT["Vault Local<br/>.cortex/vault/ (new) o vault/ (legacy)<br/>Obsidian-compatible"]
    end
    
    subgraph "🔧 DevSecDocOps Pipeline"
        direction TB
        GHA["GitHub Actions<br/>CI/CD Gates"]
        SEC["Security Gate<br/>OWASP / vulnerabilidades"]
        TST["Test Gate<br/>Cobertura >80%"]
        LINT["Lint Gate<br/>Ruff / calidad"]
        DOC["Docs Gate<br/>Documentación obligatoria"]
    end
    
    subgraph "🏢 Cortex Enterprise — Repositorio Corporativo"
        direction TB
        ORG["org.yaml<br/>Topología declarativa<br/>Presets por industria"]
        EVLT["Enterprise Vault<br/>vault-enterprise/<br/>Conocimiento institucional"]
        EMEM["Enterprise Memory<br/>ChromaDB corporativa"]
        PRO["Promotion Pipeline<br/>candidate → reviewed → promoted<br/>Trazabilidad completa"]
        RET["Enterprise Retrieval<br/>scope: local | enterprise | all"]
    end
    
    subgraph "🌐 WebGraph + Observabilidad"
        WG["WebGraph Server<br/>Flask + Visualización D3"]
        FED["Federación<br/>Multi-workspace"]
        REP["memory-report<br/>JSON estable + Humano"]
    end
    
    IDE -->|"MCP Tools:<br/>search, context,<br/>create-spec,<br/>save-session"| CLI
    GIT -->|"git diff<br/>branch context"| CE
    CLI --> FACADE
    FACADE --> EP
    FACADE --> SEM
    FACADE --> VLT
    EP --> RRF
    SEM --> RRF
    CE -->|"inyecta contexto<br/>proactivo"| RRF
    RRF -->|"resultados unificados"| IDE
    
    FACADE -->|"store_pr_context"| GHA
    GHA --> SEC --> TST --> LINT --> DOC
    DOC -->|"genera session-note"| VLT
    SEC -->|"genera incident-note"| VLT
    TST -->|"métricas de cobertura"| EP
    
    VLT -->|"promote-knowledge"| PRO
    EP -->|"promote-knowledge"| PRO
    PRO -->|"aprobado"| EVLT
    PRO -->|"aprobado"| EMEM
    
    ORG -->|"configura scopes<br/>y pesos"| RET
    EVLT -->|"fuentes semánticas"| RET
    EMEM -->|"fuentes episódicas"| RET
    RET -->|"búsqueda cross-source"| CLI
    
    EP -->|"nodos episódicos"| WG
    SEM -->|"nodos semánticos"| WG
    EVLT -->|"nodos enterprise"| WG
    WG --> FED
    FED -->|"reporte federado"| REP
    
    style ONNX fill:#ffeb3b,stroke:#f57f17,stroke-width:2px
    style RRF fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style PRO fill:#f8bbd0,stroke:#ad1457,stroke-width:2px
    style CE fill:#b3e5fc,stroke:#0277bd,stroke-width:2px
    style IDE fill:#d1c4e9,stroke:#4527a0,stroke-width:2px
```

---

## 🏦 El Vault Empresarial: Local vs Remoto

Cortex distingue dos geometrías de vault que trabajan en conjunto mediante el mismo motor ONNX:

```mermaid
graph TB
    subgraph "💻 Instancia Local — Proyecto Individual"
        direction TB
        LROOT["Directorio del Proyecto<br/>~/proyecto-acme/"]
        LCORTEX[".cortex/ — Workspace"]
        LCFG["config.yaml<br/>Configuración local"]
        LVLT["vault/<br/>Specs, decisiones,<br/>runbooks, incidents"]
        LMEM["memory/chroma/<br/>Embeddings ONNX<br/>Sesiones, PRs, eventos"]
        LORG["org.yaml<br/>Topología local"]
        
        LROOT --> LCORTEX
        LCORTEX --> LCFG
        LCORTEX --> LVLT
        LCORTEX --> LMEM
        LCORTEX --> LORG
    end
    
    subgraph "🌐 Repositorio Empresarial — Contexto Compartido"
        direction TB
        EROOT["Repositorio Enterprise<br/>cortex-enterprise/ o<br/>monorepo compartido"]
        EVLT["vault-enterprise/<br/>Conocimiento aprobado<br/>por el Promotion Pipeline"]
        EMEM["memory/enterprise/chroma/<br/>Embeddings ONNX corporativos<br/>accesibles multi-proyecto"]
        EORG["org.yaml maestro<br/>Perfiles: small-company,<br/>multi-project, regulated"]
        
        EROOT --> EVLT
        EROOT --> EMEM
        EROOT --> EORG
    end
    
    subgraph "🔄 Inyección de Contexto Cross-Project"
        direction TB
        Q["Query del Desarrollador:<br/>'autenticación JWT'"]
        ONNX2["ONNX Runtime<br/>Embedding de la query"]
        RET2["Enterprise Retrieval<br/>scope: all"]
        RES["Resultados Unificados:<br/>• Spec local (proyecto A)<br/>• Incident enterprise (proyecto B)<br/>• Runbook corporativo<br/>• Sesión episódica de ayer"]
    end
    
    LVLT -->|"promoción<br/>auditada"| EVLT
    LMEM -->|"promoción<br/>auditada"| EMEM
    EORG -->|"gobierna<br/>pesos y scopes"| RET2
    
    Q --> ONNX2
    ONNX2 --> RET2
    LVLT -->|"fuentes locales"| RET2
    LMEM -->|"fuentes locales"| RET2
    EVLT -->|"fuentes enterprise"| RET2
    EMEM -->|"fuentes enterprise"| RET2
    RET2 --> RES
    
    style LVLT fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style LMEM fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style EVLT fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style EMEM fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style RET2 fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style RES fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
```

### Cómo funciona la inyección de contexto multi-local

1. **Cada proyecto local** tiene su propio vault y memoria episódica, ambos indexados con ONNX.
2. Cuando un desarrollador ejecuta `cortex search "auth JWT" --scope all`, la query se convierte en un vector ONNX.
3. El **Enterprise Retrieval Service** consulta simultáneamente:
   - Vault local del proyecto actual
   - Memoria episódica local del proyecto actual
   - Vault enterprise compartido (si está habilitado)
   - Memoria episódica enterprise (si está habilitada)
4. Los resultados se fusionan con **RRF (Reciprocal Rank Fusion)** con pesos configurables por scope.
5. El desarrollador recibe contexto que incluye decisiones de arquitectura de **otros proyectos** que nunca vio, porque el espacio vectorial ONNX es compartido.

> **Valor de negocio**: Un equipo que resuelve un problema de seguridad en el proyecto A genera conocimiento que el equipo del proyecto B recupera automáticamente semanas después, sin reuniones ni documentación manual.

---

## 🧩 Descripción Detallada de Componentes

### 1. `cortex setup agent` — La Memoria Cognitiva
- **Qué hace**: Instala ChromaDB (episódica), el vault Markdown (semántica), skills de documentación y el servidor MCP.
- **Valor**: Elimina la "amnesia de sesión" de los agentes de IA. Cada tarea deja un rastro persistente.
- **Tecnología clave**: ONNX Runtime para embeddings locales, ChromaDB como vector store, Typer para CLI.

### 2. `cortex setup pipeline` — La Gobernanza CI/CD
- **Qué hace**: Genera GitHub Actions con gates de Security, Lint, Test y Documentation.
- **Valor**: Convierte la calidad, seguridad y documentación en requisitos automáticos, no afterthoughts.
- **Tecnología clave**: Workflows YAML parametrizados, perfiles de enforcement (`advisory` vs `enforced`).

### 3. `cortex setup full` — La Fundación Completa
- **Qué hace**: Ejecuta `agent` + `pipeline` en una sola operación idempotente.
- **Valor**: Un solo comando para que un nuevo proyecto entre en gobernanza total.
- **Tecnología clave**: `SetupOrchestrator` con `WorkspaceLayout` que adapta la estructura de directorios automáticamente.

### 4. `cortex setup webgraph` — La Visualización del Conocimiento
- **Qué hace**: Levanta un servidor Flask que visualiza el grafo de relaciones entre specs, decisiones, sesiones e incidents.
- **Valor**: Transforma la memoria textual en topología navegable. Permite descubrir clusters de conocimiento ocultos.
- **Tecnología clave**: Federación multi-workspace, enriquecimiento de nodos con embeddings ONNX.

### 5. `cortex setup enterprise` — La Escalabilidad Organizacional
- **Qué hace**: Crea `org.yaml`, vault enterprise, y habilita el Promotion Pipeline.
- **Valor**: El conocimiento deja de ser propiedad de un repo y se convierte en activo corporativo con trazabilidad.
- **Tecnología clave**: Pydantic models para validación de topología, RRF cross-source, pesos configurables `local_weight` / `enterprise_weight`.

---

## 🎯 Flujos de Valor para el Patrocinador

```mermaid
graph LR
    subgraph "📉 Sin Cortex"
        S1["Agente olvida contexto<br/>entre sesiones"]
        S2["Documentación obsoleta<br/>o inexistente"]
        S3["Vulnerabilidades<br/>detectadas tarde"]
        S4["Conocimiento atrapado<br/>en silos por proyecto"]
        S5["Sin trazabilidad de<br/>decisiones técnicas"]
    end
    
    subgraph "📈 Con Cortex Enterprise"
        C1["Memoria persistente<br/>local + enterprise"]
        C2["save-session obligatorio<br/>Docs siempre actualizadas"]
        C3["Security gate en cada PR<br/>en tiempo real"]
        C4["Promotion Pipeline<br/>conocimiento fluye org-wide"]
        C5["Vault auditado +<br/>Decisiones trazables"]
    end
    
    S1 -->|"ONNX + ChromaDB"| C1
    S2 -->|"Context Enricher +<br/>Skills obligatorias"| C2
    S3 -->|"Pipeline CI gates"| C3
    S4 -->|"Enterprise Retrieval +<br/>RRF cross-source"| C4
    S5 -->|"Vault Markdown +<br/>Promotion Pipeline"| C5
    
    style S1 fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px
    style S2 fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px
    style S3 fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px
    style S4 fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px
    style S5 fill:#ffcdd2,stroke:#b71c1c,stroke-width:1px
    style C1 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style C2 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style C3 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style C4 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style C5 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
```

---

## 🔐 Modelo de Seguridad y Gobernanza

| Capa | Control | Implementación |
|------|---------|----------------|
| **Datos** | Embeddings y vault permanecen on-premise | ONNX local + ChromaDB local/empresarial |
| **Promoción** | Conocimiento no fluye sin revisión | `require_review: true` en `org.yaml` |
| **CI** | Gates pueden bloquear merge | `block_on_failure: true` por stage |
| **Auditoría** | Todo cambio en vault es git-tracked | Markdown bajo control de versiones |
| **Aislamiento** | Proyectos pueden operar aislados o compartidos | `project_memory_mode: isolated \| shared` |

---

## 📊 Métricas de Arquitectura

| Indicador | Valor |
|-----------|-------|
| Latencia de embedding | `< 1 ms` (CPU) |
| Dimensiones vectoriales | `384` (all-MiniLM-L6-v2) |
| Footprint de memoria ONNX | `~50 MB` |
| Comandos CLI disponibles | `30+` |
| Backends de embedding soportados | `ONNX (default), sentence-transformers, OpenAI` |
| Scopes de retrieval | `local, enterprise, all` |
| Estados del Promotion Pipeline | `candidate, reviewed, promoted` |
| Perfiles de organización | `small-company, multi-project-team, regulated-organization, custom` |
| Cobertura de tests objetivo | `> 85%` |

---

> **Conclusión para el Patrocinador**: Cortex no es una herramienta más. Es infraestructura cognitiva que convierte el conocimiento disperso de desarrolladores y agentes de IA en **activo corporativo estructurado, auditable y reutilizable**. La arquitectura modular permite adoptarlo progresivamente (agent → pipeline → enterprise), mientras que ONNX garantiza que cada pieza del sistema comparta el mismo lenguaje semántico sin costos de API ni dependencia de terceros.
