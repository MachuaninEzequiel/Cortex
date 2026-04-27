# Diagramas de Memoria Cortex: Estado Actual y Arquitectura Objetivo

## Documento

- Fecha: 2026-04-26
- Proyecto: Cortex
- Objetivo: explicar visualmente como funciona hoy la memoria de Cortex, desde el nivel micro hasta el nivel empresarial, y mostrar la arquitectura objetivo recomendada
- Audiencia: tecnica y no tecnica

---

## Como leer este documento

Este documento esta organizado de menor a mayor escala:

1. Primero se muestra como Cortex guarda y recupera memoria dentro de un proyecto.
2. Luego se muestra como ONNX y el CI participan en ese proceso.
3. Despues se muestra como queda la topologia real de memoria en multi-proyecto.
4. Finalmente se muestra que puede hacer hoy una empresa chica y cual es la arquitectura objetivo para llegar a una memoria empresarial completa.

La idea principal es separar tres conceptos que muchas veces se mezclan:

- `vault/` = conocimiento durable, compartible, revisable por humanos
- `.memory/chroma` = memoria episodica operativa persistida en Chroma
- recuperacion hibrida = fusion inteligente entre ambas capas en el momento de buscar

---

## 1. Vista micro: como Cortex guarda memoria hoy

```mermaid
flowchart LR
    A["Agente / CLI / Servicio"] --> B["AgentMemory<br/>cortex/core.py"]
    B --> C["Runtime metadata<br/>project_id + branch + repo"]
    C --> D["remember() / store_pr_context() / save_session_note() / create_spec_note()"]
    D --> E["EpisodicMemoryStore<br/>cortex/episodic/memory_store.py"]
    E --> F["Embedder"]
    F --> G["ONNX / local / OpenAI"]
    E --> H["Chroma PersistentClient"]
    H --> I[".memory/chroma"]

    D --> J["VaultReader / create_note"]
    J --> K["vault/*.md"]
```

### Que muestra este diagrama

- La memoria episodica y la memoria semantica no son lo mismo.
- Cuando Cortex guarda un hecho operativo, ese hecho entra por `AgentMemory`.
- Antes de persistirlo, Cortex le agrega contexto de ejecucion real: `project_id`, `branch` y `repo`.
- La memoria episodica se embebe y se guarda en Chroma.
- La memoria semantica se guarda como archivo Markdown en `vault/`.

### Idea clave

Hoy Cortex no piensa la memoria como "un solo deposito", sino como una combinacion de:

- una capa operativa vectorial
- una capa documental durable

---

## 2. Vista micro: como Cortex recupera memoria hoy

```mermaid
flowchart TD
    Q["Consulta del agente<br/>ej: 'como resolvimos auth?'"] --> A["HybridSearch<br/>cortex/retrieval/hybrid_search.py"]
    A --> B["Busqueda episodica<br/>Chroma + embeddings"]
    A --> C["Busqueda semantica<br/>vault indexado"]
    B --> D["Hits episodicos"]
    C --> E["Hits semanticos"]
    D --> F["RRF Fusion"]
    E --> F
    F --> G["Unified Results"]
    G --> H["Contexto final para SPEC, implementacion o documentacion"]
```

### Que muestra este diagrama

- Cortex busca en ambos mundos por separado.
- No mezcla los datos al guardar; los mezcla al recuperar.
- La fusion se hace con `RRF`, para que resultados de ambas capas compitan en un ranking comun.

### Idea clave

La "memoria hibrida" hoy existe sobre todo en la etapa de recuperacion.  
La arquitectura actual esta orientada a responder mejor, no a unificar fisicamente todo en un solo storage.

---

## 3. Como interviene ONNX realmente

```mermaid
flowchart LR
    A["Texto a indexar o buscar"] --> B["Embedder<br/>cortex/episodic/embedder.py"]
    B --> C{"embedding_backend"}
    C --> D["onnx<br/>default"]
    C --> E["local"]
    C --> F["openai"]

    D --> G["ONNXMiniLM_L6_V2<br/>via chromadb"]
    G --> H["Vectores numericos"]
    H --> I["Chroma episodico o indexado semantico en memoria"]
```

