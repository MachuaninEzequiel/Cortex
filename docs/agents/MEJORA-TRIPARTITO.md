# Análisis: Mejoras de mattpocock/skills para Cortex

He hecho una lectura granular de ambos repos. Cortex ya tiene una base sólida (gobernanza tripartita, RRF híbrido, ONNX, autopilot con anti-rationalization signals), pero Matt Pocock resuelve tres problemas que Cortex aún no resuelve bien y que afectan directo a tu `cortex-documenter` y al modo autónomo.

---

## 1. Análisis comparativo

### Lo que Cortex ya hace mejor que Matt Pocock

- Memoria persistente real (ChromaDB + ONNX) en vez de archivos `.md` sueltos.
- Gobernanza forzada por MCP (`cortex_sync_ticket` obligatorio).
- Anti-amnesia explícita y aislamiento de memoria externa.
- Separación tripartita: sync / SDDwork / documenter.
- Autopilot con tabla de "señales de que estás saltando el flujo".


### Lo que Matt Pocock resuelve y a Cortex le falta

| Problema | Cómo lo resuelve Matt | Estado en Cortex
|-----|-----|-----
| Lenguaje compartido (Ubiquitous Language) | `CONTEXT.md` como glosario vivo, actualizado inline durante el grilling | No existe
| ADRs disciplinados | 3 criterios estrictos: irreversible + sorprendente + trade-off real | Criterio vago ("decisión significativa")
| No duplicar artefactos | Handoff referencia por ruta, nunca copia contenido | El documenter dice "documenta TODO" -> ruido
| Verificación cruzada | Confronta el código real con lo que dice el usuario/agente | Solo en autopilot, no en documenter
| Progressive disclosure | SKILL.md menor a 100 líneas, referencias en archivos separados | Skills monolíticos
| Modo caveman (compresión) | -75% tokens en comunicación inter-agente | No existe
| Zoom-out con glosario | Mapa arquitectónico usando vocabulario del dominio | No existe
| Handoff entre sesiones | Doc compacto que referencia artefactos existentes | `save-session` cumple parcial pero verbose


---

## 2. Mejoras propuestas para `cortex-documenter`

### 2.1 Cambiar la filosofía: "Signal > Noise" en vez de "documenta TODO"

**Problema actual** en `cortex-documenter.md`:

> "NO OMITAS INFORMACIÓN. Documenta TODO el contexto acumulado."



Esto produce notas de sesión verbosas, redundantes con specs/ADRs ya persistidos, y el RRF luego retorna ruido. Matt Pocock lo dice claro en `handoff`:

> "Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead."



**Cambio sugerido:**

```markdown
## HIGH-SIGNAL DOCUMENTATION MODE

Tu objetivo: persistir SOLO la información que no esté ya capturada
en otros artefactos del Vault. Referencia por ruta, no dupliques.

### Regla de oro: Reference > Duplicate
- La spec ya lo dice  -> enlaza con [[spec-id]], NO repitas.
- El diff lo muestra  -> enlaza al PR/commit, NO transcribas archivos.
- El ADR lo justifica -> enlaza con [[adr-id]], NO repitas el rationale.

### Qué SÍ debe contener la session note (el delta cognitivo)
1. Decisiones que NO están en specs ni ADRs (micro-decisiones in-flight).
2. Sorpresas: cosas que no esperabas y que el próximo agente debe saber.
3. TODOs y deuda técnica generada (nuevos, no los preexistentes).
4. Enlaces a: spec, ADR(s), PR, commits, issues relacionadas.
5. Métricas objetivas: cobertura, líneas cambiadas, archivos tocados.
```

### 2.2 Adoptar ADR sparingly (regla de los 3 criterios)

**Problema actual:** "Crea un ADR si hubo una decisión técnica significativa". Demasiado ambiguo: se generan ADRs triviales que contaminan la memoria.

**Cambio sugerido (tomado de `grill-with-docs`):**

```markdown
### Cuándo crear un ADR (los 3 criterios DEBEN cumplirse)

1. Hard to reverse        - el costo de cambiar de opinión luego es real.
2. Surprising w/o context - un lector futuro dirá "por qué hicieron esto".
3. Real trade-off         - había alternativas y se eligió por razones específicas.

Si falta UNO de los tres, NO crees el ADR. Anota la decisión en la session note.

Ejemplos:
OK   ADR: "Elegimos event sourcing sobre CRUD para órdenes" (cumple los 3).
NO   ADR: "Renombramos userId a user_id" (no es irreversible ni sorprendente).
NO   ADR: "Usamos bcrypt para hashear passwords" (no es sorprendente).
```

### 2.3 Introducir `CONTEXT.md`como tercera capa de memoria

Este es el cambio más potente. Hoy Cortex tiene 2 capas (episódica + semántica). Matt agrega una tercera implícita: el glosario del dominio (ubiquitous language). Esto:

