---
title: Fase 04 — Pilares tecnológicos
doc_type: phase
phase: 4
status: pending
depends_on: [phase-03]
unlocks: [phase-05]
estimated_duration: 5 días-persona
---

# Fase 04 — Pilares tecnológicos

## Objetivo

Construir la sección `#pilares`: **4 pilares** profundizados con visuales propios, métricas y links a documentación. Esta sección **transforma curiosidad en convicción**.

Los 4 pilares (en orden):

1. **Memoria Híbrida RRF** — la pieza diferenciadora.
2. **Modelo Tripartito** — la disciplina.
3. **Autopilot** — la autonomía opt-in.
4. **Enterprise Governance** — la madurez corporativa.

## Entregables

1. **Sección `#pilares`** con 4 sub-secciones alternadas (texto-imagen / imagen-texto).
2. **4 visuales animados** (uno por pilar) construidos como islas React.
3. **Métricas en `<MetricCard>`** integradas en cada pilar.
4. **Links** a documentación correspondiente.
5. **Animaciones scroll-driven**: cada pilar se "activa" al entrar en viewport.

## Tareas detalladas

### 4.1 Layout y composición (0.5 día)

`src/sections/Pillars.astro`:

- [ ] Eyebrow + H2 + intro corto.
- [ ] 4 sub-secciones, alternando posición del visual (zigzag): pilar 1 visual derecha, pilar 2 visual izquierda, etc.
- [ ] Cada sub-sección con grid 12 columnas, 6 col texto + 6 col visual.
- [ ] En mobile, stack vertical (visual arriba, texto abajo).
- [ ] Separadores sutiles (línea hairline con gradient) entre pilares.

### 4.2 Pilar 1 — Memoria Híbrida (1 día)

#### Texto

Copy en `03-estrategia-contenido.md` §3.5 "Pilar 1".

#### Visual: "Memory Fusion"

Isla React `src/components/islands/MemoryFusionViz.tsx`:

- 3 capas horizontales:
  1. **Episodic** (teal gradient, ícono `Database`, label "ChromaDB · <1ms").
  2. **Semantic** (violet gradient, ícono `BookOpen`, label "Vault Markdown").
  3. **Enterprise** (orange gradient, ícono `Building`, label "Corporate Vault").
- Una "query" entra desde la izquierda (texto floating "¿Cómo manejamos auth?").
- Cada capa devuelve sus resultados como cards mini.
- En el medio, un nodo "RRF Fusion" combina los resultados y emite el output final a la derecha.
- Loop continuo: la query se reescribe cada ~6 segundos con queries diferentes (rotativo de 3-4 queries).

#### Métricas (MetricCards)

| Valor | Label |
| --- | --- |
| `<1ms` | Latencia por embedding |
| `~50MB` | Footprint en memoria |
| `0` | API keys requeridas |
| `~384` | Dimensiones del embedding (all-MiniLM-L6-v2) |

#### Animación

- [ ] Cada capa entra con stagger 100ms al scroll-into-view.
- [ ] Query y fusion son animaciones loopadas con Framer Motion.
- [ ] Pause en hover sobre el visual.

### 4.3 Pilar 2 — Modelo Tripartito (1 día)

#### Texto

Copy en `03-estrategia-contenido.md` §3.5 "Pilar 2".

#### Visual: "Triptych Flow"

Isla React `src/components/islands/TriptychFlow.tsx`:

- 3 columnas (estilo tríptico medieval, sin la connotación religiosa):
  1. **Sync — El Analista** (ícono `Search`, color teal).
     - Frase: "Recupera contexto. Escribe spec."
     - Mini-output: tarjeta YAML con `create-spec` summary.
  2. **SDDwork — El Orquestador** (ícono `GitBranch`, color violet).
     - Frase: "Enruta. Implementa. Verifica."
     - Mini-output: dos badges "Fast Track" y "Deep Track" con toggle visual.
  3. **Documenter — El Guardián** (ícono `BookmarkCheck`, color orange).
     - Frase: "Persiste. Audita. Cierra el ciclo."
     - Mini-output: tarjeta `save-session` con confidence labels.
- Flecha animada conectando las 3 columnas (data flow), con paquetes de "datos" (small dots) viajando.
- Debajo, un **handoff YAML** flotante con typewriter effect que muestra ejemplo de handoff entre agentes.

#### Animación

