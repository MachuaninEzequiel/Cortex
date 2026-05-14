---
title: Fase 02 — Hero y sección Problema/Solución
doc_type: phase
phase: 2
status: pending
depends_on: [phase-01]
unlocks: [phase-03]
estimated_duration: 5 días-persona
---

# Fase 02 — Hero y Problema/Solución

## Objetivo

Construir las **3 primeras secciones narrativas** de la landing: Hero, Problema, Solución (overview). Estas tres juntas tienen que **vender Cortex en 60 segundos** de scroll.

## Entregables

1. **Sección Hero** (`#hero`) con composición animada y CTAs.
2. **Sección Problema** (`#problema`) con lista de pains y narrativa.
3. **Sección Solución** (`#solucion`) con 3 cards de pilares + CTA a arquitectura.
4. **Background system** con gradientes y patrones reutilizables.
5. **Helper `<Section>`** que aplica padding, max-width y anchor automáticamente.

## Tareas detalladas

### 2.1 Componente `<Section>` (0.5 día)

`src/components/Section.astro`:

```astro
---
interface Props {
  id: string;
  eyebrow?: string;
  variant?: 'default' | 'subtle' | 'dark';
  fullBleed?: boolean;
}
const { id, eyebrow, variant = 'default', fullBleed = false } = Astro.props;
---
<section
  id={id}
  class:list={[
    'relative scroll-mt-20 py-24 md:py-32',
    variant === 'subtle' && 'bg-bg-subtle',
    variant === 'dark' && 'bg-bg-elevated',
  ]}
>
  <div class:list={[!fullBleed && 'mx-auto max-w-7xl px-6 md:px-12']}>
    {eyebrow && (
      <p class="mb-4 text-sm font-medium uppercase tracking-widest text-accent-primary">
        {eyebrow}
      </p>
    )}
    <slot />
  </div>
</section>
```

### 2.2 Hero (2 días)

#### Estructura HTML/Astro

`src/sections/Hero.astro`:

- [ ] Container con `min-h: 90vh` en desktop, `min-h: 80vh` en mobile.
- [ ] Background: `--gradient-hero` (ver `02-sistema-diseno.md`).
- [ ] Patrón decorativo de dots SVG con opacity 0.05.
- [ ] Eyebrow + H1 + Lead + CTAs (copy en `03-estrategia-contenido.md` §3.1).
- [ ] Visual a la derecha (desktop) / abajo (mobile): composición de **3 capas de memoria** flotantes.

#### Composición visual ("Memory Stack")

Isla React `src/components/islands/HeroMemoryStack.tsx`:

- 3 cards apiladas con offset Z:
  1. **Episodic** — fondo gradient teal, ícono `Brain`.
  2. **Semantic** — fondo gradient violeta, ícono `BookOpen`.
  3. **Enterprise** — fondo gradient naranja, ícono `Building`.
- Cada card flota con animación `y: [0, -8, 0]` desfasada (delay incremental).
- Líneas SVG conectando las 3 cards a un punto central (ícono `Bot`).
- Al hover, las cards se separan en Z y muestran un tooltip con nombre + descripción.

#### Animación de entrada

- [ ] H1 entra con `opacity 0 → 1` + `y: 20 → 0` en 600ms ease-out.
- [ ] Lead paragraph entra 200ms después.
- [ ] CTAs entran 400ms después.
- [ ] Visual entra 600ms después con `scale 0.95 → 1`.
- [ ] Si `prefers-reduced-motion: reduce`, todo aparece con fade simple 150ms.

#### CTAs

- [ ] `<Button variant="primary" size="lg">` con efecto shimmer en gradient al hover.
- [ ] `<Button variant="secondary" size="lg">` con ícono `Play` antes del texto.
- [ ] Microcopy debajo: "Open source · MIT · Python 3.10+ · Sin API keys obligatorias".

#### Analytics

- [ ] Click en CTA primario → evento `cta_click` con `cta_id: hero_primary`.
- [ ] Click en CTA secundario → evento `cta_click` con `cta_id: hero_secondary`.
- [ ] Section view → evento `section_view` con `section_id: hero` (debe ser inmediato).

### 2.3 Problema (1 día)

`src/sections/Problem.astro`:

