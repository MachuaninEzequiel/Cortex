---
title: Plan de adopción y crecimiento — Cortex 2026-2027
doc_type: business
status: v1
author: Ezequiel Adrián Machuanin
date: 2026-05-16
audience: profesional conector + potenciales early adopters
---

# Plan de adopción y crecimiento — Cortex

> *"Tu equipo ya usa inteligencia artificial. La pregunta no es si la adoptás. La pregunta es quién la gobierna."*

---

## 1. Tesis

En los últimos veinticuatro meses, la industria del software cruzó una línea que no había cruzado nunca: **el código dejó de escribirse mayoritariamente a mano**. Equipos de tres ingenieros publican hoy un millón de líneas de código al mes; empresas que antes producían diez pull requests por semana producen ahora cuarenta. Lo hace una nueva categoría de software llamada **agente de IA**.

Pero hay un hecho incómodo que toda la industria está empezando a admitir en voz alta: **un gran porcentaje del codigo que se escribe hoy con IA tiene problemas para llegar correctamente a producción**. No fracasan porque los modelos sean malos. Fracasan porque alrededor del modelo no hay nada. No hay memoria que sobreviva entre sesiones. No hay reglas que rijan qué se decide y cómo. No hay registro de qué hizo cada agente, sobre qué base, ni cómo se puede auditar después.

La industria nombró ya esa "capa que rodea al modelo" y la disciplina para construirla. El término técnico canónico, popularizado por OpenAI, Anthropic y Addy Osmani en la primera mitad de 2026, es **agent harness** y **harness engineering**. La definición consensuada es:

> *"Harness engineering es la disciplina de diseñar el scaffolding — context delivery, tool interfaces, planning artifacts, verification loops, memory systems y sandboxes — que rodea a un agente de IA y determina si tiene éxito o falla en tareas reales."*

La fórmula que cierra cada paper técnico, atribuida a Viv Trivedy, es la misma en todas partes:

```
Agente = Modelo + Harness
```

El modelo se comoditiza. El harness es lo que sostiene al agente en producción.

**Cortex no compite con los harnesses personales — los gobierna.**

Hoy existen harnesses personales muy buenos: Claude Code, Cursor, Codex, Opencode, Pi. Cada uno implementa los componentes canónicos del harness — loop, tools, contexto, control flow — para un único desarrollador en una única sesión. Lo que **ninguno** resuelve son los tres problemas que aparecen cuando ese desarrollador deja de ser uno y pasa a ser un equipo:

1. **Memoria que cruza sesiones, proyectos y personas** — no la memoria local del IDE, que se pierde con el `clear`, sino una memoria episódica + semántica + enterprise federada que un compliance officer pueda consultar tres meses después.
2. **Governance declarativa** — un archivo donde la organización dice "estas son las reglas que todos los agentes deben seguir, sin importar qué IDE uses".
3. **MCP uniforme cross-IDE** — el mismo agente, las mismas reglas, las mismas tools, ya sea que el dev abra Claude Code, Cursor, Opencode, Codex o Pi.

Cortex es el **control plane** que añade estos tres componentes sobre cualquier harness personal. No los reemplaza: los enchufa.

---

## 2. Producto en una frase

> **Cortex es un framework gratuito de governance que convierte a los agentes de IA en miembros disciplinados del equipo: con memoria persistente, decisiones auditables y reglas uniformes para toda la empresa. Se instala en tres comandos y funciona sobre Claude Code, Cursor, Codex, Opencode y Pi desde el día uno.**

### Lo que cualquier persona no técnica tiene que entender


Cortex es el sistema que le da a esa IA: **una libreta de memoria**, **un manual de la empresa** y **un libro de actas** que cualquiera puede leer. Y le impone un ritual de trabajo de tres pasos: **antes** de empezar, abrir el ticket y dejar registro de qué se va a hacer; **durante**, dejar marcas cada vez que se decide algo importante; **al final**, escribir con criterio editorial la documentación de lo hecho. Sin excepciones, sin atajos.

### Lo que un técnico tiene que entender

