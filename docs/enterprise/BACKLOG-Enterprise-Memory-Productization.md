# Backlog Tecnico Ejecutable: Enterprise Memory Productization

## Documento

- Fecha: 2026-04-26
- Proyecto: Cortex
- Iniciativa madre: `Enterprise Memory Productization`
- Objetivo: convertir el plan estrategico en un backlog tecnico ejecutable, priorizado y preparado para seguimiento incremental
- Estado inicial: backlog base, sin tareas marcadas como completadas

---

## Como usar este backlog

Este backlog esta pensado para ser usado como documento vivo de implementacion.

- Cada bloque tiene prioridad, objetivo, impacto tecnico, dependencias y checklist.
- Los checks deben marcarse a medida que se completa trabajo real.
- El orden recomendado ya esta reflejado en la estructura.
- Si una tarea cambia de alcance, conviene actualizar el item existente en lugar de duplicarlo.

### Convenciones

- `[ ]` pendiente
- `[x]` completado
- `P0` critico y fundacional
- `P1` alto valor, siguiente ola
- `P2` mejora importante pero no bloqueante

---

## 1. Objetivo del backlog

Construir una version enterprise de Cortex que permita:

- memoria local de proyecto
- memoria institucional corporativa
- retrieval local + corporativo
- promocion formal de conocimiento
- setup enterprise interactivo
- gobernanza y CI enterprise
- observabilidad y reportes de salud de memoria

---

## 2. Criterios globales de exito

- [ ] Cortex soporta topologia enterprise declarativa mediante configuracion formal.
- [ ] Cortex puede consultar memoria local y memoria corporativa en una misma experiencia de retrieval.
- [ ] Existe un pipeline oficial de promocion de conocimiento entre niveles de memoria.
- [ ] Existe un `cortex setup enterprise` usable para clientes reales.
- [ ] La gobernanza enterprise puede ejecutarse desde CI.
- [ ] Existe una capa minima de observabilidad de memoria y salud operativa.

---

## 3. Orden recomendado de ejecucion

### Onda 1: Fundacion

- P0.1 Modelo organizacional
- P0.2 Retrieval multi-nivel base

### Onda 2: Operabilidad

- P1.1 Promotion pipeline
- P1.2 Gobernanza y CI enterprise

### Onda 3: Productizacion

- P1.3 Setup enterprise interactivo
- P2.1 Observabilidad y reporting

### Onda 4: Hardening

- P2.2 Presets, documentacion final, refinamientos de adopcion

---

## 4. Mapa de epics

| Epic | Prioridad | Nombre | Resultado |
| --- | --- | --- | --- |
| E1 | P0 | Modelo organizacional enterprise | Topologia formal y declarativa |
| E2 | P0 | Retrieval multi-nivel | Consulta local + enterprise |
| E3 | P1 | Promotion pipeline | Promocion auditable de conocimiento |
| E4 | P1 | Gobernanza y CI enterprise | Politicas automáticas de memoria |
| E5 | P1 | Setup enterprise interactivo | Instalacion guiada para clientes |
| E6 | P2 | Observabilidad y reporting | Salud de memoria y adopcion |
| E7 | P2 | Presets, docs y hardening | Cierre de productizacion |

---

## 5. EPIC E1 - Modelo organizacional enterprise

### Prioridad

`P0`

### Objetivo

Agregar una capa formal de configuracion organizacional para representar como una empresa usa la memoria de Cortex.

### Impacto tecnico

Medio.

### Dependencias

Ninguna. Es la base del resto.

### Definition of Done del epic

- [x] Existe una configuracion organizacional formal validada por codigo.
- [x] El runtime puede cargar esa configuracion.
- [x] La CLI puede exponer esa configuracion.
- [x] Existen defaults razonables para distintos perfiles de empresa.

### Archivos / modulos objetivo

