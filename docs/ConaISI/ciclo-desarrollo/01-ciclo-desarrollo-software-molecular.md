# Ciclo de Desarrollo de Software Asistido por Cortex: Especificación Molecular

Este documento describe la interacción milimétrica entre el Desarrollador (Humano), los Entornos de Ejecución (Host CLIs e IDEs), el Servidor de Herramientas MCP, la Capa de Micro-Decisión Cognitiva (SystemOne), los Modelos de Lenguaje (Remotos y Locales) y los Almacenes de Memoria Híbrida de Cortex.

Toda la arquitectura descripta corresponde a la implementación 100% nativa en Rust (22 crates de workspace) y elimina cualquier dependencia o abstracción heredada.

---

## 1. Entrada del Desarrollador y Despliegue Automático

El ciclo comienza cuando el desarrollador abre su entorno habitual de desarrollo o ejecuta un comando. Cortex nunca impone un IDE privativo; se integra transparentemente en la superficie elegida por el usuario.

### 1.1 Superficies Soportadas y Detección de Host (`cortex-setup`)

Al ingresar al directorio del proyecto:

1. **Descubrimiento del Workspace (`WorkspaceLayout::discover`)**:
   - Detecta la raíz del repositorio y la ubicación canónica de Cortex: `.cortex/` (nuevo layout canónico conteniendo `config.yaml`, `org.yaml`, `vault/`, `memory/`, `sessions/`) o fallback a legacy en raíz.
