# Confidence

Fuente: `https://docs.typesafe.ai/confidence`.

## Qué es

Todas las answers Score y Choice incluyen `probabilities` (distribución sobre opciones o niveles). La **forma** de esa distribución dice qué tan cierto está el modelo: concentrada en un outcome = confiado; spread = indeciso.

`confidence` colapsa esa forma a un número 0–1 para poder thresholdar sin hacer la matemática. **Noul no trae uno.**

## Se deriva de las probabilities

Es un estadístico computado de la distribución que la answer ya da. TypeSafe lo calcula y lo devuelve. El caller nunca está locked a esa definición: tiene el `probabilities` completo y puede usar otra medida. La docs deja la comparación de fórmulas para un cookbook futuro.

Choice: distribución sobre opciones. Score: sobre niveles. Más plana = menor confidence.

- Baja confidence en Choice: ninguna opción es un ganador claro sobre las otras.
- Baja confidence en Score: niveles ambiguos, multi-dimensionales, o el state no alcanza.

## “I don’t know” es una señal útil

Cita oficial:

> If an intelligent system, whether human or machine, cannot express honest uncertainty, the system cannot be trusted.

Confidence es el mecanismo built-in para que el modelo diga “no estoy seguro”. Eso permite comportamiento distinto según certeza, base de sistemas en los que se puede confiar.

## Tres paths oficiales

**High:** actuar automático.

**Medium:** proceder con cautela. Confirmar con el usuario, flaggear, o juntar más información.

**Low:** no actuar. Humano, clarificación, u otro sistema. El modelo dice que no tiene suficiente información o que la question no es un buen fit.

Dónde se dibujan los bordes depende de las stakes.

## Los umbrales escalan con el riesgo

Un threshold de confidence **no es un número**. Distintas acciones del mismo sistema se gaten a distintos niveles según las consecuencias de equivocarse.

Ejemplo oficial (banca por voz):

```python
if confidence < 0.5:
    route_to_human(user_message)
elif action.choice == "check_balance":
    show_balance(account_id)          # low stakes, recoverable
elif action.choice == "approve_transfer":
    if confidence > 0.9:
        confirm_then_execute(...)
    else:
        ask_user_to_confirm(...)
```

El piso 0.5 atrapa lo genuinamente indeciso. Arriba, el umbral para actuar sin confirmación es más alto para una operación destructiva que para una read-only. El código encodea la tolerancia al riesgo.

Nota oficial:

> The correct threshold values depend on your domain and the performance of the model for your use case. Start with conservative thresholds, test with your own data, and adjust as you observe results.

El agent skill agrega una advertencia operativa: no poner confidence thresholds en todos lados. Si solo importa elegir la mejor opción, basta con la de mayor probabilidad/confidence. Si hay un algoritmo estadístico en mente, usar `probabilities` en vez de `confidence`.
