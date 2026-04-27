# Enterprise Memory Productization

## Documento

- Fecha: 2026-04-26
- Proyecto: Cortex
- Objetivo: definir un plan de implementacion concreto, completo y detallado para convertir la arquitectura actual de Cortex en una solucion de memoria empresarial productizada
- Estado de partida: Cortex ya dispone de memoria hibrida real, modularidad por proyecto/rama, WebGraph federado, CI con indexado documental y capa inicial de gobernanza

---

## 1. Resumen ejecutivo

El objetivo de esta iniciativa es llevar a Cortex desde un sistema con muy buena memoria hibrida a nivel proyecto hacia un producto capaz de ofrecer, de forma estandarizada y repetible, una **memoria empresarial transversal**, gobernada y automatizable.

La idea no es reemplazar lo que Cortex ya hace bien. La idea es agregar una nueva capa de producto sobre la base actual para resolver cuatro cosas que hoy todavia dependen demasiado del criterio manual de cada empresa:

1. Como se organiza la memoria entre proyectos, ramas y empresa.
2. Como se promueve conocimiento local hacia conocimiento institucional.
3. Como consultan los agentes tanto el contexto local como el corporativo.
4. Como se instala todo esto de forma guiada, automatizada y apta para clientes.

La conclusion principal es esta:

- No hace falta reescribir Cortex.
- Si hace falta una ampliacion estructurada de complejidad media.
- El mayor trabajo no esta en embeddings o Chroma, sino en **topologia, gobernanza, configuracion organizacional, promotion pipelines y setup interactivo enterprise**.

---

## 2. Problema que resuelve esta iniciativa

Hoy Cortex funciona muy bien para:

- memoria episodica por proyecto
- memoria semantica en `vault/`
- recuperacion hibrida entre ambas capas
- observabilidad y analitica multi-proyecto mediante WebGraph federado

Pero todavia no resuelve de forma nativa y productizada:

- una memoria institucional corporativa formal
- un mecanismo de promocion de conocimiento desde los proyectos hacia esa memoria corporativa
- una consulta hibrida local + corporativa como comportamiento estandar
- una experiencia de setup empresarial completa, guiada y automatizable

Dicho de otro modo: la arquitectura ya esta cerca, pero le falta una **capa de producto enterprise**.

---

## 3. Vision objetivo

La memoria objetivo de Cortex no debe ser una sola base plana de todo.  
Debe ser una arquitectura por niveles:

1. **Memoria local de trabajo**
   Cada repo conserva su memoria episodica y su vault tecnico.
2. **Memoria de proyecto durable**
   Specs, decisiones, runbooks e incidentes del proyecto.
3. **Memoria institucional corporativa**
   Patrones transversales, decisiones globales, modelos de negocio, criterios de compliance, runbooks corporativos y conocimiento comun.
4. **Capa de promocion**
   Reglas y pipelines que deciden que conocimiento sube desde lo local hacia lo corporativo.
5. **Capa de consulta unificada**
   Agentes capaces de recuperar contexto desde memoria local y memoria corporativa en la misma consulta.

---

## 4. Principios de diseno

Este plan asume los siguientes principios:

1. `vault/` sigue siendo la mejor representacion del conocimiento durable y gobernado.
2. `.memory/chroma` sigue siendo la mejor representacion del estado episodico operativo y vectorial.
3. La memoria corporativa no debe llenarse automaticamente con todo.
4. La promocion de conocimiento debe ser explicita, auditable y configurable.
5. La experiencia enterprise debe poder montarse con `setup` guiado, no con pasos manuales dispersos.
6. La arquitectura debe servir tanto a una empresa chica como a una mediana, sin obligarlas a adoptar una topologia desproporcionada.

---

## 5. Diagnostico: que parte es Cortex y que parte es setup de la empresa

La transformacion hacia memoria objetivo es una mezcla de producto y operacion.

### 5.1 Que depende de la empresa

- Definir que conocimiento es local y cual es institucional.
- Decidir si habra un vault corporativo compartido.
- Definir quien aprueba o cura conocimiento promovido.
- Decidir si los repositorios mantendran vault propio, vault compartido o ambos.
- Definir politicas Git y CI de la organizacion.

