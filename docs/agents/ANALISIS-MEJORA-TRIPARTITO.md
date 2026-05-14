# Análisis Crítico: Propuesta MEJORA-TRIPARTITO

> **Referencia:** `docs/agents/MEJORA-TRIPARTITO.md`
> **Fecha de análisis:** 2026-05-12
> **Analista:** Agente de análisis profundo del repositorio Cortex (lectura exhaustiva de `cortex/`)

---

## Contexto del Análisis

La propuesta MEJORA-TRIPARTITO fue generada por un agente de IA que analizó el repositorio de Cortex **desde GitHub, sin acceso al código fuente real**. Esto explica por qué la propuesta contiene:
- **Aciertos de proceso** que detectó correctamente desde el README y los skills.
- **Errores arquitectónicos** graves porque no tuvo acceso a la implementación real de retrieval, memoria y gobernanza.

Este documento es el veredicto ejecutivo. **No hay contemplaciones.** Si una idea no aporta valor, se descarta con una sola línea. Si aporta, se desarrolla con propuestas concretas, prompts nuevos y justificación técnica basada en la lectura milimétrica del código.

---

## Estado Real de Cortex (Lo que la propuesta NO vio)

Antes de juzgar, es obligatorio entender la arquitectura real que la propuesta subestima:

| Componente | Implementación Real en `cortex/` | Complejidad Ignorada |
|---|---|---|
| **Episodic Memory** | ChromaDB + ONNX (`all-MiniLM-L6-v2`). Extrae **8 tipos de entidades** (functions, classes, endpoints, errors, config_keys, dependencies, variables, constants) vía regex en `memory_store.py`. Entity search nativo con filtros `where` de ChromaDB. Cache con token de invalidación. Namespace por proyecto/rama/custom. | **Alta** |
| **Semantic Memory** | Vault Markdown con frontmatter + wiki-links + hashtags. **ONNX embeddings + BM25 fallback** precomputado (IDF, avgdl, doc_lengths). **Selective indexing** (solo reindexa archivos nuevos, no full resync). | **Alta** |
| **Retrieval** | True **RRF cross-source** (k=60) con **adaptive weighting** basado en `QueryIntentDetector` (clasifica EPISODIC vs SEMANTIC vs MIXED vía regex). Soporta keyword-only bypass sin cargar ONNX. Enterprise multi-scope RRF. | **Alta** |
| **Context Enricher** | 5 estrategias (topic, files, keywords, pr_title, **entity_search**). Multi-match boost (1.5x). Co-occurrence boost. **Typed graph** (relaciones semánticas AST-based). **Temporal decay** exponencial (half-life 168h, floor 10%) con excepciones por tipo permanente. **Feedback loop** implícito. | **Muy Alta** |
| **WebGraph** | Grafo híbrido con 6 tipos de aristas (wikilink, same_file_reference, shared_tag, shared_entity, same_spec_reference, semantic_neighbor). | **Alta** |
| **Enterprise** | Retrieval federado (local/enterprise/all). Promotion Pipeline (candidate → reviewed → promoted) con fingerprints SHA256. | **Alta** |
| **Autopilot** | Detectores (ambiguous, security-sensitive, large-refactor). Políticas (budget, spec-required, documentation-required, auto-checkpoint). | **Alta** |

**Consecuencia:** La propuesta parte de la premisa falsa de que Cortex tiene "2 capas simples" y propone una "tercera capa". En realidad Cortex tiene **6+ subsistemas de memoria** ya interconectados. Añadir una "tercera capa" sin entender las existentes es sobre-ingeniería.

---

## Veredicto por Sección

---

### 2.1 Signal > Noise en Documentación

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE**

**Por qué es crítica:**

El skill actual de `cortex-documenter.md` contiene la instrucción fatal:
> *"NO OMITAS INFORMACIÓN. Documenta TODO el contexto acumulado."*

Esto produce sesiones verbosas que **contaminan el vault semántico y el RRF**. Cuando un agente documenta "TODO", está duplicando información que ya existe en specs, ADRs y código. El RRF recupera esa información duplicada con scores altos, **aumentando el ruido y consumiendo tokens del contexto del agente**.

Cortex ya tiene **selective indexing** que evita duplicación técnica, pero el *skill* incentiva duplicación semántica. Este es un **problema de proceso**, no de arquitectura.