- Reduce tokens en cada sesión (el agente usa términos canónicos en vez de paráfrasis).
- Mejora la búsqueda RRF (vocabulario consistente -> embeddings más estables).
- Hace que los nombres de variables/funciones/archivos sean consistentes.


**Propuesta de arquitectura:**

```plaintext
vault/
├── CONTEXT.md         <- NUEVO: glosario vivo (lexical layer)
├── CONTEXT-MAP.md     <- NUEVO: si hay múltiples bounded contexts
├── sessions/          <- existente (episódica indexada)
├── specs/             <- existente
└── adrs/              <- existente
```

**Responsabilidad nueva del documenter:**

```markdown
### Mantenimiento del CONTEXT.md (Ubiquitous Language)

Al finalizar la sesión, revisa si aparecieron términos del dominio
nuevos o redefinidos. Si sí:

1. Lee CONTEXT.md actual.
2. El término ya existe -> verificar uso consistente. Si no, marca conflicto.
3. Es nuevo -> agrégalo con: definición canónica, sinónimos prohibidos, ejemplo.
4. Entró en conflicto con uso previo -> crea ADR de "rename" y actualiza glossary.

Formato de entrada:
## Materialization Cascade
Definition: el proceso por el cual una lesson dentro de una section
adquiere un slot en el filesystem.
Synonyms to avoid: "hacerla real", "darle un spot", "instanciar".
Used in: [[spec-2026-04-15-lesson-creation]], src/lessons/materialize.ts
```

Esto se conecta directo con tu RRF: el `cortex_search` debería bumpear resultados que usen vocabulario del CONTEXT.md (boost lexical).

### 2.4 Verificación cruzada antes de documentar

Hoy el documenter confía ciegamente en lo que le pasa el implementer. Matt fuerza la verificación contra el código real:

```markdown
### Antes de afirmar algo en la session note (verification gate)

Para cada claim sobre el código (archivos modificados, patrones usados):
1. Lee el diff real (git diff o read_file de los archivos mencionados).
2. Si el implementer dijo "usé patrón X" -> verifica que el código lo refleje.
3. Si hay discrepancia -> NO escribas la versión del implementer. Escribe lo
   que muestra el código y marca con:
   > El implementer reportó X pero el código muestra Y.

NO es aceptable escribir "implementé JWT con refresh tokens" si nunca
leíste el archivo que supuestamente lo implementa.
```

Esto convierte al documenter en el último gate de gobernanza, no en un escriba pasivo.

### 2.5 Handoff mode para sesiones interrumpidas (clave para autopilot)

Hoy si autopilot corta a la mitad, queda un `auto-draft` poco útil. Mejor:

```markdown
### Modo Handoff (cuando la sesión se interrumpe)

Si detectas que la tarea NO está completa al cierre (build falla, tests
en rojo, TODOs críticos pendientes), genera la session note en modo
HANDOFF en vez de COMPLETED:

---
status: handoff
date: YYYY-MM-DD
next-session-needs: [lista concreta de lo que falta]
blockers: [lo que bloquea]
verified-state: [qué SI está verificado funcionando]
unverified-claims: [qué afirmaciones del implementer NO pude verificar]
suggested-skills: [skills que el próximo agente debería cargar]
---

# Handoff: <título>
## Estado verificado
## Qué falta exactamente
## Archivos en estado intermedio
## Cómo retomar (pasos concretos)
---

Se indexa con tag #handoff para que el próximo cortex_sync_ticket
lo priorice en RRF.
```

### 2.6 Progressive disclosure del propio skill

El `cortex-documenter.md` actual mezcla todo en un solo archivo (~135 líneas). Matt recomienda:

```plaintext
.cortex/subagents/cortex-documenter/
├── SKILL.md            <- menor a 100 líneas, reglas y triggers
├── SESSION-FORMAT.md   <- plantilla detallada
├── ADR-FORMAT.md       <- plantilla + criterios
├── HANDOFF-FORMAT.md   <- plantilla de handoff
├── CONTEXT-FORMAT.md   <- formato del glosario
└── EXAMPLES.md         <- buenos y malos ejemplos
```

El agente carga primero `SKILL.md` (barato en tokens) y solo lee las referencias cuando las necesita.

---

## 3. Mejoras al concepto de Memoria (cross-cutting)

### 3.1 Tercera capa: Lexical Memory (glosario)

Tu arquitectura actual de retrieval es:

```plaintext
RRF(episodic + semantic)
```

Propuesta:

```plaintext
RRF(episodic + semantic + lexical_boost)

donde lexical_boost = +score si el documento usa términos canónicos del CONTEXT.md
```

Implementa el insight de Matt: un vocabulario compartido hace que la búsqueda funcione mejor sin cambiar el motor.

### 3.2 Confidence levels en memoria episódica

Hoy todas las memorias se almacenan igual. Sugerencia:

```yaml
# Frontmatter de cada session note
confidence:
  verified:     [claims respaldados por tests/build/diff]
  asserted:     [claims del implementer no verificados]
  contradicted: [claims que contradicen memoria previa]
```