Cortex no construye un harness nuevo desde cero — se enchufa sobre el harness personal del IDE (Claude Code, Cursor, etc.) y le añade los componentes que un harness por-sesión no puede tener:

1. **Modelo triádico de agentes (Pluggable Middle)** — tres skills invocables con `/` en todos los IDEs: `/cortex-sync` (anchor de inicio, obligatorio, persiste la spec y abre la Session) → middle pluggable (`/cortex-SDDwork`, subagents code-*, o BYO) → `/cortex-documenter` (anchor de cierre, obligatorio, escribe la documentación a mano con criterio editorial usando MCP tools dedicadas).
2. **Memoria triádica federada** — episódica (Session actual, ChromaDB local con embeddings ONNX) + semántica (vault del proyecto, 13 doc types canónicos: spec, design, session, handoff, adr, decision, runbook, incident, postmortem, architecture, changelog, hu, glossary) + enterprise (cross-project vía `org.yaml`), con promoción auditable entre niveles vía Reciprocal Rank Fusion.
3. **Servidor MCP con governance enforcement** — ~30 tools registradas (search, context, sync_ticket, create_spec, emit_proposal, session lifecycle, documenter briefing, write_doc, close_session, self_review_note, ping). El servidor **rechaza** operaciones que violen el orden de gobernanza: `cortex_create_spec` falla si no se llamó antes a `cortex_sync_ticket`; `cortex_create_spec` con `proposal_mode="required"` falla si no hubo una llamada previa a `cortex_emit_proposal` con un gap temporal que pruebe que el usuario alcanzó a confirmar.
4. **Verification hooks declarativos** — cada spec declara comandos que prueban objetivamente que el trabajo está hecho (ej. `pytest`, `mypy`). El cierre de Session los corre y decide automáticamente `closed` vs `handoff`.
5. **Modo degradado gitless** — si el proyecto no tiene git, Cortex sigue funcionando con un sentinel `GITLESS_COMMIT_PLACEHOLDER` y avisa al usuario que la fidelidad del documenter será menor.

---

## 3. Mercado

### Cliente ideal (ICP) — primer wave

| Atributo | Definición |
|---|---|
| Industria | Software factory y fintech |
| Tamaño | Startups, pymes y pequeñas empresas (5 a 80 personas) |
| Geografía | Argentina hasta consolidar 5-10 adopters; LATAM después; global cuando el producto esté enterprise-ready |
| Madurez en IA | "Recién adoptando" o "ya la usan pero sin control" — ambas |
| Trigger de adopción | El líder técnico detectó que cada dev usa la IA de forma distinta y los resultados son incoherentes, o que pasó algo que no se puede explicar y necesita trazabilidad |

### Por qué empezamos por Argentina

Tres razones operativas, no patrióticas:

1. **Red de confianza directa** — el founder es argentino, las primeras introducciones vienen de su red local.
2. **Ciclo de feedback corto** — pymes argentinas iteran rápido, son tolerantes a productos jóvenes y dan feedback honesto.
3. **Costo de servicio bajo** — la consultoría de implementación enterprise (modelo de monetización futura) es viable con tarifas locales mientras el producto madura.

Una vez que haya cinco a diez pymes argentinas con Cortex en producción y casos de uso documentados, el siguiente paso natural es LATAM (México, Colombia, Chile, Uruguay) donde el mismo idioma y zona horaria reducen fricción de soporte.

---

## 4. Modelo de negocio

### Hoy (2026) — Adopción libre

- **Framework gratis al 100%.** Sin freemium, sin tiers, sin trial.
- **Objetivo único:** recolectar feedback intensivo de los primeros adopters hasta que el producto sea genuinamente enterprise-ready.
- **Métrica de éxito:** cantidad de adopters que llegan a producción, no facturación.

### Mañana (2027 en adelante) — Consultoría enterprise

- **Framework sigue gratis.** Open-core, código abierto, sin asterisco.
- **Monetización vía consultoría de implantación.** El founder (y eventualmente un equipo) cobra por:
  - Implementación inicial en empresas medianas/grandes
  - Diseño del `org.yaml` corporativo (taxonomía de memoria, reglas de gobernanza)
  - Integración con stacks legacy (LDAP, audit logs corporativos, on-prem)
  - Training de equipos internos
  - Soporte enterprise con SLA