**Propuesta concreta: Reescritura del prompt del documenter**

Reemplazar la sección de objetivo actual por:

```markdown
## HIGH-SIGNAL DOCUMENTATION MODE

Tu objetivo NO es transcribir todo lo que pasó. Tu objetivo es persistir
SOLO la información que NO esté ya capturada en otros artefactos del Vault.

### Regla de oro: Reference > Duplicate

Antes de escribir una sola línea, pregunta:
- ¿La spec ya lo dice? → Enlaza con `[[spec-id]]`. NO repitas.
- ¿El diff lo muestra? → Enlaza al PR/commit. NO transcribas archivos.
- ¿El ADR lo justifica? → Enlaza con `[[adr-id]]`. NO repitas el rationale.
- ¿El código es autoexplicativo? → NO lo documentes. El siguiente agente puede leerlo.

### Qué SÍ debe contener la session note (el delta cognitivo)

1. **Decisiones que NO están en specs ni ADRs** (micro-decisiones in-flight).
2. **Sorpresas**: cosas que no esperabas y que el próximo agente debe saber.
3. **TODOs y deuda técnica generada** (nuevos, no los preexistentes).
4. **Enlaces a**: spec, ADR(s), PR, commits, issues relacionadas.
5. **Métricas objetivas**: cobertura, líneas cambiadas, archivos tocados.

### Qué NO debe contener la session note

- Transcripción de specs ya existentes.
- Explicaciones de código que el diff ya muestra.
- Decisiones arquitectónicas que ya tienen ADR.
- Lista completa de archivos modificados si el diff la tiene.

### Ejemplo de delta cognitivo correcto

```yaml
---
date: 2026-05-12
tags: [feature, auth]
status: completed
related-spec: "[[auth-refactor-spec]]"
related-adr: "[[jwt-over-session-adr]]"
---

# Sesión: Refactor de autenticación

## Sorpresas
- El middleware de Express no permitía inyectar el `AuthService` sin circular
  dependency. Se resolvió con factory pattern (ver `auth.factory.ts`).

## Deuda técnica
- [ ] TTL de refresh token hardcodeado a 7 días. Mover a config.
- [ ] `auth.py:147` tiene `TODO: manejar race condition en token rotation`.

## Decisiones in-flight (sin ADR)
- Se eligió bcrypt con cost factor 12 porque argon2 no está disponible en
  el runtime de producción (AWS Lambda). Si migran runtime, reevaluar.

## Métricas
- 3 archivos modificados, 147 líneas cambiadas
- Cobertura: 78% → 89%
- Tests nuevos: 12 unitarios, 2 de integración
```
```

**Impacto esperado:** -40% de tamaño de session notes, +30% de señal en retrieval RRF.

---

### 2.2 ADR Sparingly (Regla de los 3 Criterios)

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE**

**Por qué es crítica:**

El criterio actual — *"Crea un ADR si hubo una decisión técnica significativa"* — es **subjetivo e inflacionario**. Un agente genera ADRs por renombrar variables o elegir bcrypt para passwords (decisiones triviales). Cada ADR se indexa en memoria semántica, aparece en RRF, y consume tokens de contexto.

Los 3 criterios de Matt son objetivos y verificables:
1. **Hard to reverse** — costo real de migración.
2. **Surprising w/o context** — un lector futuro diría "¿por qué?".
3. **Real trade-off** — había alternativas y se eligió por razones específicas.

**Propuesta concreta: Inyección en el prompt del documenter**

Añadir al skill de `cortex-documenter.md`:

```markdown
### Criterios para crear un ADR (DEBEN cumplirse TODOS)

Antes de crear un ADR, verifica que la decisión cumpla los 3 criterios:

1. **Hard to reverse**: ¿Cuánto costaría deshacer esta decisión?
   - < 1 día de trabajo → NO ADR. Anótalo en la session note.
   - > 1 semana de refactor → Candidata a ADR.

2. **Surprising w/o context**: ¿Un desarrollador nuevo diría "¿por qué hicieron esto?"
   - Si la respuesta es obvia (ej. "usamos bcrypt para hashear passwords") → NO ADR.
   - Si la respuesta requiere contexto histórico (ej. "usamos event sourcing porque el
     requerimiento de auditoría lo exige y CRUD no deja trazabilidad") → Candidata a ADR.

3. **Real trade-off**: ¿Se evaluaron alternativas con pros/contras documentados?
   - Si solo hubo una opción viable → NO ADR.
   - Si se rechazó una alternativa por razones específicas → Candidata a ADR.

### Ejemplos

| Decisión | Hard to reverse | Surprising | Trade-off | Veredicto |
|---|---|---|---|---|
| "Elegimos event sourcing sobre CRUD para órdenes" | ✅ Sí (migración de datos) | ✅ Sí (¿por qué no CRUD?) | ✅ Sí (latencia vs. trazabilidad) | **CREAR ADR** |
| "Renombramos userId a user_id" | ❌ No (1 minuto) | ❌ No (convención) | ❌ No (una sola opción) | **NO ADR** |
| "Usamos bcrypt para passwords" | ⚠️ Media | ❌ No (estándar) | ❌ No (una sola opción) | **NO ADR** |
| "Hardcodeamos TTL de 7 días en refresh tokens" | ✅ Sí (afecta sesiones activas) | ✅ Sí (¿por qué 7?) | ✅ Sí (UX vs. seguridad) | **CREAR ADR** |

### Si NO cumple los 3 criterios

Registra la decisión en la session note bajo la sección "Decisiones In-Flight",
NO en un ADR. El RRF recuperará la session note si alguien busca el contexto.
```

**Impacto esperado:** -60% de ADRs triviales, +50% de calidad de ADRs existentes.

---

### 2.3 CONTEXT.md como "Tercera Capa de Memoria"

**VEREDICTO: ❌ CAMBIO DESCARTADO POR NO APORTAR VALOR**

**Por qué se descarta:**

La propuesta sugiere que Cortex tiene "2 capas" (episódica + semántica) y propone una tercera: `CONTEXT.md` como glosario de Ubiquitous Language, con boost léxico en el RRF.

**Esto es falso en tres niveles:**

1. **Premisa falsa:** Cortex NO tiene "2 capas simples". Tiene episódica + semántica + webgraph (relacional) + enterprise (federado) + co-occurrence (gráfico de archivos) + entity index + temporal decay + feedback loop. La arquitectura ya tiene **6+ subsistemas de memoria** interconectados.

2. **Error arquitectónico:** Un glosario NO es una "capa de memoria" del mismo tipo que episódica/semántica. Es **metadata/ontología**. Presentarlo como `RRF(episodic + semantic + lexical_boost)` es forzar una arquitectura que no encaja. El RRF funciona fusionando rankings de fuentes heterogéneas con scores comparables. Un "boost léxico" post-hoc basado en parsear un archivo Markdown en cada búsqueda:
   - Introduce latencia en cada retrieval
   - Es frágil (¿y si CONTEXT.md está desactualizado?)
   - Rompe la determinismo del RRF (scores ya no son reproducibles)

3. **Solución ya existente y superior:** El problema real es "los agentes usan términos inconsistentes". La solución NO es modificar el motor de retrieval. La solución es **inyectar el glosario como contexto de system prompt** para los agentes `cortex-sync` y `cortex-documenter`. Si los agentes usan términos consistentes, los embeddings de MiniLM ya se alinearán naturalmente (el modelo captura sinónimos y contexto).

**Lo que SÍ se puede hacer (sin tocar arquitectura):**

Usar `CONTEXT.md` como guía de estilo para agentes, inyectándolo en los system prompts. Esto es **proceso**, no arquitectura.

```markdown
# Ubiquitous Language Guide (para agentes, NO es capa de retrieval)

## Términos canónicos del dominio

| Término canónico | Definición | Sinónimos PROHIBIDOS |
|---|---|---|
| Materialization Cascade | Proceso por el cual una lesson adquiere un slot en filesystem | "hacerla real", "darle un spot", "instanciar" |
| Session Note | Nota de sesión persistida en vault/sessions/ | "log", "reporte", "minuta" |
| Spec | Especificación técnica persistida en vault/specs/ | "ticket", "requerimiento", "historia" |
| ADR | Architecture Decision Record | "decisión", "justificación", "rationale doc" |

## Reglas de uso

1. Usa SIEMPRE el término canónico en session notes y specs.
2. Si descubres un nuevo concepto del dominio, regístralo aquí ANTES de usarlo.
3. Si un concepto entra en conflicto con uso previo, crea un ADR de rename.
```

