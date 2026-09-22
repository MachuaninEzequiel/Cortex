# Patrones arquitectónicos

Fuente: `https://docs.typesafe.ai/patterns` y las cuatro páginas hijas.

Asume primitivas y confidence. TypeSafe se sienta **dentro** de un sistema más grande. El skill clave: pensar en decisiones atómicas que componen comportamiento complejo.

## Tabla oficial

| Patrón | Qué hace | Beneficios |
|---|---|---|
| Speculative Fan-Out | Muchas questions en un call, incluidas especulativas; el código decide cuáles importan | Cost, Speed |
| Confidence-Gated Routing | Confidence como segundo eje | Reliability, Safety |
| Composite Scoring | Varias dimensiones → un score | Cost, Reliability, Speed |
| Intent Routing | Clasificar intent y ruteear al handler óptimo | Cost, Speed |

---

## Speculative fan-out

Fuente: `/patterns/fan-out`.

Ejemplo: triage de tickets. Hace falta categoría. Si es bug, también severidad. En vez de categoría primero y severidad después, **las dos a la vez**. Si no es bug, se ignora severidad.

Questions del ejemplo: `category` (Choice), `bug_severity` (Score, especulativa), `has_reproducible_steps` (Noul, especulativa), `refund_requested` (Noul, especulativa), `frustration` (Score, útil en todas las categorías).

El código ramifica:

```text
si bug_report y severity > 1.5 y repro > 0.6 → escalate engineering
si billing y refund > 0.7 → billing con flag
si feature_request → log
si frustration > 1.5 → priority (independiente de categoría)
```

Todo el árbol de decisión sale de **un** call. Las especulativas son irrelevantes a veces y ahorran un round trip cuando no lo son.

Demo smart-home: la misma idea a escala (categoría, dominio, device, action — la mayoría irrelevante para un request concreto).

El anti-patrón explícito: calls secuenciales “pregunto A, espero, pregunto B”. Optimiza cantidad de questions y sale **más lento y más caro**.

---

## Confidence-gated routing

Fuente: `/patterns/confidence-routing`.

La answer dice **qué**. Confidence dice **si actuar**.

Ejemplo: voice banking. Choice `check_balance | approve_transfer | other`.

```text
confidence < 0.6            → humano (cualquier acción)
check_balance               → mostrar saldo (0.6 alcanza)
approve_transfer y > 0.85   → ejecutar
approve_transfer y 0.6–0.85 → confirmar con el usuario
other                       → humano
```

Piso 0.6 = genuinamente indeciso. Arriba, cada acción tiene su umbral por consecuencias. Leer el saldo mal es recoverable. Aprobar un transfer no.

---

## Composite scoring

Fuente: `/patterns/composite-scoring`.

Romper un juicio complejo en Scores atómicos; combinar con pesos que controla el código.

Ejemplo: screening de resumes. Cuatro Scores 0–4: python_depth, team_leadership, system_design, generalist. Normalizar `/4`. Dos fórmulas:

```text
IC senior:  0.40 py + 0.10 lead + 0.40 arch + 0.10 general
EM:         0.15 py + 0.40 lead + 0.20 arch + 0.25 general
```

Se puede rankear. Más importante: se ve **cómo** se calcula el número. Si los top no matchean expectativas, se ajustan pesos sin perder el detalle de cada dimensión.

---

## Intent routing

Fuente: `/patterns/intent-routing`.

Clasificar requests y ruteear cada uno al handler óptimo: lógica determinista, LLM especialista, o humano. No mandar todo por un LLM caro.

Ejemplo customer service:

- Choice intent: order_status, product_question, return_exchange, complaint.
- Score complexity: lookup simple / juicio multi-step / edge case.

Routing:

```text
intent.confidence < 0.5     → humano
order_status                → código determinista (lookup)
product_question            → LLM PRODUCT_SPECIALIST
return_exchange             → LLM RETURNS_SPECIALIST
complaint + complexity > 1 o complexity.confidence < 0.5 → humano
complaint resto             → LLM COMPLAINT_RESOLUTION
```

Un intent no usa LLM. Dos usan LLMs distintos con distinto contexto. Uno usa el Score para elegir LLM vs humano. TypeSafe clasifica en un call rápido; los recursos caros solo para lo que los necesita.