`cortex_sync_ticket` debería priorizar `verified` sobre `asserted` y excluir `contradicted` salvo que el usuario lo pida.

### 3.3 Contradiction detection en `cortex_save_session`

Antes de persistir, el documenter debería:

1. Buscar memorias previas relacionadas (`cortex_search` interno).
2. Detectar contradicciones (ej: "antes dijiste X, ahora Y").
3. Si hay contradicción -> forzar ADR de "supersedes".


Es lo que Matt llama "Challenge against the glossary" pero aplicado a memoria episódica.

### 3.4 Memory hygiene skill (`cortex-prune`)

Nuevo skill recurrente (correr semanalmente en CI):

- Detecta sessions duplicadas o redundantes.
- Marca como `archived` notas superadas por ADRs posteriores.
- Compacta runs de auto-drafts del autopilot que nunca llegaron a `completed`.


### 3.5 Caveman mode para comunicación inter-subagente

En Deep Track, los subagentes (`cortex-SDDwork`, `code-explorer`, `code-implementer`, `documenter`) intercambian texto verboso. Activando un modo caveman solo en handoffs internos (no al usuario), bajás tokens ~75% sin perder señal.

```markdown
# Inter-agent communication: caveman mode
auth.py refactor JWT. middleware.py new. tests pass.
TODO: rotate keys. deuda: hardcoded TTL.
```

---

## 4. Mejoras específicas para Modo Autónomo

### 4.1 Verification gate obligatorio antes de `finish`

Tu `using-cortex-autopilot.md` ya tiene la regla de verificación. Llevala al documenter:

```markdown
# En cortex-documenter, antes de cortex_save_session

PRE-FLIGHT del save:
- [ ] Leí el diff real (no solo el reporte del implementer)
- [ ] Verifiqué que los tests mencionados existen y pasan
- [ ] Verifiqué que no haya contradicciones con memorias previas
- [ ] El CONTEXT.md está actualizado si hay términos nuevos
- [ ] Marqué claims no verificados como unverified-claims

Si algún check falla -> status: handoff (no completed).
```

### 4.2 Anti-rationalization signals para el documenter

Replicá la tabla del autopilot pero adaptada:

| Pensamiento del documenter | Realidad
|-----|-----|-----
| "El implementer ya documentó esto" | Verificá. Tu trabajo es persistir, no asumir.
| "Es muy largo, voy a resumir" | Resumir no es lo mismo que omitir verificación.
| "No vale la pena un ADR" | Aplicá los 3 criterios, no tu intuición.
| "El código habla por sí solo" | El próximo agente no leerá todo el repo.
| "Lo agrego al CONTEXT.md después" | Después = nunca. Hacelo inline.


### 4.3 Chain-of-responsibility con handoff estructurado entre subagentes

En lugar de pasar texto crudo, cada subagente debe entregar un mini-handoff estructurado:

```yaml
# Output estandarizado de cada subagente
agent: cortex-code-implementer
status: complete | partial | blocked
verified_claims:
  - "auth.py: JWT validation added (tested)"
unverified_claims:
  - "performance impact negligible"
artifacts_produced:
  - path: src/auth.py
    action: modified
context_for_next:
  - "documenter needs to verify TTL hardcoding decision"
suggested_adr: false
suggested_context_md_terms: ["JWT refresh window"]
```

Esto hace al `cortex-documenter` mucho más fácil de auditar y verificar porque recibe input estructurado, no prosa.

---

## 5. Roadmap sugerido (orden de prioridad)

| # | Cambio | Impacto | Esfuerzo
|-----|-----|-----
| 1 | Reescribir `cortex-documenter.md` con Signal>Noise + 3 criterios ADR + verification gate | Alto | Bajo
| 2 | Introducir `CONTEXT.md` y responsabilidad del documenter de mantenerlo | Alto | Medio
| 3 | Handoff mode con frontmatter `status: handoff` | Alto | Bajo
| 4 | Output estructurado YAML entre subagentes | Alto | Medio
| 5 | Progressive disclosure del skill (split en archivos) | Medio | Bajo
| 6 | Lexical boost en RRF basado en CONTEXT.md | Medio | Alto
| 7 | Confidence levels + contradiction detection | Medio | Alto
| 8 | Caveman mode inter-subagente | Bajo | Bajo
| 9 | `cortex-prune` skill de hygiene | Bajo | Medio


---

## 6. Siguiente paso

Tengo dos entregables concretos para arrancar:

**Opción A** — Reescribir el `cortex-documenter.md` completo aplicando los puntos 2.1 a 2.5 (signal>noise, ADR sparingly, verification gate, handoff mode, progressive disclosure). Lo entrego listo para pegar en `.cortex/subagents/`.

**Opción B** — Diseñar la spec del `CONTEXT.md` + lexical layer con formato, reglas de mantenimiento, y cómo integrarlo al RRF.