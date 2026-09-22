# Estructura avanzada en instructions y criteria

Fuente: `https://docs.typesafe.ai/primitives/advanced`.

## Qué acepta estructura

System One está entrenado para entender estructura. Estos campos son `EntryType` (string, object, array o null):

| Campo | Aplica a |
|---|---|
| `instructions` | Choice, Score, Noul |
| values de `criteria` (descripciones de opción) | Choice |
| entries de `criteria` (descripciones de nivel) | Score |
| `criteria.true` y `criteria.false` | Noul |

## Cuándo estructurar

- Cuando ayuda a la claridad: una question con varias partes, keys etiquetadas.
- Cuando la question necesita supporting data: un schema, una taxonomía o una row de DB ya es JSON. Pasarlo entero o los subfields relevantes, no serializarlo a un string template.

Una question corta e inequívoca puede seguir siendo string.

## Instructions estructuradas

Un objeto `field` describe el campo que se chequea; cada question lo referencia por key. La misma shape puede manejar un Noul que verifica un valor, un Choice que elige entre candidatos, y Scores que colocan un valor en una escala.

Ejemplo oficial (invoice):

```json
"instructions": {
  "field": {
    "name": "invoice_number",
    "type": "string",
    "description": "The identifier printed on the invoice."
  },
  "extracted_value": "4471",
  "question": "Does `extracted_value` match the `field` as it appears in `source_text`?"
}
```

Arrays también. Usar uno cuando la instruction es una lista de cosas a chequear o comparar:

```json
"instructions": {
  "question": "Does the claimed sender identity conflict with the sending domain?",
  "compare": ["ticket.sender.display_name", "ticket.sender.email"],
  "focus": "Compare the named organization with the email domain."
}
```

En código se puede loopear records y armar una question por field, todas en un call. El cookbook SDE cascade hace algo similar.

## Choice options estructuradas

### Rúbrica JSON para clarificar bordes

Cada opción con los **mismos field names** para que el modelo compare like-with-like:

```json
"billing": {
  "what": "Charges, invoices, refunds, or subscriptions",
  "not_for": "Order tracking or account access",
  "examples": ["I was charged twice", "Where is my refund?"]
}
```

### Caminar una taxonomía

Un Choice por nivel. En cada paso las opciones son los children del nodo actual, y el value de cada opción es el subtree del child. El modelo ve qué vive bajo un branch antes de comprometerse. Importa cuando el ítem pertenece a una leaf cuyo nombre no es obvio desde el branch.

Ejemplo oficial: botella 32oz con flip straw que “fits most bike cages”. El subtree muestra tanto `Sporting Goods > Cycling > Bike Bottles` como `Home & Kitchen > Drinkware > Water Bottles`. Las `probabilities` dicen si el split está lo bastante cerca como para explorar ambas ramas.

Después, Choice con los children del departamento elegido, repetir hasta una leaf. En código: loop sobre un dict anidado. Cookbook Hierarchical Classification agrega beam search cuando las probabilities están cerca.

Si un branch es demasiado grande: trim al direct children más una sample de leaves.

## Score levels estructurados

Cada entry del array puede ser objeto. Mismos field names en todos los niveles.

Ejemplo oficial (foco de un PR):

```json
{
  "summary": "Several independent changes bundled together",
  "signals": [
    "Two or more unrelated fixes or features",
    "Changes that could each be their own PR"
  ]
}
```

La instruction puede aclarar qué **no** se está midiendo: “Judge the number of independent changes, not the size of any one change.”

## Noul criteria estructurados

Cuando el borde sí/no es sutil, `true`/`false` como objetos con `what` + `examples`.

Ejemplo oficial (¿pide credencial?):

- true.what: “Asks the recipient to reply with, type, or send a password, PIN, one-time code…”
- false.what: “No sensitive credential is requested”
- false examples incluyen “Reset your password from the settings page” — un reset **no** cuenta como pedir la credencial.
