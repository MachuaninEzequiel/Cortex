# Casos de uso y demos

Fuentes: `/concepts/use-case-map`, `/demos`, `/demos/smart-home`.

## Categorías (use-case map)

### AI Automation Software
Intercalar AI con software fiable de un modo que se pueda correr un millón de veces en background sin copiloto humano. El código dueña el control flow (no markdown files); TypeSafe maneja decisiones semánticas y language understanding.

### Real-time applications
Inteligencia de frontera a velocidades reales (~150 ms): AI que decide más rápido que la percepción humana. Suficiente para games o embeber en UI.

### AI Map Reduce over Big Data
“100x cheaper” permite procesar datasets gigantes: search sobre corpus grandes, clasificar traces de agentes, extraer features para predicción.

### Universal Verification
Verificar input prompt, extractions, reasoning traces, tool calls u otros inputs de cualquier AI. Detectar jailbreaks, errores de cita, alucinaciones, mistakes — a una fracción del costo de la call LLM real.

### Harness Engineering
Queries Jev para hacer el harness más inteligente: model routing, semantic context retrieval, detección de errores LLM y guardrails, clasificación de reasoning traces a lightspeed y fracción de costo.

## Automatizaciones listadas (scan de la página)

- **Search y retrieval.** Complementar o reemplazar embeddings en RAG: semantic search, scoring, ranking, pairwise, cross-encode, select context.
- **Scientific discovery.** Inclusion/exclusion de papers, label de pasajes, check de citas, flag de métodos faltantes, entities/relaciones para knowledge graphs.
- **Model routing.** Router custom: intent, domain, difficulty, risk → qué LLM recibe el prompt.
- **LLM guardrails.** Checks semánticos in/out/tool a fracción del costo. Jailbreak, policy, PII, tool-call errors.
- **Semantic code linting.** Lints semánticos de convenciones de equipo, en CI.
- **Feature extraction for predictive modeling.** Features probabilísticas desde NL + structured data; autoresearch contra ground truth.
- **Recruiting.** Resumes vs criterios explícitos, competencies, match a roles, escalate inciertos.
- **Lead generation.** Fit a ICP, intent de compra, priorización.
- **Customer support.** Clasificar tickets, transcripts, urgencia, frustración, churn, refund, ruteo, verificar respuestas vs policy.
- **Insurance claims.** FNOL, complexity, missing info, fraud indicators, straight-through vs specialist.
- **Financial crime.** Narrativas, KYC, entity match, priorizar alerts.
- **Legal and compliance.** (la página continúa en esa familia: contratos, policy, etc.)

La página es un mapa para brainstorm, no un catálogo de productos shippeados.

## Demos

`/demos` es el índice de ejemplos interactivos.

### Smart home assistant (`/demos/smart-home`)

SPA Vite/React. Video Loom embebido. Source promised on GitHub at release.

**Patrón principal: speculative fan-out.** Cada user request se evalúa contra una lista larga de questions, muchas irrelevantes para la mayoría de requests.

Request “Turn off all of the lights in the house” — el código solo necesita:

- ¿categoría? (smarthome command)
- ¿dominio? (whole house)
- ¿tipo de device? (lights)
- ¿acción sobre las luces? (turn off)

La última se escribe **asumiendo** que el user está comandando luces, **antes** de saberlo. Eso es una speculative question. Todas en paralelo; el código filtra.

Anti-patrón: secuencial (categoría → después dominio/device → después acción). Más lento y más caro.

**TypeSafe + LLM pairing:**

- Si un Noul dice que el request pide más de una acción distinta, un LLM splittea en comandos atómicos; cada uno se evalúa con TypeSafe.
- Si TypeSafe determina que es conversación / información general, fallback a un LLM conversacional.

La respuesta TypeSafe es tan rápida vs el LLM que agrega latencia negligible, y permite manejar lo determinista barato y lo generativo solo cuando hace falta.
