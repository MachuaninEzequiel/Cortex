# Primitivas (Questions)

Fuente: `https://docs.typesafe.ai/primitives`.

## Qué son

Las primitivas de TypeSafe son bloques chicos y tipados que se componen en código. Vienen en pares: una **question** define un juicio sobre un state; su **answer** es el valor tipado que vuelve. Hay tres tipos.

| Tipo | Qué responde | Devuelve |
|---|---|---|
| Choice | ¿Cuál de estas opciones? | `choice`, `probabilities`, `confidence` |
| Score | ¿Cuál nivel? | `score`, `legend`, `probabilities`, `confidence` |
| Noul | ¿Es esto cierto? | `noul` (0 a 1) |

Se puede preguntar una o varias juntas. Cada question del request ve el mismo state, se evalúa independiente, y vuelve bajo el ID que eligió el caller.

## Un snap judgment por pregunta

System One está hecho para juicios rápidos y enfocados. “Does this message convey urgency?” es una buena pregunta. “Analyze this message and determine the best course of action” no lo es: necesita razonamiento lento; hay que romperla.

Si el juicio depende de varios factores independientes, un factor por pregunta y lógica propia. En vez de “rate this startup pitch”: market size, technical feasibility, differentiation, y pesos en código.

## Anatomía de una question

Toda question tiene ID, `type` e `instructions`. Choice y Score también toman `criteria`. Noul acepta `criteria` opcional.

- **ID.** La key que elige el caller (`refund_requested`). Identifica la answer. **No se manda al modelo.** Tip oficial: escribir la pregunta completa en `instructions` aunque el ID parezca autoexplicativo.
- **`type`.** `choice` | `score` | `noul`.
- **`instructions`.** La pregunta o el statement a juzgar. Acá va la lógica de evaluación.
- **`criteria`.** Las posibles answers: mapa de opciones (Choice), lista ordenada de niveles (Score), descripción opcional de yes/no (Noul).

## Cómo elegir el tipo

- **Choice** cuando la answer es una de un conjunto conocido **sin orden** entre opciones: ruteo a departamento, tipo de documento, lenguaje. Lista completa. Agregar `other` / `none of the above` si la lista puede no cubrir todo input.
- **Score** cuando la answer cae en un espectro y se puede describir cada punto: severidad de bug, frustración, skill level. Los niveles los define el caller; el modelo devuelve una posición a lo largo de ellos.
- **Noul** para un sí/no limpio donde la probabilidad misma es la señal: ¿reporta un bug?, ¿pide reembolso?, ¿el resume menciona distributed systems?

Nota oficial crítica:

> Use Noul for a yes/no judgment and Score to measure a position on a spectrum. "Is this candidate strong in Python?" needs a clear definition of "strong". A Noul value of 0.5 means the model gives yes and no equal probability. It does not mean the candidate has a medium skill level.

Si se quiere medir skill: Score con niveles (no experience / some familiarity / daily use / deep expertise). Si se necesita sí/no: definir la condición (“Does the resume state that the candidate has used Python at work?”).

Si dos tipos parecen caber, preferir el cuya answer el código puede actuar directo. Choice `refund|rebook|information` mapea a tres paths. Score de frustración mapea a un umbral. Noul mapea a un `if`.

## Qué vuelve (y por qué es componible)

| Tipo | Campos | Cómo leerlo |
|---|---|---|
| Choice | `choice`, `probabilities`, `confidence` | `choice` = opción seleccionada. `probabilities` = distribución. `confidence` resume qué tan picuda está. |
| Score | `score`, `legend`, `probabilities`, `confidence` | `score` es posición a lo largo de los niveles y puede caer entre dos. `legend` repite niveles por número. |
| Noul | `noul` | P(sí). Cerca de 1 = sí fuerte, cerca de 0 = no fuerte, cerca de 0.5 = indeciso. **Noul no tiene `confidence` aparte.** |

Dos propiedades que hacen componible el output:

1. **Toda answer está acotada a las opciones que se suministraron.** Distribución sobre esas opciones/niveles, nunca un valor fuera. El código nunca recupera un valor de prosa.
2. **Toda answer es independiente.** Una no es contexto oculto de otra. Se pueden agregar o quitar questions sin cambiar las demás.

## Varias questions juntas

Mandar **todas** las que usan el mismo state en un request. Mezclar tipos. Evaluadas en paralelo. Añadir questions casi no cambia latencia y solo cuesta los tokens de las questions extra, que son baratos. Preguntar algo que quizás no se necesite es casi gratis.

Esto es el patrón [Speculative fan-out](12-patrones.md). El cookbook Parallel questions: batchar 13 questions en una call es **12.2× más barato y 10.0× más rápido** (llms.txt; la página de primitivas cita 11.5× / 9.6× — se dejan ambas cifras porque las dos están en docs oficiales de distintas páginas).

El número de questions de un request solo está limitado por el presupuesto de tokens que state y questions **comparten**.

Presupuesto (tensión entre páginas, se citan ambas):

- `/primitives`: “around 32,000 tokens, roughly 150,000 characters of English text”.
- `/model-jaggedness/jev-1.13`: 64k tokens juntos para todo `state` + `questions`; 32k para el `state` + la `question` más larga.

La forma eficiente de usar el contexto es empacar muchas questions por query.

## Segunda request: la excepción

Questions del mismo request son independientes: una answer no se vuelve contexto de otra. Si un juicio posterior **depende** de una answer anterior, segunda request en código. La dependencia es real solo cuando el código no puede armar el segundo request hasta tener la primera answer: necesita la answer para fetch más datos, decidir de qué está hecho el state, o elegir las opciones de la siguiente question. Si no, preguntar junto y combinar en código.

Dos requests son la excepción. Tres cookbooks lo hacen por una razón real:

- **Skill suggestion:** rankea 182 skills, después fetch del texto de las top 3 y juzga otra vez.
- **Structure recovery (autoformat):** pregunta si cada line break partió una oración, mergea, después clasifica bloques que no existían.
- **Hierarchical classification:** cada Choice decide qué opciones ofrece el siguiente request.

## Tip sobre coding agents

La docs advierte que los coding agents caen en el hábito de una question por call más que las personas. El [agent skill](19-agent-skill.md) les dice que pongan muchas questions por call, incluidas las que solo importan para algunos inputs.
