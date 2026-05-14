---
title: Sistema de Diseño — Cortex Docs
doc_type: reference
status: draft
parent: README.md
---

# Sistema de Diseño — Cortex Docs

> **Heredamos** la mayoría de tokens de `web-landing/02-sistema-diseno.md` (paleta, tipografía, espaciado). Este documento solo lista **diferencias específicas** del docs.

## 1. Filosofía

La landing prioriza **estética**; el docs prioriza **legibilidad y eficiencia de lookup**.

| | Landing | Docs |
| --- | --- | --- |
| Densidad informativa | Baja | Alta |
| Animaciones | Sí, signature | Mínimas, funcionales |
| Tipografía | Display + expressive | Legible + consistente |
| Layout | Single-page narrativo | Multi-page jerárquico |
| Color | Gradientes y blobs | Plano, alto contraste |
| Visual hero | Sí, prominente | Solo en landing del docs |

## 2. Tokens (overrides desde landing)

### Color

Heredamos paleta. Diferencias:

| Token docs | Valor | Uso |
| --- | --- | --- |
| `--bg-base` | `#0B0B0F` (oscuro) / `#FCFCFD` (claro) | Más neutro que landing |
| `--bg-sidebar` | `#0F0F13` / `#F4F4F5` | Sidebar |
| `--bg-code` | `#1A1A1F` / `#F4F4F5` | Code blocks |
| `--accent-link` | `#FF6B1A` | Links body (heredado) |
| `--accent-link-visited` | `#B45309` | Link visitado |
| `--inline-code-bg` | `#27272A` / `#E4E4E7` | Code inline `like this` |
| `--inline-code-fg` | `#FFB280` / `#9A3412` | |

### Tipografía

- **Body**: Inter Variable a **17px** (más grande que landing) para lectura larga.
- **Mono**: JetBrains Mono Variable a **14px** inline, **15px** en bloques.
- **Headings**: misma escala que landing.

### Espaciado

- **Sidebar width**: 280px desktop, full-width mobile.
- **Right rail width**: 240px desktop.
- **Content max-width**: 760px en zona central (lectura óptima 65-75 caracteres por línea).

## 3. Componentes específicos del docs

### 3.1 `<Callout>`

Cuatro variantes:

| Variant | Color | Icono | Uso |
| --- | --- | --- | --- |
| `info` | azul muted | `Info` | Información complementaria |
| `tip` | verde | `Lightbulb` | Recomendaciones, atajos |
| `warning` | amarillo | `AlertTriangle` | Advertencias no críticas |
| `danger` | rojo | `AlertOctagon` | Acciones destructivas |

```mdx
<Callout type="warning">
Este comando reescribe el vault. Hacé backup antes.
</Callout>
```

### 3.2 `<CodeBlock>` (extendido)

```mdx
<CodeBlock
  lang="bash"
  title="instalar-cortex.sh"
  showLineNumbers
  highlight="2-4"
  copy
  runnable
>
{`pipx install cortex-memory
cd mi-proyecto
cortex setup full
cortex inject --ide claude-code`}
</CodeBlock>
```

Features:

- **Filename label** arriba.
- **Tabs** para múltiples shells/lenguajes:
  ```mdx
  <CodeTabs>
    <CodeTab label="macOS / Linux" lang="bash">brew install just</CodeTab>
    <CodeTab label="Windows" lang="powershell">winget install Casey.Just</CodeTab>
  </CodeTabs>
  ```
- **Copy button** con feedback.
- **Line numbers** opt-in.
- **Highlight** ranges.
- **Diff syntax** soportado (`lang="diff"` + `+/-` prefix).
- **Output blocks**: `<CodeBlock variant="output">` para resultado.
- **Highlighter**: Shiki SSR.

### 3.3 `<CommandReference>`

Componente especializado para documentar comandos CLI:

