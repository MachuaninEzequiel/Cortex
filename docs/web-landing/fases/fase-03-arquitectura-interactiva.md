---
title: Fase 03 — Diagrama de arquitectura interactivo
doc_type: phase
phase: 3
status: pending
depends_on: [phase-02]
unlocks: [phase-04]
estimated_duration: 6 días-persona
---

# Fase 03 — Diagrama de arquitectura interactivo

## Objetivo

Construir **la pieza estelar visual** de la landing: un **diagrama interactivo** de la arquitectura de Cortex donde el visitante puede explorar cada módulo, ver qué hace, y profundizar con un click. Es la sección más memorable; tiene que tener "wow factor" sin sacrificar legibilidad.

## Entregables

1. **Sección `#arquitectura`** con diagrama SVG/Canvas interactivo.
2. **Datos del diagrama** en `src/data/architecture.ts` (nodos, edges, descripciones).
3. **Interacción**: hover (tooltip), click (panel lateral con detalle), drag (panear), wheel (zoom controlado).
4. **Tour automático** opcional: al primer scroll-into-view, el diagrama se "presenta" animadamente.
5. **Fallback responsive**: en mobile, el diagrama se reemplaza por **carrusel de cards**.
6. **Versión accesible**: navegable por teclado, descripción textual paralela.

## Tareas detalladas

### 3.1 Datos de arquitectura (1 día)

`src/data/architecture.ts`:

```ts
export type ArchNode = {
  id: string;
  group: 'core' | 'memory' | 'governance' | 'integration' | 'ui';
  label: string;
  icon: string;
  shortDesc: string;
  longDesc: string;
  position: { x: number; y: number };
  docsLink: string;
};

export type ArchEdge = {
  from: string;
  to: string;
  kind: 'data' | 'control' | 'dependency';
  animated?: boolean;
};

export const nodes: ArchNode[] = [
  { id: 'core', group: 'core', label: 'AgentMemory', icon: 'Box', shortDesc: 'Fachada principal', longDesc: '...', position: { x: 50, y: 50 }, docsLink: '...' },
  { id: 'episodic', group: 'memory', label: 'Episodic', icon: 'Database', shortDesc: 'ChromaDB + ONNX', longDesc: '...', position: { x: 25, y: 30 }, docsLink: '...' },
  { id: 'semantic', group: 'memory', label: 'Semantic Vault', icon: 'BookOpen', shortDesc: 'Markdown', longDesc: '...', position: { x: 75, y: 30 }, docsLink: '...' },
  { id: 'retrieval', group: 'core', label: 'RRF Retrieval', icon: 'Search', shortDesc: 'Hybrid search', longDesc: '...', position: { x: 50, y: 35 }, docsLink: '...' },
  { id: 'autopilot', group: 'core', label: 'Autopilot', icon: 'Bot', shortDesc: 'Orchestrator opt-in', longDesc: '...', position: { x: 50, y: 70 }, docsLink: '...' },
  { id: 'enterprise', group: 'governance', label: 'Enterprise', icon: 'Building', shortDesc: 'org.yaml, promotion', longDesc: '...', position: { x: 25, y: 70 }, docsLink: '...' },
  { id: 'mcp', group: 'integration', label: 'MCP Server', icon: 'Cable', shortDesc: 'Tools para IDE', longDesc: '...', position: { x: 75, y: 70 }, docsLink: '...' },
  { id: 'webgraph', group: 'ui', label: 'WebGraph', icon: 'Network', shortDesc: 'Knowledge graph viz', longDesc: '...', position: { x: 90, y: 50 }, docsLink: '...' },
  { id: 'cli', group: 'ui', label: 'CLI', icon: 'Terminal', shortDesc: '30+ comandos', longDesc: '...', position: { x: 10, y: 50 }, docsLink: '...' },
];

export const edges: ArchEdge[] = [
  { from: 'core', to: 'episodic', kind: 'dependency' },
  { from: 'core', to: 'semantic', kind: 'dependency' },
  { from: 'retrieval', to: 'episodic', kind: 'data' },
  { from: 'retrieval', to: 'semantic', kind: 'data' },
  { from: 'core', to: 'retrieval', kind: 'control' },
  { from: 'autopilot', to: 'core', kind: 'control', animated: true },
  { from: 'enterprise', to: 'core', kind: 'data' },
  { from: 'mcp', to: 'core', kind: 'control' },
  { from: 'webgraph', to: 'core', kind: 'data' },
  { from: 'cli', to: 'core', kind: 'control' },
];
```

- [ ] Long descriptions extraídas del análisis del repo (ver READMEs de cada módulo).
- [ ] Cada `docsLink` apunta a la página correspondiente en `web-docs`.

### 3.2 Componente `<ArchitectureDiagram>` (3 días)

