# Cómo construir con TypeSafe

Fuente: `https://docs.typesafe.ai/concepts/how-to-build-with-system-one`.

## Summary oficial

Construir un workflow de software normal e insertar System One **solo donde hace falta AI**.

- Control flow, reglas deterministas y side effects en código.
- Juicios amplios → questions angostas, tipadas, con instructions y criteria explícitos.
- Cada question recibe solo el contexto que necesita.
- Probabilities y confidence para actuar, pedir review, o escalar.
- Questions independientes juntas; answers combinadas en código.

System One es el modelo de TypeSafe para construir **software con AI, no agentes**. No genera código ni elige su próximo action. Da primitivas que se embeben en software: el código sigue en control; el modelo maneja juicios de sentido común sobre datos no estructurados.

## Tres arquitecturas (tabs oficiales)

1. **Traditional software.** Árbol de decisión complejo hecho de primitivas de software simples. Como cada primitiva es fiable, se componen en abstracciones más altas.
2. **LLM agents.** El agente procesa instructions y elige el siguiente paso. Funciona bien con un humano mirando; cada loop es otra oportunidad de irse de las vías.
3. **AI-powered software.** El código hace el trabajo determinista y dueña el control flow. El modelo aparece solo donde el sistema necesita sentido común programable o interpretar datos no estructurados. Cada tarea de AI se mantiene atómica y acotada.

## Qué hace componible a System One (cards oficiales)

| Propiedad | Significado |
|---|---|
| Structured | Type-safe by construction. Decisiones y probabilities conforman a los tipos y JSON schema que el código espera. Nunca hay que recuperar un valor de prosa. |
| Parallel | Questions independientes y en paralelo. El resultado de una no se vuelve contexto oculto de otra. |
| Comparable | Outputs ordenables; pueden manejar `if`s, thresholds, comparaciones. |
| Fast | La mayoría de queries ~**100 ms**. Suficiente para request paths en tiempo real y UIs. |
| Calibrated confidence | RLCD comunica incertidumbre con probabilities calibradas en vez de tender a overconfidence. |
| Self-consistent | Diseñado para answers estables en evaluaciones repetidas. Ver cookbook self-consistency. |

Target declarado: ratio intelligence-to-speed-and-cost **> 100×**. La apuesta de fondo: inteligencia más barata crea mucha más demanda.

## Pasos de diseño (Steps oficiales)

### 1. Usar código cuando se puede

Trabajo determinista en código. Es fiable y barato. Evitar agent `while` loops cuando un workflow de software expresa el mismo comportamiento. Ejemplo: `days_overdue > 30` → collections, sin modelo.

### 2. Descomponer el input state

Incluir solo el contexto relevante a las questions actuales. Ayuda a evitar distracciones y context rot. No apoyarse en knowledge de los weights del modelo cuando la información actual puede venir de la propia knowledge base.

### 3. Usar estructura en el state

JSON anidado. Apuntar questions a values específicos con paths con backticks (`support.tickets[0].message`).

### 4. Descomponer las questions (el concepto más importante del guide)

Cita:

> This is probably the most important concept in this guide. Broad questions hide several judgments behind one answer. Atomic questions expose those judgments so you can inspect, tune, and combine them in code.

Ejemplo spam: no `is_spam`. Sí: `requests_credentials`, `offers_unexpected_reward`, `creates_time_pressure`, `sender_identity_mismatch`, `link_domain_mismatch`, `disguises_link_destination`.

Ejemplo tool-call trace: no `tool_calls_are_correct`. Sí: tool relevante, arguments match schema, coordinates match geocode result, date match, unit match — un Noul por hecho.

### 5. Estructura en las questions

Questions atómicas cortas. Cuando instructions o criteria necesitan varios tipos de guidance, objects/arrays con fields nombrados, no un prosa densa. Para Choice: qué pertenece a cada opción, qué pertenece a la vecina, ejemplos representativos. Mismos field names across options.

### 6. Preguntar muchas questions

Muchas, angostas, independientes, mismo state, un request. Así se maximiza efectividad e intelligence per dollar: paralelo, sin round trips seriales.

### 7. Combinar outputs en código (o en un modelo ML clásico)

Reglas deterministas o weighted sums. Para composición aprendida: las probabilities como features de un modelo clásico aguas abajo. Si no hay labels, un ensemble de reasoning models caros las genera (cookbook AutoResearch + CatBoost).

### 8. Ruteear en incertidumbre

Código distinto para answers confiadas y no confiadas. Escalar a persona o a un reasoning model más caro. Testear thresholds ploteando confidence vs accuracy en datos propios.

Tip: la descomposición **no exige más round trips**. Questions sobre el mismo state corren en paralelo.

## Ejemplo de cierre: triage_ticket.py

El walkthrough largo de la docs (reproducido acá en espíritu, no copiado entero):

- Si `ticket.status == closed` → no_action, **sin modelo**.
- State filtrado: message, sender, links, plan, open_orders, policy.sensitive_credentials. No el customer entero.
- Questions atómicas estructuradas: topic (Choice con what/not_for/examples), varios Noul de spam (credentials, sender mismatch, unexpected reward), refund_requested, mentions_open_order, frustration (Score).
- spam_risk = 0.45·credentials + 0.30·mismatch + 0.25·reward (pesos en código).
- Si spam_risk ∈ (0.4, 0.6) o topic.confidence < 0.75 → humano.
- Si spam_risk ≥ 0.6 → quarantine.
- Recién ahí se usan las answers especulativas del path (refund solo si billing; open_order solo si orders).
- Priority high si frustration.confidence ≥ 0.7 **y** score ≥ 1.5.