### Lo que NO buscamos

- **No buscamos capital de riesgo.** No en esta etapa, no en el horizonte de los próximos doce meses.
- **No buscamos vender SaaS por seat.** No hay servidor central de Cortex con cuentas y suscripciones.
- **No buscamos lock-in.** Si un adopter quiere irse, su `vault/` es suyo, en archivos planos, sin migración necesaria.

---

## 5. Actualidad: Mayo de 2026

| Frente | Estado |
|---|---|
| GitHub | Estrellas creciendo de forma orgánica; comunidad de desarrolladores individuales adoptando Cortex para uso personal |
| Adopters confirmados | Un equipo de proyecto final usando Cortex como marco metodológico completo |
| Adopters en pipeline | Dos equipos adicionales de proyecto final acordados; dos acercamientos industriales con reunión formal en ~1 semana (una startup del sector y un desarrollador freelance senior con cuatro años de experiencia que destinará un proyecto entero al testing intensivo del framework) |
| Producto | Modelo triádico de agentes (`/cortex-sync` → middle pluggable → `/cortex-documenter`) opera sobre cinco IDEs, aún con falta de validación : Claude Code, Cursor, Codex, Opencode y Pi; arquitectura **Pluggable Middle** completa (las cinco fases post-MVP cerradas en Phase 09.A+ de May 2026); servidor MCP con ~30 tools y governance enforcement por timestamp; pipeline de documentación canónica cubriendo trece doc types (spec, design, session, handoff, adr, decision, runbook, incident, postmortem, architecture, changelog, hu, glossary); embeddings ONNX locales con singleton compartido cross-instance; cobertura **2.064 tests verdes** en la última corrida (+1.300 desde la versión anterior del plan) |
| Documentación | Manifiestos Enterprise, arquitectura global del modelo triádico (`docs/architecture/triadic-agents.md`), arquitectura Pluggable Middle completa, fases de hardening multi-IDE, plantillas CI para GitHub Actions y GitLab CI — todo público en el repo |

### Lo que estos números significan

Lo importante no es la magnitud. Es la **composición**: tenemos adopters que están dispuestos a destinar **proyectos enteros** al uso intensivo de Cortex a cambio de feedback. Eso es exactamente el insumo que necesita un framework joven para madurar — no usuarios casuales sino usuarios comprometidos.

---

## 6. Competencia y diferenciación

### Mapa competitivo

Conviene primero ubicar a Cortex en la categoría correcta. Cortex **no es** un harness personal compitiendo con Claude Code; **es un control plane de governance** que se enchufa sobre cualquier harness personal. La diferencia es la misma que entre un IDE (Claude Code) y un sistema de control de versiones (Git): no compiten, conviven y se necesitan.

| Categoría | Ejemplos | Posición respecto a Cortex |
|---|---|---|
| Harnesses personales de IDE | Claude Code, Cursor, Codex, Opencode, Pi, Continue, Aider | **Cortex se enchufa sobre estos**, no los reemplaza. Resuelven el harness por sesión; no resuelven memoria persistente cross-sesión ni governance organizacional. |
| Memoria personal para devs | Mem0, Letta (ex-MemGPT), Zep | Memoria del individuo, sin escalado a nivel corporativo ni promoción auditable entre niveles. |
| Frameworks de agentes | LangChain, LangGraph, CrewAI, AutoGen | Cajas de herramientas para construir agentes desde cero. Requieren equipo de ingeniería propio; no son productos terminados ni tienen capa de governance lista para producción. |
| Agentes-producto | Devin (Cognition), Factory, Sourcegraph Cody | Productos cerrados que reemplazan al developer humano. Opacos, sin gobernanza configurable por la empresa cliente, sin trazabilidad auditable. |


### El wedge de Cortex

Tres propiedades simultáneas que **ningún competidor** combina hoy:

1. **Modelo triádico de agentes uniforme cross-IDE.** Tres skills (`/cortex-sync`, middle pluggable, `/cortex-documenter`) que se invocan exactamente igual en los cinco IDEs soportados. El dev nunca aprende un workflow distinto según el IDE que use, y la organización nunca tiene que mantener cinco políticas distintas.
2. **Promoción auditable de memoria** del proyecto al nivel corporativo. Una decisión arquitectónica buena tomada en el Proyecto A puede promoverse a regla corporativa visible para el Proyecto B con trazabilidad completa de quién la promovió y por qué — vía los 13 doc types canónicos y el `org.yaml`.
3. **Governance enforcement en el servidor MCP, no en el prompt.** Las reglas de gobernanza (spec antes que código, propuesta confirmada antes que spec en modo `required`, documenter obligatorio al cierre) no son sugerencias del prompt: son rechazos del servidor MCP. El agente no puede saltearlas aunque quiera.


## 7. Roadmap de adopción

### Próximos 3 meses (mayo - agosto 2026)

**Objetivo:** llevar a producción de cinco pymes argentinas el modelo triádico de Cortex.

- Cerrar las dos conversaciones industriales pendientes (Tero + freelance senior)
- Onboarding documentado y reproducible para que un nuevo adopter levante Cortex en menos de treinta minutos sobre el IDE de su elección
- Tres casos de uso publicados (anonimizados si hace falta) con métricas reales de impacto
- Bug bash mensual con la comunidad de adopters

### Próximos 6 meses (agosto 2026 - febrero 2027)

**Objetivo:** transformar feedback de campo en versión enterprise-ready.

- `org.yaml` con suficiente expresividad para los casos legal/compliance más comunes en pyme argentina
- Manifiesto público de seguridad con threat model documentado
- Documentación bilingüe (ES/EN) del core

### Próximos 12-18 meses (febrero 2027 - noviembre 2027)

**Objetivo:** validar el modelo de consultoría.

- Primera contratación de consultoría enterprise paga
- Expansión geográfica a LATAM (al menos un adopter fuera de Argentina)
- Decisión informada sobre si crece como empresa de consultoría o si justifica buscar capital para escalar producto

---

## 8. Lo que busco en esta etapa

Esta es la sección más importante del documento, y la más simple.

**No busco capital.** No en esta etapa. Una ronda de inversión hoy obligaría a Cortex a optimizar para crecimiento por encima de calidad, y eso es exactamente lo opuesto a lo que un framework de gobernanza necesita en su primer año.

**Busco adopters serios.** Equipos técnicos que estén dispuestos a probar Cortex en un proyecto real, no en un sandbox, y dar feedback honesto a cambio del beneficio de ser early adopters de un producto que les va a dar ventaja competitiva permanente.

**Busco conexiones con perfiles complementarios.** En particular:

- Compliance officers o responsables de seguridad de la información en pymes — para validar que el `org.yaml` cubre los controles que realmente les piden los auditores.
- Tech leads de software factories — para hacer adoption en equipo y stress-testear el harness multi-dev.
- Inversores ángel **estratégicos** (no financieros): personas que aporten red de contactos y experiencia en go-to-market de developer tools, más que capital.


## 9. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Founder bus factor de 1 | Alta | Crítico | Documentación pública obsesiva del por qué de cada decisión arquitectónica; todo en el repo, nada en la cabeza. |
| Una big tech publica un control plane de governance gratis sobre su propio IDE | Media | Alto | Cortex se posiciona como **cross-IDE** desde el día uno (cinco IDEs validados). Un control plane atado a un solo IDE rompe el wedge "todos los devs hablan el mismo idioma". El modelo open-core + enfoque pyme también disuade — las big tech tradicionalmente fallan en pymes por costo de servicio y rigidez de pricing. |
| Adopters tempranos no logran llegar a producción | Media | Alto | Onboarding asistido directo del founder durante el primer año; bug-bashes mensuales; SLA implícito de respuesta en horas, no días. |
| El concepto de "harness engineering" pierde tracción en la industria | Baja | Medio | Convergencia ya consolidada en 2026: el término aparece en publicaciones de OpenAI, Anthropic, Addy Osmani (`addyosmani.com/blog/agent-harness-engineering`), Adnan Masood en Medium (Apr 2026), el repositorio público `awesome-harness-engineering`, y el ecosistema MCP de Anthropic. Es vocabulario establecido, no moda. |
| Modelo de consultoría no escala más allá del founder | Media | Medio | Decisión consciente y diferida a 2027; si no escala, el framework sigue vivo como infra open-source y el founder mantiene consultoría boutique sostenible. |
| Pyme argentina no tiene cultura de pagar por consultoría enterprise | Media | Alto | Por eso la geografía se abre a LATAM en M12-18; AR es campo de pruebas, no mercado final. |