### Que muestra este diagrama

- ONNX hoy es el backend default de embeddings.
- Se usa tanto para la capa episodica como para la capa semantica.
- No es un servicio aparte de empresa: es el motor local que transforma texto en vectores.

### Lo mas importante

ONNX no crea por si solo una "memoria corporativa".  
ONNX solo hace posible que la memoria se pueda buscar semanticamente.

---

## 4. Como se indexa la documentacion del vault

```mermaid
flowchart TD
    A["vault/*.md"] --> B["VaultReader.sync()<br/>cortex/semantic/vault_reader.py"]
    B --> C["Parseo markdown + frontmatter"]
    C --> D["Construccion de SemanticDocument"]
    D --> E["Embedding ONNX por documento"]
    E --> F["Indice semantico en memoria del proceso"]
    C --> G["BM25 metadata"]
    G --> H["vault/.cortex_index.json"]
```

### Que muestra este diagrama

- La documentacion del `vault/` se convierte en documentos semanticos buscables.
- Cada documento recibe embedding.
- El indice semantico principal vive en memoria del proceso.
- Lo que se persiste en disco para esta parte es liviano: metadatos de apoyo como `vault/.cortex_index.json`.

### Implicancia real

Hoy la capa semantica no queda persistida como una gran base vectorial compartida del tipo "empresa completa en un solo Chroma".  
Se re-indexa cuando hace falta.

---

## 5. Como participa CI hoy

```mermaid
flowchart TD
    A["Pull Request"] --> B["GitHub Actions<br/>ci-pull-request.yml"]
    B --> C["cortex doctor"]
    C --> D["Restore cache<br/>.memory/chroma"]
    D --> E["Capture PR context"]
    E --> F["Store PR context<br/>memoria episodica"]
    F --> G{"Hay docs del agente?"}
    G -->|Si| H["cortex index-docs"]
    G -->|No| I["cortex pr-context generate"]
    I --> J["cortex sync-vault"]
    H --> K["Validate docs"]
    J --> K
    K --> L["Save cache<br/>.memory/chroma"]
```

### Que muestra este diagrama

- El CI si usa memoria.
- El CI si puede regenerar o reindexar conocimiento documental.
- El CI guarda contexto episodico de PR en `.memory/chroma`.
- El CI cachea `.memory/chroma` entre runs del workflow.

### Lo que no significa

Esto no significa que exista una memoria canonica global versionada en `main`.  
Lo que existe hoy es:

- uso operativo de `.memory/chroma` en CI
- cache de esa memoria entre ejecuciones
- y conocimiento durable en `vault/` si ese contenido se versiona

---

## 6. Topologia actual de memoria por proyecto y por rama

```mermaid
flowchart TB
    A["Proyecto / Repo"] --> B{"namespace_mode"}
    B -->|project| C[".memory/chroma"]
    B -->|branch| D[".memory/chroma/branches/<branch>"]
    B -->|custom| E[".memory/chroma/custom/<namespace>"]

    A --> F["vault/"]
    F --> G["specs/"]
    F --> H["decisions/"]
    F --> I["runbooks/"]
    F --> J["hu/"]
    F --> K["incidents/"]
    F --> L["sessions/"]
```

### Que muestra este diagrama

- La memoria episodica hoy es modular.
- El default real es por proyecto.
- Si se activa `namespace_mode: branch`, la memoria episodica queda separada por rama.
- El `vault/` organiza conocimiento durable por carpetas, no por vectores.

### Interpretacion

La modularidad hoy esta mas fuerte que la transversalidad total.  
Eso fue una decision saludable para evitar mezcla de contexto, ruido y acoplamiento excesivo.

---

## 7. Por que `.memory/`, `*.chroma/` y `vault/sessions/` aparecen en `.gitignore`

```mermaid
flowchart LR
    A["Conocimiento durable"] --> B["Se revisa"]
    B --> C["Se versiona en Git"]

    D["Estado operativo local"] --> E["Puede regenerarse"]
    E --> F["No conviene versionarlo"]

    C --> G["vault/specs<br/>vault/decisions<br/>vault/runbooks<br/>vault/hu<br/>vault/incidents"]
    F --> H[".memory/<br/>*.chroma/<br/>vault/sessions/"]
```