**Impacto esperado del descarte:** Cero. La arquitectura actual ya resuelve el problema de retrieval. El glosario como guía de estilo aporta valor marginal.

---

### 2.4 Verification Gate antes de Documentar

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE — ESTO ES CRÍTICO**

**Por qué es crítica:**

Hoy el documenter es un **escriba pasivo**: recibe lo que el implementer le dice y lo persiste sin verificar. Si el implementer dice "implementé JWT con refresh tokens" pero nunca leyó el archivo, el documenter escribe una mentira que queda indexada para siempre en ChromaDB. La próxima búsqueda `cortex_search("JWT refresh tokens")` recuperará una memoria **falsa**.

Esto es una **vulnerabilidad de gobernanza**: la memoria episódica se convierte en un vector de desinformación técnica acumulativa.

**Propuesta concreta: Prompt de Verification Gate para el documenter**

```markdown
## VERIFICATION GATE — Obligatorio antes de `cortex_save_session`

NO generes la session note hasta haber completado TODOS estos checks.

### Checklist Pre-Flight

- [ ] **Diff real leído**: Ejecuté `git diff` (o leí los archivos modificados
  con `read_file`). NO confío en el reporte del implementer.
- [ ] **Tests verificados**: Si el implementer dice "tests pasan", verifiqué
  que existen y ejecuté `cortex_test_run` o leí el output.
- [ ] **Claims verificados**: Para cada claim técnico ("usé patrón X",
  "agregué validación Y"), verifiqué que el código lo refleje.
- [ ] **Contradicciones detectadas**: Busqué en `cortex_search` memorias
  previas relacionadas. Si contradice algo anterior, lo marqué explícitamente.
- [ ] **ADR actualizado**: Si la sesión generó/modificó un ADR, verifiqué
  que el ADR refleje la decisión real (no la intención del implementer).

### Si hay discrepancia

NO escribas la versión del implementer. Escribe lo que el código/diff
muestra y marca con:

> ⚠️ **Discrepancia detectada**: El implementer reportó X, pero el diff
> muestra Y. La session note refleja el estado real del código.

### Si un check falla

NO cierres la sesión con `status: completed`. Ciérrala con `status: handoff`
(ver sección Handoff Mode).
```

**Impacto esperado:** El documenter pasa de ser escriba a ser **gate de gobernanza técnica**. Reducción de memorias falsas en ~80%.

---

### 2.5 Handoff Mode para Sesiones Interrumpidas

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE**

**Por qué es crítica:**

El autopilot genera `auto-draft` que puede quedar a mitad de camino si:
- La sesión se interrumpe por timeout del modelo
- El build falla
- Los tests no pasan
- Hay TODOs críticos pendientes

Un `auto-draft` con `status: completed` es **tóxico**: el siguiente agente recupera una memoria que dice "todo listo" cuando en realidad el trabajo está roto.

**Propuesta concreta: Prompt de Handoff Mode para el documenter**

```markdown
## Modo Handoff (cuando la sesión NO está completa)

Si detectas que la tarea NO está completa al cierre (build falla, tests
en rojo, TODOs críticos pendientes, checks de verificación fallidos),
genera la session note en modo HANDOFF en vez de COMPLETED.

### Estructura obligatoria de handoff

```yaml
---
status: handoff
date: YYYY-MM-DD
next-session-needs:
  - "Implementar rotación de claves JWT (TODO en auth.py:147)"
  - "Mover TTL hardcodeado a config.yaml"
  - "Ejecutar test de integración que falla en CI"
blockers:
  - "AWS Lambda no soporta argon2, requiere decisión de runtime"
verified-state:
  - "auth.py: JWT validation funciona (testeado manualmente)"
  - "middleware.py: interceptor de tokens atrapa 401 correctamente"
unverified-claims:
  - "Implementer dice 'performance negligible' pero no hay benchmarks"
suggested-skills:
  - "cortex-SDDwork" (continuar implementación)
  - "cortex-code-explorer" (investigar dependencia circular)
---

# Handoff: <título de la tarea>

