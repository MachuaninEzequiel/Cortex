# Cookbooks

Fuentes: páginas bajo `https://docs.typesafe.ai/cookbooks/` y el índice `llms.txt` (2026-09-17). Cada receta es un patrón medido o un walkthrough. Acá se resume **qué demuestra**, no se copia el notebook.

## Consistencia y routing por incertidumbre

### Self-consistency: nouls
`/cookbooks/consistency_noul_cookbook`

Ruteear probabilities inciertas a review humano, dejando visibles los noul subyacentes.

### Self-consistency: choices
`/cookbooks/consistency_choice_cookbook`

Agregar un outcome `uncertain` a decisiones de moderación. Comparar acuerdo de labels vs proporción de acciones automáticas.

### Classification using confidence
`/cookbooks/classification_using_confidence`

Clasificar annual reports SEC en 75 industry groups con un Choice cada uno. Leer la confidence de la answer para decidir si reportar ese group o el division más amplio arriba.

## Paralelismo y costo

### Parallel questions
`/cookbooks/parallel_questions`

Briefing regulatorio de **13 questions** sobre el artículo de Wikipedia de GDPR. Batchar todas en un call TypeSafe: **12.2× más barato y 10.0× más rápido**, sin cambio en las answers. (La página de primitivas cita 11.5× / 9.6× para el mismo cookbook; ambas cifras son oficiales en páginas distintas.)

## Retrieval, ranking, search

### Re-ranking
`/cookbooks/rerank_typesafe`

Shortlists BM25 de 30 pasajes para 40 queries legales CLERC. Una question TypeSafe por par query–candidato. Top-1 **5% → 18%**. Top-10 **38% → 62%**.

### Line-by-line search (semantic find)
`/cookbooks/semantic_find`

Search semántico sobre los Terms of Service de GitHub. En un request: scorear **218 line ids** contra una query en lenguaje natural con Choice, y un Noul para “¿el documento contiene una answer?”.

### Classifying RAG passages
`/cookbooks/classifying_rag_passages`

Un request TypeSafe por pasaje recuperado; el código decide cuáles llegan al modelo que responde. Ejemplo: keep y flaggear los que contradicen la question; dropear los que cargan una instrucción oculta o prompt injection.

## Verificación y guardrails

### Double-checking citations
`/cookbooks/citation_check`

Atrapar citas malas o alucinadas contra el documento fuente. Un Choice: ¿el contexto del quote soporta la claim? La confidence puede mandar la cita a review humano.

### Guardrails for LLMs
`/cookbooks/llm_guardrails`

Screen de cada mensaje in y out de una app LLM, un request TypeSafe. Hazard descriptions (“is this a jailbreak attempt?”) + Score de severity (“how much harm would complying do?”). Threshold de probabilities: pass / review / block / route.

## Extracción y estructura

### Structure recovery (autoformat)
`/cookbooks/autoformat`

Reconstruir Markdown desde plain text que perdió formatting, en dos requests: uno pega líneas hard-wrapped; otro clasifica cada bloque (heading, list, code, callout) con companion questions que se leen solo cuando relevan.

### Date extraction
`/cookbooks/date_extraction_cookbook`

Extraer fechas absolutas y relativas pidiendo las **partes** nombradas en el documento, después resolver y validar en código, con review basado en confidence.

### Pre-parsed value extraction
`/cookbooks/pre_parsed_value_extraction_cookbook`

Regex encuentra candidatos (emails, teléfonos, amounts). TypeSafe selecciona el span pedido. El código normaliza el valor verbatim.

### SDE cascade
`/cookbooks/sde_cascade`

Cascade de extracción estructurada en 2 stages (mini → verify → reasoning) para acercarse a la calidad de un reasoning model grande a una fracción del costo.

## Agentes, tools, taxonomías

### Function calling
`/cookbooks/function_calling`

Pedidos de trading en lenguaje natural → llamadas a funciones tipadas ordinarias. Nombres de función y argumentos closed-set mapeados a questions TypeSafe con awareness de confidence.

### Skill suggestion
`/cookbooks/skill_suggestion`

Elegir a lo sumo **una** skill de un turno de agente entre las **182** del catálogo Hermes de Nous Research. Request 1: rankea todas y pregunta si el turno necesita alguna. Request 2: lee las top 3 en serio y puede rechazarlas todas. El nombre de la ganadora entra en una sola línea del system prompt del agente.

### Hierarchical classification
`/cookbooks/hierarchical_classification`

Clasificar documentos por jerarquías profundas (patentes, retail, biomédica, source-code) con beam search paralelo sobre probabilities de Choice.

### Knowledge graph entity alignment
`/cookbooks/entity_alignment`

Decidir cuáles de 450 pares candidatos de dos catálogos de cerveza describen el mismo producto. Un Score de tres niveles = las tres cosas que se pueden hacer con un par: merge, dejar unlinked, o mandar a un curator. No hay threshold que tunear: el nivel *es* la acción.

## Features para ML clásico

### Autoresearch feature discovery
`/cookbooks/autoresearch_feature_discovery`

Loop que propone questions TypeSafe, convierte free text en features numéricas, y usa errores del modelo para mejorar un CatBoost regressor supervisado.