### 5.2 Que debe resolver Cortex

- Modelar esa topologia sin parches manuales.
- Proveer configuracion organizacional formal.
- Permitir retrieval local + corporativo.
- Automatizar promocion de conocimiento.
- Generar estructura, workflows, configs y runbooks desde un setup interactivo.

### 5.3 Concluson

Hoy el problema es aproximadamente:

- 60% setup y gobernanza organizacional
- 40% producto Cortex

La meta de esta iniciativa es bajar esa dependencia manual y hacer que Cortex absorba la mayor parte posible de la complejidad de implantacion.

---

## 6. Estrategia general de implementacion

La implementacion recomendada se divide en seis etapas:

1. Fundaciones de modelo organizacional
2. Retrieval multi-nivel
3. Promotion pipeline de conocimiento
4. Setup enterprise interactivo
5. Gobernanza y CI enterprise
6. Observabilidad, adopcion y hardening

El orden es importante.  
Primero hay que modelar bien la topologia, despues permitir consumo, luego automatizar la promocion, y recien despues empaquetar todo en una experiencia de setup enterprise para clientes.

---

## 7. Etapa 1: Fundaciones de modelo organizacional

### Objetivo

Introducir en Cortex una configuracion organizacional formal que represente la topologia de memoria de la empresa.

### Resultado esperado

Cortex debe poder saber, de manera nativa:

- cual es el vault local del proyecto
- cual es el vault corporativo
- cual es la politica de memoria episodica
- que namespaces se usan
- que clases de documentos son promovibles
- que flujos de promocion estan habilitados

### Entregables

1. Nuevo archivo de configuracion organizacional, por ejemplo:
   - `.cortex/org.yaml`
2. Nuevo modelo tipado en codigo:
   - `cortex/enterprise/config.py`
3. Carga y validacion de esa config desde CLI y runtime
4. Defaults razonables para empresa chica y empresa mediana

### Contenido sugerido de `org.yaml`

- `organization.name`
- `memory.mode`
- `memory.enterprise_vault_path`
- `memory.enterprise_semantic_enabled`
- `memory.enterprise_episodic_enabled`
- `memory.project_memory_mode`
- `memory.branch_isolation_enabled`
- `promotion.enabled`
- `promotion.allowed_doc_types`
- `promotion.require_review`
- `promotion.default_targets`
- `governance.git_policy`
- `governance.ci_profile`

### Archivos a tocar