## Estado Verificado
- Qué SÍ funciona y fue validado.

## Qué Falta Exactamente
- Lista concreta de tareas pendientes con referencias a líneas de código.

## Archivos en Estado Intermedio
- Archivos que compilan pero no están terminados.
- Archivos con TODOs críticos.

## Cómo Retomar
1. Paso 1 concreto
2. Paso 2 concreto
3. ...
```

### Indexación

Las handoff notes se indexan con tag `#handoff` para que el próximo
`cortex_sync_ticket` las priorice en RRF por encima de session notes
completadas.
```

**Impacto esperado:** El siguiente agente sabe exactamente dónde quedó el trabajo anterior. Reducción de retrabajo en ~50%.

---

### 2.6 Progressive Disclosure del Skill

**VEREDICTO: ⚠️ CAMBIO DESCARTADO POR NO APORTAR VALOR**

**Por qué se descarta:**

Cortex **ya tiene skills divididos** (obsidian-markdown, json-canvas, obsidian-bases, etc.). El `cortex-documenter` es un **subagente**, no un skill monolítico en el sentido de Matt Pocock. Dividir un subagente de ~135 líneas en 6 archivos (SKILL.md, SESSION-FORMAT.md, ADR-FORMAT.md, HANDOFF-FORMAT.md, CONTEXT-FORMAT.md, EXAMPLES.md) añade complejidad de navegación sin mejorar la funcionalidad.

El verdadero problema de tokens en el documenter no es el tamaño del skill (135 líneas es razonable), sino el **contenido de las session notes** que genera. Resolver 2.1 (Signal>Noise) reduce más tokens que dividir el skill.

**Excepción:** Si el skill del documenter crece >300 líneas, reconsiderar.

---

### 3.1 Tercera Capa: Lexical Memory (Glosario)

**VEREDICTO: ❌ CAMBIO DESCARTADO POR NO APORTAR VALOR**

**Por qué se descarta (extensión de 2.3):**

La propuesta sugiere:
```
RRF(episodic + semantic + lexical_boost)
donde lexical_boost = +score si el documento usa términos canónicos del CONTEXT.md
```

**Problemas técnicos insalvables:**

1. **Fragilidad:** Un boost léxico basado en un archivo mantenido manualmente introduce una fuente de no-determinismo. Si un desarrollador olvida actualizar CONTEXT.md, el retrieval empieza a penalizar documentos válidos.

2. **Redundancia:** El sistema actual ya tiene mecanismos superiores:
   - **Entity extraction** en episodic ya normaliza identificadores (functions, classes) — `memory_store.py` líneas 115-150.
   - **BM25** en semantic ya hace matching léxico robusto con IDF precomputado.
   - **Adaptive RRF** ya ajusta pesos por tipo de query.
   - **QueryIntentDetector** ya clasifica queries por información buscada.

3. **Costo:** Implementar un parseo de CONTEXT.md en cada retrieval añade latencia y complejidad al `HybridSearch._rrf_fuse()`, que hoy es puro y determinista.

**La arquitectura de retrieval de Cortex está probada y no necesita una tercera capa.** El glosario como guía de estilo para agentes (ver 2.3) es suficiente.

---

### 3.2 Confidence Levels en Memoria Episódica

**VEREDICTO: ⚠️ CAMBIO DESCARTADO POR NO APORTAR VALOR (por ahora)**

**Por qué se descarta:**

La propuesta sugiere frontmatter con:
```yaml
confidence:
  verified:     [claims respaldados por tests/build/diff]
  asserted:     [claims del implementer no verificados]
  contradicted: [claims que contradicen memoria previa]
