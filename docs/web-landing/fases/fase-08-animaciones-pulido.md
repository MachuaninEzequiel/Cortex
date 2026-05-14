---
title: Fase 08 — Animaciones, micro-interacciones y pulido
doc_type: phase
phase: 8
status: pending
depends_on: [phase-07]
unlocks: [phase-09]
estimated_duration: 5 días-persona
---

# Fase 08 — Animaciones, micro-interacciones y pulido

## Objetivo

Llevar la landing de "funcional" a "memorable". Esta fase es la que diferencia un sitio competente de uno **espectacular**.

Trabajamos exclusivamente sobre lo que ya existe: agregamos motion contextual, micro-interacciones, transiciones entre secciones, sonidos sutiles (opt-in) y refinamiento visual general.

## Entregables

1. **Sistema de scroll-driven animations** unificado.
2. **Micro-interacciones** en TODOS los elementos interactivos.
3. **Page transitions** entre `/`, `/enterprise`, `/changelog`.
4. **Cursor effects** opcionales (desktop only).
5. **Loading states / skeletons** para islas.
6. **Pulido visual** de cada sección con review en mesa.

## Tareas detalladas

### 8.1 Sistema de scroll-driven animations (1.5 días)

Crear hook unificado `src/lib/useScrollAnimation.ts`:

```ts
import { useScroll, useTransform } from 'framer-motion';

export function useScrollReveal(ref: RefObject<HTMLElement>) {
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });
  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0, 1, 1, 0.95]);
  const y = useTransform(scrollYProgress, [0, 0.3], [40, 0]);
  return { opacity, y };
}
```

Aplicar consistentemente a:

- [ ] Cada sección que tenga `<Section>` wrapper.
- [ ] Cards en grids (con stagger).
- [ ] Headings H2 individuales.
- [ ] Imágenes/visuales secundarios.

#### Animaciones parallax

- [ ] **Hero**: el gradient blob se mueve sutilmente con el scroll (`translateY * 0.3`).
- [ ] **Memory Stack hero**: cada capa se desplaza con un factor diferente.
- [ ] **Pilares**: el visual de cada pilar tiene un mini parallax dentro de su sub-sección.

#### Animaciones scroll-snap-style

- [ ] Al scrollear lento, las secciones "respiran" (escala 0.98 → 1).
- [ ] Sutil; nunca obvio. Test con dirección.

### 8.2 Micro-interacciones (1.5 días)

#### Buttons

- [ ] Primary: shimmer gradient en hover (gradient animado con `background-position`).
- [ ] Secondary: border accent crece de 1 → 2px.
- [ ] Ghost: bg ligero accent on hover.
- [ ] Link: underline gradient anchored from-left.
- [ ] Active state (pressed): scale 0.97 con transition 100ms.

#### Cards

- [ ] Lift 4px on hover + glow shadow accent.
- [ ] Border si es "interactive": gradient accent animated rotation.
- [ ] Tilt 3D leve siguiendo cursor (desktop, opcional).

#### Code blocks

- [ ] Copy button aparece en hover (fade-in 150ms).
- [ ] On copy, ícono cambia a check verde por 1.5s.
- [ ] Tabs: indicador con `layoutId` Framer para morphing smooth.

#### Form inputs

- [ ] Border accent en focus.
- [ ] Label flota arriba en focus (Material-style).
- [ ] Validación inline con icono check verde / X rojo.

#### Toasts

- [ ] Sistema unificado (`react-hot-toast` o custom).
- [ ] Slide-in desde top-right (desktop) o bottom (mobile).
- [ ] Auto-dismiss 3s, hover para pausar.

### 8.3 Page transitions (1 día)

Usar **Astro View Transitions** API:

- [ ] Configurar `<ViewTransitions />` en `Base.astro`.
- [ ] `view-transition-name` en logo (shared element transition).
- [ ] `view-transition-name` en hero H1 (cuando se navega entre `/` y `/enterprise`).
- [ ] Fallback graceful en navegadores sin soporte.

### 8.4 Cursor effects (0.5 día, opcional)

Solo desktop con pointer:fine:

- [ ] **Magnetic cursor**: botones primarios tienen atracción ligera del cursor (radio 60px).
- [ ] **Cursor accent**: pequeño dot accent siguiendo el cursor con lag.
- [ ] **Hover en interactivos**: cursor se transforma o cambia.

Opt-out:

- [ ] Botón en footer o config para desactivar cursor effects.
- [ ] Auto-deshabilitado en `prefers-reduced-motion`.

### 8.5 Loading states y skeletons (0.5 día)

Para islas hidratadas con `client:visible`:

- [ ] Antes de hidratar: render del HTML estático.
- [ ] Durante hidratación: opcional spinner o "...".
- [ ] Para componentes con datos async (WebGraph snapshot):
  - Skeleton con shimmer mientras carga.
  - Fallback con screenshot si error.

### 8.6 Pulido visual cross-section (1 día)

Review section-by-section con criterios:

- [ ] Espaciado consistente entre secciones (192px vertical en desktop).
- [ ] Alineación tipográfica vertical (baseline grid si es viable).
- [ ] Border-radius consistente (16px en cards, 12px en buttons, 8px en pills).
- [ ] Sombras alineadas: `--shadow-sm`, `--shadow-md`, `--shadow-lg`.
- [ ] Sin "huérfanos" tipográficos (palabras solas al final de heading).
- [ ] Eyebrows todas en el mismo color y peso.
- [ ] Iconos del mismo set (Lucide) y mismo stroke width.

#### Review con dirección

- [ ] Sesión de 90 min recorriendo la landing en desktop + mobile.
- [ ] Sign-off por sección.
- [ ] Lista de "nice-to-have" no bloqueantes para V1.1.

## Criterios de aceptación

- ✅ Cada interacción se siente "snappy" (< 100ms de feedback).
- ✅ Scroll es suave y las animaciones cohesivas.
- ✅ `prefers-reduced-motion` respetado en TODO.
- ✅ Cero jank al scrollear rápido.
- ✅ Visual review con 3 personas (incluyendo no técnicas) — feedback positivo.
- ✅ Lighthouse Performance ≥ 90 todavía.

## Pruebas de UX

- [ ] **5-second test**: mostrar la landing 5s a 5 personas, preguntar qué es Cortex. ≥ 4 deben acertar.
- [ ] **Scroll test**: ¿cuánto scroll antes de aburrirse? Idealmente llega al final ≥ 50% de testers.
- [ ] **Click test**: ¿en qué CTA pinchan primero? Debe ser el primario del hero.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Overload de animaciones marea al usuario | Animation budget: máximo 3 animaciones simultáneas por viewport |
| Page transitions rompen en Safari viejo | Fallback puro con CSS fade |
| Cursor effects se ven gimmick | A/B test con 10 usuarios, si suma a percepción de calidad mantener, sino remover |
| Pulido extiende timeline | Sign-off por sección permite cierre incremental |

## Siguiente fase

→ [Fase 09 — Performance, SEO y a11y](fase-09-performance-seo-a11y.md)