```mdx
<CommandReference
  command="cortex search"
  description="Búsqueda híbrida en la memoria con fusión RRF"
  syntax="cortex search [QUERY] [OPTIONS]"
  since="0.1.0"
/>

<CommandFlag name="--scope" type="string" default="all" choices="local,enterprise,all">
  Define el alcance de la búsqueda.
</CommandFlag>

<CommandFlag name="--top-k" type="int" default="10">
  Número máximo de resultados.
</CommandFlag>

<CommandExample title="Búsqueda básica">
{`cortex search "JWT refresh"`}
</CommandExample>
```

Renderiza una "ficha" estructurada con metadata + flags + ejemplos.

### 3.4 `<McpToolReference>`

Similar para MCP tools:

```mdx
<McpToolReference
  name="cortex_search"
  since="0.1.0"
  inputSchema={...}
  outputSchema={...}
/>
```

### 3.5 `<ConfigReference>`

Para documentar opciones de `config.yaml` y `org.yaml`:

```mdx
<ConfigReference
  key="memory.episodic.embedder"
  type="string"
  default="onnx"
  choices="onnx,local,openai"
  since="0.1.0"
>
Backend de embeddings para memoria episódica.
</ConfigReference>
```

### 3.6 `<Steps>`

Para tutoriales paso a paso:

```mdx
<Steps>
1. Instalá Cortex:
   ```bash
   pipx install cortex-memory
   ```
2. Entrá a tu proyecto:
   ```bash
   cd mi-proyecto
   ```
3. Inicializá:
   ```bash
   cortex setup full
   ```
</Steps>
```

Renderiza con números grandes y línea conectora.

### 3.7 `<Tabs>`

Para variantes de contenido:

```mdx
<Tabs>
  <Tab label="Claude Code">...</Tab>
  <Tab label="Cursor">...</Tab>
  <Tab label="Pi">...</Tab>
</Tabs>
```

### 3.8 `<Cards>` y `<Card>`

Para landings de sección:

```mdx
<Cards columns={3}>
  <Card title="Quickstart" icon="Rocket" href="/getting-started/">
    Tu primer save-session en 10 minutos.
  </Card>
  <Card title="Conceptos" icon="Brain" href="/concepts/overview">
    Memoria híbrida, RRF, ciclo tripartito.
  </Card>
  <Card title="CLI Reference" icon="Terminal" href="/cli/overview">
    Todos los comandos `cortex`.
  </Card>
</Cards>
```

### 3.9 `<VersionBadge>`

Indica desde qué versión está disponible algo:

```mdx
<VersionBadge since="0.3.0">cortex autopilot</VersionBadge>
```

Renderiza como pill discreto con label "Since 0.3.0".

### 3.10 `<Deprecated>`

Para warnings de deprecación:

```mdx
<Deprecated in="0.5.0" replacement="cortex autopilot start">
Este comando fue reemplazado por...
</Deprecated>
```

### 3.11 `<Term>`

Glosario inline:

```mdx
La <Term>memoria episódica</Term> se almacena en ChromaDB.
```

Renderiza con underline punteado y tooltip con definición.

### 3.12 `<Figure>` y `<Caption>`

```mdx
<Figure>
  <ThemeImage src-light="/diagrams/arch-light.svg" src-dark="/diagrams/arch-dark.svg" alt="..." />
  <Caption>
    Diagrama de la arquitectura de Cortex con sus tres capas de memoria.
  </Caption>
</Figure>
```

### 3.13 `<ApiReference>`

Para SDK Python:

```mdx
<ApiReference
  name="AgentMemory"
  module="cortex.core"
  since="0.1.0"
/>

<ApiMethod name="retrieve" signature="retrieve(query: str, scope: str = 'all', top_k: int = 10) -> RetrievalResult">
  Busca en la memoria con fusión híbrida.
</ApiMethod>
```

## 4. Layout de página

### 4.1 Página estándar