---

## 10. Cierre

Hay un momento de oportunidad muy concreto, y se está cerrando. En los próximos doce meses, la categoría "control plane de governance para agentes de IA en pymes" va a tener uno o dos ganadores. La pregunta no es si va a existir esa categoría — la respuesta a eso ya está decidida por el mercado, y los harnesses personales (Claude Code, Cursor, Codex) no la van a ocupar porque chocan con su propio pricing por seat. La pregunta es **quién la va a definir**.

Cortex tiene tres ventajas que se pagan caro: el producto técnico ya funciona, el posicionamiento es claro y honesto, y el founder está construyéndolo a tiempo completo con la disciplina necesaria.

Lo que necesita es exactamente esto: las primeras cinco pymes que se animen a usarlo en serio.

---

**Contacto:** Ezequiel Adrián Machuanin
**Repositorio:** [github.com/MachuaninEzequiel/Cortex](https://github.com/MachuaninEzequiel/Cortex)
**Email:** ezequieladrianmachuanin@gmail.com

---

> *Apéndice — Glosario rápido para no técnicos*
>
> **Agente de IA:** software que usa un modelo de inteligencia artificial para hacer trabajo real (escribir código, analizar datos, redactar documentos) en vez de solo conversar.
>
> **Harness (de agente):** la infraestructura de software que rodea al modelo y maneja todo lo que el modelo no hace — bucle de razonamiento, llamadas a herramientas, gestión de contexto, memoria, persistencia, recuperación de errores. Sin harness un modelo es solo un chat; con harness es un empleado. La fórmula consensuada en la industria es `Agente = Modelo + Harness`.
>
> **Harness engineering:** la disciplina, formalizada en 2025-2026 por OpenAI / Anthropic / Addy Osmani / Adnan Masood, de diseñar harnesses bien hechos. Los IDEs como Claude Code o Cursor implementan harness personales (uno por sesión, uno por developer); Cortex añade encima de ellos los componentes que un harness por-sesión no puede tener: memoria que sobrevive, governance organizacional, MCP uniforme cross-IDE.
>
> **Control plane (de agentes):** término popularizado por Adnan Masood en 2026 para nombrar la capa de governance + observabilidad que se monta sobre los harnesses personales. Es la categoría en la que Cortex se posiciona — no compitiendo con Claude Code, sino gobernándolo junto a sus pares.
>
> **MCP (Model Context Protocol):** protocolo estándar publicado por Anthropic en 2024 para que un IDE de IA descubra y use herramientas y datos externos. Cortex se expone a los IDEs vía un servidor MCP propio con ~30 herramientas registradas.
>
> **Modelo triádico de agentes:** la arquitectura de Cortex desde mayo de 2026. Tres skills invocables con `/`: opening anchor (sync), middle pluggable, closing anchor (documenter). Los dos anchors son obligatorios; el medio se elige según preferencia del equipo.
>
> **Gobernanza:** las reglas y registros que permiten que una organización entienda y controle qué está haciendo su tecnología. Sin gobernanza, una empresa no puede auditar, no puede cumplir regulaciones, no puede explicar errores.
>
> **Memoria corporativa:** lo que la empresa sabe colectivamente. Hoy vive en cabezas, en Notion, en wikis abandonadas. Cortex la convierte en un activo consultable por agentes y humanos por igual, organizado en trece tipos de documento canónicos (spec, design, session, handoff, adr, decision, runbook, incident, postmortem, architecture, changelog, hu, glossary).