Stack interno: **React + SVG nativo** (no D3 directamente; usar React Flow opcionalmente).

#### Decisión: SVG manual vs React Flow

| Criterio | SVG manual | React Flow |
| --- | --- | --- |
| Customización visual | Total | Limitada por API |
| Bundle | Liviano | ~40 KB |
| Tiempo de desarrollo | Mayor | Menor |
| Animaciones custom | Total con Framer Motion | Limitado |

**Decisión recomendada**: SVG manual + Framer Motion. Permite control total para animaciones signature (líneas dibujándose, nodos pulsando, glow effects).

#### Estructura

`src/components/islands/ArchitectureDiagram.tsx`:

```tsx
type Props = { nodes: ArchNode[]; edges: ArchEdge[] };

export default function ArchitectureDiagram({ nodes, edges }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  // ...
}
```

Sub-componentes:

- `<NodeBubble>` — círculo con icono + label, color por `group`.
- `<EdgeLine>` — path SVG con `stroke-dasharray` animado.
- `<NodeTooltip>` — tooltip flotante en hover.
- `<DetailPanel>` — panel lateral o modal con descripción larga + link a docs.

#### Interacciones

- [ ] **Hover**: nodo se eleva (scale 1.05), tooltip aparece, edges salientes se highlight.
- [ ] **Click**: panel lateral slide-in desde la derecha con detalle del nodo.
- [ ] **Esc**: cierra panel.
- [ ] **Drag**: pan del viewport (solo desktop, opcional).
- [ ] **Wheel**: zoom limitado entre 0.8 y 1.5 (no permitir extremos que rompan diseño).
- [ ] **Keyboard**: `Tab` recorre nodos en orden lógico, `Enter` selecciona.

#### Animaciones signature

- [ ] **Entrance**: al primer scroll-into-view, los nodos aparecen en stagger (núcleo primero, luego los demás expandiéndose hacia afuera).
- [ ] **Edges**: las líneas se "dibujan" con `stroke-dashoffset` animado (Framer Motion).
- [ ] **Edges animadas (`kind: 'control'` con `animated: true`)**: tienen `<animateMotion>` mostrando flujo de datos.
- [ ] **Pulso constante** en el nodo `core` para indicar el centro.

#### Performance

- [ ] Nodos y edges como elementos SVG nativos (no canvas, no WebGL).
- [ ] Throttle de eventos mouse a 60fps.
- [ ] Lazy import del componente con `client:visible`.

### 3.3 Panel de detalle (1 día)

Cuando el usuario clickea un nodo, se abre un **panel lateral** (desktop) o **bottom sheet** (mobile):

- [ ] Header: ícono + label + group pill.
- [ ] Body: `longDesc` formateado en Markdown (usa MDX o `marked`).
- [ ] Lista de "Conexiones" (otros nodos a los que se conecta).
- [ ] CTA: `[Leer documentación →]` → link externo a `docs.cortex.dev/...`.
- [ ] Botón cerrar (Esc también funciona).
- [ ] Trap focus dentro del panel mientras está abierto.

### 3.4 Fallback responsive (0.5 día)

En `<md` (768px):

- [ ] El diagrama interactivo se oculta (`hidden md:block`).
- [ ] En su lugar, mostrar **carrusel horizontal** de cards (una por nodo).
- [ ] Cada card tiene icono + label + shortDesc + botón "Ver más".
- [ ] Scroll snap.
- [ ] Indicadores de paginación.

### 3.5 Versión accesible textual (0.5 día)

Debajo (o en `<details>` colapsable):

- [ ] Lista textual de todos los nodos y conexiones.
- [ ] Estructurada como descripción para screen-readers.
- [ ] `aria-describedby` desde el diagrama enlaza a esta lista.

## Criterios de aceptación

- ✅ El diagrama se ve **espectacular** en desktop (validar con dirección y 3 testers).
- ✅ Interacciones suaves a 60fps incluso con todos los nodos visibles.
- ✅ Mobile fallback funciona bien con touch swipe.
- ✅ Keyboard navigation completa.
- ✅ Screen reader puede entender la estructura.
- ✅ Bundle de esta isla < 50 KB gzipped.
- ✅ Lighthouse Performance sigue ≥ 90.

## Validación visual

- [ ] Captura de pantalla del diagrama "wow" para usar en redes sociales.
- [ ] Video Loom mostrando interacciones (hover, click, drag, zoom).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| SVG con muchos nodos laggea | Limitar a ≤ 12 nodos en V1; agregar más en V2 |
| Layout no responsive | Definir posiciones en porcentaje, no en píxeles fijos |
| Edge crossings se ven feos | Curvar edges con Bezier; revisar layout manualmente |
| Texto ilegible en mobile | Mobile usa carrusel, no el diagrama |

## Siguiente fase

→ [Fase 04 — Pilares y features](fase-04-pilares-features.md)