- [ ] Variant `subtle` para diferenciar del hero.
- [ ] Eyebrow + H2 + body (copy en `03-estrategia-contenido.md` §3.2).
- [ ] Grid de 5 cards (mobile: stack; tablet: 2+2+1; desktop: 5 columnas o 2+3).
- [ ] Cada card tiene ícono, título corto, body corto.
- [ ] Cierre del problema en quote-style con border-left accent.

#### Pains cards (5)

```tsx
const pains = [
  { icon: 'Brain', title: 'Amnesia de sesión', body: 'El agente olvida lo que decidiste hace dos días.' },
  { icon: 'ClipboardList', title: 'Cero trazabilidad', body: 'Nadie sabe quién aprobó qué arquitectura.' },
  { icon: 'Repeat', title: 'Bugs recurrentes', body: 'La misma vulnerabilidad se reintroduce cada trimestre.' },
  { icon: 'FileWarning', title: 'Docs desincronizada', body: 'El código avanza, los docs no.' },
  { icon: 'Users', title: 'Conocimiento siloed', body: 'Cada proyecto reinventa el wheel.' },
];
```

#### Animación

- [ ] Cards entran en stagger 80ms al scroll-into-view.
- [ ] Hover: lift 4px + border-color accent.

### 2.4 Solución overview (1.5 días)

`src/sections/Solution.astro`:

- [ ] Variant `default` (vuelve al bg-base).
- [ ] Eyebrow + H2 + body (copy en `03-estrategia-contenido.md` §3.3).
- [ ] Grid de 3 cards grandes (`<FeatureCard>`).
- [ ] CTA al final: `[Explorar arquitectura ⇲]`.

#### Feature cards (3)

```tsx
const features = [
  {
    icon: 'Brain',
    title: 'Memoria Híbrida',
    body: 'Vault Markdown + ChromaDB con embeddings ONNX. Búsqueda RRF adaptativa. <1ms.',
    link: { href: '#pilares', label: 'Ver detalle' },
    gradient: 'from-teal-500/20 to-purple-500/20',
  },
  {
    icon: 'Workflow',
    title: 'Ciclo Tripartito',
    body: 'Sync → SDDwork → Documenter. Cada tarea pasa por análisis, implementación y persistencia.',
    link: { href: '#pilares', label: 'Ver detalle' },
    gradient: 'from-purple-500/20 to-orange-500/20',
  },
  {
    icon: 'Building',
    title: 'Enterprise Governance',
    body: 'Topología org.yaml, promotion auditable, políticas de retención, scopes multi-proyecto.',
    link: { href: '#pilares', label: 'Ver detalle' },
    gradient: 'from-orange-500/20 to-teal-500/20',
  },
];
```

#### Animación

- [ ] Cards entran 100ms staggered con `y: 30 → 0` + `opacity: 0 → 1`.
- [ ] Border gradient animado al hover.

### 2.5 Background system (0.5 día)

`src/components/Backgrounds.astro` (helpers reutilizables):

- [ ] `<DotPattern />` — SVG con dots, opacity 0.05, tile.
- [ ] `<GradientBlob position="top-left" color="primary" />` — radial gradient blur.
- [ ] `<GridLines />` — líneas técnicas estilo "circuit board" para hero secundario.

## Criterios de aceptación

- ✅ Hero se renderiza correctamente en mobile, tablet, desktop.
- ✅ Animaciones suaves a 60fps, sin jank.
- ✅ `prefers-reduced-motion` respetado.
- ✅ Lighthouse Performance ≥ 90 con solo estas 3 secciones.
- ✅ Análisis visual: el hero captura intención en 5 segundos (test con 3 usuarios).
- ✅ Copy en ES y EN sincronizado.
- ✅ Analytics events disparándose correctamente.

## Validación de contenido

- [ ] Lectura cronometrada del hero ≤ 5s (lead paragraph).
- [ ] Lectura cronometrada problema + solución ≤ 60s.
- [ ] Lectura sin scroll en mobile: ¿el H1 + CTA principal son visibles sin scrollear en iPhone 14? (debe ser sí).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Animaciones laggean en mobile | Usar `transform`/`opacity` only, evitar `width/height` en animations |
| Composición Memory Stack se ve crowded | Reducir a 3 cards bien espaciadas, no más |
| H1 muy largo en mobile | `text-wrap: balance`, breakpoints específicos |

## Siguiente fase

→ [Fase 03 — Arquitectura interactiva](fase-03-arquitectura-interactiva.md)