2. **Detección del Entorno Host (`HostEnvironment`)**:
   - Módulo: [`host_detector.rs`](file:///home/chucho/Cortex/rust/crates/cortex-setup/src/ide/host_detector.rs).
   - Identifica el entorno activo mediante variables de entorno y artefactos del workspace:
     - `Antigravity` (`ANTIGRAVITY_SESSION`, `GEMINI_CLI`, `GEMINI.md`).
     - `Pi` (`PI_SESSION`, `PI_AGENT`, `PI_HOME`, `.pi/`).
     - `ClaudeCode` (`CLAUDE_CODE_ENTRYPOINT`, `CLAUDE.md`).
     - `Cursor` (`CURSOR_PROJECT`, `.cursor/`).
     - `Codex` (`OPENAI_CODEX`, `.codex/`).
     - `OpenCode` (`OPENCODE_ENV`).
     - `StandaloneDesktop` (Cortex Brain App / CLI nativo).
3. **Escudo de Cumplimiento de Políticas y ToS (`is_provider_allowed`)**:
   - **Regla innegociable de aislamiento**: Las credenciales de una suscripción jamás deben contaminar otro entorno.
   - En **Google Antigravity**, la política restringe estrictamente la inferencia a modelos de Google (`google:*` / `gemini:*`).
   - En **Pi Agent**, se bloquea la exportación de tokens de Google Antigravity y se limita a proveedores autenticados en `~/.pi/agent/auth.json` (OpenRouter, Codex, xAI, etc.).
   - En **Claude Code**, se restringe a modelos directos de Anthropic.
4. **Inyección de Perfiles y Hooks (`IdeAdapter::inject_profiles`)**:
   - Cada adaptador (`cortex-setup/src/ide/adapters/`) inyecta la configuración del agente, skills y hooks con delimitadores canónicos:
     ```markdown
     <!-- BEGIN CORTEX SECTION -->
     ... configuración inyectada por Cortex ...
     <!-- END CORTEX SECTION -->
     ```
   - **Hooks automáticos de sesión**:
     - Claude Code: intercepta eventos de edición (`Edit`, `Write`, `MultiEdit`) en `settings.json` para emitir `cortex session checkpoint --source ide-hook`.
     - Cursor: hook de git `post-commit`.
     - Pi: tareas del `justfile`.
5. **Descubrimiento Pasivo de Modelos (`cli_discovery.rs`)**:
   - Sin llamadas de red ni solicitudes lentas, Cortex lee pasivamente en disco los modelos reales ya autenticados en la máquina del usuario (`~/.pi/agent/models-store.json`, `~/.gemini/antigravity-cli/`, `~/.claude/`).
   - Genera el catálogo local de modelos con formato canónico `provider:model_id` (ej. `google:gemini-2.5-pro`, `openrouter:anthropic/claude-3.5-sonnet`).

### 1.2 El Servidor MCP Nativo (`cortex-mcp`)

Cuando el IDE o CLI del agente inicia, levanta automáticamente en un subproceso el servidor MCP de Cortex:

- **Protocolo**: Model Context Protocol (MCP) estándar sobre `stdio` bloqueante (`serve_stdio_blocking`).
- **Implementación**: Rust nativo con framework `rmcp`, `SERVER_VERSION = "2.2"`.
- **Comportamiento**: Inyecta backends nativos (`NativeSearchBackend`, `NativeSessionsBackend`, `NativeSpecBackend`, `NativeDocsBackend`, `NativeFinishBackend`, `NativeAutopilotBackend`).
- **Catálogo Fijo**: Expone exactamente **32 tools** auditadas bajo contrato golden byte-a-byte.

---

## 2. Catálogo Exhaustivo de las 32 Tools MCP

A continuación se detalla la totalidad de las 32 herramientas del servidor MCP de Cortex, organizadas por su rol funcional en el ciclo de desarrollo:

| N° | Nombre Canónico de la Tool | Handler y Backend Nativo | Parámetros Clave | Rol en el Ciclo de Desarrollo |
|:---|:---|:---|:---|:---|
| 1 | `cortex_ping` | `server.rs` (`_ping_text`) | Ninguno | Health check de conexión stdio y reporte de versión `2.2`. |
| 2 | `cortex_search_vector` | `handlers_search.rs` (`NativeSearchBackend`) | `query`, `top_k` | Búsqueda puramente vectorial k-NN sobre `vectors.v3.bin` usando embeddings normalizados. |
| 3 | `cortex_search` | `handlers_search.rs` (`NativeSearchBackend`) | `query`, `top_k`, `filters` | Búsqueda híbrida RRF ($k=60$) sobre memoria semántica y episódica. Aplica filtros estructurales. |
| 4 | `cortex_context` | `handlers_search.rs` (`NativeSearchBackend`) | `query`, `max_chars`, `max_items`, `pack_depth` | Recuperación con enriquecedor contextual, expansión de grafo y budget de caracteres. |
| 5 | `cortex_sync_ticket` | `handlers_search.rs` (`NativeSearchBackend`) | `ticket_id`, `request` | Sincronización y anclaje de un ticket/HU externa en el contexto vivo de la sesión. |
| 6 | `cortex_create_spec` | `handlers_spec.rs` (`NativeSpecBackend`) | `spec_id`, `title`, `summary`, `scope` | Creación de especificación técnica canónica (`vault/specs/*.md`) y apertura de sesión. |
| 7 | `cortex_emit_proposal` | `handlers_spec.rs` (`NativeSpecBackend`) | `title`, `summary`, `changes` | Emisión de propuesta formal de cambio técnico/refactor para revisión. |
| 8 | `cortex_save_session` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `session_yaml` | Persistencia explícita del estado serializado de una sesión en `.cortex/sessions/`. |
| 9 | `cortex_validate_handoff` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `handoff_yaml` | Validación de contrato de handoff al pasar la posta entre agentes o turnos. |
| 10 | `cortex_verify_session_claims` | `handlers_spec.rs` (`NativeSpecBackend`) | `session_id`, `claims` | Verificación analítica de afirmaciones contra diffs de git y resultados de testing. |
| 11 | `cortex_import_hu` | `handlers_spec.rs` (`NativeSpecBackend`) | `external_id`, `source`, `payload` | Ingesta estructurada de Historias de Usuario en el Vault (`vault/hu/*.md`). |
| 12 | `cortex_get_hu` | `handlers_spec.rs` (`NativeSpecBackend`) | `hu_id` | Lectura completa de criterios de aceptación y contexto de una HU. |
| 13 | `cortex_sync_vault` | `server.rs` (ruta inline `NativeSearchBackend`) | Ninguno | Reindexación BM25 substring y actualización de estadísticas IDF/avgdl del Vault. |
| 14 | `cortex_autopilot_start` | `handlers_autopilot.rs` (`NativeAutopilotBackend`) | `task_description`, `budget_profile` | Inicialización de la máquina de estados autónoma con detectores de intención. |
| 15 | `cortex_autopilot_preflight` | `handlers_autopilot.rs` (`NativeAutopilotBackend`) | `session_id` | Verificación previa de seguridad, árbol de trabajo limpio e invariantes. |
| 16 | `cortex_autopilot_checkpoint` | `handlers_autopilot.rs` (`NativeAutopilotBackend`) | `session_id`, `phase`, `claims` | Punto de control automatizado dentro de una secuencia de Autopilot. |
| 17 | `cortex_autopilot_finish` | `handlers_autopilot.rs` (`NativeAutopilotBackend`) | `session_id` | Cierre y balance de ejecución autónoma delegando en Documenter. |
| 18 | `cortex_autopilot_status` | `handlers_autopilot.rs` (`NativeAutopilotBackend`) | `session_id` | Telemetría en tiempo real y consumo de presupuesto de Autopilot. |
| 19 | `cortex_session_open` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `spec_id`, `spec_path`, `spec_summary` | Apertura de una sesión de ingeniería viva con hash de commit inicial y branch. |
| 20 | `cortex_session_checkpoint` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `source`, `verified_claims`, `unverified_claims`, `artifacts_touched`, `note`, `phase` | Registro atómico de progreso e invariantes verificadas. |
| 21 | `cortex_session_close` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `status`, `documenter_decision`, `session_note_path`, `adrs_created` | Cierre formal con asignación de commit final y decisión del documentador. |
| 22 | `cortex_session_status` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id` (opcional) | Estado de la sesión y exposición dinámica del menú de especialistas ("Rebuild the Menu"). |
| 23 | `cortex_finish_session` | `handlers_finish.rs` (`NativeFinishBackend`) | `session_id`, `intent` | Reconstrucción de sesión desde diff + checkpoints, contradicciones y cierre. |
| 24 | `cortex_documenter_briefing` | `handlers_finish.rs` (`NativeFinishBackend`) | `session_id` | Briefing ejecutivo concentrado para el subagente Documentador al cierre. |
| 25 | `cortex_close_session` | `handlers_finish.rs` (`NativeFinishBackend`) | `session_id`, `decision` | Cierre transaccional idempotente en la capa de finalización. |
| 26 | `cortex_session_list` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `status` (opcional) | Resumen tabular de sesiones históricas (`open`, `closed`, `handoff`, `abandoned`). |
| 27 | `cortex_self_review_note` | `handlers_spec.rs` (`NativeSpecBackend`) | `session_id`, `note_content` | Persistencia de notas de introspección y auto-revisión de calidad. |
| 28 | `cortex_write_doc` | `handlers_docs.rs` (`NativeDocsBackend`) | `doc_type`, `payload` | Escritura tipada en Vault para 11 tipos (`adr`, `architecture`, `changelog`, `decision`, `glossary`, `handoff`, `hu`, `incident`, `postmortem`, `runbook`, `session`). |
| 29 | `write_design_note_canonical` | `handlers_docs.rs` (`NativeDocsBackend`) | `title`, `decision`, `context`, `consequences` | Redacción canónica de notas de diseño arquitectónico. |
| 30 | `cortex_session_task_list` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `status` | Lista de tareas desglosadas en el plan de la sesión activa. |
| 31 | `cortex_session_task_update` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `task_id`, `status`, `note` | Actualización de estado de una tarea (`pending`, `in-progress`, `done`, `skipped`, `blocked`). |
| 32 | `cortex_review_checkpoint` | `handlers_sessions.rs` (`NativeSessionsBackend`) | `session_id`, `claims_to_audit` | Punto de control exclusivo de auditoría y revisión de claims analíticos. |

---

## 3. El Ciclo de Vida del Software ("El Sandwich Canónico de Cortex")

El flujo de trabajo en Cortex sigue una regla arquitectónica estricta denominada el **Sandwich Canónico**:

$$\text{Top: Sync (Oficio)} \longrightarrow \text{Medio: Implementación Ágil (Direct)} \longrightarrow \text{Bottom: Documenter (Oficio)}$$

Ningún trabajo significativo puede comenzar sin anclar su contexto (Sync), ni puede darse por concluido sin persistir su aprendizaje (Documenter).

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           0. UTTERANCE GATEWAY                                │
│       Prompt del Desarrollador analizado en <10ms por SystemOne               │
│       Clasificación: question (0 sesión) | implement (sync) | done (finish)   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ implement
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    1. TOP: SYNC & APERTURA DE SESIÓN                          │
│   cortex_session_open / cortex_create_spec                                    │
│   Commit inicial registrado · WorkspaceLayout anclado                        │
│   Menú dinámico: Recomienda Architect (cortex-code-designer)                  │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                 2. MODEL ROUTER: ASIGNACIÓN POR ROL                           │
│   Evaluación según Host activo (Antigravity / Pi / Claude / Cursor)           │
│   Architect: Razonamiento profundo (Pro / Sonnet)                             │
│   Implementer: Modelo de código (Pro / Sonnet / Codex)                        │
│   Auditor: Modelo analítico                                                   │
│   Documenter: Modelo rápido de prosa (Flash / Haiku / Mini)                   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│            3. RECUPERACIÓN HÍBRIDA (RRF) & TIERED MEMORY                      │
│   cortex_search / cortex_context                                              │
│   Memoria Semántica (Vault) + Memoria Episódica (Vectors JSONL)              │
│   Fusión RRF k=60 · Documentos 'tier: archive' atenuados al 20%               │
│   Search Squeeze (Noul) + Context Pack (punteros canónicos sin duplicar)      │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│               4. EL MEDIO: IMPLEMENTACIÓN & CHECKPOINTS VIVOS                 │
│   El desarrollador / implementer escribe código y tests                       │
│   Session Compact: poda tool results viejos sin resumir                       │
│   Checkpoints periódicos (cortex_session_checkpoint / ide-hook)              │
│   Actualización de tareas (cortex_session_task_update)                        │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│             5. AUDITORÍA, VERIFICATION GATE & PRIMITIVA SCORE                 │
│   cortex_verify_session_claims / cortex_review_checkpoint                     │
│   Rebuild the Menu: Recomienda Auditor si hay unverified claims               │
│   Primitiva Score (0.0..2.0): impacto arquitectónico de ADRs                  │
│   Umbral de certeza CONFIDENCE_THRESHOLD >= 0.85                              │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                   6. BOTTOM: DOCUMENTER & CIERRE                              │
│   cortex_finish_session / cortex_documenter_briefing                          │
│   Reconstrucción desde git diff + checkpoints                                 │
│   Detección de contradicciones con ADRs existentes                            │
│   Escritura de notas de sesión y ADRs (cortex_write_doc)                      │
│   Filtro worth_remembering antes de escribir memoria episódica                │
│   cortex_session_close                                                        │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│              7. MEMORIA ORGANIZACIONAL & PROMOCIÓN ENTERPRISE                 │
│   Candidatos de promoción detectados en .cortex/org.yaml                      │
│   PromotionRulesEngine evalúa calidad, tests y governance                     │
│   Promoción hacia el Vault Corporativo Compartido                             │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detalle Molecular de las Fases del Ciclo

### Fase 0: Utterance Gate (El Portero Cognitivo)
- **Objetivo**: Proteger la memoria de contaminación por chatter o consultas casuales.
- **Mecanismo**: Ante el primer mensaje del dev, SystemOne ejecuta una micro-decisión paralela (`Purpose::Utterance`):
  - `Choice work`: clasifica en `question | implement | chore | done`.
  - `Noul needs_session`: probabilidad de requerir apertura de sesión.
  - `Noul worth_remembering`: valor de persistencia a largo plazo.
- **Comportamiento**:
  - Si el dev pregunta *"¿Cómo funciona el parser de markdown?"*: Clasificado como `question`. Cero apertura de sesión, cero escritura en memoria episódica.
  - Si el dev indica *"Implementá el nuevo algoritmo de hash en el store"*: Clasificado como `implement`. Dispara automáticamente el inicio del Sandwich (Fase 1).
  - Si la confianza es menor a 0.50, se asume `question` y nunca se abre una sesión fantasma.

### Fase 1: Sync y Apertura de Sesión
- El sistema crea un `SessionRecord` asociado a una especificación (`cortex_create_spec` o `cortex_session_open`).
- Registra el commit base de git (`start_commit`) y la branch activa (`start_branch`).
- **Rebuild the Menu Inicial**: Como `checkpoint_count == 0`, `cortex_session_status` expone al subagente **Architect / Designer (`cortex-code-designer`)** como el especialista *recomendado* para fijar contratos y alcance antes de picar código.

### Fase 2: Model Router Inteligente (`Purpose::ModelRouting`)
- En lugar de usar un modelo monolítico caro para todo o un modelo débil que falle en arquitectura:
  1. El Model Router consulta los modelos autorizados en el Host activo (`available_models`).
  2. Asigna roles:
     - **Architect**: Razonamiento profundo (Gemini 2.5 Pro / Claude 3.5 Sonnet) para diseñar especificaciones, contratos y ADRs.
     - **Implementer**: Modelo enfocado en refactor y síntesis de código.
     - **Auditor**: Modelo analítico para evaluar diffs y verificar evidencia de tests.
     - **Documenter**: Modelo económico y veloz (Gemini 2.5 Flash / Claude 3.5 Haiku) con excelente prosa para redactar notas de sesión, ADRs y changelogs.
  3. Si hay múltiples candidatos, SystemOne elige el modelo óptimo evaluando complejidad y costo.

### Fase 3: Recuperación Híbrida (RRF) y Tiered Memory
- **Búsqueda Híbrida**: Combina la búsqueda léxica BM25 sobre notas semánticas del Vault con la búsqueda semántica vectorial sobre fragmentos episódicos (`vectors.v3.bin`).
- **Fusión RRF ($k=60$)**: Cada resultado se pondera por su rango relativo:
  $$\text{RRF Score}(d) = \sum_{m \in \{\text{episodic, semantic}\}} \frac{w_m}{60 + \text{rank}_m(d)}$$
- **Tiered Memory (Memoria en Dos Niveles)**:
  - *Memoria Primaria*: ADRs vigentes, especificaciones canónicas y contratos (peso $1.0$).
  - *Memoria de Archivo (`tier: archive` / `tags: [archive]`)*: Diffs completos, logs antiguos y notas intermedias. Reciben una atenuación de peso al **20%** ($w_{\text{sem}} \times 0.2$), permaneciendo accesibles para auditorías históricas sin saturar las consultas de desarrollo cotidiano.
- **Search Squeeze & Context Pack**:
  - `Search Squeeze`: SystemOne filtra candidatos con Noul y descarta distracciones.
  - `Context Pack`: Se sustituyen textos redundantes por punteros canónicos estables (`pack_pointer`).

### Fase 4: Implementación, Refactor y Checkpoints Vivos
- El agente o el humano modifica archivos en el workspace.
- **Session Compact (`Purpose::SessionCompact`)**: A medida que la conversación avanza y se acumulan llamadas a herramientas (lecturas de archivos, ejecuciones de terminal), SystemOne recorta los outputs voluminosos de herramientas antiguas sustituyéndolos por `[output truncated verbatim by session_compact]`, preservando intactos los mensajes fijados recientes y el razonamiento. Esto mantiene el consumo de contexto estable y previene la degradación por distracción.
- **Checkpoints**: Con cada hito de avance (`cortex_session_checkpoint`), se asientan:
  - `verified_claims`: Invariantes demostradas por tests.
  - `unverified_claims`: Hipótesis o cambios pendientes de comprobación.
  - `artifacts_touched`: Archivos modificados en la iteración.

### Fase 5: Auditoría, Verification Gate y Primitiva Score
- Si se acumulan `unverified_claims`, el menú dinámico conmuta: **Auditor (`review_checkpoint`)** pasa a ser el especialista recomendado y bloquea el cierre prematuro.
- **Primitiva `Score` (Escala 0.0 a 2.0)**:
  - Se invoca para calificar el impacto de un cambio arquitectónico (ADR):
    - `0.0`: Cosmético o refactor local sin alteración de contratos.
    - `1.0`: Decisión de diseño modular local.
    - `2.0`: Decisión arquitectónica estructural innegociable.
  - Umbral de decisión determinista: $\ge 0.85$ para automatización; si es inferior, se exige confirmación explícita con el desarrollador humano.

### Fase 6: Cierre, Documentación y Persistencia (Documenter)
- Al concluir las tareas (`cortex_finish_session`):
  1. El Reconstructor analiza el git diff entre `start_commit` y `HEAD`, contrastándolo con los checkpoints registrados.
  2. Verifica contradicciones contra los ADRs preexistentes en el Vault.
  3. Redacta la nota de sesión final y los nuevos ADRs mediante `cortex_write_doc`.
  4. **Filtro de Memoria Episódica**: Antes de llamar a `AgentMemory.remember`, SystemOne evalúa `worth_remembering`. Solo se indexan en JSONL y vectores los aprendizajes genuinos y resoluciones de bugs; se ignora el ruido de la conversación.
  5. `cortex_session_close` sella la sesión con el commit final (`end_commit`).

### Fase 7: Memoria Organizacional & Promoción Enterprise
- Las notas y lecciones generadas en el repositorio local son analizadas por el motor de gobierno corporativo (`cortex-enterprise`).
- Si una nota aporta valor transversal (ej. un ADR de autenticación o una guía de performance), se marca como `PromotionCandidate` en `.cortex/org.yaml`.
- El equipo de arquitectura revisa y promueve la nota (`cortex promote-knowledge`) hacia el Vault Central de la Organización, enriqueciendo la memoria de todos los desarrolladores del equipo.

---

## 5. Modelos Locales de IA vs Suscripciones Remotas

Cortex provee una arquitectura híbrida y soberana:

1. **Cortex Brain (`cortex-brain` + `llama.cpp`)**:
   - Asistente de escritorio local de latencia ultrabaja.
   - Ejecuta modelos locales en formato GGUF descargados en `~/.cache/cortex/models/`.
   - Utiliza un **Router Determinista** con protocolo `TOOL`:
     - Herramientas seguras de lectura (`Tier::Read`): `memory.search`, `docs.related`, `cortex.health`, `vault.stats`, `session.current`.
     - Acciones con mutación: se proponen al humano con diálogo de confirmación interactivo (`actions.propose`), jamás mutando archivos a ciegas.
2. **LLMs de Suscripción Remota**:
   - Modelos de frontera provistos por las suscripciones del usuario en sus CLIs (Antigravity, Pi, Claude Code).
   - Acceden a través del servidor MCP nativo.
3. **SystemOne (TypeSafe Engine)**:
   - No es un LLM generador de código ni un agente con herramientas.
   - Es un clasificador probabilístico determinista de menos de 10ms (Kahneman Sistema 1) que toma micro-decisiones binarias o continuas (`Choice`, `Noul`, `Score`) sin interferir en la autonomía del modelo principal.
