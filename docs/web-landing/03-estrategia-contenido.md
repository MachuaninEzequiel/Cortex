---
title: Estrategia de Contenido — Cortex Landing
doc_type: reference
status: draft
parent: README.md
---

# Estrategia de Contenido — Cortex Landing

Este documento contiene **el copy completo** de la landing, sección por sección, en español (idioma primario). La traducción al inglés se aborda en [Fase 08 del docs-site](../web-docs/fases/fase-08-versionado-i18n.md) y en una sub-tarea de [Fase 10](fases/fase-10-lanzamiento.md) de la landing.

## 1. Tono y estilo

| Atributo | Cómo se manifiesta |
| --- | --- |
| **Editorial** | Frases completas, no telegrama. Punto al final. |
| **Técnico sin jergón** | Si decimos "RRF", explicamos "Reciprocal Rank Fusion" la primera vez. |
| **Directo** | Verbo activo. Sujeto explícito cuando importa. |
| **Confiado, no arrogante** | Decimos "Cortex resuelve X", no "el único framework capaz de…". |
| **En segunda persona** | "Tu agente recuerda" — habla al lector. |
| **Voseo argentino sutil** | Solo en ES; "querés", "podés", "tu equipo". |

### Reglas de escritura

1. **Frases ≤ 22 palabras** en body. Excepciones solo para listas o legales.
2. **Párrafos ≤ 4 líneas**.
3. **Bullets ≤ 7 ítems** por lista.
4. **Cifras concretas siempre que existan**: "<1ms latencia", "+85% coverage", "30+ comandos".
5. **No emojis decorativos** en headings; permitidos en footnotes y captions.
6. **No mayúsculas de todo** ("ENTERPRISE GRADE"). Sí title case en headings.

## 2. Glosario obligatorio (primera mención = explicación)

| Término | Definición corta |
| --- | --- |
| Amnesia de sesión | El olvido del agente IA entre sesiones de trabajo. |
| Vault | Base de conocimiento Markdown estructurada (Obsidian-compatible). |
| Memoria episódica | Memoria efímera tipo "qué hice esta semana" (ChromaDB). |
| Memoria semántica | Memoria estable tipo "cómo se construye nuestra API" (vault). |
| RRF (Reciprocal Rank Fusion) | Técnica para fusionar resultados de múltiples motores de búsqueda. |
| ONNX | Runtime de modelos de ML eficiente; corre embeddings en CPU sin GPU. |
| MCP (Model Context Protocol) | Protocolo abierto para que agentes IA accedan a herramientas. |
| Modelo Tripartito | Ciclo Sync (analista) → SDDwork (implementador) → Documenter (guardián). |
| Autopilot | Modo opt-in donde Cortex orquesta automáticamente el ciclo. |
| Enterprise vault | Vault corporativo compartido entre proyectos. |

## 3. Copy por sección

### 3.1 Hero (`#hero`)

**Eyebrow** (label superior, accent color):
> Memoria corporativa + Gobernanza para agentes IA

**H1**:
> **Tu agente ya no olvida. Tu equipo deja de repetirse.**

(Alternativa A) *"La memoria que tu agente IA siempre debió tener."*
(Alternativa B) *"Cortex: el sistema operativo de la memoria de tu equipo."*

**Lead paragraph** (text-body-lg, ≤ 40 palabras):
> Cortex es la capa de **memoria híbrida** y **gobernanza disciplinada** que convierte a tu agente IA en un colaborador con historia, criterios y trazabilidad. Específicaciones, decisiones y sesiones quedan persistidas en un vault corporativo accesible desde Claude Code, Cursor, Pi, VSCode y más.

**CTAs**:
- Primario: `[Probar Cortex →]` (anchor a `#instalacion`)
- Secundario: `[Ver cómo funciona en 90s ▶]` (anchor a `#demos`)

**Tertiary microcopy**:
> Open source · MIT · Python 3.10+ · Sin API keys obligatorias

**Visual sugerido**: composición con tres capas de memoria (episódica · semántica · enterprise) flotando en parallax, conectadas por líneas pulsantes hacia un ícono de agente. Animación de entrada por capa.

---

### 3.2 Problema (`#problema`)

**Eyebrow**:
> El problema

**H2**:
> **Cada sesión de tu agente empieza en blanco. Otra vez.**

