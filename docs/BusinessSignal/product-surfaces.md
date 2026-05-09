# BusinessSignal Product Surfaces

## Principio De Producto

BusinessSignal no debe saturar al usuario. Su valor esta en aparecer cuando hay evidencia suficiente y hacerlo con una recomendacion breve, accionable y navegable.

No debe convertir cada enrichment en una alerta.

## CLI

### `cortex signals`

Lista senales activas del proyecto.

```text
cortex signals
```

Salida humana:

```text
Business Signals for project: client-mobile-redesign

1. Historical Project Analogy [high]
   Similar to: client-portal-v1
   Score: 0.78
   Evidence: 14/20 recent work items
   Action: Review ADR-004 and incident-2025-09-auth-refresh
```

### `cortex signals --json`

Salida estable para CI, dashboards o agentes.

### `cortex signals explain <signal-id>`

Muestra evidencia detallada.

```text
cortex signals explain sig_123
```

Debe mostrar:

- Metricas.
- Documentos relacionados.
- Hits agrupados.
- Como se calculo el score.
- Acciones recomendadas.

### `cortex signals report`

Genera un reporte en Markdown.

Opciones futuras:

```text
cortex signals report --window 30d
cortex signals report --project current
cortex signals report --include-archived
```

## MCP Tools

### `cortex_business_signals`

Devuelve senales activas y compactas para el agente.

Uso:

- Al iniciar una tarea compleja.
- Antes de planificar una feature.
- Antes de cerrar una fase.

### `cortex_explain_business_signal`

Devuelve evidencia especifica para una senal.

### `cortex_record_signal_feedback`

Permite registrar si una senal fue util.

Ejemplo:

```text
feedback: useful | not_useful | false_positive | acted_on | ignored
```

## Autopilot

Autopilot no deberia inyectar todas las senales por defecto.

Regla recomendada:

- En `question_only`: no inyectar senales.
- En `docs_only`: inyectar solo senales relacionadas con documentacion faltante.
- En `fast_code`: inyectar como maximo 1 advisory si es high confidence.
- En `deep_code`: inyectar hasta 3 senales compactas.
- En `finish_only`: registrar si la sesion confirma o contradice una senal.

Ejemplo de inyeccion compacta:

```text
BusinessSignal: el proyecto actual se parece a client-portal-v1.
Evidencia: 14/20 HU recientes recuperaron contexto de ese proyecto.
Revisar: ADR-004, incident-auth-refresh, session-scope-change.
No asumas que el patron se repetira; usalo como referencia historica.
```

## Vault Notes

BusinessSignal podria escribir notas opcionales bajo:

```text
vault/signals/
```

Ejemplo:

```text
vault/signals/2026-05-09-client-mobile-redesign-historical-analogy.md
```

Estas notas deben ser opcionales, porque no toda senal merece persistencia documental.

## Enterprise Reports

En modo enterprise, BusinessSignal puede ayudar a responder:

- Que proyectos actuales se parecen a proyectos pasados.
- Que dominios generan mas ecos de riesgo.
- Que clientes o verticales repiten patrones.
- Que conocimiento historico esta siendo reutilizado.
- Que areas tienen memoria insuficiente.

Reporte posible:

```text
cortex enterprise signals-report
```

## Doctor

El doctor podria validar:

- Si la telemetria esta habilitada.
- Si los eventos JSONL rotan correctamente.
- Si hay eventos sin metadata de origen.
- Si hay senales activas sin evidencia.
- Si los detectores configurados cargan correctamente.

## CI

BusinessSignal no deberia bloquear CI por defecto.

Modo recomendado:

- `advisory`: reporta senales.
- `warning`: marca riesgo, no falla.
- `enforced`: solo para organizaciones maduras y reglas muy especificas.

Ejemplo de uso maduro:

```text
Fallar CI si una feature de pagos activa Compliance Echo critical y no hay ADR asociado.
```

Eso debe ser una politica empresarial explicita, no comportamiento default.

