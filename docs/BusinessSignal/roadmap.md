# BusinessSignal Roadmap

## Estrategia General

BusinessSignal debe construirse por capas. La primera version debe capturar telemetria y detectar una senal muy confiable. Despues se agregan detectores mas sofisticados.

La filosofia de implementacion debe ser:

- Primero metadata.
- Despues agregados.
- Despues senales.
- Despues interfaces.
- Finalmente automatizacion y feedback.

## Fase 0: Decision De Producto

### Objetivo

Definir el contrato de producto antes de implementar.

### Decisiones

- Nombre final: `BusinessSignal`, `PatternRadar`, `Cortex Signals` u otro.
- Si sera modulo enterprise-only o disponible en Cortex base.
- Si escribira notas en vault por defecto o solo bajo comando.
- Que metadata de proyecto/cliente se considera confiable.
- Que nivel de privacidad requiere.

### Salida

Documento de decision con alcance MVP.

## Fase 1: Telemetria De Enrichment

### Objetivo

Registrar eventos livianos cada vez que Cortex enriquece contexto.

### Tareas

- Crear modelos `EnrichmentEvent` y `EnrichmentHitRef`.
- Crear `EnrichmentTelemetryStore`.
- Guardar eventos en JSONL.
- No guardar contenido completo por defecto.
- Preservar `origin_project_id`, `origin_scope`, `origin_vault`.
- Agregar tests unitarios.

### Criterio De Salida

Al ejecutar enrichment, Cortex deja un evento estructurado que puede analizarse sin leer todo el vault.

## Fase 2: Agregacion Por Proyecto

### Objetivo

Construir trayectorias del proyecto actual a partir de eventos.

### Tareas

- Crear `ProjectTrajectory`.
- Agregar agrupaciones por proyecto, HU, dominio y ventana temporal.
- Calcular distribucion de proyectos historicos.
- Calcular scores ponderados.
- Calcular memoria critica recuperada: incidentes, ADRs, security.
- Agregar tests con eventos sinteticos.

### Criterio De Salida

Un comando o servicio puede decir:

```text
En los ultimos N eventos, el proyecto actual recupero X% de contexto desde project-Y.
```

## Fase 3: Detector Project Concentration

### Objetivo

Implementar el primer detector MVP.

### Tareas

- Crear contrato `BusinessSignalDetector`.
- Crear registry de detectores.
- Implementar `project_concentration.py`.
- Crear modelo `BusinessSignal`.
- Crear `EvidencePointer`.
- Generar senales con confianza baja/media/alta.

### Criterio De Salida

Cortex detecta analogias historicas fuertes entre proyecto actual y proyecto anterior.

## Fase 4: CLI Inicial

### Objetivo

Exponer senales al usuario.

### Tareas

- Agregar `cortex signals`.
- Agregar `cortex signals --json`.
- Agregar `cortex signals explain <id>`.
- Mantener salida compacta.
- Agregar tests CLI.

### Criterio De Salida

Un usuario puede ver senales activas y su evidencia sin abrir archivos manualmente.

## Fase 5: Reporte Markdown

### Objetivo

Generar reportes para leads, PMs y equipos.

### Tareas

- Crear renderer Markdown.
- Agregar `cortex signals report`.
- Incluir top analogias, riesgos y documentos recomendados.
- Permitir guardar reporte en `vault/signals/` bajo comando explicito.

### Criterio De Salida

El equipo puede compartir un reporte accionable.

## Fase 6: MCP Tools

### Objetivo

Permitir que agentes consulten senales sin leer todo el vault.

### Tareas

- Agregar `cortex_business_signals`.
- Agregar `cortex_explain_business_signal`.
- Agregar `cortex_record_signal_feedback`.
- Mantener respuestas con presupuesto bajo.

### Criterio De Salida

Un agente puede usar senales de negocio como contexto compacto y explicable.

## Fase 7: Integracion Con Autopilot

### Objetivo

Hacer que Autopilot use senales de forma prudente.

### Tareas

- Definir reglas por budget profile.
- Inyectar maximo 1 senal en `fast_code`.
- Inyectar hasta 3 en `deep_code`.
- No inyectar en `question_only`.
- Registrar si la sesion confirma o contradice la senal.

### Criterio De Salida

Autopilot puede advertir patrones historicos sin aumentar demasiado el consumo.

## Fase 8: Risk Echo

### Objetivo

Detectar ecos de riesgo basados en incidentes, ADRs, seguridad y retrabajo.

### Tareas

- Implementar detector `risk_echo.py`.
- Definir tags/memory types criticos.
- Priorizar evidencia de alta calidad.
- Agregar scoring conservador.

### Criterio De Salida

Cortex advierte cuando un proyecto actual se parece a una zona historica riesgosa.

## Fase 9: Sequence Similarity

### Objetivo

Comparar secuencias de avance entre proyectos.

### Tareas

- Crear fingerprints de trayectoria.
- Comparar dominios, tags, componentes y memory types.
- Implementar similitud de secuencia.
- Evitar conclusiones fuertes con pocos datos.

### Criterio De Salida

Cortex detecta cuando el orden de trabajo actual se parece al de un proyecto previo.

## Fase 10: Feedback Loop

### Objetivo

Aprender si las senales fueron utiles.

### Tareas

- Crear `SignalFeedback`.
- Integrar con CLI/MCP.
- Ajustar scoring usando feedback.
- Reportar falsos positivos.

### Criterio De Salida

BusinessSignal mejora con el uso real.

## Fase 11: Enterprise Dashboard

### Objetivo

Crear visibilidad organizacional.

### Tareas

- Reporte por proyecto.
- Reporte por cliente.
- Reporte por dominio.
- Reporte por detector.
- Identificar conocimiento historico mas reutilizado.
- Identificar gaps de documentacion.

### Criterio De Salida

La organizacion puede ver como se reutiliza su memoria y donde aparecen riesgos recurrentes.

## Fase 12: Politicas Gobernadas

### Objetivo

Permitir que organizaciones maduras creen reglas.

### Ejemplos

- Si `Compliance Echo` es high, sugerir ADR.
- Si `Risk Echo` toca pagos, notificar seguridad.
- Si `Knowledge Gap` se repite, crear tarea de documentacion.

### Criterio De Salida

BusinessSignal pasa de advisory a governance opcional.

