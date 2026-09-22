# State

Fuente: `https://docs.typesafe.ai/concepts/state`.

## Definición

**State** es el contenido que se le pide evaluar a un modelo System One. Puede ser un mensaje de soporte, un pasaje, o el estado actual de la aplicación. Viaja en el campo `state` del request, junto a las questions.

Cada request evalúa **un** state contra una o más questions. Todas ven el mismo state y se evalúan independientes. Se pueden mezclar Choice, Score y Noul.

## Tres formas

| Formato | Útil para | Ejemplo de la docs |
|---|---|---|
| String | Un mensaje, artículo o pasaje | `"My card was charged twice."` |
| Object | Campos con nombre, records relacionados, application state | `{"message": "My card was charged twice.", "order_id": "A-104"}` |
| Array | Secuencia de mensajes o records | `["Hi", "My customer number is TS1337.", "My card was charged twice."]` |

Recomendación oficial: **usar un objeto en la mayoría de los requests**, para que cada parte tenga nombre y las relaciones queden claras. String solo cuando el caso es simple y hay una sola pieza de texto.

Jev acepta solo texto. State debe ser string, objeto JSON o array de valores de texto. Sin imagen, audio ni video.

## Analogía oficial

Pensar el state como el material que se le presentaría a un panel de expertos antes de pedirles un juicio.

## Separar contenido de questions

El state contiene el contenido y los hechos de apoyo. Las questions definen los juicios. Ejemplo: el pedido de reembolso y la policy van en el state; “¿el cliente pidió reembolso?” y “¿la policy lo cubre?” son questions.

## Ejemplo oficial: conversación de soporte como un solo state

```json
{
  "ticket": {
    "subject": "Duplicate charge",
    "messages": [
      {"from": "customer", "text": "I was charged twice for order A-104. Please refund the duplicate."},
      {"from": "support", "text": "We are checking the charges."}
    ]
  },
  "order": {
    "id": "A-104",
    "charges": [
      {"amount_usd": 49, "status": "captured"},
      {"amount_usd": 49, "status": "captured"}
    ]
  },
  "refund_policy": "Duplicate charges are eligible for a refund."
}
```

Es **un** state, aunque tenga conversación, orden y policy. Juntar información relacionada cuando la decisión exige comparar esas partes.

## Referenciar campos (docs de primitivas)

Cuando el state es un objeto, las instructions pueden apuntar a una parte con un path con puntos e índices, **incluyendo backticks**:

```text
Does `ticket.messages[0].text` request a refund?
Does `refund_policy` support the refund requested in `ticket.messages[0].text`, given `order.charges`?
```

Los paths explícitos dejan claro qué partes del state informan cada juicio.
