# Entrenamiento: RLCD y “Machine Native Intelligence”

Fuente: `https://docs.typesafe.ai/introduction/machine-learning-primer`.

## La apuesta

La mayoría de productos de AI se construyen alrededor de una conversación modelo–persona. TypeSafe parte de otra: la automatización a gran escala estará dominada por interacciones AI-a-AI y AI-a-software, así que **la interfaz de máquina importa más que la de chat**.

Cita oficial:

> **We call this Machine Native Intelligence:**
> AI with software-like properties such as structure, reliability, observability, testability, speed, consistency, and low cost.

## “Building prod, not God”

TypeSafe no intenta un modelo que haga todo. Está diseñado para sistemas de producción donde el código necesita una decisión estrecha que pueda inspeccionar y actuar.

Expectativa declarada: la automatización a gran escala será ~99% machine-to-machine y ~1% interacción humana. Eso mueve el target de “respuestas que se sienten bien de leer” a “outputs que se comportan predecible dentro de software”.

Manifiesto citado por la docs: `https://typesafe.ai/manifesto`.

## Tres caminos de post-training

Los modelos preentrenados se adaptaron de dos maneras mayores. TypeSafe agrega una tercera.

| Camino | Qué optimiza | Resultado típico |
|---|---|---|
| **RLHF** | Preferencia humana sobre texto | Chatbots (InstructGPT, ChatGPT). RLHF fue co-inventado por Diogo Almeida, cofundador de TypeSafe. |
| **RLVR** | Rewards verificables | Reasoning models fuertes en math, más lentos y caros. |
| **RLCD** | Decisiones calibradas | TypeSafe: decisiones + probabilidades, no texto generado. |

RLCD = **Reinforcement learning for calibrated decisions**.

## Contrato de output de RLCD

- El modelo no genera texto.
- Devuelve decisiones y probabilidades.
- Mayor probabilidad debe corresponder a mayor chance de que la answer sea correcta.

Calibración usable por software. En grupos de predicciones de un modelo bien calibrado:

- Outcomes con probabilidad `0.2` deberían ocurrir ~20% de las veces.
- `0.8` → ~80%.
- `1.0` → 100%.

Esas tasas describen **grupos**, no una predicción suelta.

## Problemas que TypeSafe atribuye a RLHF

RLHF enseña a decir lo que la gente prefiere. Sirve para chatbots, pero puede premiar sicofancia y alucinaciones que suenan seguras.

También causa **mode dropping**: el modelo favorece un estilo (p. ej. instruction following) y reduce la probabilidad de otros outputs. Es una versión más suave de **mode collapse** (el fallo clásico de GANs: el generador produce siempre el mismo tipo de output porque sigue engañando al discriminador).

Warning oficial:

> An output can be compelling to a person without being reliable enough for unattended automation. Human preference and machine trustworthiness are different optimization targets.

RLHF sigue siendo un buen fit para modelos conversacionales. La posición de TypeSafe es que la automatización de producción necesita otro objetivo: decisiones acotadas e incertidumbre calibrada.