### Que muestra este diagrama

- Git no debe guardar todo indiscriminadamente.
- Hay una diferencia entre conocimiento durable y estado operativo.
- `.memory/` y `*.chroma/` representan almacenamiento tecnico regenerable y ruidoso.
- `vault/sessions/` puede tener mucho churn y no siempre conviene versionarlo por defecto.

### Filosofia de fondo

Antes podia existir la intuicion de que "si todo es memoria, todo deberia guardarse en Git".  
Ahora Cortex separa mejor:

- lo que debe quedar como patrimonio empresarial durable
- de lo que es estado operativo de una corrida, indexado o cache

Eso mejora:

- gobernanza
- limpieza del repositorio
- revisabilidad
- y claridad sobre cual es la verdadera fuente de verdad

---

## 8. Como se ve hoy Cortex a nivel empresa

```mermaid
flowchart TB
    subgraph P1["Proyecto A"]
        A1["vault A"]
        A2[".memory/chroma A"]
    end

    subgraph P2["Proyecto B"]
        B1["vault B"]
        B2[".memory/chroma B"]
    end

    subgraph P3["Proyecto C"]
        C1["vault C"]
        C2[".memory/chroma C"]
    end

    U["Agentes"] --> A1
    U --> A2
    U --> B1
    U --> B2
    U --> C1
    U --> C2

    W["WebGraph Federado"] --> A1
    W --> A2
    W --> B1
    W --> B2
    W --> C1
    W --> C2
```

### Que muestra este diagrama

- Hoy Cortex esta muy preparado para varios proyectos.
- Pero cada proyecto sigue teniendo su propia frontera natural de memoria.
- WebGraph puede federar observacion y analisis entre proyectos.
- Eso no equivale todavia a una unica memoria empresarial canonica de escritura y lectura.

### Conclusion honesta

Hoy Cortex soporta muy bien:

- multi-proyecto
- memoria modular
- conocimiento durable por repo
- observabilidad federada

Pero todavia no resuelve automaticamente:

- una macro memoria episodica corporativa unica
- una capa de promocion nativa entre memorias locales y memoria central

---

## 9. Como una empresa chica puede aproximarse hoy a la vision original

```mermaid
flowchart TB
    subgraph Shared["Memoria institucional compartida"]
        S1["Vault corporativo compartido"]
        S2["Patrones de negocio"]
        S3["Decisiones"]
        S4["Runbooks"]
        S5["HU / Incidentes"]
    end

    subgraph Proj1["Proyecto 1"]
        P1A[".memory/chroma local"]
        P1B["vault tecnico local"]
    end

    subgraph Proj2["Proyecto 2"]
        P2A[".memory/chroma local"]
        P2B["vault tecnico local"]
    end

    AG["Agentes"] --> S1
    AG --> P1A
    AG --> P1B
    AG --> P2A
    AG --> P2B

    P1B --> S1
    P2B --> S1
```

### Que muestra este diagrama

- Una empresa chica puede usar un vault corporativo compartido como memoria institucional.
- Cada proyecto conserva su memoria episodica local para no mezclar ruido.
- El conocimiento relevante se promueve al vault compartido cuando ya es durable.

### Por que esta opcion es sana

- minimiza complejidad
- evita que errores o sesiones locales contaminen a toda la empresa
- mantiene transversalidad donde mas valor aporta: patrones, decisiones, reglas de negocio y runbooks

---

## 10. Antes vs ahora: cambio conceptual

```mermaid
flowchart LR
    subgraph Antes["Vision inicial fuerte"]
        A1["Memoria hibrida empresarial total"]
        A2["Todo el conocimiento y decisiones deberian alimentar una unica memoria"]
        A3["Agentes consumen una memoria transversal comun"]
    end

    subgraph Ahora["Estado actual real"]
        B1["Memoria hibrida si"]
        B2["Pero con separacion entre durable y operativo"]
        B3["Y con modularidad fuerte por proyecto/rama"]
        B4["La transversalidad depende del diseno operativo"]
    end
```