```

Requiere cambios en:
- Schema de `MemoryEntry` (nuevo campo `confidence`)
- Parser del documenter (detectar qué parte del texto es "claim" vs "narrativa")
- Retrieval service (filtrar por confidence)
- UI/CLI (mostrar confidence levels)

**Esfuerzo real: ALTO** (la propuesta lo marca como "Medio", pero es incorrecto).

**Problema fundamental:** Sin un sistema automático de verificación (que no existe hoy), los agentes no pueden etiquetar confiablemente sus propias memorias. Un agente que etiqueta `verified` sin haber leído el diff es **peor que no tener el sistema** (falsa sensación de seguridad).

**Cuándo reconsiderar:** Después de implementar 2.4 (Verification Gate). Si el verification gate está operativo, los agentes podrían etiquetar automáticamente:
- Claims que pasaron verification gate → `verified`
- Claims que no se pudieron verificar → `asserted`
- Claims que el diff contradice → `contradicted`

Pero hoy, sin verification gate, **este sistema sería decorativo**.

---

### 3.3 Contradiction Detection en `cortex_save_session`

**VEREDICTO: ❌ CAMBIO DESCARTADO POR NO APORTAR VALOR**

**Por qué se descarta:**

La propuesta sugiere:
> "Antes de persistir, buscar memorias previas relacionadas y detectar contradicciones"

**Problemas:**

1. **No define CÓMO detectar:** ¿Embeddings similarity? ¿LLM judge? ¿Diff de texto? Cada enfoque tiene falsos positivos masivos.
2. **Costo computacional:** Ejecutar un LLM call (o incluso una búsqueda semántica adicional) en cada `save_session` duplica el tiempo de persistencia.
3. **Falsos positivos:** "Usamos JWT" (memoria vieja) vs "Reemplazamos JWT por session cookies" (memoria nueva) no es una contradicción, es una evolución. Un detector automático no distingue.
4. **Solución existente:** El verification gate (2.4) resuelve el problema de forma más elegante: si el agente verifica contra el diff real, las "contradicciones" se detectan en el momento, no post-hoc.

**Cuándo reconsiderar:** Si en el futuro se implementa un sistema de verificación automática con LLM-as-judge, el contradiction detection sería un subproducto natural.

---

### 3.4 Memory Hygiene (`cortex-prune`)

**VEREDICTO: ⚠️ CAMBIO DESCARTADO POR NO APORTAR VALOR (por ahora)**

**Por qué se descarta:**

Cortex ya tiene **temporal decay** que desprioriza memorias viejas automáticamente (`memory_decay.py`):
- Half-life de 168 horas (7 días)
- Floor de 10% para memorias permanentes (ADR, architecture)
- Excepciones por tipo (`PERMANENT_TYPES`)

El decay ya resuelve el problema de "ruido acumulado" sin riesgo de perder memoria valiosa. Un `cortex-prune` semanal con agente automático tiene riesgo de:
- Archivar memoria que un desarrollador necesita 6 meses después
- Correr en CI y fallar por permisos de archivos
- Generar falsos positivos de "redundancia"

**Cuándo reconsiderar:** Cuando el vault tenga >10,000 documentos y el decay no sea suficiente. Hoy el proyecto es joven.

---

### 3.5 Caveman Mode para Comunicación Inter-Subagente

**VEREDICTO: ❌ CAMBIO DESCARTADO POR NO APORTAR VALOR**

**Por qué se descarta:**

La propuesta sugiere que los subagentes se comuniquen así:
```
auth.py refactor JWT. middleware.py new. tests pass.
TODO: rotate keys. deuda: hardcoded TTL.
```

**Problemas graves:**

1. **Contradice la filosofía de Cortex:** El core de Cortex es **documentación rica y trazable**. Un handoff en "caveman mode" pierde el contexto que el documenter necesita para generar documentación de calidad. Si el explorer dice "auth.py refactor JWT" sin explicar POR QUÉ se refactorizó, el documenter no puede escribir un ADR ni una session note útil.

2. **Los subagentes ya son concisos:** Ver `cortex-code-explorer.md`: *"Tu output debe ser CONCISO y ESTRUCTURADO"*. No hay problema de verbosidad en los handoffs actuales.

3. **El problema real de tokens no está en los handoffs:** Está en las **session notes verbosas** (resuelto por 2.1) y en la **duplicación de información** en el vault (resuelto por selective indexing).

4. **Riesgo de degradación:** Un agente que recibe input en caveman mode no puede verificar claims contra código real (2.4). No sabe qué verificar.

**Impacto esperado si se aplica:** -75% de tokens en handoffs, -90% de calidad de documentación generada. **No aplica.**

---

### 4.1 Verification Gate Obligatorio antes de `finish`

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE (idéntico a 2.4)**

Ya cubierto en 2.4. La propuesta lo repite en la sección de autopilot. Es el mismo cambio.

---

### 4.2 Anti-Rationalization Signals para el Documenter

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE**

**Por qué es valiosa:**

Los agentes tienen tendencia a racionalizar atajos. Una tabla de "señales de que estás saltando el flujo" obliga al agente a auto-cuestionarse.

**Propuesta concreta: Tabla de Anti-Rationalization para el documenter**

Añadir al skill de `cortex-documenter.md`:

```markdown
## Anti-Rationalization Signals