- [x] Crear `cortex/enterprise/config.py`
- [x] Crear `cortex/enterprise/models.py`
- [x] Integrar lectura desde [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [x] Integrar en [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)
- [x] Integrar templates en [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)

### Historias tecnicas

#### E1-S1 - Disenar schema organizacional

Prioridad: `P0`

- [x] Definir estructura de `.cortex/org.yaml`
- [x] Definir secciones `organization`, `memory`, `promotion`, `governance`, `integration`
- [x] Definir versionado del schema
- [x] Definir defaults y campos opcionales
- [x] Documentar ejemplos minimos y avanzados

#### E1-S2 - Implementar modelos y validacion

Prioridad: `P0`

- [x] Crear modelos Pydantic para `org.yaml`
- [x] Validar rutas, enums y combinaciones invalidas
- [x] Agregar errores claros de validacion
- [x] Agregar funcion de carga centralizada

#### E1-S3 - Integrar config enterprise al runtime

Prioridad: `P0`

- [x] Resolver discovery de `.cortex/org.yaml`
- [x] Exponer acceso a config enterprise desde servicios
- [x] Definir precedence entre `config.yaml` y `org.yaml`
- [x] Asegurar backward compatibility cuando `org.yaml` no exista

#### E1-S4 - Agregar soporte CLI y doctor

Prioridad: `P0`

- [x] Agregar comando `cortex doctor --scope enterprise`
- [x] Reportar configuracion organizacional faltante o inconsistente
- [x] Exponer diagnostico de topologia elegida

### Validacion del epic

- [x] Existe fixture minima de empresa chica
- [x] Existe fixture multi-proyecto
- [x] Existe fixture con vault corporativo
- [x] Existen tests de validacion de schema

---

## 6. EPIC E2 - Retrieval multi-nivel

### Prioridad

`P0`

### Objetivo

Permitir retrieval local, corporativo o combinado, con trazabilidad clara de origen.

### Impacto tecnico

Medio/alto.

### Dependencias

- E1 completo o en estado estable

### Definition of Done del epic

- [x] Se puede consultar solo memoria local.
- [x] Se puede consultar solo memoria enterprise.
- [x] Se puede consultar ambas fuentes en una sola operacion.
- [x] Los resultados identifican su origen.
- [x] El ranking es configurable y comprensible.

### Archivos / modulos objetivo

- [x] Extender [cortex/core.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/core.py)
- [x] Extender [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py)
- [x] Extender [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py)
- [x] Evaluar extension de [cortex/episodic/memory_store.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/episodic/memory_store.py)
- [x] Crear `cortex/enterprise/retrieval_service.py`
- [x] Crear `cortex/enterprise/sources.py`

### Historias tecnicas

#### E2-S1 - Modelar scopes de retrieval

Prioridad: `P0`

- [x] Definir scopes `local`, `enterprise`, `all`
- [x] Definir como se configuran por CLI y por runtime
- [x] Definir metadata de origen que debe retornar cada hit

#### E2-S2 - Implementar multi-vault semantic retrieval

Prioridad: `P0`

- [x] Permitir multiples `vault_path` en lectura
- [x] Agregar fusion de resultados semanticos por fuente
- [x] Etiquetar hits con `scope`, `project_id` y `origin_vault`

#### E2-S3 - Implementar multi-source episodic retrieval

Prioridad: `P0`

- [x] Resolver estrategia para uno o varios `persist_dir`
- [x] Permitir consultar memoria episodica local y enterprise
- [x] Mantener compatibilidad con `namespace_mode`
- [x] Exponer filtros por proyecto, rama y repo

#### E2-S4 - Fusion unificada multi-nivel

Prioridad: `P0`

- [x] Diseñar estrategia RRF para mas de dos fuentes
- [x] Definir pesos por source y por scope
- [x] Agregar observabilidad de pesos efectivos
- [x] Evitar sobre-penalizacion o duplicacion de hits

#### E2-S5 - CLI ejecutable para retrieval enterprise

Prioridad: `P0`

- [x] Agregar `--scope` a `cortex search`
- [x] Agregar salida JSON enriquecida con origen
- [x] Agregar opcion para mostrar score por fuente

### Validacion del epic

- [x] Tests de retrieval solo local
- [x] Tests de retrieval solo enterprise
- [x] Tests de retrieval local + enterprise
- [x] Tests con conflictos o duplicados entre fuentes
- [x] Tests de backward compatibility

---

## 7. EPIC E3 - Promotion pipeline de conocimiento

### Prioridad

`P1`

### Objetivo

Formalizar como el conocimiento local se promueve a memoria institucional.

### Impacto tecnico

Medio.

### Dependencias

- E1 completo
- E2 base operativa

### Definition of Done del epic

- [ ] Existe un pipeline oficial de promocion.
- [ ] Los documentos promovibles se identifican formalmente.
- [ ] El estado de promocion queda trazado.
- [ ] La promocion puede ser manual, asistida o CI-driven.

### Archivos / modulos objetivo

- [ ] Crear `cortex/enterprise/knowledge_promotion.py`
- [ ] Crear `cortex/enterprise/promotion_models.py`
- [ ] Extender [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [ ] Extender [cortex/doc_validator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doc_validator.py)
- [ ] Extender [cortex/doc_verifier.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doc_verifier.py)

### Historias tecnicas

#### E3-S1 - Definir modelo de promocion

Prioridad: `P1`

- [ ] Definir estados `draft`, `candidate`, `reviewed`, `promoted`, `rejected`
- [ ] Definir metadata de origen y trazabilidad
- [ ] Definir estrategia de promotion record

#### E3-S2 - Definir reglas de promovibilidad

Prioridad: `P1`

- [ ] Definir tipos de docs promovibles
- [ ] Definir docs excluidos por defecto
- [ ] Definir reglas declarativas por org
- [ ] Definir si `vault/sessions/` entra o no al pipeline

#### E3-S3 - Implementar comandos de promocion

Prioridad: `P1`

- [ ] Agregar `cortex promote-knowledge`
- [ ] Agregar `cortex review-knowledge`
- [ ] Agregar `cortex sync-enterprise-vault`
- [ ] Agregar `--dry-run`

#### E3-S4 - Implementar copiado, transformacion o referencia

Prioridad: `P1`

- [ ] Definir si se promociona por copia, mirror o referencia
- [ ] Crear estrategia inicial recomendada
- [ ] Asegurar metadata de origen y fecha de promocion

#### E3-S5 - Integrar con validacion documental

Prioridad: `P1`

- [ ] Validar docs antes de promocion
- [ ] Rechazar o advertir por errores de estructura
- [ ] Generar reporte de promotion candidates

### Validacion del epic

- [ ] Tests de promotion rules
- [ ] Tests de promotion dry-run
- [ ] Tests de trazabilidad
- [ ] Tests de promocion repetida / idempotencia

---

## 8. EPIC E4 - Gobernanza y CI enterprise

### Prioridad

`P1`

### Objetivo

Llevar la memoria enterprise a una operacion gobernada por politicas configurables y CI.

### Impacto tecnico

Bajo/medio.

### Dependencias

- E1 completo
- E3 al menos en version inicial

### Definition of Done del epic

- [ ] CI puede validar memoria enterprise.
- [ ] CI puede correr checks de promotion.
- [ ] Existen modos observability, advisory y enforced.
- [ ] `doctor` reporta salud enterprise.

### Archivos / modulos objetivo

- [ ] Extender [cortex/doctor.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doctor.py)
- [ ] Extender [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [ ] Extender [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- [ ] Agregar templates workflow enterprise
- [ ] Ajustar `.github/workflows/` generados

### Historias tecnicas

#### E4-S1 - Diseñar perfiles de enforcement

Prioridad: `P1`

- [ ] Definir `observability`
- [ ] Definir `advisory`
- [ ] Definir `enforced`
- [ ] Conectar perfiles con `org.yaml`

#### E4-S2 - Extender doctor enterprise

Prioridad: `P1`

- [ ] Verificar presencia de vault corporativo
- [ ] Verificar integridad de promotion policy
- [ ] Verificar compatibilidad entre repos y topologia
- [ ] Verificar politicas Git/Vault

#### E4-S3 - Crear pasos CI para promotion y validacion

Prioridad: `P1`

- [ ] Agregar validacion de promotion candidates
- [ ] Agregar validacion de docs enterprise
- [ ] Agregar jobs configurables segun enforcement
- [ ] Agregar artefactos JSON de reporte

#### E4-S4 - Reportes de estado en CI

Prioridad: `P1`

- [ ] Generar resumen de memoria y promotion
- [ ] Generar reportes consumibles por humanos
- [ ] Definir salidas para observabilidad

### Validacion del epic

- [ ] Workflow example small-company
- [ ] Workflow example regulated
- [ ] Tests de doctor enterprise
- [ ] Tests de render de templates enterprise

---

## 9. EPIC E5 - Setup enterprise interactivo

### Prioridad

`P1`

### Objetivo

Empaquetar toda la complejidad enterprise dentro de una experiencia guiada y usable por clientes.

### Impacto tecnico

Medio.

### Dependencias

- E1 estable
- E3 y E4 con contratos definidos

### Definition of Done del epic

- [ ] Existe `cortex setup enterprise`.
- [ ] Existe modo guiado interactivo.
- [ ] Existe modo no interactivo con presets.
- [ ] El setup genera estructura completa y coherente.

### Archivos / modulos objetivo

- [ ] Extender [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)
- [ ] Extender [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- [ ] Crear `cortex/setup/enterprise_wizard.py`
- [ ] Crear `cortex/setup/enterprise_presets.py`

### Historias tecnicas

#### E5-S1 - Definir modo SetupMode.ENTERPRISE

Prioridad: `P1`

- [ ] Crear nuevo modo en orchestrator
- [ ] Definir pipeline de generacion asociado
- [ ] Definir summary final de setup

#### E5-S2 - Implementar wizard interactivo

Prioridad: `P1`

- [ ] Preguntar perfil organizacional
- [ ] Preguntar topologia de memoria
- [ ] Preguntar gobernanza de promotion
- [ ] Preguntar politicas Git/Vault
- [ ] Preguntar integraciones CI / IDE / WebGraph
- [ ] Mostrar resumen antes de aplicar

#### E5-S3 - Implementar modo no interactivo

Prioridad: `P1`

- [ ] Soportar `--preset`
- [ ] Soportar `--org-config`
- [ ] Soportar `--dry-run`
- [ ] Soportar salida resumen JSON

#### E5-S4 - Generar estructura enterprise completa

Prioridad: `P1`

- [ ] Generar `.cortex/org.yaml`
- [ ] Generar vault corporativo si aplica
- [ ] Generar vault local y runbooks
- [ ] Generar workflows enterprise
- [ ] Generar workspace federado inicial
- [ ] Generar politicas Git/Vault

#### E5-S5 - Presets iniciales

Prioridad: `P1`

- [ ] Preset `small-company`
- [ ] Preset `multi-project-team`
- [ ] Preset `regulated-organization`

### Validacion del epic

- [ ] Smoke test setup enterprise interactivo
- [ ] Smoke test preset small-company
- [ ] Smoke test preset multi-project-team
- [ ] Smoke test preset regulated-organization

---

## 10. EPIC E6 - Observabilidad y reporting

### Prioridad

`P2`

### Objetivo

Permitir que la empresa observe el estado de su memoria, sus promociones y su salud general.

### Impacto tecnico

Bajo/medio.

### Dependencias

- E2 operativo
- E3 operativo
- E4 base disponible

### Definition of Done del epic

- [ ] Existe reporte de salud de memoria.
- [ ] Existe trazabilidad de promociones.
- [ ] WebGraph puede enriquecerse con informacion enterprise.

### Archivos / modulos objetivo

- [ ] Crear `cortex/enterprise/reporting.py`
- [ ] Extender [cortex/webgraph/federation.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/webgraph/federation.py)
- [ ] Extender [cortex/webgraph/service.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/webgraph/service.py)
- [ ] Extender [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)

### Historias tecnicas

#### E6-S1 - Reporte de memoria

Prioridad: `P2`

- [ ] Agregar `cortex memory-report`
- [ ] Reportar volumen por fuente
- [ ] Reportar docs promovidos
- [ ] Reportar gaps de salud

#### E6-S2 - Reporte de promotion

Prioridad: `P2`

- [ ] Mostrar candidatos pendientes
- [ ] Mostrar ultimas promociones
- [ ] Mostrar rechazos o warnings

#### E6-S3 - Enriquecimiento WebGraph

Prioridad: `P2`

- [ ] Agregar notion de nodos enterprise
- [ ] Permitir filtro por scope
- [ ] Mostrar relaciones entre proyecto y memoria corporativa

### Validacion del epic

- [ ] Report JSON de memory-report
- [ ] Report legible para humanos
- [ ] Visualizacion WebGraph minima funcional

---

## 11. EPIC E7 - Presets, docs y hardening

### Prioridad

`P2`

### Objetivo

Cerrar la iniciativa como producto usable, explicable y sostenible.

### Impacto tecnico

Bajo/medio.

### Dependencias

- E1 a E6 en estado razonablemente estable

### Definition of Done del epic

- [ ] La documentacion enterprise esta completa.
- [ ] Los presets estan refinados.
- [ ] La experiencia de adopcion es clara.
- [ ] Los riesgos operativos principales quedaron cubiertos.

### Historias tecnicas

#### E7-S1 - Documentacion de producto enterprise

Prioridad: `P2`

- [ ] Documento de arquitectura final
- [ ] Documento de setup enterprise
- [ ] Documento de promotion policy
- [ ] Documento de gobernanza CI

#### E7-S2 - Hardening tecnico

Prioridad: `P2`

- [ ] Revisar backward compatibility
- [ ] Revisar defaults peligrosos
- [ ] Revisar mensajes de error y UX
- [ ] Revisar migracion desde setups existentes

#### E7-S3 - Adopcion por perfiles

Prioridad: `P2`

- [ ] Guia para developers
- [ ] Guia para tech leads
- [ ] Guia para arquitectura
- [ ] Guia para operaciones / platform

### Validacion del epic

- [ ] Checklist de lanzamiento interno
- [ ] Checklist de setup cliente
- [ ] Checklist de migracion desde modo actual

---

## 12. Backlog transversal de testing y calidad

### Prioridad

`P0-P2 transversal`

### Objetivo

Evitar que la iniciativa avance sin base verificable.

### Checklist

- [x] Crear carpeta o modulo de tests enterprise
- [x] Agregar fixtures de topologias organizacionales
- [x] Agregar tests de schema y config
- [ ] Agregar tests de retrieval multi-nivel
- [ ] Agregar tests de promotion pipeline
- [ ] Agregar tests de setup enterprise
- [ ] Agregar tests de templates y workflows
- [x] Agregar tests de doctor enterprise
- [ ] Agregar tests de reporting

### Quality gates recomendados

- [ ] Cada epic nuevo sale con tests minimos
- [ ] Cada comando CLI nuevo sale con tests de humo
- [ ] Cada template generado sale con validacion estructural

---

## 13. Backlog transversal de documentacion interna

### Objetivo

Mantener alineados codigo, producto y operacion.

### Checklist

- [ ] Actualizar README cuando exista `setup enterprise`
- [ ] Actualizar docs de runbooks
- [ ] Crear ejemplo de `org.yaml`
- [ ] Documentar topologias soportadas
- [ ] Documentar modelo de promotion
- [ ] Documentar scopes de retrieval
- [ ] Documentar politicas Git/Vault enterprise

---

## 14. Backlog transversal de migracion y compatibilidad

### Objetivo

Asegurar que clientes o repos actuales no queden rotos.

### Checklist

- [ ] Diseñar migracion desde setups actuales sin `org.yaml`
- [ ] Mantener funcionamiento actual si no se usa modo enterprise
- [ ] Agregar warnings claros y no breaking
- [ ] Definir estrategia de versionado / release notes
- [ ] Crear comando o guia de migracion asistida

---

## 15. Milestone propuesto por releases

## M1 - Enterprise Foundation

Incluye:

- [ ] E1 completo
- [ ] E2 base operativa

Resultado:

- Cortex entiende topologia enterprise y puede recuperar memoria multi-nivel

## M2 - Enterprise Governance

Incluye:

- [ ] E3 completo
- [ ] E4 base operativa

Resultado:

- Cortex puede promover y gobernar conocimiento institucional

## M3 - Enterprise Setup

Incluye:

- [ ] E5 completo

Resultado:

- Un cliente puede desplegar la topologia enterprise con setup guiado

## M4 - Enterprise Visibility

Incluye:

- [ ] E6 completo
- [ ] E7 base operativa

Resultado:

- Cortex deja trazabilidad, observabilidad y documentacion final de producto

---

## 16. Backlog inmediato recomendado

Si hubiera que arrancar ya, este es el primer corte de implementacion recomendado:

### Sprint de arranque

- [x] Crear paquete `cortex/enterprise/`
- [x] Diseñar `.cortex/org.yaml`
- [x] Implementar modelos y validacion
- [x] Integrar carga basica a CLI
- [x] Extender `doctor` con awareness enterprise
- [ ] Diseñar scopes de retrieval
- [ ] Crear esqueleto de `retrieval_service.py`

### Segundo corte

- [ ] Implementar multi-vault semantic retrieval
- [ ] Implementar multi-source episodic retrieval
- [ ] Exponer `cortex search --scope`
- [ ] Agregar tests iniciales de retrieval enterprise

### Tercer corte

- [ ] Diseñar promotion model
- [ ] Implementar `promote-knowledge --dry-run`
- [ ] Generar reporte de promotion candidates
- [ ] Diseñar enforcement profiles CI

---

## 17. Riesgos de ejecucion del backlog

- [ ] Evitar meter logica enterprise pesada dentro de `AgentMemory`
- [ ] Evitar wizard demasiado complejo en la primera version
- [ ] Evitar promotion automatica sin reglas
- [ ] Evitar confundir memoria durable con estado operativo
- [ ] Evitar que el scope enterprise rompa el comportamiento local existente

---

## 18. Cierre del backlog

Este backlog queda preparado para ser usado como hoja de ruta de implementacion real.  
La forma mas sana de avanzar es por epics, cerrando primero E1 y E2, y usando este mismo documento como tablero de progreso.

Cuando arranque la implementacion, conviene actualizar:

- checks completados
- modulos ya creados
- decisiones de alcance
- items descartados o replanificados

---

## 19. Documentos relacionados

- [Enterprise Memory Productization.md](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/Enterprise%20Memory%20Productization.md)
- [DIAGRAMAS-Memoria-Cortex-Actual-y-Objetivo.md](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/DIAGRAMAS-Memoria-Cortex-Actual-y-Objetivo.md)
- [AVANCE-Alineacion-Fases-MultiProyecto-y-Gobernanza.md](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/AVANCE-Alineacion-Fases-MultiProyecto-y-Gobernanza.md)