- [ ] Las 3 columnas se "activan" en stagger al scroll.
- [ ] La flecha se dibuja izquierda → derecha.
- [ ] Los dots de data flow loopean.
- [ ] El handoff YAML typewritea cuando la sección está visible.

#### Métricas

| Valor | Label |
| --- | --- |
| `100%` | Tareas con session note |
| `2` | Tracks de routing (Fast/Deep) |
| `7+` | Roles de agente disponibles |

### 4.4 Pilar 3 — Autopilot (1 día)

#### Texto

Copy en `03-estrategia-contenido.md` §3.5 "Pilar 3".

#### Visual: "Autopilot Timeline"

Isla React `src/components/islands/AutopilotTimeline.tsx`:

- Timeline horizontal de izquierda a derecha con 5 estaciones:
  1. `start` (ícono `Play`)
  2. `preflight` (ícono `Radar`)
  3. `checkpoint` (ícono `BookmarkPlus`) — múltiples
  4. `finish` (ícono `CheckCircle`)
  5. `report` (ícono `FileText`)
- Una "cabeza lectora" se mueve por la timeline mostrando el estado actual.
- A cada lado de la timeline, dos "carriles":
  - Arriba: badges de **políticas activas** (Budget, Timeout, Enforcement).
  - Abajo: notas que se generan automáticamente.
- Toggle de **modo** (Observe / Assist / Autopilot) que cambia el comportamiento visual:
  - `observe`: la cabeza lectora avanza pero no genera notas.
  - `assist`: genera notas pero pide confirmación (badge "Confirma?").
  - `autopilot`: avanza sola y genera todo.

#### Animación

- [ ] Loop infinito de la timeline (60s de duración).
- [ ] Cambio de modo es instantáneo, animado con cross-fade.

#### Métricas

| Valor | Label |
| --- | --- |
| `3` | Modos de operación |
| `5+` | Políticas configurables |
| `opt-in` | Activación |
| `reversible` | Desinstalación |

### 4.5 Pilar 4 — Enterprise Governance (1 día)

#### Texto

Copy en `03-estrategia-contenido.md` §3.5 "Pilar 4".

#### Visual: "Enterprise Topology"

Isla React `src/components/islands/EnterpriseTopologyViz.tsx`:

- **Nodo central** ("Organización") con label dinámico (rotación: "Banco · Healthtech · Fintech · Startup regulada").
- **Sub-nodos** (proyectos):
  - Proyecto A, Proyecto B, Proyecto C, Proyecto D.
- **Vault local** por proyecto + **vault enterprise** compartido (visible en el centro).
- **Flujo de promoción** animado: un documento "candidate" sale de Proyecto A, va al vault central, pasa por revisión (badge `reviewed`), llega como `promoted`.
- **Retention timer** visible para algunos docs (cuenta regresiva mostrando "expires in 365d").

#### Animación

- [ ] Flujo de promoción loopea cada 8 segundos.
- [ ] Sub-nodos pulsan suavemente.
- [ ] Toggle visible para cambiar **preset**: `small-company | multi-project-team | regulated-org` — cambia la cantidad y disposición de proyectos.

#### Métricas

| Valor | Label |
| --- | --- |
| `4` | Presets disponibles |
| `3` | Profiles de gobernanza (observability/advisory/enforced) |
| `JSON` | Reporting estable |
| `auditable` | Promotion pipeline |

### 4.6 CTA al final de cada pilar (0.5 día)

Cada pilar termina con un link estilo:

```astro
<a href="https://docs.cortex.dev/concepts/{pilar}" class="link-accent">
  Cómo funciona en detalle →
</a>
```

## Criterios de aceptación

- ✅ Los 4 visuales se ven hermosos, no genéricos.
- ✅ Animaciones loopean sin causar GPU strain.
- ✅ Toggles funcionan (modo Autopilot, preset Enterprise).
- ✅ Links a docs son correctos.
- ✅ En mobile, los visuales se simplifican pero siguen funcionando.
- ✅ Lighthouse Performance ≥ 90.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| 4 islas Framer Motion saturan CPU | Pausar animaciones fuera de viewport con IntersectionObserver |
| Visuales se ven "infantiles" | Revisión visual con diseñador senior obligatoria antes de finalizar |
| Mucho texto, poco escaneo | Cada pilar tiene visual prominente + métricas; el body es breve |

## Siguiente fase

→ [Fase 05 — Demos interactivos](fase-05-demos-interactivos.md)