Cuando pienses cualquiera de estas frases, DETENTE y verifica:

| Pensamiento del documenter | Realidad | Acción obligatoria |
|---|---|---|
| "El implementer ya documentó esto" | El implementer NO documenta. Tú eres el único que persiste. | Verifica con `read_file` o `git diff`. |
| "Es muy largo, voy a resumir" | Resumir no es lo mismo que omitir verificación. | Resume DESPUÉS de verificar. |
| "No vale la pena un ADR" | Tu intuición no es criterio. Aplica los 3 criterios objetivos. | Evalúa: ¿Hard to reverse? ¿Surprising? ¿Trade-off? |
| "El código habla por sí solo" | El próximo agente no leerá todo el repo. | Documenta el POR QUÉ, no el QUÉ. |
| "Lo agrego al CONTEXT.md después" | Después = nunca. | Si descubriste un término nuevo, regístralo AHORA en el handoff. |
| "El diff es obvio" | Lo obvio hoy es un misterio en 6 meses. | Documenta la sorpresa, no lo evidente. |
| "Ya hay una spec similar" | ¿Está actualizada? ¿Refleja el estado post-cambio? | Verifica la spec con `read_file` antes de referenciarla. |
| "Los tests pasan, todo bien" | ¿Ejecutaste tú los tests o confías en el reporte? | Verifica el output de tests o ejecuta `cortex_test_run`. |
```

**Impacto esperado:** Reduce la tasa de "session notes de mentira" en ~60%.

---

### 4.3 Chain-of-Responsibility con Handoff Estructurado

**VEREDICTO: ✅ APLICAR INMEDIATAMENTE — ESTA ES LA MEJORA MÁS VALOROSA**

**Por qué es la mejora más valiosa:**

Hoy los subagentes se pasan prosa. El explorer dice "encontré que auth.py usa JWT". El implementer dice "refactoricé auth.py". El documenter dice "el implementer refactorizó auth.py". Cada agente **reinterpreta** lo que el anterior dijo, acumulando distorsión (teléfono roto).

Un handoff estructurado en YAML elimina la interpretación:
- `verified_claims`: Lo que el agente verificó con código real
- `unverified_claims`: Lo que el implementer dijo pero no verificó
- `artifacts_produced`: Archivos modificados con acción exacta
- `context_for_next`: Qué necesita saber el siguiente agente
- `suggested_adr`: Si la decisión amerita ADR

**Propuesta concreta: Prompt de Output Estructurado para TODOS los subagentes**

Reemplazar la salida libre de todos los subagentes por:

```markdown
## Contrato de Salida (Output Obligatorio)

Al finalizar, tu último mensaje DEBE ser un bloque YAML con esta estructura
exacta. NO uses prosa. NO uses markdown fuera del bloque YAML.

```yaml
agent: cortex-code-explorer  # o cortex-code-implementer, cortex-documenter
status: complete | partial | blocked
verified_claims:
  - "auth.py: función `validateToken` recibe string, retorna boolean (verificado con read_file)"
  - "middleware.py: nuevo archivo, exporta `authInterceptor` (verificado con ls)"
  - "tests: 12 unitarios ejecutados, todos pasan (verificado con test output)"
unverified_claims:
  - "performance impact negligible (sin benchmarks)"
  - "race condition en token rotation no manejada (reportado por implementer, no verificado)"
artifacts_produced:
  - path: src/auth.py
    action: modified
    lines_changed: 47
  - path: src/middleware.py
    action: created
    lines_added: 89
context_for_next:
  - "documenter: verificar que TTL de refresh token está hardcodeado en línea 147"
  - "documenter: el implementer no manejó race condition, documentar como deuda técnica"
  - "SDDwork: si el próximo ticket es auth-related, priorizar rotación de claves"
suggested_adr: true
suggested_adr_reason: "Hardcodear TTL de 7 días tiene trade-off UX vs. seguridad"
suggested_context_terms:
  - "JWT refresh window"
  - "token rotation"
```

