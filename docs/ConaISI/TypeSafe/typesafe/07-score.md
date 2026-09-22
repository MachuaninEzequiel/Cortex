# Score

Fuente: `https://docs.typesafe.ai/primitives/score`.

## Cuándo usarlo

Cuando la answer es una posición en un espectro que se puede describir en pasos. Ejemplos: severidad de bug, formalidad de un outfit, relevancia de experiencia a un job posting. Sin orden entre opciones → Choice. Sí/no → Noul.

## Request

- `type`: `"score"`
- `instructions`: qué está rating
- `criteria`: array **ordenado** de descripciones de nivel, del extremo bajo al alto. Mínimo 2, máximo **10**

El ID no se manda al modelo.

## Niveles

Cada entry de `criteria` es un nivel: un punto del espectro, descrito en palabras. El número de un nivel es su posición en el array, **desde 0**. El modelo recibe las descripciones y nada más. Cada nivel se juzga **por su cuenta** contra el state.

El modelo **no ve el número del nivel ni a sus vecinos**. “Peor que el nivel anterior” no significa nada. Poner números en las descriptions o en las instructions no ayuda.

Contraejemplo oficial (reporte de botón desalineado):

```
instructions: "Rate severity from 0 to 2, where 2 is worst"
criteria: ["0", "1", "2"]
→ score 0.57, confidence 0.35, probabilities 0: 0.43, 1: 0.57, 2: 0.0
```

Los mismos tres niveles **descriptivos** dan score 0.0 con confidence 1.0.

Reglas de escritura:

- Describir **situaciones**, no grados. “Broken or degraded feature, but workaround exists” le da algo contra qué matchear. “Moderately severe” no.
- Tantas niveles como se puedan describir de forma distinta, hasta 10. Tres está bien. No agregar niveles que no se puedan distinguir.
- Un Score = **una dimensión**. Si una descripción dice “punctual and smart and experienced”, está midiendo tres cosas y un input alto en una y bajo en otra no se puede colocar. Confidence cae. Split en un Score por cosa.
- Si el extremo alto tiene un caso raro que hay que tratar distinto, darle su propio nivel. Una escala de sentimiento que termina en “very angry” puede agregar “abusive or threatening”. Sin ese nivel, ambos mensajes pueden recibir score cerca del tope.
- Testear los niveles contra datos propios. Dos wordings de la misma escala se comportan distinto.

## Response

- `type`
- `probabilities`: probabilidad de cada nivel, key = número de nivel como string. Suman 1
- `score`: posición en la recta de niveles, de 0 al número del nivel tope. Es **media ponderada**: `Σ (nivel × probabilidad)`. Ejemplo oficial: 0×0.0 + 1×0.70 + 2×0.30 = **1.30**
- `legend`: número → descripción
- `confidence`: 0–1 según spread

El SDK Python clavea `probabilities` y `legend` por entero, no por string.

## Cómo leer un Score (tabla oficial de severidad)

Misma pregunta, distintos states:

| State | score | confidence | P0 | P1 | P2 |
|---|---|---|---|---|---|
| Botón desalineado unos píxeles | 0.0 | 1.0 | 1.0 | 0 | 0 |
| PDF export no hace nada; CSV sigue | 1.0 | 1.0 | 0 | 1.0 | 0 |
| Spinner infinito; CSV a veces anda | 1.12 | 0.81 | 0 | 0.88 | 0.12 |
| Crash en Safari; Chrome OK | 1.3 | 0.54 | 0 | 0.7 | 0.3 |
| Nadie puede loguearse, 500 | 2.0 | 1.0 | 0 | 0 | 1.0 |

Confidence 1.0 significa que toda la probabilidad está en un nivel. Describe la answer del modelo, **no garantiza que sea correcta**.

Un score fraccionario es una **posición**. Sirve para rankear, o redondear al nivel más cercano cuando el código necesita un outcome (cookbook entity alignment).

**Distintas distribuciones pueden producir el mismo score.** Un 1.0 puede ser 100% en nivel 1, o 50/50 entre 0 y 2. Hay que leer `probabilities` y `confidence` junto al score.

Baja confidence en Score suele significar una de tres cosas: los niveles se solapan para este state, la question mide más de una cosa, o el state no dice suficiente.

## Composite scoring (oficial)

Un juicio complejo → un Score por dimensión → normalizar (`score / (len(criteria)-1)`) → pesos en código.

Ejemplo triage: severity 0.6 + frustration 0.3 + report_quality 0.1. Los pesos son del caller. Si el ranking no matchea lo que el equipo decidiría, se cambian en código y se corre de nuevo. Las questions van en **un** request.

No usar el score para reconstruir la magnitud exacta de un número interpolando entre niveles. Jaggedness: la calibración numérica de los niveles de Score en jev-1.13 es débil para eso. Sí se puede thresholdar.