**Body**:
> Los agentes IA modernos son brillantes en aislamiento y desastrosos en continuidad. Cada nueva tarea ignora las decisiones arquitectónicas del pasado, las vulnerabilidades ya detectadas y los acuerdos del equipo. El resultado: PRs inconsistentes, bugs que regresan, y desarrolladores explicando el contexto en cada prompt.

**Lista de pains** (con íconos):

- 🧠 **Amnesia de sesión** — El agente olvida lo que decidiste hace dos días.
- 📋 **Cero trazabilidad** — Nadie sabe quién aprobó qué arquitectura.
- 🔁 **Bugs recurrentes** — La misma vulnerabilidad se reintroduce cada trimestre.
- 🏗️ **Documentación desincronizada** — El código avanza, los docs no.
- 🏢 **Conocimiento siloed** — Cada proyecto reinventa el wheel.

**Cierre del problema**:
> No es un problema de modelo. Es un problema de **infraestructura de memoria**.

---

### 3.3 Solución overview (`#solucion`)

**Eyebrow**:
> La solución

**H2**:
> **Cortex impone un ciclo disciplinado. Tu agente lo ejecuta. Tu vault recuerda.**

**Body**:
> Cortex es un framework Python instalable con `pipx` que dota a tu agente IA de tres capacidades inseparables: **memoria persistente**, **gobernanza de ciclo de vida** y **observabilidad enterprise**. No reemplaza a Claude Code, Cursor o Pi: los amplifica.

**3 columnas (cards con ícono)**:

1. **Memoria Híbrida**
   Un vault Markdown (Obsidian-compatible) + memoria vectorial ChromaDB con embeddings ONNX. Búsqueda con Reciprocal Rank Fusion adaptativa. Latencia <1ms.

2. **Ciclo Tripartito**
   Sync → SDDwork → Documenter. Cada tarea pasa por análisis, implementación y persistencia. Auditable. Reversible.

3. **Enterprise Governance**
   Topología `org.yaml`, promotion pipeline auditable, políticas de retención, scopes multi-proyecto, reporting JSON.

**CTA**:
- `[Explorar arquitectura ⇲]` (anchor a `#arquitectura`)

---

### 3.4 Arquitectura interactiva (`#arquitectura`)

**Eyebrow**:
> Bajo el capó

**H2**:
> **Una arquitectura para explorar, no para memorizar.**

**Body** (corto, ≤ 30 palabras):
> Hacé hover sobre cada módulo para entender qué hace. Clic para profundizar. Cada nodo enlaza a su documentación técnica.

**Componente**: ver [Fase 03](fases/fase-03-arquitectura-interactiva.md). El diagrama es **el contenido**; el copy es mínimo.

**Captions por nodo** (al hover):

| Nodo | Caption |
| --- | --- |
| `core.AgentMemory` | Fachada principal. Punto único de entrada al sistema. |
| `episodic` | Memoria efímera vectorial. ChromaDB + embeddings ONNX. |
| `semantic` | Vault Markdown. Specs, sesiones, decisiones, runbooks. |
| `retrieval` | Motor de búsqueda híbrida RRF con detección de intención. |
| `autopilot` | Orquestador opt-in que automatiza el ciclo tripartito. |
| `enterprise` | Capa corporativa: org.yaml, promotion, retention, scopes. |
| `mcp` | Servidor MCP que expone Cortex a tu IDE. |
| `webgraph` | Visualizador interactivo del knowledge graph. |
| `cli` | 30+ comandos `cortex ...` para usar todo desde la terminal. |

---

### 3.5 Pilares (`#pilares`)

**Eyebrow**:
> Lo que hace Cortex distinto

**H2**:
> **Cuatro pilares. Una sola fuente de verdad.**

#### Pilar 1 — Memoria Híbrida RRF

**Body**:
> La memoria episódica (qué hicimos esta semana) y la semántica (cómo se construye nuestra API) se fusionan en una única búsqueda con **Reciprocal Rank Fusion**. La capa enterprise agrega conocimiento corporativo compartido. El motor detecta tu intención y rebalancea pesos automáticamente.

**Visual**: 3 capas separadas que se fusionan animadamente al hover.

**Métricas**:
- `<1ms` latencia por embedding (CPU)
- `~50MB` footprint (vs ~2.5GB PyTorch)
- `0` API keys requeridas