```
┌─────────────────────────────────────────────────────────────────┐
│ Header (sticky)                                                 │
├─────────────┬──────────────────────────────────────┬────────────┤
│             │ breadcrumbs                          │ On this    │
│ Sidebar     │                                      │ page       │
│ (280px)     │ # H1                                  │ - H2       │
│             │ <Summary>                             │ - H2       │
│ - Section   │                                      │   - H3     │
│   - Page    │ ## H2                                 │ - H2       │
│   - Page    │ Body...                              │            │
│   ▸ Active  │                                      │ ─────      │
│             │ <CodeBlock>...</CodeBlock>            │ [Edit]     │
│             │                                      │ [Útil?]    │
│             │ <Callout>...</Callout>                │            │
│             │                                      │            │
│             │ ── divider                           │            │
│             │ [← Prev]    [Next →]                  │            │
└─────────────┴──────────────────────────────────────┴────────────┘
```

### 4.2 Página landing de sección

```
┌─────────────────────────────────────────────────────────────────┐
│ Header                                                          │
├─────────────┬──────────────────────────────────────────────────┤
│ Sidebar     │ # H1 Sección                                       │
│             │ <Summary>                                          │
│             │                                                   │
│             │ <Cards>                                            │
│             │   <Card>...</Card>                                  │
│             │   <Card>...</Card>                                  │
│             │   <Card>...</Card>                                  │
│             │ </Cards>                                            │
│             │                                                   │
│             │ ## Recursos relacionados                            │
│             │ - Link                                              │
│             │ - Link                                              │
└─────────────┴──────────────────────────────────────────────────┘
```

### 4.3 Página landing del docs (`/`)

```
┌─────────────────────────────────────────────────────────────────┐
│ Header                                                          │
├─────────────────────────────────────────────────────────────────┤
│ Hero docs:                                                       │
│   # Documentación de Cortex                                       │
│   [🔍 Search the docs ⌘K]                                          │
│                                                                  │
│ <Cards columns={4}>                                              │
│   Getting started · Concepts · CLI · MCP · Enterprise · ...      │
│ </Cards>                                                          │
│                                                                  │
│ ## Populares                                                      │
│ - cortex setup full                                              │
│ - First save-session                                              │
│ - Configure Enterprise                                            │
│                                                                  │
│ ## Recursos                                                       │
│ - GitHub · Changelog · Community                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Tema claro/oscuro

- **Default**: respeta `prefers-color-scheme`.
- **Persistencia**: localStorage.
- **Toggle**: en header.
- **Code blocks**: el theme de Shiki cambia con el tema general (configurable: `github-dark` / `github-light`).
- **Diagrams**: `<ThemeImage>` con variantes light/dark cuando exista.

## 6. Responsive

| Breakpoint | Layout |
| --- | --- |
| `xs` (<640px) | Sidebar como drawer, sin right rail |
| `sm` (≥640) | Idem |
| `md` (≥768) | Sidebar como drawer; content full-width |
| `lg` (≥1024) | Sidebar visible persistente; sin right rail |
| `xl` (≥1280) | Sidebar + content + right rail |
| `2xl` (≥1536) | Idem con más padding lateral |

## 7. Iconografía

- **Lucide React** consistente con landing.
- Iconos en cards, callouts, badges.
- Stroke 1.5px.

## 8. Accesibilidad específica del docs

- **Skip-to-content** en cada página.
- **Headings jerárquicos** sin saltos (H1 → H2 → H3).
- **Code blocks**: con `aria-label="código en bash"`.
- **Tablas**: con `<caption>` y `<th scope>` correcto.
- **Forms** (feedback ¿útil?): labels asociadas, errores anunciados.
- **Modals** (search overlay): focus trap, Esc cierra, `aria-modal`.

## 9. Branding visual mínimo

- **Logo** del docs reutiliza el de la landing (variantes light/dark).
- **Favicon** + manifest reutilizados.
- **OG image** específica para docs (variants por página opcional).

## 10. Entregables del sistema de diseño (docs)

- ✅ Componentes en Storybook con todos los estados.
- ✅ Theme tokens en `tokens.json` extendido con keys `docs.*`.
- ✅ Tailwind config exportando estos tokens.
- ✅ MDX components map en `apps/docs/src/components/mdx.ts`.
