# Jaggedness de Jev 1.13

Fuente: `https://docs.typesafe.ai/model-jaggedness/jev-1.13`. Aplica a `jev-1.13`. Last reviewed **2026-09-16**.

Jev es rápido, calibrado y bueno en juicio de sentido común. No es perfecto. Rinde mejor en tareas System One. Puede fallar con indirección extra. Es bastante literal. Lucha con precisión numérica.

## Tabla de failure modes

| # | Failure mode | Hacer esto en vez |
|---|---|---|
| 1 | Lectura literal | Escribir la condición exacta; criteria por opción |
| 2 | Math y números | Aritmética en código |
| 3 | Comparación de fechas | Extraer componentes; comparar en código |
| 4 | Indirección | Reducir hops; apuntar al state relevante |
| 5 | State grande lleno de detalle irrelevante | Filtrar primero; mandar solo lo que la question necesita |
| 6 | Contenido adversarial | Prompts precisos; testear edge cases antes de deploy |
| 7 | Instructions y criteria contradictorios | Alinearlos |
| 8 | Generación | Usar un modelo generativo |

## 1. Lectura literal

Jev responde la question **escrita**, no la que se “quería decir”. Palabras de scoping, negaciones y condiciones implícitas se leen at face value.

En vez: estado exacto en `instructions`. Casos borde en criteria. Si al mirar una answer incorrecta uno se oye explicando “lo que realmente significaba”, esa explicación es la mitad que faltaba de la instruction. Donde la interpretación es inevitable: dos questions literales y combinar en código.

## 2. Math y números

Jev no es calculadora. Lógica matemática en código. Rinde mejor en questions semánticas que matemáticas.

### Counting

No cuenta de forma fiable: caracteres de una palabra, ocurrencias de un término, ítems de una lista larga. Reconoce la *forma* de una answer en vez de tallying; el error crece con el tamaño.

Si una regex o un parser encuentra la unidad, el count es de código y el modelo no aporta.

Patrón oficial para “contar los que matchean un criterio”: iterar candidatos en código, **una question por ítem**, sumar answers.

```python
YES = 0.5  # el caller elige el umbral
result = client.system_one(
    {"items": items},
    {f"item_{i}": Noul(instructions=f"Is `items[{i}]` the name of a fruit?")
     for i in range(len(items))},
)
count = sum(result.nouls[f"item_{i}"].noul > YES for i in range(len(items)))
```

### Representaciones numéricas

Mejor en representaciones semánticas que numéricas. Colores por nombre en inglés > hex/RGB. Lenguajes de alto nivel > assembly o binario.

En vez: convertir en código y pasar el número computado o un bucket nombrado. Dejarle al modelo la parte que es juicio (¿este color se lee como warning?).

### Math usando Score

No usar outputs de Score (expectativas y probability) para computar la magnitud exacta de un número entre dos niveles. Se puede usar la expectativa para ver si pasa un threshold. Los niveles de Score de jev-1.13 son débiles en calibración numérica; no reconstruyen el número exacto interpolando.

## 3. Fechas y horas

Jev lee fechas como texto, no como cantidades ordenadas. ¿Cuál de dos fechas viene primero, cuán lejos están, si una cae en una ventana? Poco fiable. Empeora con formatos mixtos, referencias relativas y bordes de dominio (quarters, settlement windows, accrual).

En vez: split. **Extracción es juicio** → modelo. **Aritmética no** → código.

Cada parte de una fecha es un closed set (12 meses, 31 días, rango de años) → Choice sobre opciones enumeradas, con opción `"not stated"` para no adivinar. El código arma el date real y dueña ordering, duration, offset, weekday.

Cookbook: date extraction.

## 4. Indirección

Doble negación o indirección compleja: menos fiable. Una question sobre una propiedad de una propiedad, o varios hops, cuesta accuracy.

En vez: instructions lo más directas posible. Identificar partes del state por nombre.

## 5. State grande e irrelevante

La accuracy cae cuando el state crece con contenido no relacionado. El detalle unrelated es distractor, y un state grande hace más difícil saber qué parte produjo una answer incorrecta.

En vez: retrieve y filtrar en código primero. Si no se puede filtrar el state, un Noul de relevancia. Cookbook classifying RAG passages.

Límites de contexto: ver [modelos](15-modelos-precio-limites.md).

## 6. Contenido adversarial

State es data. jev-1.13 **no lo trata como hostil por default**. Contenido escrito para steer el modelo (instrucción inyectada, framing engañoso, texto que argumenta su propia clasificación) puede mover la answer. Esperan mejorar esto.

En vez: criteria explícitos. Testear la integración a fondo antes de muchos users.

## 7. Instructions vs criteria contradictorios

Si piden cosas distintas, jev-1.13 se puede confundir. Mejor performance: phrasing clara. Un Noul donde `true` mapea a no y `false` a yes rinde peor. Aim: instructions fáciles de leer para una persona promedio.

Criteria = extensión de la instruction. Alinear con lenguaje preciso.

## 8. Generación

Jev no está entrenado para generar texto. Forzarlo encadenando Choices no funciona bien y es muy lento. Para data extraction: extraer opciones posibles con regex o un modelo generativo y dejar que Jev **elija** la extracción correcta.

Si el answer space está bounded, convertir extracción en Choice sobre opciones, no pedir el valor mismo.

## Reminder oficial (evitar)

- Preguntarle algo que el código puede computar exacto.
- Esconder varios juicios en una question.
- Tareas System Two (más capas de indirección).
- Darle más contexto en `state` del que la question necesita. Jev sufre context rot; material unrelated en el state cuesta accuracy.

Canal de reporte: Discord `https://discord.com/invite/WUujKYBp8s`.