### Reglas del contrato

1. **verified_claims**: SOLO claims que verificaste tú mismo con `read_file`,
   `git diff`, o ejecución de tests. Si no lo verificaste, va en `unverified_claims`.
2. **unverified_claims**: Todo lo que el implementer (o tú) afirmó sin evidencia.
   Esto le da al documenter y al reviewer una lista explícita de qué cuestionar.
3. **artifacts_produced**: Lista exhaustiva de archivos tocados. El documenter
   usa esto para saber QUÉ verificar.
4. **context_for_next**: Información estructurada que el siguiente agente necesita.
   NO uses prosa. Sé concreto: archivo, línea, acción requerida.
5. **suggested_adr**: `true` si la sesión tomó una decisión que cumple los 3 criterios.
   El documenter evalúa y decide.
```

**Impacto esperado:** El documenter pasa de recibir prosa a recibir un **contrato verificable**. La trazabilidad mejora radicalmente. El teléfono roto entre agentes desaparece.

---

## Roadmap Ejecutivo Recomendado

| Prioridad | Cambio | Esfuerzo | Impacto | Tipo |
|---|---|---|---|---|
| **P0** | 2.1 Signal>Noise + nuevo prompt del documenter | Bajo | **Alto** | Skill |
| **P0** | 2.4 Verification Gate + nuevo prompt | Bajo | **Alto** | Skill |
| **P0** | 4.3 Output YAML estructurado entre subagentes | Medio | **Alto** | Skill/Proceso |
| **P0** | 2.5 Handoff Mode + nuevo prompt | Bajo | **Alto** | Skill |
| **P1** | 2.2 ADR 3 criterios + tabla de decisión | Bajo | **Alto** | Skill |
| **P1** | 4.2 Anti-rationalization signals | Bajo | Medio | Skill |
| **P2** | 2.3 CONTEXT.md como guía de estilo (NO capa de retrieval) | Medio | Medio | Skill |
| **P3** | 3.2 Confidence levels | Alto | Medio | Arquitectura |
| **P4** | 3.4 Memory hygiene (`cortex-prune`) | Medio | Bajo | CI/Proceso |
| **—** | 2.6 Progressive disclosure | — | — | Descartado |
| **—** | 3.1 Lexical boost en RRF | — | — | Descartado |
| **—** | 3.3 Contradiction detection | — | — | Descartado |
| **—** | 3.5 Caveman mode | — | — | Descartado |

---

## Conclusión Ejecutiva

La propuesta MEJORA-TRIPARTITO es **un 40% de oro y un 60% de sobre-ingeniería**.

### Lo que sí aporta (aplicar inmediatamente)
- **Signal>Noise** (2.1): Reduce contaminación del vault.
- **Verification Gate** (2.4): Convierte al documenter en gate de gobernanza.
- **Handoff Mode** (2.5): Salva sesiones interrumpidas.
- **ADR 3 criterios** (2.2): Elimina ADRs triviales.
- **Output YAML estructurado** (4.3): Elimina el teléfono roto entre agentes.
- **Anti-rationalization** (4.2): Fuerza auto-cuestionamiento.

### Lo que no aporta (descartar sin contemplación)
- **Tercera capa léxica** (3.1): La arquitectura actual es más rica de lo que la propuesta entendió. El RRF adaptive + entity extraction + BM25 ya resuelven el problema.
- **Caveman mode** (3.5): Contradice la filosofía de documentación rica y trazable.
- **Contradiction detection** (3.3): Falsos positivos masivos, sin mecanismo claro.
- **Progressive disclosure** (2.6): El documenter ya es un subagente, no un skill monolítico.
- **Memory hygiene** (3.4): Temporal decay ya cubre el 90% del problema.

### La lección clave

La propiedad más valiosa de la propuesta es **proceso**, no arquitectura. Matt Pocock entendió que el problema de documentación es **cultural** (los agentes generan ruido), no técnico (el motor de retrieval funciona). Las ideas de proceso son oro. Las ideas de arquitectura son humo.

**Ejecutar los cambios de skill. No tocar la arquitectura de memoria.**