- [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)
- [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- nuevo `cortex/enterprise/config.py`
- nuevo `cortex/enterprise/models.py`

### Impacto tecnico

- Bajo a medio
- No rompe la arquitectura central
- Agrega una nueva capa de configuracion formal

### Riesgos

- Diseñar una config demasiado compleja
- Mezclar configuracion de proyecto con configuracion de empresa

### Criterio de cierre

Un proyecto Cortex debe poder inicializarse con una topologia enterprise declarativa, sin depender de convenciones informales.

---

## 8. Etapa 2: Retrieval multi-nivel

### Objetivo

Permitir que Cortex consulte de forma nativa:

- memoria local de proyecto
- memoria corporativa
- o ambas a la vez

### Problema actual

Hoy `AgentMemory` trabaja con un `vault_path` principal y una memoria episodica principal.  
Eso sirve muy bien para proyecto, pero no para consumo enterprise productizado.

### Resultado esperado

Una consulta deberia poder ejecutarse en alguno de estos modos:

- `local`
- `enterprise`
- `hybrid-local-enterprise`

### Entregables

1. Nuevo servicio, por ejemplo:
   - `cortex/enterprise/retrieval_service.py`
2. Soporte multi-vault en lectura
3. Soporte de multiples fuentes episodicas
4. Filtro y weighting entre fuentes
5. Nuevas opciones CLI:
   - `cortex search --scope local`
   - `cortex search --scope enterprise`
   - `cortex search --scope all`

### Posibles decisiones tecnicas

#### Opcion recomendada

Mantener `AgentMemory` como fachada de proyecto y crear una capa superior enterprise que componga varios readers y stores.

Esto evita sobrecargar la clase central con demasiada logica.

#### Opcion no recomendada

Intentar convertir `AgentMemory` en una mega fachada universal con todos los casos.

Eso complicaria demasiado el core.

### Archivos a tocar

- [cortex/core.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/core.py)
- [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py)
- [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py)
- [cortex/episodic/memory_store.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/episodic/memory_store.py)
- nuevo `cortex/enterprise/retrieval_service.py`
- nuevo `cortex/enterprise/sources.py`

### Impacto tecnico

- Medio
- Es el primer cambio realmente estructural de producto

### Riesgos

- Confusion entre resultados locales y corporativos
- Ranking desbalanceado entre fuentes
- Sobre-recuperacion y ruido contextual

### Mitigacion

- Agregar metadata de origen visible
- Configurar pesos por scope
- Permitir filtros y top-k por fuente

### Criterio de cierre

El agente puede recuperar contexto relevante desde memoria local y corporativa en una sola operacion, con trazabilidad clara de origen.

---

## 9. Etapa 3: Promotion pipeline de conocimiento

### Objetivo

Crear el mecanismo oficial por el cual conocimiento local se convierte en conocimiento corporativo.

### Problema actual

Hoy el sistema sabe guardar y buscar, pero no tiene una politica nativa de "promocion" entre niveles de memoria.

### Resultado esperado

Cortex debe poder decir:

- este documento queda local
- este documento es promovible
- este documento debe revisarse
- este documento ya fue promovido a memoria corporativa

### Entregables

1. Nuevo servicio:
   - `cortex/enterprise/knowledge_promotion.py`
2. Nuevos comandos CLI:
   - `cortex promote-knowledge`
   - `cortex review-knowledge`
   - `cortex sync-enterprise-vault`
3. Metadata de promotion status
4. Mecanismo de copiado, transformacion o referencia hacia vault corporativo
5. Politica para tipos documentales promovibles

### Tipos de documentos recomendados para promocion

- specs maduras
- decisiones de arquitectura
- runbooks estables
- incidentes relevantes
- HU importadas que representen conocimiento de negocio reusable

### Tipos que no deberian promocionarse automaticamente

- sesiones crudas
- notas temporales
- resuenes de PR sin curacion
- artefactos de troubleshooting local muy ruidosos

### Archivos a tocar

- nuevo `cortex/enterprise/knowledge_promotion.py`
- nuevo `cortex/enterprise/promotion_models.py`
- [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [cortex/doc_validator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doc_validator.py)
- [cortex/doc_verifier.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doc_verifier.py)

### Impacto tecnico

- Medio
- Mucho valor funcional sin tocar demasiado el corazon vectorial

### Riesgos

- Promocion excesiva de ruido
- Duplicacion de documentos
- Falta de criterio empresarial para aceptar contenido

### Mitigacion

- Promotion rules declarativas
- Review humana opcional u obligatoria
- Marcado de origen y fecha de promocion

### Criterio de cierre

Existe un pipeline oficial y auditable de promocion de conocimiento desde proyecto hacia empresa.

---

## 10. Etapa 4: Setup enterprise interactivo

### Objetivo

Convertir toda esta complejidad en una experiencia de instalacion guiada y automatizable.

### Resultado esperado

Un cliente deberia poder ejecutar algo parecido a:

```bash
cortex setup enterprise
```

y Cortex deberia preguntarle de forma interactiva:

- cuantos proyectos tiene
- si quiere vault corporativo compartido
- si quiere memoria episodica modular o compartida
- si quiere branch isolation
- que politicas Git quiere
- que runbooks y workflows quiere generar
- que tipo de organizacion quiere montar

### Entregables

1. Nuevo modo de setup:
   - `SetupMode.ENTERPRISE`
2. Nuevo wizard interactivo:
   - `cortex/setup/enterprise_wizard.py`
3. Nuevos templates:
   - `org.yaml`
   - estructura de vault corporativo
   - runbooks enterprise
   - workflows de promotion
4. Soporte no interactivo para automatizacion:
   - `cortex setup enterprise --preset small-company`
   - `cortex setup enterprise --org-config company.yaml`

### Preguntas que deberia hacer el wizard

#### Perfil organizacional

- cuantas unidades o proyectos principales existen
- si hay un equipo central de arquitectura
- si habra curacion manual del conocimiento

#### Memoria

- vault corporativo compartido o no
- memoria episodica por proyecto o compartida
- aislamiento por rama o no
- promotion automatica o con review

#### Gobernanza

- politica de versionado de `vault/sessions/`
- politica de docs obligatorias
- enforcement en CI o modo observability

#### Integracion

- GitHub Actions
- IDEs objetivo
- WebGraph federado inicial

### Archivos a tocar

- [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)
- [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- nuevo `cortex/setup/enterprise_wizard.py`
- nuevo `cortex/setup/enterprise_presets.py`

### Impacto tecnico

- Medio
- Mucho valor comercial y de implantacion

### Riesgos

- Wizard demasiado largo o confuso
- demasiadas combinaciones de setup

### Mitigacion

- ofrecer presets
- ofrecer modo avanzado y modo simplificado
- generar resumen final antes de escribir archivos

### Criterio de cierre

Una empresa puede desplegar Cortex con una topologia enterprise usable sin depender de consultoria manual repo por repo.

---

## 11. Etapa 5: Gobernanza y CI enterprise

### Objetivo

Automatizar la gobernanza de la memoria corporativa y su mantenimiento desde CI.

### Resultado esperado

La empresa debe poder elegir entre:

- modo observability
- modo advisory
- modo enforced

para promotion, validacion y sincronizacion de conocimiento.

### Entregables

1. Workflows enterprise nuevos o extendidos
2. Job de promotion review
3. Validacion de docs corporativas
4. Sincronizacion controlada del vault corporativo
5. Reportes de salud de memoria

### Posibles comandos nuevos

- `cortex doctor --scope enterprise`
- `cortex validate-docs --scope enterprise`
- `cortex promote-knowledge --ci`
- `cortex memory-report`

### Archivos a tocar

- [cortex/doctor.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doctor.py)
- [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- `.github/workflows/`

### Impacto tecnico

- Bajo a medio
- Mucha mejora operativa

### Riesgos

- CI demasiado verboso
- flujos de promotion que bloqueen productividad si se configuran mal

### Mitigacion

- perfiles de enforcement configurables
- dry-runs y reportes antes de bloquear

### Criterio de cierre

La memoria enterprise queda gobernada automaticamente por CI con politicas configurables.

---

## 12. Etapa 6: Observabilidad, adopcion y hardening

### Objetivo

Cerrar la productizacion con capacidades de diagnostico, reporte y adopcion organizacional.

### Resultado esperado

Cortex debe permitir ver:

- que memoria existe
- de donde viene
- que fue promovido
- que proyectos estan conectados
- que gaps de documentacion o curacion existen

### Entregables

1. Reportes de memory health
2. Dashboard o exportes para WebGraph federado enriquecido
3. Documentacion operativa enterprise
4. Playbooks de adopcion por rol
5. Telemetria local o reportes offline de uso

### Archivos a tocar

- [cortex/webgraph/federation.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/webgraph/federation.py)
- [cortex/webgraph/service.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/webgraph/service.py)
- nuevo `cortex/enterprise/reporting.py`
- docs de ops en `docs/ops/`

### Impacto tecnico

- Bajo a medio
- Alto valor de adopcion y madurez

### Criterio de cierre

La empresa no solo usa Cortex, sino que puede observar y gobernar la salud de su memoria.

---

## 13. Orden recomendado de implementacion

El orden recomendado es el siguiente:

1. Etapa 1: Fundaciones de modelo organizacional
2. Etapa 2: Retrieval multi-nivel
3. Etapa 3: Promotion pipeline
4. Etapa 5: Gobernanza y CI enterprise
5. Etapa 4: Setup enterprise interactivo
6. Etapa 6: Observabilidad y hardening

### Por que este orden

- Sin modelo organizacional, todo lo demas queda ambiguo.
- Sin retrieval multi-nivel, no existe consumo enterprise real.
- Sin promotion pipeline, no existe memoria institucional formal.
- Sin gobernanza, el setup enterprise generaria topologias sin control.
- El wizard conviene construirlo cuando la topologia, los flujos y la gobernanza ya esten claros.

---

## 14. Alcance tecnico: cuanto codigo habria que modificar

Esto no parece una reescritura grande, pero tampoco es un simple ajuste de config.

### Magnitud estimada

- **Cambio bajo** en el corazon de embeddings y storage
- **Cambio medio** en runtime, CLI, retrieval y setup
- **Cambio alto** en producto operativo, templates, configuracion enterprise y experience layer

### Modulos existentes con mayor impacto

- [cortex/core.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/core.py)
- [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py)
- [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)
- [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py)
- [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py)
- [cortex/doctor.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doctor.py)

### Modulos nuevos probables

- `cortex/enterprise/config.py`
- `cortex/enterprise/models.py`
- `cortex/enterprise/retrieval_service.py`
- `cortex/enterprise/sources.py`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/reporting.py`
- `cortex/setup/enterprise_wizard.py`
- `cortex/setup/enterprise_presets.py`

### Estimacion de esfuerzo relativa

- Etapa 1: media
- Etapa 2: media/alta
- Etapa 3: media
- Etapa 4: media
- Etapa 5: media
- Etapa 6: baja/media

---

## 15. Recomendacion de arquitectura de producto

La recomendacion mas sana es **no forzar todo dentro de `AgentMemory`**.

### Recomendacion

Mantener:

- `AgentMemory` como fachada principal de proyecto
- una nueva capa `enterprise` por encima, compuesta por servicios especializados

### Beneficios

- menos riesgo de romper consumidores actuales
- mejor separacion de responsabilidades
- mas claridad para evolucionar el producto enterprise sin ensuciar el core

### Antipatron a evitar

Convertir el core actual en una mega clase universal con switches para todos los modos organizacionales.

---

## 16. Presets de producto recomendados

Para que el setup enterprise sea vendible y usable, conviene ofrecer presets.

### Preset 1: Small Company

- vault corporativo compartido
- memoria episodica por proyecto
- promotion con review ligera
- CI en modo advisory

### Preset 2: Multi-Project Team

- vault corporativo compartido
- vault local por proyecto
- WebGraph federado
- promotion formal por tipo de documento
- branch isolation opcional

### Preset 3: Regulated Organization

- vault corporativo obligatorio
- promotion con aprobacion
- politicas fuertes de docs
- CI enforced
- reportes de memory governance

---

## 17. Riesgos globales del programa

1. Querer resolver todo con una sola memoria fisica.
   Eso mezclaria ruido, sesion y conocimiento durable.
2. Subestimar la gobernanza documental.
   Sin promotion rules, la memoria corporativa se contamina rapido.
3. Hacer el setup demasiado complejo.
   Un buen producto enterprise necesita presets y opinionated defaults.
4. Intentar imponer una topologia unica a todos los clientes.
   Cortex debe soportar varias madureces organizacionales.

---

## 18. Criterios de exito

La iniciativa puede considerarse exitosa cuando:

1. Cortex puede operar con memoria local y memoria corporativa de forma nativa.
2. Existe un pipeline oficial de promocion de conocimiento.
3. Una empresa puede instalar la topologia enterprise con setup guiado.
4. El CI puede gobernar docs, promotion y salud de memoria.
5. Los agentes pueden generar SPECs usando contexto local y empresarial en la misma recuperacion.
6. La solucion es suficientemente opinionated para clientes pequenos, pero extensible para organizaciones mas maduras.

---

## 19. Recomendacion final

La mejor forma de encararlo no es como una feature aislada, sino como un mini-programa de productizacion con dos macro bloques:

### Bloque A: habilitacion tecnica

- modelo organizacional
- retrieval multi-nivel
- promotion pipeline
- gobernanza enterprise

### Bloque B: productizacion de implantacion

- wizard interactivo
- presets
- templates
- workflows
- runbooks
- observabilidad

Si Cortex quiere que la memoria empresarial deje de ser una capacidad "posible" y pase a ser una capacidad "vendible, instalable y repetible", esta iniciativa es el camino correcto.

---

## 20. Proxima bajada recomendada

El siguiente documento que convendria producir despues de este plan es uno mas ejecutivo y operativo:

- backlog por etapa
- historias tecnicas
- dependencias entre modulos
- criterio de versionado
- secuencia de releases

Ese seria el paso natural previo a empezar a implementar.
