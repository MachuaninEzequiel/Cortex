# Cortex BusinessSignal

## Proposito

BusinessSignal es una propuesta para convertir el uso historico de Cortex en una capa de inteligencia de negocio explicable.

La idea central es simple: Cortex ya detecta memoria similar cuando enriquece el contexto de un agente. Si durante un proyecto actual aparecen una y otra vez memorias, documentos, historias, ADRs o incidentes de un mismo proyecto anterior, eso no deberia quedar encerrado solamente dentro del prompt del agente. Esa repeticion puede ser una senal de negocio.

BusinessSignal no intenta predecir el futuro como una certeza. Su trabajo es detectar analogos historicos fuertes y avisar:

> "El proyecto actual se esta pareciendo mucho a este proyecto anterior. Vale la pena revisar esa experiencia antes de que el patron se repita."

## Objetivo Ambicioso

Crear un modulo de analitica predictiva y preventiva para Cortex que permita:

- Detectar similitudes entre proyectos actuales y proyectos historicos.
- Identificar patrones de comportamiento de clientes, product owners, equipos o dominios funcionales.
- Advertir riesgos tempranos basados en evidencia del vault.
- Recomendar documentos historicos concretos para revisar.
- Reducir retrabajo, cambios tardios, incidentes repetidos y perdida de conocimiento organizacional.
- Mantener bajo consumo de tokens usando metadata, conteos, scores y referencias en lugar de resumir todo el vault.

## Principio Rector

BusinessSignal debe ser una capa de senales, no una capa de opinion.

Cada insight debe poder responder:

- Que patron se detecto.
- En que evidencia historica se basa.
- Que tan fuerte es la similitud.
- Que documentos o sesiones conviene revisar.
- Que accion humana recomienda.
- Que nivel de confianza tiene.

Si no hay evidencia suficiente, no se emite una senal.

## Relacion Con Cortex Actual

Cortex ya tiene piezas que hacen viable esta propuesta:

- `ContextEnricher`: encuentra memorias similares al trabajo actual.
- `WorkContext`: representa archivos, keywords, dominio y queries actuales.
- `EnrichedContext`: contiene hits recuperados, scores, estrategias y presupuesto.
- `AgentMemory`: conecta memoria episodica y semantica.
- `EnterpriseRetrievalService`: maneja origen local/enterprise y project ids.
- `vault` y `vault-enterprise`: contienen sesiones, HU, ADRs, incidentes, decisiones y conocimiento historico.
- `Autopilot`: puede consumir senales sin obligar al usuario a pedirlas manualmente.

BusinessSignal debe apoyarse en estas piezas, no reemplazarlas.

## Arquitectura Resumida

```text
ContextEnricher
   |
   | emite metadata de cada enrichment
   v
EnrichmentTelemetryStore
   |
   | agrega eventos por proyecto, HU, sprint, dominio, cliente
   v
PatternRadarEngine
   |
   | ejecuta detectores modulares
   v
BusinessSignalRegistry
   |
   | guarda senales explicables y evidencia
   v
Surfaces
   |
   +-- CLI reports
   +-- MCP tools
   +-- Autopilot advisory
   +-- Enterprise dashboards
   +-- Vault notes
```

La arquitectura completa esta desarrollada en [architecture.md](architecture.md).

## Documentos

- [architecture.md](architecture.md): arquitectura tecnica propuesta.
- [data-model.md](data-model.md): eventos, agregados, senales y evidencia.
- [detectors.md](detectors.md): detectores modulares iniciales y futuros.
- [product-surfaces.md](product-surfaces.md): CLI, MCP, Autopilot, reportes y vault.
- [roadmap.md](roadmap.md): fases de implementacion recomendadas.

## MVP Recomendado

El primer MVP no deberia intentar "predecir clientes". Debe resolver un caso muy claro:

> Detectar que el proyecto actual esta recuperando contexto de forma concentrada desde un proyecto historico especifico.

Ejemplo:

```text
BusinessSignal: Historical Project Analogy

Proyecto actual: client-mobile-redesign
Proyecto historico similar: client-portal-v1

Evidencia:
- 14 de las ultimas 20 HU recuperaron contexto de client-portal-v1.
- 9 coincidencias fueron por dominio y archivos.
- 5 coincidencias fueron por ADRs y decisiones.
- 3 incidentes historicos aparecen cerca del mismo dominio funcional.

Confianza: alta
Accion recomendada:
- Revisar ADR-004, incident-2025-09-auth-refresh y sessions/sprint-03-scope-change.md.
- Anticipar preguntas sobre permisos, reporting y migracion de datos.
```

Ese MVP ya aporta valor sin IA adicional, sin grandes costos y con trazabilidad fuerte.