### Lectura conceptual

La vision inicial no estaba equivocada.  
Lo que paso es que la implementacion real maduro hacia un modelo mas gobernable:

- menos monolitico
- mas trazable
- mas compatible con multi-proyecto
- y mas claro respecto de que debe ser patrimonio institucional y que no

### Sintesis

Antes el ideal era una gran memoria transversal unica.  
Ahora el sistema real funciona mejor como:

- memoria institucional durable compartida
- mas memorias episodicas modulares
- mas recuperacion hibrida unificada

---

## 11. Arquitectura objetivo recomendada

```mermaid
flowchart TB
    subgraph Enterprise["Capa empresarial canonica"]
        EV["Enterprise Vault<br/>conocimiento durable global"]
        EI["Enterprise Index Layer<br/>indice semantico corporativo"]
        EG["Enterprise Governance<br/>validacion, politicas, curacion"]
    end

    subgraph Delivery["Capa de proyectos"]
        subgraph PA["Proyecto A"]
            AV["Vault A"]
            AM["Episodic A<br/>.memory/chroma"]
        end
        subgraph PB["Proyecto B"]
            BV["Vault B"]
            BM["Episodic B<br/>.memory/chroma"]
        end
        subgraph PC["Proyecto C"]
            CV["Vault C"]
            CM["Episodic C<br/>.memory/chroma"]
        end
    end

    subgraph Promotion["Capa de promocion de conocimiento"]
        PR["Pipeline de promocion<br/>de local a corporativo"]
        CU["Curacion humana o asistida"]
    end

    subgraph Consumption["Capa de consumo"]
        AG["Agentes"]
        WG["WebGraph federado / observabilidad"]
        CT["SPEC / contexto / decisiones"]
    end

    AV --> PR
    BV --> PR
    CV --> PR
    PR --> CU
    CU --> EV
    EV --> EI
    EG --> EV
    EG --> EI

    AG --> AM
    AG --> BM
    AG --> CM
    AG --> EI
    AG --> EV

    WG --> AV
    WG --> AM
    WG --> BV
    WG --> BM
    WG --> CV
    WG --> CM
    WG --> EV

    EI --> CT
    EV --> CT
    AM --> CT
    BM --> CT
    CM --> CT
```

### Que propone esta arquitectura objetivo

- Mantener la memoria episodica cerca de cada proyecto.
- Mantener la memoria durable global en una capa empresarial canonica.
- Agregar una capa explicita de promocion y curacion.
- Permitir que los agentes lean tanto contexto local como contexto corporativo.
- Evitar que toda sesion, todo ruido o todo log termine contaminando la memoria institucional.

### Filosofia final de la arquitectura objetivo

La empresa no necesita una sola memoria plana.  
Necesita una arquitectura de memoria con niveles:

- memoria local de trabajo
- memoria documental de proyecto
- memoria institucional corporativa
- y reglas de promocion entre niveles

Ese modelo conserva el espiritu original de Cortex, pero lo vuelve sostenible, auditable y escalable.

---

## 12. Conclusiones finales

- Cortex hoy si tiene memoria hibrida real.
- Esa memoria hoy funciona mejor a nivel proyecto que a nivel empresa total automatica.
- El `vault/` representa mejor la memoria institucional durable que `.memory/chroma`.
- `.memory/chroma` representa mejor la memoria operativa persistente y buscable.
- ONNX hoy es el motor de embeddings, no la memoria empresarial en si misma.
- El CI hoy alimenta memoria y reindexa conocimiento, pero no construye por si solo una macro memoria corporativa canonica.
- La arquitectura objetivo mas sana no es una bolsa unica de todo, sino una memoria por capas con promocion de conocimiento hacia una capa empresarial durable.

---

## Archivo relacionado

Este documento complementa el avance general documentado en:

- [AVANCE-Alineacion-Fases-MultiProyecto-y-Gobernanza.md](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/AVANCE-Alineacion-Fases-MultiProyecto-y-Gobernanza.md)