**Link**: `[Cómo funciona RRF →]` (docs)

---

#### Pilar 2 — Modelo Tripartito

**Body**:
> Cada cambio pasa por tres roles obligatorios. **Cortex-sync** recupera contexto histórico y escribe la especificación. **Cortex-SDDwork** orquesta la implementación con Intelligent Routing (Fast Track o Deep Track según complejidad). **Cortex-documenter** persiste la decisión final. Sin sesión guardada, el ciclo no se considera completo.

**Visual**: 3 columnas con flecha animada conectándolas + handoff YAML floating.

**Link**: `[Ver el manifiesto del ciclo →]`

---

#### Pilar 3 — Autopilot (opt-in)

**Body**:
> Activá Autopilot cuando estés listo. Cortex detecta el tipo de tarea (código, docs, pregunta), aplica políticas (budget, timeout, enforcement), enruta a Fast/Deep Track, valida handoffs entre subagentes y cierra la sesión automáticamente. **Tres modos**: `observe` (registra sin intervenir), `assist` (sugiere), `autopilot` (cierra). Reversible con un comando.

**Visual**: timeline animado mostrando un ciclo `start → preflight → checkpoints → finish`.

**Link**: `[Configurar Autopilot →]`

---

#### Pilar 4 — Enterprise Governance

**Body**:
> Topología corporativa declarativa en `.cortex/org.yaml`. Pipeline de promoción auditable (`candidate → reviewed → promoted`). Políticas de retención por tipo de documento. Scopes `local | enterprise | all`. Reporting JSON estable. Presets para empresa chica, equipo multi-proyecto u organización regulada.

**Visual**: diagrama de la topología corporativa con flujos de promoción.

**Link**: `[Manifiesto Enterprise →]` (`/enterprise`)

---

### 3.6 Demos en vivo (`#demos`)

**Eyebrow**:
> Velo en acción

**H2**:
> **Tres demos. Cero instalación.**

#### Demo 1 — CLI Animado

> Mirá cómo Cortex transforma un `save-session` en memoria viva. Demo en terminal con timing realista, syntax highlighting y output progresivo.

#### Demo 2 — WebGraph Embebido

> Explorá el knowledge graph de un proyecto real (snapshot exportado del propio Cortex). Filtros por tipo, scope y proyecto. Click en nodo para ver detalle.

#### Demo 3 — Autopilot Replay

> Reproducí una sesión Autopilot real: preflight → detección → routing → checkpoints → close. Cada paso documentado y verificable.

---

### 3.7 Casos de uso (`#casos-de-uso`)

**Eyebrow**:
> Para quién

**H2**:
> **Tres historias. Tres formas de adoptar Cortex.**

#### Caso 1 — El equipo que para de repetirse

**Antes**: 7 desarrolladores, 4 IDEs distintos, 3 PRs por semana donde alguien comenta "esto ya lo discutimos hace un mes".

**Con Cortex**: cada sesión termina con `cortex save-session`. Cada nuevo PR empieza con `cortex search "lo que sea"`. La memoria es del equipo, no de las personas.

#### Caso 2 — El founder que recupera 30 min/día

**Antes**: cada mañana, 30 minutos pegándole contexto a Claude antes de poder programar.

**Con Cortex**: `cortex context` inyecta automáticamente el contexto relevante. El agente sabe qué hiciste ayer. Te concentrás en programar, no en explicar.

#### Caso 3 — La empresa que demuestra gobernanza

**Antes**: el área de Compliance no aprueba el uso de IA porque "no hay trazabilidad".

**Con Cortex**: `org.yaml` declara políticas. `memory-report --json` audita. `promote-knowledge` deja huella inmutable. La IA pasa la auditoría.

---

### 3.8 Comparativa (`#comparativa`)

**Eyebrow**:
> Comparado

**H2**:
> **No es solo "una base de datos para tu agente".**

**Tabla comparativa**:

| | Sin memoria | Memoria casera | **Cortex** |
| --- | --- | --- | --- |
| Persistencia entre sesiones | ❌ | ⚠️ Manual | ✅ Automática |
| Búsqueda híbrida (semántica + keyword) | ❌ | ⚠️ Uno solo | ✅ RRF fusión |
| Trazabilidad de decisiones | ❌ | ❌ | ✅ Specs + sesiones |
| Integración IDE nativa | ❌ | ❌ | ✅ 6 IDEs vía MCP |
| Gobernanza enterprise | ❌ | ❌ | ✅ `org.yaml` |
| Promotion pipeline auditable | ❌ | ❌ | ✅ candidate → promoted |
| Tutor offline integrado | ❌ | ❌ | ✅ `cortex tutor` |
| Setup en | n/a | Días | **3 comandos** |

---

### 3.9 Instalación (`#instalacion`)

**Eyebrow**:
> Empezá hoy

**H2**:
> **Tres comandos. Cualquier proyecto. En menos de 5 minutos.**

**Code block (con copy)**:

```bash
# 1. Instalar Cortex globalmente
pipx install cortex-memory

# 2. Inicializar en tu proyecto
cd mi-proyecto
cortex setup full

# 3. Conectar con tu IDE preferido
cortex inject --ide claude-code   # o cursor, pi, vscode, codex
```

**Selector visual de IDE** (tabs):

`[Claude Code]` `[Cursor]` `[Pi]` `[VSCode + Cline]` `[OpenCode]` `[Codex]`

Cada tab muestra el comando específico + screenshot de "qué ves después".

**Microcopy**:
> ¿Querés probarlo sin instalar? `[Demo en línea →]`

**Footer del bloque**:
> ¿Vienes de una organización regulada? Mirá [Cortex Enterprise →](/enterprise)

---

### 3.10 Comunidad y siguiente paso (`#comunidad`)

**H2**:
> **Open source, en serio.**

**Body**:
> Cortex es MIT, escrito en Python, con suite de tests >85% coverage. Toda la roadmap es pública. Las decisiones de arquitectura viven en `docs/vision/` y `docs/refact/`. Si te interesa contribuir, empezá por [CONTRIBUTING.md](https://github.com/MachuaninEzequiel/Cortex/blob/master/CONTRIBUTING.md).

**3 cards finales**:

- **[Estrella en GitHub →]** — Apoyá el proyecto.
- **[Leé la documentación →]** — Quickstart, conceptos y referencia completa.
- **[Hablá con el equipo →]** — Enterprise, partnerships, dudas.

---

## 4. FAQ (sección colapsable opcional al fin)

| Pregunta | Respuesta |
| --- | --- |
| ¿Cortex requiere API keys? | No. Los embeddings corren localmente en ONNX. Opcionalmente podés usar OpenAI/Anthropic. |
| ¿Funciona offline? | Sí. Toda la funcionalidad core no requiere internet. |
| ¿Funciona en Windows? | Sí, oficialmente soportado. Linux y macOS también. |
| ¿Es compatible con Obsidian? | Sí, el vault usa formato Obsidian con frontmatter YAML. |
| ¿Cuánto pesa? | ~50MB en disco (ONNX). El vault crece según tu proyecto. |
| ¿Cómo desinstalo? | `pipx uninstall cortex-memory`. Tu vault queda intacto. |
| ¿Hay versión cloud? | No por ahora. Cortex está pensado para correr donde corre tu código. |
| ¿Es production-ready? | Sí en v0.5.0. Ver [CHANGELOG](https://github.com/MachuaninEzequiel/Cortex/blob/master/CHANGELOG.md). |

## 5. Microcopy de error y vacío

- **Demo offline**: "La demo no pudo cargar el grafo en vivo. Mostramos un snapshot estático."
- **Form enterprise enviado**: "¡Recibido! Te respondemos en menos de 48 horas."
- **Form enterprise error**: "No pudimos enviar tu mensaje. Probá de nuevo o escribinos a hello@cortex.dev."

## 6. SEO (meta tags)

| Tag | Valor |
| --- | --- |
| `<title>` | Cortex — Memoria corporativa y gobernanza para agentes IA |
| `<meta description>` | Cortex es la capa de memoria híbrida y gobernanza disciplinada que tu agente IA necesita. Open source, MIT, integración con Claude Code, Cursor y más. |
| `<meta og:image>` | `/og/landing-og.png` (1200×630, ver Fase 09) |
| `<meta og:type>` | `website` |
| `<meta twitter:card>` | `summary_large_image` |
| Keywords (no-meta, semantic) | cortex, ai agent memory, claude code memory, cursor memory, agent governance, devsecdocops, RAG vault |
