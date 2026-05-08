# Propuesta Arquitectónica: Git-Like Distributed Vault Enterprise

> **Versión:** 1.0-draft  
> **Fecha:** 2026-05-07  
> **Autor:** Análisis arquitectónico automatizado sobre código existente  
> **Estado:** Propuesta — sin modificaciones de código  
> **Premisa:** *"Llevar el concepto de vault empresarial lo más cerca de la lógica de Git posible"*

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Estado Actual Detallado de Vault Enterprise](#2-estado-actual-detallado-de-vault-enterprise)
   - 2.1 [Instalación y Bootstrap](#21-instalación-y-bootstrap)
   - 2.2 [Descubrimiento de Layout y Resolución de Paths](#22-descubrimiento-de-layout-y-resolución-de-paths)
   - 2.3 [Configuración Organizacional (org.yaml)](#23-configuración-organizacional-orgyaml)
   - 2.4 [Almacenamiento: Local vs Enterprise](#24-almacenamiento-local-vs-enterprise)
   - 2.5 [Motor de Retrieval y Búsqueda Híbrida](#25-motor-de-retrieval-y-búsqueda-híbrida)
   - 2.6 [Context Enricher: Inyección al Agente](#26-context-enricher-inyección-al-agente)
   - 2.7 [Pipeline de Promoción de Conocimiento](#27-pipeline-de-promoción-de-conocimiento)
   - 2.8 [Gobernanza, CI y Observabilidad](#28-gobernanza-ci-y-observabilidad)
   - 2.9 [Integración MCP e Inyección IDE](#29-integración-mcp-e-inyección-ide)
3. [La Premisa: Git-Like Vault Enterprise](#3-la-premisa-git-like-vault-enterprise)
4. [Mapeo Conceptual Git → Cortex Vault (Completo)](#4-mapeo-conceptual-git--cortex-vault-completo)
5. [Análisis de Brechas (Gap Analysis)](#5-análisis-de-brechas-gap-analysis)
6. [Grado de Dificultad por Componente](#6-grado-de-dificultad-por-componente)
7. [Arquitectura Target: Estados Futuros](#7-arquitectura-target-estados-futuros)
   - 7.1 [Fase 1: UX Layer — CLI Git-Like](#71-fase-1-ux-layer--cli-git-like)
   - 7.2 [Fase 2: Storage Layer — Git-Backed Vaults](#72-fase-2-storage-layer--git-backed-vaults)
   - 7.3 [Fase 3: Network Layer — Protocolo de Federación](#73-fase-3-network-layer--protocolo-de-federación)
   - 7.4 [Fase 4: Semantic Layer — Merge y Conflict Resolution](#74-fase-4-semantic-layer--merge-y-conflict-resolution)
8. [Especificación de Comandos Git-Like Propuestos](#8-especificación-de-comandos-git-like-propuestos)
9. [Riesgos, Trade-offs y Consideraciones](#9-riesgos-trade-offs-y-consideraciones)
10. [Conclusión y Recomendación](#10-conclusión-y-recomendación)

---

## 1. Resumen Ejecutivo

El sistema **Cortex Enterprise Memory** (completado en 7 Épicas, E1–E7) ya opera un modelo de memoria de dos niveles con analogía conceptual a Git: `vault/` como *working directory/local repo* y `vault-enterprise/` como *remote origin*. Sin embargo, esta analogía es **meramente documental y conceptual**. Los comandos, la semántica de almacenamiento, el protocolo de sincronización y el modelo de distribución **no son Git**.

Esta propuesta desglosa qué significaría llevar la analogía al extremo técnico: un sistema donde cada vault es conceptualmente un repositorio con historial, staging area, commits, branches, remotes, push/pull y merge semantics. Se analiza el estado actual al detalle (basado en inspección de código fuente), se cuantifica la distancia hasta el objetivo, se califica la dificultad y se propone un roadmap de transición en 4 fases.

**Hallazgo central:** La arquitectura actual está preparada para una **Fase 1 (UX Layer)** con esfuerzo bajo–medio. Las Fases 2–4 requieren rediseño de storage, networking y semantics, con complejidad alta a muy alta.

---

## 2. Estado Actual Detallado de Vault Enterprise

> Esta sección documenta exactamente cómo funciona el sistema hoy, basado en lectura directa de los módulos productivos. Se citan archivos y comportamientos observados sin modificación.

### 2.1 Instalación y Bootstrap

**Comando de entrada:** `cortex setup enterprise [opciones]`

- **Implementación:** `cortex/cli/main.py::setup_enterprise()` (l. 340–413) y `cortex/setup/orchestrator.py`.
- **Wizard interactivo:** `cortex/setup/enterprise_wizard.py` — pregunta perfil organizacional, nombre, CI profile, branch isolation.
- **Presets declarativos:** `cortex/setup/enterprise_presets.py` — soporta `small-company`, `multi-project-team`, `regulated-organization`, `custom`.
- **Generación de artefactos:**
  - `.cortex/org.yaml` (configuración enterprise)
  - `.cortex/vault-enterprise/` (directorio vacío o con README)
  - `.github/workflows/ci-enterprise-governance.yml`
  - `.cortex/workspace.yaml` (workspace federado)

**Observación técnica:** El setup **no inicializa un repositorio Git** en `vault-enterprise/`. Es un directorio plano de Markdown. La "promoción" no es un `git push`; es una **copia de archivos** con transformación de frontmatter.

### 2.2 Descubrimiento de Layout y Resolución de Paths

**Módulo clave:** `cortex/workspace/layout.py`

El sistema soporta dos layouts:

**New layout (v2+):**
```
repo-root/
  .cortex/                    ← workspace_root
    config.yaml
    vault/
    vault-enterprise/
    memory/
    org.yaml
    workspace.yaml
```

**Legacy layout:**
```
repo-root/
  config.yaml
  vault/
  vault-enterprise/
  .memory/
  .cortex/org.yaml
```

**Mecanismo:** `WorkspaceLayout.discover(start)` camina hacia arriba desde el directorio actual buscando `.cortex/workspace.yaml` (con `layout_version >= 2`), `.cortex/config.yaml`, o `config.yaml` en raíz. Resuelve rutas relativas contra `workspace_root`.

**Relevancia para Git-Like:** En Git, el `.git/` directory es el *object store* y el *index*. En Cortex, `.cortex/` contiene config y datos, pero **no tiene un object store versionado**. El `vault_index_path` (`vault/.cortex_index.json`) es un índice de búsqueda, no un historial de commits.

### 2.3 Configuración Organizacional (org.yaml)

**Módulo clave:** `cortex/enterprise/models.py` + `cortex/enterprise/config.py`

**Schema actual (v1):**

```yaml
schema_version: 1
organization:
  name: "Mi Empresa"
  slug: "mi-empresa"
  profile: "multi-project-team"   # small-company | multi-project-team | regulated-organization | custom
memory:
  mode: layered
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: memory/enterprise/chroma
  enterprise_semantic_enabled: true
  enterprise_episodic_enabled: false
  project_memory_mode: isolated
  branch_isolation_enabled: false
  retrieval_default_scope: all     # local | enterprise | all
  retrieval_local_weight: 1.0
  retrieval_enterprise_weight: 1.2
promotion:
  enabled: true
  allowed_doc_types: [spec, decision, runbook, hu, incident]
  require_review: true
  default_targets: [enterprise_vault]
governance:
  git_policy: balanced             # balanced | strict | custom
  ci_profile: advisory             # observability | advisory | enforced
  version_sessions_in_git: false
integration:
  github_actions_enabled: true
  webgraph_workspace_enabled: true
  ide_profiles: []
```

**Observación:** El campo `git_policy` es un nombre equívoco desde la perspectiva Git-Like: **no opera sobre el historial de Git del vault**. Solo determina si las sesiones se versionan en Git del *proyecto de código* (`.git/` del repo), no del vault como repo independiente.

### 2.4 Almacenamiento: Local vs Enterprise

**Vault Local (semántico):**
- Ruta: `WorkspaceLayout.vault_path` → `.cortex/vault/` (new) o `vault/` (legacy)
- Contenido: Markdown plano con frontmatter YAML
- Subcarpetas: `specs/`, `sessions/`, `decisions/`, `runbooks/`, `hu/`, `incidents/`
- Indexación: `cortex/semantic/vault_reader.py` — parsea Markdown, genera embeddings vía ONNX (`all-MiniLM-L6-v2`, 384 dims), almacena en ChromaDB local
- Index file: `.cortex_index.json` (no es un historial, es un cache de búsqueda)

**Memoria Episódica Local:**
- Ruta: `WorkspaceLayout.episodic_memory_path` → `.cortex/memory/` (ChromaDB)
- Backend: ChromaDB con colección `cortex_episodic`
- Embeddings: ONNX Runtime (<1ms latencia, ~50MB footprint)
- Namespace: configurable por proyecto o rama (`namespace_mode`)

**Vault Enterprise (semántico):**
- Ruta: `WorkspaceLayout.enterprise_vault_path` → `.cortex/vault-enterprise/`
- Estructura idéntica al local, pero organizada por proyecto al promocionar:
  ```
  vault-enterprise/
    specs/
      mi-proyecto/
        2026-04-30-auth-jwt.md
    decisions/
      mi-proyecto/
        ADR-001-hybrid-search.md
  ```
- **No hay ChromaDB enterprise por defecto** (`enterprise_episodic_enabled: false` en la mayoría de presets)

**Observación crítica:** El almacenamiento enterprise es **un filesystem plano compartido**. No hay:
- DAG de objetos (como Git)
- Referencias (refs/heads, refs/remotes)
- Packfiles o compresión delta
- Protocolo de transferencia
- Verificación criptográfica de contenido (solo SHA-256 de fingerprint para idempotencia de promoción)

### 2.5 Motor de Retrieval y Búsqueda Híbrida

**Módulos clave:**
- `cortex/retrieval/hybrid_search.py` — `HybridSearch` (local)
- `cortex/enterprise/retrieval_service.py` — `EnterpriseRetrievalService` (multi-nivel)
- `cortex/enterprise/sources.py` — `MultiVaultReader`, `MultiEpisodicReader`

**Flujo local (`scope=local`):**
```
query → HybridSearch.search()
  ├── episodic.search(query) → list[EpisodicHit]
  ├── semantic.search(query) → list[SemanticDocument]
  └── _rrf_fuse(episodic, semantic) → list[UnifiedHit]
```

**Fórmula RRF:** `score += weight / (60 + rank)`  
Donde `K=60` es la constante del paper original. Los pesos son adaptativos por intención de query (`cortex/retrieval/intent.py`).

**Flujo enterprise (`scope=enterprise|all`):**
```
query → AgentMemory.retrieve(scope=...)
  └── EnterpriseRetrievalService.search()
        ├── MultiVaultReader.search()     # lee vault local + vault enterprise
        ├── MultiEpisodicReader.search()  # lee ChromaDB local + enterprise (si habilitado)
        └── _fuse_multi_scope()           # RRF con pesos por scope (local_weight vs enterprise_weight)
```

**Metadata de origen:** Cada hit lleva `origin_scope`, `origin_project_id`, `origin_vault`, `origin_persist_dir`.

**Observación:** El retrieval enterprise es **lectura multi-fuente con fusión RRF**. No es un `git fetch` que traiga refs y objetos. Las fuentes se leen **in-place** en cada búsqueda. No hay cache de objetos traídos, no hay "working tree" que se actualice.

### 2.6 Context Enricher: Inyección al Agente

**Módulo clave:** `cortex/context_enricher/enricher.py` — `ContextEnricher`

**Pipeline de enriquecimiento (6 fases):**

1. **Observación:** `ContextObserver.observe_from_files()` analiza archivos modificados en git (staged, modified, untracked), extrae keywords, entidades (funciones, clases), PR metadata.
2. **Estrategias de búsqueda paralelas:**
   - `topic_search`: query semántica principal
   - `file_search`: nombres de archivos
   - `keyword_search`: términos extraídos
   - `pr_title_search`: título del PR/tarea
   - `entity_search`: funciones, clases, imports
3. **Deduplicación:** por `source_id` (path o mem_id)
4. **Multi-match boost:** `1.5^(n-1)` por cada estrategia adicional que matchee
5. **Co-occurrence boost:** grafo de archivos que aparecen juntos en memorias previas
6. **Budget enforcement:** `max_items` (default 8), `max_chars` (default 2000)

**Integración con agente:**
- **MCP Server:** `cortex/mcp/server.py` — `CortexMCPServer` expone `cortex_context` tool. El IDE llama a `memory.enrich(changed_files=...)` y recibe un `EnrichedContext` formateado como texto para inyección en el prompt del LLM.
- **Skill Pi:** `cortex-pi/.pi/skills/cortex-vault/SKILL.md` documenta al agente cuándo usar `cortex search`, `cortex context`, `cortex save-session`.

**Observación:** El enricher opera **exclusivamente sobre la memoria local del proyecto actual** (más el vault enterprise si `scope=all`). No hay concepto de `fetch` previo: si el vault enterprise no está localmente accesible (misma máquina, mismo filesystem), no puede enriquecer. No hay protocolo de red para traer contexto de un vault remoto.

### 2.7 Pipeline de Promoción de Conocimiento

**Módulos clave:**
- `cortex/enterprise/knowledge_promotion.py` — `KnowledgePromotionService`
- `cortex/enterprise/promotion_models.py` — modelos Pydantic

**Estados del pipeline:**

```
vault/doc.md  →  candidate  →  reviewed  →  promoted  →  vault-enterprise/
     (local)       (descubierto)  (aprobado)   (copiado)     (corporativo)
                    ↑ rejected
```

** Estados formales:** `draft`, `candidate`, `reviewed`, `promoted`, `rejected`

**Flujo técnico detallado:**

1. **Discovery:** `discover_candidates()` escanea `vault/**/*.md`.
   - Filtra por `promotion.allowed_doc_types` (default: spec, decision, runbook, hu, incident; **excluye session** a menos que se habilite)
   - Filtra paths internos (no `.cortex/`)
   - Valida con `DocValidator`
   - Calcula fingerprint SHA-256 del cuerpo normalizado
   - Genera `origin_id = "{project_slug}:{rel_path}"`

2. **Review:** `review(selector, approve, actor, reason)`
   - Requiere que no haya errores de validación
   - Genera `PromotionRecord` con evento `reviewed` o `rejected`
   - Persiste en `records.jsonl` (append-only, formato NDJSON)

3. **Promoción:** `apply_promotion(candidates, actor)`
   - Lee archivo fuente
   - Escribe en destino: `vault-enterprise/{family}/{project_slug}/{filename}`
   - **Upsert de frontmatter** de trazabilidad:
     ```yaml
     promotion_status: promoted
     promotion_origin_id: mi-proyecto:specs/2026-04-30-auth-jwt.md
     promotion_origin_path: specs/2026-04-30-auth-jwt.md
     promotion_origin_project: mi-proyecto
     promotion_fingerprint: sha256...
     promotion_promoted_at: 2026-04-30T12:00:00+00:00
     ```
   - Idempotencia: skip si ya está promovido con el mismo fingerprint

**Persistencia de records:**
- Ruta: `WorkspaceLayout.promotion_records_path` → `.cortex/vault-enterprise/promotion/records.jsonl`
- Formato: NDJSON (una línea por record)
- No hay historial de diff, no hay rollback nativo, no hay branches de promoción.

**Observación crítica:** La promoción es **copia unidireccional con metadata**. No es un `git push` que envíe objetos a un remote y actualice refs. No hay:
- Referencias simbólicas (refs/heads/main)
- Packfile negotiation
- Fast-forward vs non-fast-forward
- Pre-receive hooks (solo CI post-facto)
- Capacidad de "push force"

### 2.8 Gobernanza, CI y Observabilidad

**Doctor:** `cortex/doctor.py`
- Chequea existencia de `.cortex/org.yaml`
- Valida schema de `org.yaml`
- Verifica directorios de vault enterprise
- Valida markdown de vault local y enterprise (`vault_validation_errors`, `enterprise_vault_validation_errors`)

**Memory Report:** `cortex/enterprise/reporting.py` — `EnterpriseReportingService`
- `cortex memory-report --scope [local|enterprise|all]`
- Reporta: cantidad de archivos markdown, errores/warnings de validación, candidatos a promoción, últimos eventos de promoción
- Salida JSON estable para pipelines externos

**CI Enterprise:** `.github/workflows/ci-enterprise-governance.yml`
- Ejecuta `cortex doctor --scope enterprise`
- Ejecuta `cortex promote-knowledge --dry-run --json`
- Ejecuta `cortex sync-enterprise-vault --json`
- Enforcement condicional por `ci_profile`: `observability` (solo log), `advisory` (warn), `enforced` (fail CI)

**Observación:** La gobernanza opera sobre **el estado actual del filesystem y los records.jsonl**. No hay un DAG de commits que auditar, no hay firmas GPG, no hay `git log --oneline` de promociones.

### 2.9 Integración MCP e Inyección IDE

**MCP Server:** `cortex/mcp/server.py` — `CortexMCPServer`

**Tools expuestas:**
- `cortex_search` / `cortex_search_vector` — búsqueda híbrida
- `cortex_context` — enriquecimiento proactivo
- `cortex_sync_ticket` — preparación de spec con contexto histórico
- `cortex_create_spec` — crear especificación
- `cortex_save_session` — guardar sesión
- `cortex_sync_vault` — re-indexar vault

**Governance en MCP:** El server rastrea `_called_tools` en memoria de sesión. `cortex_create_spec` **rechaza la llamada** si `cortex_sync_ticket` no fue invocado primero (hard validation de flujo).

**Inyección IDE:**
- `cortex inject --ide <name>` inyecta perfiles de agente en IDEs soportados (Cursor, VSCode/Cline, Claude Desktop, OpenCode)
- Los perfiles apuntan al MCP server local

**Observación:** Todo el sistema MCP asume que el vault es **local al proceso**. El `project_root` se resuelve al iniciar el server. No hay routing dinámico a múltiples vaults remotos.

---

## 3. La Premisa: Git-Like Vault Enterprise

> "Intentar llevar el concepto de vault empresarial lo más cerca de la lógica de Git posible"

### Qué significa esto en la práctica

Git es un sistema de archivos de contenido direccionable con:
1. **Object store:** blobs, trees, commits, tags (DAG inmutable)
2. **Referencias mutables:** branches, remotes, HEAD
3. **Staging area (index):** espacio intermedio entre working tree y repo
4. **Protocolo de transferencia:** push/pull/fetch/clone sobre HTTPS/SSH/git
5. **Merge semantics:** three-way merge, fast-forward, conflict markers
6. **Distribución total:** cada clon es un repositorio completo (historial + refs)

Para Cortex, "Git-Like" implica que el **vault de conocimiento** (local y enterprise) debería comportarse como un repositorio Git, donde:
- Cada documento es un objeto direccionable por contenido
- Cada "sesión de trabajo" es un commit con mensaje
- La promoción a enterprise es un `push` a un remote
- Traer conocimiento de otro proyecto es un `fetch`/`pull`
- El agente puede "clonar" un vault remoto para enriquecerse
- Existe un `status` que muestra qué conocimiento está pendiente de promocionar
- Existe un `log` que muestra el historial de cambios de conocimiento
- Existe un `diff` entre local y enterprise

### Analogía actual (documentada pero no implementada técnicamente)

La documentación ya presenta esta tabla (de `docs/guides/enterprise-vault.md`):

| Concepto Git | Concepto Cortex Enterprise |
|-------------|---------------------------|
| Repo local (`.git/`) | `.cortex/vault/` |
| Repo remoto (origin) | `.cortex/vault-enterprise/` |
| `git commit` | `cortex save-session` / `create-spec` |
| `git push` | `cortex promote-knowledge` |
| `git pull` / `git fetch` | `cortex search --scope all` |
| Pull Request | `cortex review-knowledge` |
| Feature branch | Vault de un proyecto individual |
| `main` / `master` | `.cortex/vault-enterprise/` |
| `.gitignore` | `.cortex/memory/` |
| `git clone` + rebuild | `cortex sync-vault` |

**Problema:** Esta analogía es **cosmética**. `cortex search --scope all` no es un `git fetch`; es una búsqueda vectorial que lee archivos planos. `cortex promote-knowledge` no es un `git push`; es una copia de archivos con frontmatter inyectado. No hay historial, no hay refs, no hay protocolo.

---

## 4. Mapeo Conceptual Git → Cortex Vault (Completo)

Este mapeo representa el **estado objetivo** de la premisa Git-Like:

### 4.1 Object Model

| Git Object | Cortex Equivalente Propuesto | Descripción |
|-----------|------------------------------|-------------|
| **Blob** | `KnowledgeBlob` | Contenido normalizado de un documento Markdown (body sin frontmatter, LF-normalizado) |
| **Tree** | `KnowledgeTree` | Snapshot de un subdirectorio del vault (specs/, sessions/, etc.) en un momento dado |
| **Commit** | `KnowledgeCommit` | Snapshot del vault completo + autor + timestamp + mensaje + parent(s) |
| **Tag** | `KnowledgeTag` | Referencia inmutable a un commit (ej: `v1.0-release`, `audit-2026-Q2`) |
| **Ref** | `KnowledgeRef` | Branch (`refs/heads/main`) o Remote tracking (`refs/remotes/origin/main`) |
| **Index** | `PromotionIndex` / `StagingArea` | Estado intermedio de documentos marcados para promoción |

### 4.2 Comandos Core

| Comando Git | Comando Cortex Propuesto | Semántica Actual | Semántica Git-Like Target |
|-------------|-------------------------|------------------|---------------------------|
| `git init` | `cortex init` | Crea config, vault, memory | **Igual**, pero inicializa object store + refs |
| `git add <file>` | `cortex add <path>` | *No existe* | Marca documento en el Promotion Index |
| `git status` | `cortex status` | *No existe* | Muestra: modified, staged, untracked, ahead/behind de remotes |
| `git commit -m "msg"` | `cortex commit -m "msg"` | Alias de `save-session` | Crea un `KnowledgeCommit` con snapshot completo del vault |
| `git log` | `cortex log` | *No existe* | Muestra historial de commits del vault (no del repo de código) |
| `git diff` | `cortex diff` | *No existe* | Diff entre working tree y HEAD, o entre local y remote |
| `git branch` | `cortex branch` | *No existe* | Lista/crea/elimina branches de conocimiento |
| `git checkout <branch>` | `cortex checkout <branch>` | *No existe* | Cambia el vault activo a otra branch |
| `git merge <branch>` | `cortex merge <branch>` | *No existe* | Fusiona conocimiento de otra branch (three-way merge semántico) |
| `git remote -v` | `cortex remote -v` | *No existe* | Lista vaults enterprise remotos configurados |
| `git remote add <name> <url>` | `cortex remote add <name> <url>` | *No existe* | Registra un vault enterprise remoto |
| `git push [remote] [branch]` | `cortex push [remote] [branch]` | `promote-knowledge --apply` | Envía commits locales al remote; actualiza refs |
| `git fetch [remote]` | `cortex fetch [remote]` | *No existe* | Trae refs y objetos del remote sin mergear |
| `git pull [remote] [branch]` | `cortex pull [remote] [branch]` | `search --scope all` (parcial) | Trae y mergea conocimiento del remote |
| `git clone <url>` | `cortex clone <url>` | *No existe* | Clona un vault enterprise completo como proyecto local |
| `git stash` | `cortex stash` | *No existe* | Guarda temporalmente cambios del working tree |
| `git stash pop` | `cortex stash pop` | *No existe* | Restaura cambios stashed |
| `.gitignore` | `.cortexignore` | `.gitignore` sugiere ignorar `.memory/` | Archivo específico de Cortex para excluir paths del vault |

### 4.3 Flujos de Trabajo Objetivo

**Flujo de trabajo diario (desarrollador):**
```bash
# Trabajo en una feature
cortex checkout -b feature/auth-jwt          # Branch de conocimiento
cortex add vault/sessions/2026-05-07-auth.md  # Stage del documento
cortex commit -m "feat: investigación preliminar de OAuth2 vs JWT"

# Más trabajo...
cortex add vault/specs/2026-05-07-auth-spec.md
cortex commit -m "spec: especificación técnica de auth con refresh tokens"

# Preparar promoción
cortex status                                    # Ver qué commits faltan push
cortex log --oneline origin/main..HEAD           # Ver commits locales no promocionados
cortex push origin main                          # Promociona al enterprise
```

**Flujo de trabajo cross-project (arquitecto):**
```bash
# Ver vaults remotos disponibles
cortex remote -v
# origin    file:///shared/vault-enterprise/ (fetch/push)
# auth-team https://vaults.cortex.internal/auth-team (fetch/push)

# Traer conocimiento de otro equipo sin mergear aún
cortex fetch auth-team
cortex log auth-team/main --oneline              # Ver qué saben

# Mergear patrones de auth
cortex merge auth-team/main --into specs/decisions/
```

**Flujo de enriquecimiento del agente (MCP):**
```bash
# El agente, antes de responder, hace:
cortex fetch origin                              # Asegura tener último enterprise
cortex context --files src/auth/middleware.ts    # Enriquece con local + enterprise actualizado
```

---

## 5. Análisis de Brechas (Gap Analysis)

### 5.1 Brechas por Capa

#### Capa de Almacenamiento (Storage Layer)

| # | Brecha | Estado Actual | Estado Git-Like Target | Severidad |
|---|--------|---------------|------------------------|-----------|
| S1 | **Object Store** | Filesystem plano (Markdown + frontmatter) | DAG de objetos inmutables (blobs, trees, commits) por vault | Alta |
| S2 | **Direccionamiento por contenido** | SHA-256 solo en fingerprint de promoción | Todo objeto direccionado por hash criptográfico (SHA-256 o BLAKE3) | Alta |
| S3 | **Historial de versiones** | Ninguno por documento; solo `records.jsonl` de promociones | Cada documento tiene historial completo de ediciones (commit graph) | Alta |
| S4 | **Refs y Branches** | Ninguno; `branch_isolation_enabled` solo filtra por rama Git del código | Branches de conocimiento propios (`main`, `feature/x`, `release/y`) | Media-Alta |
| S5 | **Staging Area / Index** | Ninguno; promoción escanea todo el vault | `PromotionIndex` que lista objetos staged para el próximo commit/push | Media |
| S6 | **Compresión y packfiles** | Ninguna; archivos Markdown planos | Packfiles de objetos para eficiencia de storage y transferencia | Media |

#### Capa de Protocolo y Red (Network Layer)

| # | Brecha | Estado Actual | Estado Git-Like Target | Severidad |
|---|--------|---------------|------------------------|-----------|
| N1 | **Protocolo de transferencia** | Ninguno; copia local de archivos | Protocolo `cortex://` o HTTP/2 para exchange de objetos y refs | Alta |
| N2 | **Operación fetch** | `search --scope all` lee archivos planos locales | `cortex fetch` traer objetos nuevos del remote y actualizar refs remotas | Alta |
| N3 | **Operación push** | `promote-knowledge` copia archivos con frontmatter | `cortex push` envía objetos locales al remote; negociación de refs; fast-forward check | Alta |
| N4 | **Operación clone** | `cortex sync-vault` re-indexa desde archivos locales | `cortex clone <url>` descarga object store completo + refs | Alta |
| N5 | **Autenticación y autorización** | Ninguna (asume filesystem compartido o acceso al repo) | Auth por token/SSH similar a Git; ACLs por rama/documento | Media-Alta |
| N6 | **Multi-remote** | Ninguno; solo un `enterprise_vault_path` en `org.yaml` | Múltiples remotes configurables (`cortex remote add`) | Media |

#### Capa de Semántica y Merge (Semantic Layer)

| # | Brecha | Estado Actual | Estado Git-Like Target | Severidad |
|---|--------|---------------|------------------------|-----------|
| M1 | **Merge de conocimiento** | Ninguno; promoción sobrescribe si fingerprint cambia | Three-way merge semántico de Markdown (secciones, frontmatter, body) | Muy Alta |
| M2 | **Conflict resolution** | Ninguno; manual (revisar y rechazar en review) | Markers de conflicto en Markdown + herramientas de resolución | Muy Alta |
| M3 | **Diff semántico** | Ninguno; comparación por fingerprint SHA-256 completo | Diff estructurado por secciones de Markdown (frontmatter, headers, código) | Media-Alta |
| M4 | **Rebase / cherry-pick** | Ninguno | Mover/replicar commits de conocimiento entre branches | Media |

#### Capa de UX y CLI (UX Layer)

| # | Brecha | Estado Actual | Estado Git-Like Target | Severidad |
|---|--------|---------------|------------------------|-----------|
| U1 | **Comando `add`** | No existe | `cortex add <path>` para staging | Baja |
| U2 | **Comando `status`** | No existe | `cortex status` para ver estado del working tree vs HEAD | Baja |
| U3 | **Comando `commit`** | `save-session` / `create-spec` (guardan archivos, no commits) | `cortex commit -m` que cree objeto commit + actualice HEAD | Media |
| U4 | **Comando `log`** | `memory-report` muestra eventos recientes | `cortex log` con grafo de commits del vault | Media |
| U5 | **Comando `diff`** | No existe | `cortex diff` entre working tree, commits, branches, remotes | Media |
| U6 | **Comando `push`** | `promote-knowledge --apply` | `cortex push` con semántica Git completa | Media-Alta |
| U7 | **Comando `pull/fetch`** | `search --scope all` | `cortex fetch` / `cortex pull` | Media-Alta |
| U8 | **Comando `clone`** | No existe | `cortex clone <url>` | Media |
| U9 | **Comando `branch/checkout`** | No existe | `cortex branch` / `cortex checkout` | Media |
| U10 | **Comando `stash`** | No existe | `cortex stash` / `cortex stash pop` | Baja |
| U11 | **Archivo `.cortexignore`** | No existe; `.gitignore` parcial | `.cortexignore` específico del vault | Baja |

#### Capa de Retrieval y Agente (Retrieval Layer)

| # | Brecha | Estado Actual | Estado Git-Like Target | Severidad |
|---|--------|---------------|------------------------|-----------|
| R1 | **Contexto post-fetch** | Enricher lee archivos planos locales | Enricher opera sobre object store local (más eficiente) | Media |
| R2 | **Búsqueda en historial** | `cortex search` solo busca en estado actual | `cortex search` puede buscar en cualquier commit del pasado | Media |
| R3 | **Embeddings versionados** | ChromaDB se re-indexa desde archivos actuales | Embeddings persistidos por commit; checkout de embeddings históricos | Alta |

### 5.2 Matriz de Proximidad

```
                    Baja Dificultad                          Alta Dificultad
                    ┌─────────────────────────────────────────────────────────┐
Bajo Impacto        │ .cortexignore    cortex status    cortex log (básico)   │
                    │ cortex add       cortex stash     cortex diff (simple)  │
                    │                                                         │
                    ├─────────────────────────────────────────────────────────┤
Alto Impacto        │ cortex commit    cortex push      Protocolo de red       │
                    │ (sobre archivos) (sobre copia)   Object store DAG        │
                    │                                                         │
                    │ cortex fetch     Multi-remote     Merge semántico        │
                    │ (sobre archivos) (path-based)    Conflict resolution     │
                    └─────────────────────────────────────────────────────────┘
```

**Interpretación:** Las funcionalidades en la esquina superior izquierda se pueden implementar rápido sin cambiar la arquitectura subyacente. Las de la esquina inferior derecha requieren rediseño fundamental.

---

## 6. Grado de Dificultad por Componente

### 6.1 Escala de Dificultad

- **🟢 Fácil (1–2 semanas):** No requiere cambios de arquitectura; principalmente CLI wrappers, aliases o persistencia simple adicional.
- **🟡 Medio (2–6 semanas):** Requiere extensión de modelos, nuevos servicios, integración con storage existente.
- **🟠 Difícil (1–3 meses):** Requiere diseño de nuevos subsistemas, cambios en el modelo de datos, posibles migraciones.
- **🔴 Muy Difícil (3–6 meses):** Requiere investigación, prototipado, posible cambio de backend de almacenamiento o protocolos de red.
- **⚫ Extremo (6+ meses):** Requiere R&D, puede involucrar crear tecnología nueva (merge semantics de conocimiento, distributed consensus).

### 6.2 Calificación por Comando/Funcionalidad

| Funcionalidad | Dificultad | Rationale |
|--------------|------------|-----------|
| `cortex add` | 🟢 Fácil | Persistir lista de paths en un archivo de staging (`promotion_index.json` o similar). El servicio de promoción ya escanea candidatos; solo hay que filtrar por índice explícito. |
| `cortex status` | 🟢 Fácil | Comparar: (a) archivos en vault vs último fingerprint en records, (b) archivos staged vs unstaged. Puro análisis de filesystem + records.jsonl. |
| `cortex log` | 🟡 Medio | Requiere parsear `records.jsonl` y presentarlo como log. Para un log "de verdad" (commit graph) requeriría object store. |
| `cortex diff` | 🟡 Medio | Diff de archivos Markdown plano es trivial (difflib). Diff semántico por secciones requiere parser Markdown más sofisticado. |
| `cortex commit` | 🟡 Medio–Difícil | Si "commit" solo agrupa save-session + sync-vault + marca en records, es medio. Si commit crea objeto inmutable en DAG, es difícil. |
| `cortex branch / checkout` | 🟡 Medio–Difícil | Requiere aislar múltiples "líneas de conocimiento". Podría implementarse como subdirectorios (`vault-branches/feature-x/`) o como refs en object store. |
| `cortex stash` | 🟢 Fácil | Copiar archivos modificados a `.cortex/stash/` con timestamp; restaurar desde allí. |
| `.cortexignore` | 🟢 Fácil | Agregar patrón de ignore al scanner de vault (`vault_reader.py`, `knowledge_promotion.py`). |
| `cortex push` (mejorado) | 🟠 Difícil | Reemplazar copia de archivos por protocolo de transferencia de objetos + negociación de refs. Requiere rediseño del pipeline de promoción. |
| `cortex fetch / pull` | 🟠 Difícil | Requiere protocolo inverso: traer objetos del remote. Sin object store, "fetch" es solo copiar archivos desde otra ruta. |
| `cortex clone` | 🟠 Difícil | Descargar vault completo + configuración. Si el remote es filesystem local, es medio. Si es URL remota, requiere protocolo. |
| `cortex remote` | 🟡 Medio | Extender `org.yaml` para soportar múltiples remotes. Cambiar `EnterpriseOrgConfig` y `EnterpriseRetrievalService` para iterar múltiples fuentes. |
| **Object Store (Git internals)** | 🔴 Muy Difícil | Crear DAG de blobs/trees/commits para Markdown. Requiere reemplazar o complementar el storage plano actual. |
| **Protocolo de red (`cortex://`)** | 🔴 Muy Difícil | Diseñar e implementar protocolo de transferencia. HTTPS/2 con smart negotiation similar a Git HTTP smart protocol. |
| **Merge semántico de conocimiento** | ⚫ Extremo | Requiere entender estructura semántica de Markdown (headers, frontmatter, listas, bloques de código) para hacer three-way merge no destructivo. Es un problema de NLP + estructura de documentos. |
| **Conflict resolution UI** | 🟠 Difícil | Markers `<<<<<<<` en Markdown + herramientas CLI/IDE para resolver. Técnicamente no es tan complejo, pero el UX es crítico. |
| **Embeddings versionados por commit** | 🟠 Difícil | Actualmente ChromaDB se re-indexa desde archivos. Versionar embeddings requiere snapshots de la colección o re-indexación por checkout. |

---

## 7. Arquitectura Target: Estados Futuros

### 7.1 Fase 1: UX Layer — CLI Git-Like

**Objetivo:** Dar la experiencia de usuario de Git sin cambiar el storage subyacente.

**Implementación:**
- Nuevos comandos CLI que operan sobre el **modelo actual** (archivos planos + records.jsonl).
- `cortex add`, `cortex status`, `cortex log`, `cortex diff`, `cortex stash`, `.cortexignore`.
- `cortex commit` como alias mejorado de `save-session` + `sync-vault` + registro en `records.jsonl`.
- `cortex push` mejora `promote-knowledge` con staging explícito (solo los `add`ed).
- `cortex fetch` como descubrimiento de vaults remotos vía filesystem o HTTP simple.

**Cambios de código estimados:**
- Extender `cortex/cli/main.py` con ~8 nuevos comandos.
- Crear `cortex/gitlike/` paquete con:
  - `staging.py` — `StagingArea` (lee/escribe índice de paths staged)
  - `status.py` — `StatusService` (compara working tree vs último commit/promotion)
  - `log.py` — `LogFormatter` (pretty-print de records.jsonl)
  - `diff.py` — `DiffService` (comparación de archivos Markdown)
  - `stash.py` — `StashService` (copia a `.cortex/stash/`)
- Modificar `KnowledgePromotionService` para respetar el staging area (solo promover staged).

**Mantener compatibilidad:** `promote-knowledge` y `review-knowledge` siguen funcionando. `cortex push` es un frontend de `promote-knowledge` con staging.

**Tiempo estimado:** 3–4 semanas.

### 7.2 Fase 2: Storage Layer — Git-Backed Vaults

**Objetivo:** Reemplazar (o complementar) el filesystem plano por un object store Git-Like.

**Implementación:**
- Crear `cortex/object_store/` paquete:
  - `objects.py` — `Blob`, `Tree`, `Commit`, `Tag` (inmutables, direccionados por hash)
  - `refs.py` — `Refs` (mutable, almacena branches, HEAD, remotes)
  - `repository.py` — `KnowledgeRepository` (API para leer/escribir objetos y refs)
  - `packfile.py` — `PackfileReader/Writer` (opcional, para eficiencia)
- Cada vault (local y enterprise) tiene un `.cortex/vault.git/` (o similar) con object store.
- El "working tree" sigue siendo los archivos Markdown planos (para legibilidad humana), pero:
  - `cortex commit` crea objetos en el store y actualiza HEAD.
  - `cortex checkout` restaura working tree desde un commit.
  - `cortex log` lee el grafo de commits real.
- Los embeddings de ChromaDB se asocian a un `commit_hash` para poder re-hidratar por checkout.

**Cambios profundos:**
- `VaultReader` debe poder leer desde working tree **o** desde un Tree object.
- `KnowledgePromotionService` envía objetos (no archivos) al enterprise vault.
- `records.jsonl` se vuelve obsoleto; el historial está en el DAG de commits.

**Tiempo estimado:** 2–3 meses.

### 7.3 Fase 3: Network Layer — Protocolo de Federación

**Objetivo:** Permitir que los vaults se comuniquen remotamente, no solo por filesystem compartido.

**Implementación:**
- Extender `org.yaml` para múltiples remotes:
  ```yaml
  remotes:
    origin:
      url: https://vaults.cortex.internal/mi-empresa
      auth: token
    auth-team:
      url: https://vaults.cortex.internal/equipo-auth
      auth: token
  ```
- Crear `cortex/protocol/` paquete:
  - `transport.py` — abstracción HTTP/2, WebSocket, o filesystem
  - `negotiation.py` — descubrimiento de refs y objetos que faltan (similar a `git fetch-pack` / `git upload-pack`)
  - `client.py` — `CortexProtocolClient`
  - `server.py` — `CortexProtocolServer` (opcional, para self-hosted vault registry)
- `cortex fetch` negocia objetos faltantes y los trae al object store local.
- `cortex push` envía objetos locales y actualiza refs en el remote.
- `cortex clone` descarga object store + refs + working tree.

**Cambios profundos:**
- `EnterpriseRetrievalService` usa el protocolo para traer objetos antes de buscar.
- El MCP server puede operar sobre vaults remotos (con cache local).

**Tiempo estimado:** 2–4 meses.

### 7.4 Fase 4: Semantic Layer — Merge y Conflict Resolution

**Objetivo:** Permitir que el conocimiento de diferentes fuentes se fusione inteligentemente.

**Implementación:**
- `cortex merge <branch>`:
  - Encuentra base común (merge base) en el DAG de commits.
  - Realiza three-way merge de los Tree objects.
  - Para cada archivo conflictivo, aplica **merge semántico de Markdown**:
    - Frontmatter: merge key-by-key
    - Headers (##): merge por sección; si ambos editaron misma sección → conflicto
    - Listas: merge por item (si no hay duplicados exactos)
    - Bloques de código: conflicto si ambos modificaron
    - Párrafos: diff a nivel de oración
- Conflicts se marcan con `<<<<<<< HEAD` / `=======` / `>>>>>>> branch` en Markdown.
- `cortex merge-tool` abre (o genera) una vista de resolución.
- Post-merge: crea commit de merge con dos parents.

**Cambios profundos:**
- Requiere parser Markdown estructural (no solo regex).
- Requiere algoritmo de diff de árboles de documentos.
- Potencialmente requiere LLM para semantic merge de párrafos (fallback).

**Tiempo estimado:** 3–6 meses (investigación + implementación).

---

## 8. Especificación de Comandos Git-Like Propuestos

### 8.1 Comandos de Working Tree

#### `cortex add <path> [...]`

**Descripción:** Agrega uno o más documentos del vault al Promotion Index (staging area) para ser incluidos en el próximo `commit` o `push`.

**Comportamiento:**
- Crea/actualiza `.cortex/promotion_index.json` (o similar).
- Guarda: `path`, `fingerprint`, `staged_at`.
- Si el archivo no está en vault, error.
- Si el archivo ya está staged y no cambió, no-op.
- Soporta wildcards: `cortex add vault/sessions/*.md`.

**Relación con código actual:**
- Reemplaza el discovery automático de `KnowledgePromotionService.discover_candidates()` por un discovery dirigido por el usuario, idéntico a `git add`.

#### `cortex status`

**Descripción:** Muestra el estado del working tree del vault respecto al último commit/promoción.

**Salida propuesta:**
```
On branch main
Your branch is ahead of 'origin/main' by 2 commits.

Changes to be promoted:
  (use "cortex reset <file>..." to unstage)
        new:   specs/2026-05-07-auth-jwt.md
        mod:   decisions/ADR-001.md

Changes not staged for promotion:
  (use "cortex add <file>..." to stage)
        mod:   sessions/2026-05-07-tarde.md

Untracked knowledge:
  (use "cortex add <file>..." to include)
        runbooks/deploy-kubernetes.md
```

**Implementación:**
- Lee `promotion_index.json`.
- Compara fingerprints de archivos en vault contra último `PromotionRecord` por `origin_id`.
- Clasifica: staged, unstaged (modified), untracked.

#### `cortex diff [<commit>] [-- <path>]`

**Descripción:** Muestra diferencias entre working tree y un commit, o entre dos commits.

**Modos:**
- `cortex diff` — working tree vs último commit local
- `cortex diff HEAD~1` — working tree vs commit anterior
- `cortex diff origin/main` — working tree vs remote
- `cortex diff branch-a branch-b` — diff entre dos branches

**Formato de salida:**
```diff
--- a/specs/2026-05-07-auth-jwt.md
+++ b/specs/2026-05-07-auth-jwt.md
@@ -3,7 +3,7 @@
 title: Auth JWT
 ---
 
-Usaremos OAuth2.
+Usaremos JWT con refresh tokens por seguridad y simplicidad.
 
 ## Archivos relevantes
```

### 8.2 Comandos de Historial

#### `cortex commit [-m <msg>] [--amend]`

**Descripción:** Crea un nuevo commit de conocimiento.

**Comportamiento Fase 1 (sobre archivos):**
- Si no hay `-m`, abre editor (o usa default: "Knowledge update {timestamp}").
- Crea un `PromotionRecord` con status=`committed` (nuevo estado intermedio).
- Asocia todos los archivos staged al record.
- Opcionalmente ejecuta `sync_vault()` para re-indexar embeddings.
- Limpia staging area.

**Comportamiento Fase 2 (sobre object store):**
- Crea objetos `Blob` (contenido de cada archivo staged).
- Crea objeto `Tree` (snapshot del vault).
- Crea objeto `Commit` (tree + parent + mensaje + autor + timestamp).
- Actualiza ref `HEAD` y la branch actual.

#### `cortex log [--oneline] [--graph] [<branch>]`

**Descripción:** Muestra el historial de commits del vault.

**Salida Fase 1 (sobre records.jsonl):**
```
commit prj:specs/2026-05-07-auth-jwt.md (promoted)
Author: alice
Date:   2026-05-07 14:30 UTC

    feat: especificación de autenticación JWT

commit prj:decisions/ADR-001.md (reviewed)
Author: bob
Date:   2026-05-06 09:15 UTC

    adr: migración a ONNX Runtime
```

**Salida Fase 2 (sobre DAG):**
```
* a1b2c3d feat: especificación de autenticación JWT
* e4f5g6h adr: migración a ONNX Runtime
| * h7i8j9k fix: corrección en runbook de deploy
|/
* l0m1n2o chore: inicialización del vault enterprise
```

### 8.3 Comandos de Remotos y Transferencia

#### `cortex remote [-v | add <name> <url> | remove <name> | show <name>]`

**Descripción:** Gestiona los vaults enterprise remotos.

**Ejemplo:**
```bash
cortex remote add origin https://vaults.internal/mi-empresa
cortex remote add auth-team https://vaults.internal/auth-team
cortex remote -v
# origin    https://vaults.internal/mi-empresa (fetch/push)
# auth-team https://vaults.internal/auth-team (fetch/push)
```

**Impacto en config:**
- Extiende `org.yaml` con sección `remotes` (actualmente solo hay un `enterprise_vault_path` implícito que actúa como `origin`).

#### `cortex fetch [<remote>]`

**Descripción:** Trae refs y objetos del remote sin mergear al working tree.

**Fase 1 (sobre archivos):**
- Para filesystem: sincroniza archivos del remote al local (rsync-like).
- Para HTTP: descarga índice de documentos disponibles.

**Fase 2 (sobre object store):**
- Negocia refs con el remote.
- Trae objetos commits/trees/blobs faltantes.
- Actualiza `refs/remotes/<remote>/<branch>`.

#### `cortex pull [<remote> [<branch>]]`

**Descripción:** `fetch` + merge al working tree actual.

**Comportamiento:**
- Trae conocimiento del remote.
- Si no hay conflictos, fast-forward merge.
- Si hay conflictos, marca con conflict markers y pide `cortex merge --continue`.

#### `cortex push [<remote> [<branch>]]`

**Descripción:** Envía commits locales al remote.

**Fase 1 (sobre archivos):**
- Equivalente mejorado a `promote-knowledge --apply`.
- Solo envía archivos que estén en commits locales no presentes en remote.
- Requiere review si `require_review=true` en `org.yaml`.
- Verifica fast-forward (no permite sobrescribir historial remoto).

**Fase 2 (sobre object store):**
- Negocia objetos con remote.
- Envía commits, trees, blobs locales.
- Actualiza ref en remote (si fast-forward y permisos OK).
- Genera pre-receive hooks (validación de schema, lint).

#### `cortex clone <url> [<directory>]`

**Descripción:** Clona un vault enterprise completo.

**Fase 1:**
- Descarga archivos Markdown del remote.
- Crea `org.yaml` con remote pre-configurado.
- Ejecuta `sync-vault`.

**Fase 2:**
- Descarga object store completo.
- Chequea working tree desde HEAD.
- Configura remote `origin`.

### 8.4 Comandos de Branching

#### `cortex branch [<name> | -d <name> | -m <old> <new>]`

**Descripción:** Gestiona branches de conocimiento.

**Semántica:**
- Un branch es una línea independiente de evolución del vault.
- `branch_isolation_enabled` actual (que filtra por rama Git) podría migrar a este modelo nativo.
- Cada branch tiene su propio subdirectorio en ChromaDB o su propia colección.

**Ejemplo:**
```bash
cortex branch                    # lista branches
cortex branch feature/auth-jwt   # crea branch desde HEAD
cortex checkout feature/auth-jwt # cambia a branch
cortex checkout -b hotfix/login  # crea y cambia
```

### 8.5 Comandos Avanzados

#### `cortex merge <branch>`

**Descripción:** Fusiona otra branch (o remote/branch) en la actual.

**Fase 1:** No aplica (sin object store no hay merge real).

**Fase 2:**
- Encuentra merge base.
- Three-way merge de trees.
- Semantic merge de Markdown.
- Si clean: crea commit de merge.
- Si conflictos: pausa, marca archivos, pide resolución manual.

#### `cortex stash [push | pop | list | drop]`

**Descripción:** Guarda temporalmente cambios no commiteados.

**Implementación Fase 1:**
- `cortex stash push`: copia archivos modificados (working tree diff vs HEAD) a `.cortex/stash/{timestamp}/`. Restaura working tree a HEAD.
- `cortex stash pop`: aplica el stash más reciente y lo elimina.
- `cortex stash list`: muestra stashes disponibles.

---

## 9. Riesgos, Trade-offs y Consideraciones

### 9.1 Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Complejidad excesiva** | Alta | Alto | Implementar por fases; mantener modo "simple" (archivos planos) como default; Git-Like como capa opt-in |
| **Performance de object store** | Media | Alto | Usar packfiles; cache LRU; no versionar embeddings como objetos (solo referenciarlos) |
| **Merge semántico inestable** | Media | Muy Alto | Fallback a conflict markers; usar LLM como asistente, no como decisor único |
| **Backward compatibility rota** | Baja–Media | Alto | `org.yaml` `schema_version` incrementado; migración automática de `records.jsonl` a object store |
| **Sobrecarga cognitiva para usuarios** | Alta | Medio | Documentar claramente cuándo usar Git-Like vs modo simple; presets que deshabilitan Git-Like para small-company |

### 9.2 Trade-offs Arquitectónicos

**Object Store vs Filesystem Plano:**
- *Pro object store:* Historial real, branching, diff eficiente, integridad criptográfica, distribución nativa.
- *Contra object store:* Complejidad, herramientas de debugging más difíciles, curva de aprendizaje, overhead para usuarios simples.
- *Recomendación:* **Capa dual**. El working tree sigue siendo Markdown plano (legible, editable en Obsidian/VSCode). El object store es una capa transparente bajo `.cortex/vault.git/` que solo se expone vía CLI.

**Protocolo propio vs Git nativo:**
- *Opción A (Reusar Git):* Inicializar `vault-enterprise/` como repo Git real; usar `git push`/`git pull` subyacente. Cortex solo añade semantic layer.
  - Pros: Protocolo maduro, herramientas existentes (GitHub, GitLab), autenticación resuelta.
  - Contras: Git no entiende semántica de Markdown para merge; los blobs de Git son opacos a Cortex.
- *Opción B (Protocolo propio):* Crear `cortex://`.
  - Pros: Optimizado para objetos de conocimiento, semantic negotiation, embeddings en transferencia.
  - Contras: Reinventar la rueda, seguridad, mantenimiento.
- *Recomendación:* **Híbrido Fase 1–2**. Usar Git como transporte y storage para el vault enterprise (reaprovechar `git push`/`pull`/`clone`). Cortex añade:
  - `.cortex/vault.git/` como object store local (compatible con git plumbing).
  - Un `.gitattributes` o filter que normalice frontmatter.
  - Semantic merge como git merge driver (`cortex-merge-driver`).

### 9.3 Impacto en Modelos de Datos Actuales

**`EnterpriseOrgConfig` (`cortex/enterprise/models.py`):**
- Necesita extensión: `remotes: dict[str, RemoteConfig]`, `vault_git_enabled: bool`.
- `enterprise_vault_path` se mantiene para compatibilidad, pero se depreca en favor de `remotes.origin.url`.

**`KnowledgePromotionService` (`cortex/enterprise/knowledge_promotion.py`):**
- `discover_candidates()` debe respetar staging area antes de escanear todo.
- `apply_promotion()` debe operar sobre objetos, no archivos.
- `PromotionRecord` evoluciona a `KnowledgeCommit` con parent hash.

**`EnterpriseRetrievalService` (`cortex/enterprise/retrieval_service.py`):**
- `_build_vault_sources()` debe soportar múltiples remotes.
- Los `VaultSource` deben poder apuntar a un commit específico (para búsqueda en historial).

**ChromaDB / Embeddings:**
- Actualmente `VaultReader.sync()` indexa archivos del working tree.
- En Fase 2, `sync()` debe indexar desde un Tree object (o working tree, según checkout).
- Las colecciones de ChromaDB deberían nombrarse por branch/commit: `cortex_episodic_main`, `cortex_semantic_main`.

### 9.4 Consideraciones de Seguridad

- **Provenance:** Con object store, cada commit tiene autor criptográficamente verificable (GPG signing opcional).
- **ACLs:** Los refs pueden tener ACLs (quién puede push a `main` de enterprise). La config actual `require_review` es un subset.
- **Audit trail:** `records.jsonl` es append-only pero editable. Un DAG de commits es inherentemente inmutable (sin force-push).

---

## 10. Conclusión y Recomendación

### Dónde estamos exactamente

Cortex Enterprise tiene una **arquitectura sólida y funcional** para memoria corporativa de dos niveles (local + enterprise), con:
- Configuración declarativa (`org.yaml`)
- Retrieval multi-nivel con RRF y pesos configurables
- Promoción auditable con review pipeline
- Setup interactivo con presets
- Observabilidad y CI integration
- Inyección de contexto al agente vía MCP

Sin embargo, el modelo de "distribución" es **filesystem-centric**: el vault enterprise es una carpeta compartida (o subcarpeta) donde se copian archivos. No hay historial de versiones del conocimiento, no hay branches de conocimiento, no hay protocolo de red, no hay merge semantics.

### Qué tan lejos estamos

- **Fase 1 (UX Git-Like):** ~20% del camino. La infraestructura de comandos CLI existe (Typer), el modelo de promoción existe, solo falta la capa de staging, status, diff y log. **Distancia: CERCANA.**
- **Fase 2 (Storage Git-Like):** ~5% del camino. El fingerprint SHA-256 y `records.jsonl` son semillas, pero no un DAG. **Distancia: MEDIA-LEJANA.**
- **Fase 3 (Network):** ~2% del camino. `EnterpriseRetrievalService` sabe leer múltiples fuentes, pero no hay protocolo. **Distancia: LEJANA.**
- **Fase 4 (Merge Semantics):** ~0% del camino. Requiere R&D. **Distancia: MUY LEJANA.**

### Recomendación estratégica

1. **Corto plazo (próximo mes):** Implementar **Fase 1 — UX Layer**. Agregar `cortex add`, `cortex status`, `cortex diff`, `cortex log`, `.cortexignore`, y mejorar `cortex commit`/`push`/`pull` como frontends sobre la arquitectura actual. Esto da **valor inmediato** sin riesgo arquitectónico y prepara la intuición del usuario.

2. **Mediano plazo (2–4 meses):** Prototipar **Fase 2 — Storage Layer** en una rama experimental. Evaluar si reusar Git plumbing (libgit2/pygit2) como backend de object store es viable. Si lo es, el vault enterprise podría ser literalmente un repo Git con un merge driver de Cortex.

3. **Largo plazo (4–12 meses):** Si el prototipo de Fase 2 es exitoso, migrar el storage subyacente y luego construir el protocolo de red (Fase 3). Dejar Fase 4 (merge semántico avanzado) como investigación continua, usando LLMs como asistente de resolución.

4. **Mantener siempre:** El modo "archivos planos" como default para `small-company`. El modo Git-Like debe ser un **upgrade opt-in** (`cortex setup enterprise --distributed`) para equipos que necesiten verdadera federación.

### Métricas de éxito propuestas

- **Adopción Fase 1:** 80% de los usuarios enterprise usan `cortex status` semanalmente.
- **Reducción de conflictos:** Con staging explícito, reducir en 50% las promociones rechazadas en review.
- **Tiempo de onboarding:** Un nuevo proyecto debe poder `cortex clone <vault-enterprise-url>` en < 2 minutos.
- **Trazabilidad:** Cada documento enterprise debe tener historial de modificaciones consultable (`cortex log <path>`).

---

## Anexos

### Anexo A: Archivos de código inspeccionados para este análisis

| Archivo | Rol en el análisis |
|---------|-------------------|
| `cortex/core.py` | Fachada AgentMemory, wiring de servicios, retrieve con scope |
| `cortex/cli/main.py` | Comandos CLI existentes, Typer app, enterprise commands |
| `cortex/workspace/layout.py` | Resolución de paths, new vs legacy layout |
| `cortex/enterprise/models.py` | Schema de org.yaml, EnterpriseOrgConfig |
| `cortex/enterprise/config.py` | Carga/validación de config, presets, discovery |
| `cortex/enterprise/retrieval_service.py` | EnterpriseRetrievalService, fusión RRF multi-fuente |
| `cortex/enterprise/sources.py` | MultiVaultReader, MultiEpisodicReader |
| `cortex/enterprise/knowledge_promotion.py` | KnowledgePromotionService, discover, review, apply |
| `cortex/enterprise/promotion_models.py` | Modelos Pydantic de estados de promoción |
| `cortex/enterprise/reporting.py` | EnterpriseReportingService, memory-report |
| `cortex/retrieval/hybrid_search.py` | HybridSearch, RRF, adaptive weights, intent detection |
| `cortex/context_enricher/enricher.py` | ContextEnricher, multi-strategy search, co-occurrence |
| `cortex/mcp/server.py` | CortexMCPServer, tools MCP, governance de flujo |
| `cortex/models.py` | SemanticDocument, EpisodicHit, UnifiedHit, RetrievalResult, EnrichedContext |
| `docs/guides/enterprise-vault.md` | Analogía conceptual actual con Git |
| `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` | Estado completo post-Épicas E1–E7 |
| `docs/enterprise/AVANCE-EPIC-[1-7].md` | Bitácoras de implementación detalladas |
| `docs/enterprise/BACKLOG-Enterprise-Memory-Productization.md` | Backlog técnico ejecutable |
| `cortex-pi/.pi/skills/cortex-vault/SKILL.md` | Skill de agente para interacción con memoria |

### Anexo B: Glosario de términos Git mapeados

| Término Git | Significado en Cortex Git-Like |
|-------------|-------------------------------|
| **Working tree** | El directorio `vault/` con archivos Markdown editables |
| **Index / Staging area** | `promotion_index.json` — lista de docs listos para commit/push |
| **Commit** | Snapshot del vault con mensaje, autor, timestamp y parent |
| **Branch** | Línea de evolución del conocimiento (ej: `main`, `feature/x`) |
| **HEAD** | Referencia al commit activo en el working tree |
| **Remote** | Vault enterprise registrado (por URL o path) |
| **Origin** | Remote por defecto (el enterprise vault configurado en `org.yaml`) |
| **Fetch** | Traer refs y objetos del remote sin modificar working tree |
| **Pull** | Fetch + merge al working tree |
| **Push** | Enviar commits locales al remote |
| **Clone** | Copiar vault remoto completo (objetos + refs + working tree) |
| **Merge base** | Commit ancestro común más reciente entre dos branches |
| **Fast-forward** | Push/merge que solo avanza la referencia, sin crear commit de merge |
| **Object store** | DAG de blobs, trees, commits inmutables |

---

*Fin del documento.*
