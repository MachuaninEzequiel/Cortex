# Avance de Alineacion: Multi-Proyecto, WebGraph y Gobernanza Operativa

## Documento

- Fecha: 2026-04-26
- Proyecto: Cortex
- Alcance: cierre de brechas entre el plan original de implementacion multi-proyecto y el estado real del codigo, mas consolidacion operativa y de gobernanza
- Tipo de avance: alineacion funcional, tecnica, operativa y conceptual

---

## Resumen ejecutivo

En esta iteracion no se construyo una "feature aislada". Lo que se hizo fue algo mas importante para la salud del producto: se tomo el plan original de Cortex para las fases multi-proyecto, se lo comparo con la documentacion de avance y con el codigo real del repositorio, y a partir de ahi se cerraron las inconsistencias que habian quedado abiertas.

En otras palabras:

- Se verifico que partes de las fases previas estaban realmente implementadas.
- Se detecto que cosas estaban prometidas en el plan pero no terminadas del todo en el codigo.
- Se completo lo que faltaba.
- Se ordeno la capa de operacion y gobernanza para que Cortex no solo "tenga funciones", sino que tambien pueda usarse de forma clara, controlada y repetible en un entorno real.

El resultado es que Cortex ahora queda en un estado mucho mas coherente:

- El comportamiento multi-proyecto es mas consistente.
- El aislamiento de memoria por proyecto y rama queda mejor cerrado.
- WebGraph federado queda mas alineado con la idea original del workspace analitico.
- La capa de gobernanza deja de ser solo "intencion documentada" y pasa a estar reflejada en comandos, validaciones, workflows y politicas de Git.

Este trabajo deja listo el proyecto para avanzar a una nueva fase posterior, ya no como "fase 4" original, sino como una siguiente etapa construida sobre una base mas solida.

---

## Objetivo de este trabajo

El objetivo principal de esta iteracion fue llevar a Cortex desde un estado de "implementacion avanzada pero parcialmente desalineada" a un estado de "base coherente, cerrada y preparada para seguir creciendo".

Eso implico trabajar sobre cuatro preguntas:

1. Que partes de las fases 1, 2 y 3 estaban realmente implementadas.
2. Que partes habian quedado a medio camino entre plan, documentacion y codigo.
3. Que cambios habia que hacer para que el sistema real coincida mejor con lo prometido.
4. Como dejar a Cortex mejor preparado para operar en equipos, repositorios y contextos empresariales.

---

## Problema detectado antes de estos cambios

Antes de esta iteracion, Cortex ya tenia mucho trabajo hecho, pero habia una diferencia importante entre tres capas:

- El plan de implementacion.
- La documentacion de lo ya desarrollado.
- El comportamiento real del codigo.

La consecuencia de esa desalineacion era sutil pero importante:

- Algunas capacidades existian, pero no estaban completas.
- Algunas politicas estaban declaradas, pero no codificadas.
- Algunas recomendaciones aparecian en la documentacion, pero no se veian reflejadas en la practica del repositorio.
- Algunas piezas funcionaban bien por separado, pero no estaban unificadas bajo una experiencia operativa clara.

Esto no significaba que Cortex estuviera "mal", sino que estaba en un punto muy comun en productos tecnicos que evolucionan rapido: el core habia avanzado mas rapido que la capa de cierre, consistencia y gobernanza.

---

## Que se hizo, en terminos simples

### Para una persona no tecnica

Se ordeno el sistema para que:

- recuerde mejor en que proyecto y rama esta trabajando,
- pueda mostrar mejor varios proyectos juntos,
- tenga reglas mas claras sobre que informacion debe quedar en Git y cual debe quedar local,
- pueda revisar automaticamente si su configuracion y su documentacion estan bien,
- y quede mejor explicado para los equipos que lo usan.

### Para una persona tecnica

Se tocaron cuatro areas:

- contexto de ejecucion y metadata de memoria,
- WebGraph y workspace federado,
- CLI de operacion y validacion,
- gobernanza documental, Git y CI.

---

## Vista general de las areas modificadas

Las modificaciones se agrupan en estos bloques:

1. Aislamiento fuerte y metadata de memoria.
2. Cierre de brechas de WebGraph federado multi-proyecto.
3. Operacion y gobernanza mediante `doctor`, validacion de docs y politica Git/Vault.
4. Ajuste de setup, templates, workflows y README para reflejar el comportamiento real.
5. Tests puntuales para evitar regresiones en lo recien alineado.

---

## Detalle completo por area

## 1. Contexto de ejecucion y metadata de memoria

### Finalidad

La finalidad de este bloque fue cerrar una brecha muy importante de la fase 2: la memoria de Cortex ya estaba orientada a trabajar por proyecto y por rama, pero no todos los caminos de escritura guardaban la misma informacion contextual, y no todos los caminos de lectura permitian el control esperado.

En sistemas de memoria para agentes, guardar el contenido no alcanza. Tambien hay que guardar contexto:

- de que proyecto era esa memoria,
- de que rama provenia,
- y de que repositorio venia.

Sin eso, la memoria puede ser util, pero no confiable a escala.

### Archivos modificados

- `cortex/runtime_context.py`
- `cortex/core.py`
- `cortex/services/session_service.py`
- `cortex/services/spec_service.py`
- `cortex/services/pr_service.py`
- `cortex/workitems/service.py`

### Que se cambio en cada archivo

#### `cortex/runtime_context.py`

Se mejoro la capa que detecta el contexto Git del proyecto.

Antes:

- Detectaba la rama actual.
- Resolvia el `persist_dir` namespaced segun `namespace_mode`.

Ahora:

- Sigue detectando la rama.
- Ademas detecta el path real del repositorio Git (`repo root`).
- Centraliza mejor la ejecucion de comandos Git internos.

### Por que se hizo asi

Se hizo asi para que la logica de contexto no quede repartida en varias partes del sistema. Si Cortex necesita saber "que rama soy" o "que repo soy", eso debe salir de una unica fuente coherente.

### Que mejora aporta

- Reduce duplicacion.
- Mejora trazabilidad.
- Permite que la metadata de memoria sea mas confiable.

#### `cortex/core.py`

Este archivo es la fachada principal de memoria de Cortex.

Se hicieron varios cambios clave:

- Se agrego `git_repo` al contexto runtime.
- Se centralizo `self._runtime_metadata` con:
  - `project_id`
  - `branch`
  - `repo`
- `remember()` ahora acepta `extra_metadata`.
- `store_memory()` tambien acepta `extra_metadata`.
- `retrieve()` ahora soporta `cross_branch`.
- Se propaga la metadata de runtime a los servicios que generan memorias.

### Por que se hizo asi

Porque la fachada principal es el mejor lugar para definir el contrato operativo de memoria.

Antes habia una parte de la metadata que se inyectaba desde `remember()`, pero no todos los servicios secundarios tenian esa misma garantia.

Ahora la idea es:

- toda memoria creada por Cortex debe nacer con contexto consistente,
- y ese contexto no debe depender de que cada servicio lo recuerde manualmente.

### Que mejora aporta

- Cohesion.
- Menos riesgo de memorias huerfanas o ambiguas.
- Mejor filtrado posterior.
- Mejor auditabilidad.

#### `cortex/services/session_service.py`
#### `cortex/services/spec_service.py`
#### `cortex/services/pr_service.py`
#### `cortex/workitems/service.py`

En estos servicios se agrego el uso de `context_metadata`.

Antes:

- Estos servicios generaban memorias utiles.
- Pero no necesariamente inyectaban toda la metadata de runtime de forma uniforme.

Ahora:

- Las memorias generadas desde sesiones, specs, PRs y work items heredan el contexto del proyecto activo.

### Por que se hizo asi

Porque no tiene sentido que solo algunas memorias sepan de que proyecto o rama son y otras no.

Si Cortex quiere comportarse como memoria gobernada, la metadata no puede ser opcional en la practica.

### Que mejora aporta

- Uniformidad de datos.
- Mejor consistencia interna.
- Mejor base para futuros filtros, reportes y analitica.

---

## 2. Cierre de brechas de WebGraph federado multi-proyecto

### Finalidad

La finalidad de este bloque fue completar la parte de la fase 3 que ya estaba avanzada pero no completamente cerrada.

El objetivo del WebGraph federado era permitir una vista transversal de varios proyectos. Esa idea ya existia, pero faltaban piezas para que se parezca mas al modelo de workspace analitico planeado.

### Archivos modificados

- `cortex/webgraph/semantic_source.py`
- `cortex/webgraph/episodic_source.py`
- `cortex/webgraph/service.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/cli.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/templates/index.html`
- `cortex/webgraph/static/style.css`
- `cortex/webgraph/static/app.js`

### Que se cambio en cada archivo

#### `cortex/webgraph/semantic_source.py`

Se agrego soporte para `vault_path` explicito.

Antes:

- El origen semantico resolvia el vault principalmente desde `config.yaml`.

Ahora:

- Puede recibir un vault explicito desde afuera.

### Por que se hizo asi

Porque en un workspace federado no siempre alcanza con asumir que cada proyecto usa exactamente el vault por defecto.

### Que mejora aporta

- Mas flexibilidad.
- Mejor alineacion con el formato analitico multi-proyecto.

#### `cortex/webgraph/episodic_source.py`

Se agrego soporte para `persist_dir` explicito.

Antes:

- El origen episodico resolvia el store desde el proyecto y su config.

Ahora:

- Puede trabajar con una ruta de memoria provista externamente.

### Por que se hizo asi

Por la misma razon que el vault: en modo federado hay que poder describir un proyecto con mayor precision.

### Que mejora aporta

- Soporte mas realista para workspaces heterogeneos.

#### `cortex/webgraph/service.py`

Se hicieron dos cambios de fondo:

- soporte para `vault_path` y `persist_dir` explicitos,
- inyeccion de `project_id` en metadata de nodos del snapshot.

### Por que se hizo asi

Porque la federacion no solo necesita combinar nodos; necesita que cada nodo conserve identidad de origen.

### Que mejora aporta

- Facilita filtros posteriores.
- Hace mas explicable el grafo.
- Reduce ambiguedad cuando se mezclan proyectos.

#### `cortex/webgraph/federation.py`

Este fue uno de los archivos mas importantes del cierre.

Se agrego:

- soporte para `vault` y `memory` dentro de `workspace.yaml`,
- helpers para resolver el workspace por defecto,
- helper para escribir el workspace,
- soporte para registrar proyectos en `.cortex/webgraph/workspace.yaml`.

Antes:

- El workspace federado existia.
- Pero era mas minimo y menos expresivo que lo planteado en el plan.

Ahora:

- El workspace puede describir mejor a cada proyecto.
- Se acerca mas al concepto de "workspace analitico" planeado originalmente.

### Por que se hizo asi

Porque la federacion multi-proyecto no es solo "varios roots". Tambien es la posibilidad de describir de forma clara de donde sale el conocimiento de cada proyecto.

### Que mejora aporta

- Mas compatibilidad con escenarios reales.
- Mejor definicion de origen.
- Menos suposiciones ocultas.

#### `cortex/webgraph/cli.py`

Se mejoro la resolucion de `workspace-file`.

Antes:

- Si no pasabas el archivo, la federacion no intentaba apoyarse en un workspace por defecto del proyecto.

Ahora:

- Cortex puede usar `.cortex/webgraph/workspace.yaml` cuando existe.
- Se alinea mejor con el concepto de modo analista federado persistente.

### Por que se hizo asi

Para reducir friccion de uso.

Un sistema federado de analisis gana mucho valor cuando el usuario no tiene que declarar todo una y otra vez.

#### `cortex/webgraph/setup.py`

Se agrego `attach_project_root()`.

Esto permite:

- instalar WebGraph,
- y ademas registrar un proyecto inicial dentro del workspace por defecto.

### Por que se hizo asi

Porque el plan original hablaba de un setup mejorado y de un modo analista mas usable. Esta funcion convierte esa idea en un paso concreto.

#### `cortex/webgraph/templates/index.html`
#### `cortex/webgraph/static/style.css`
#### `cortex/webgraph/static/app.js`

Aqui se completo la brecha mas visible de UI.

Antes:

- La UI cargaba snapshots y permitia buscar, navegar, abrir nodos y cargar subgrafos.
- Pero no tenia los filtros analiticos planeados de forma clara.

Ahora:

- Tiene filtro por proyecto.
- Tiene filtro por tipo de nodo.
- Tiene filtro por ventana temporal.
- Refleja visualmente mejor si la vista es completa o filtrada.

### Por que se hizo asi

Porque el plan no pensaba WebGraph solo como "un canvas con nodos", sino como una herramienta analitica util para una persona que mira varios proyectos, varios artefactos y distintos momentos del tiempo.

### Que mejora aporta

- Menos ruido visual.
- Mejor lectura del grafo.
- Mejor experiencia de analisis.
- Mayor alineacion con la finalidad de fase 3.

---

## 3. Gobernanza operativa y validacion del entorno

### Finalidad

Este bloque convierte a Cortex en un sistema mas operable.

Hasta antes de esta iteracion, habia reglas, recomendaciones y buenas practicas. Lo que faltaba era una capa unificada que dijera:

- si el entorno esta bien,
- si la estructura del proyecto esta sana,
- si la documentacion del vault es valida,
- y si la politica de Git esta alineada con el modelo de Cortex.

### Archivos creados

- `cortex/doctor.py`
- `cortex/git_policy.py`

### Archivos modificados

- `cortex/cli/main.py`

### Que se cambio

#### `cortex/doctor.py`

Se creo un doctor global del sistema.

Este comando valida:

- root del proyecto,
- `config.yaml`,
- estructura de `vault/`,
- store episodico real,
- workspace Cortex,
- guidelines del agente,
- estado Git,
- branch actual,
- presencia de patrones recomendados en `.gitignore`,
- dependencias opcionales de WebGraph,
- estado de validacion del vault Markdown.

### Por que se hizo asi

Porque antes existia `webgraph doctor`, pero no un `doctor` global que integrara la salud operativa general del proyecto Cortex.

Era una brecha importante del plan original de operacion enterprise.

### Que mejora aporta

- Diagnostico rapido.
- Menos soporte manual.
- Menor ambiguedad.
- Mejor experiencia de onboarding.

#### `cortex/git_policy.py`

Se creo una capa explicita de politica Git/Vault.

Define:

- que directorios del vault se consideran conocimiento durable,
- que patrones deben ser locales,
- y cual es el snippet recomendado de `.gitignore`.

### Por que se hizo asi

Porque habia una inconsistencia entre narrativa y realidad.

La documentacion hablaba de un comportamiento, pero el repositorio no tenia una representacion formal de esa politica. Sin una politica codificada, la gobernanza queda sujeta a interpretaciones.

### Que mejora aporta

- Hace explicita la intencion del sistema.
- Permite que `doctor` valide la politica.
- Evita drift futuro entre docs, setup y repo.

#### `cortex/cli/main.py`

Se agregaron dos comandos importantes:

- `cortex doctor`
- `cortex validate-docs`

Ademas:

- `remember` ahora acepta metadata explicita como `--branch`, `--repo`, `--commit`
- `search` ahora acepta `--cross-branch`

### Por que se hizo asi

Porque la CLI es la interfaz publica del sistema. Si la gobernanza y los controles no estan expuestos ahi, quedan escondidos en el codigo y pierden impacto operativo.

### Que mejora aporta

- Hace visible la capacidad de control.
- Facilita automatizacion.
- Facilita CI.
- Facilita soporte humano.

---

## 4. Politica Git/Vault y el cambio en `.gitignore`

### Archivos modificados

- `.gitignore`
- `README.md`
- `docs/ops/Cortex-Git-Vault-Policy.md`
- `docs/ops/Cortex-Enterprise-Runbook.md`
- `cortex/setup/templates.py`
- `cortex/setup/orchestrator.py`

### Que cambio en `.gitignore`

Se agrego:

- `.memory/`
- `*.chroma/`
- `vault/sessions/`

### Por que se agrego `.memory/`

`.memory/` contiene el estado local de persistencia de Cortex, especialmente el almacenamiento episodico.

Esto no es conocimiento durable del equipo en el sentido tradicional. Es estado operativo local.

Si ese estado se sube a Git:

- se generan conflictos innecesarios,
- se mezclan estados de distintos desarrolladores,
- se vuelve fragil la reproducibilidad,
- y se contamina el repositorio con datos que no son fuente de verdad compartida.

### Cual era la finalidad

Separar claramente:

- conocimiento durable versionable,
- de estado local de ejecucion.

### Que mejora aporta

- Menos ruido en Git.
- Menos conflictos.
- Menos riesgo de corrupcion de stores locales.
- Mejor limpieza conceptual del sistema.

### Por que se agrego `*.chroma/`

Chroma es parte del almacenamiento vectorial/persistente de la memoria.

Aunque algunos stores se ubiquen bajo `.memory/`, agregar este patron amplia la proteccion para evitar que artefactos persistentes relacionados a Chroma entren por accidente al control de versiones.

### Cual era la finalidad

Blindar el repositorio contra la subida involuntaria de datos persistentes de memoria.

### Que mejora aporta

- Mayor seguridad operativa.
- Menor posibilidad de "filtrar estado local" a Git.

### Por que se agrego `vault/sessions/`

Este punto es importante conceptualmente.

No significa que las sesiones "no importan". Significa que se diferencio entre:

- conocimiento estructural y durable,
- e historial operativo de alta rotacion.

`vault/sessions/` es muy valioso como memoria, pero en muchos equipos genera demasiado churn para Git:

- muchos archivos,
- muchos cambios pequenos,
- alta frecuencia,
- bajo valor como artefacto de revision de codigo en comparacion con specs, ADRs o runbooks.

### Cual era la finalidad

Definir una politica por defecto mas sana para equipos reales:

- specs, decisiones y runbooks se revisan como conocimiento durable,
- sesiones quedan locales salvo que el equipo explicite otra politica.

### Que mejora aporta

- Menos ruido en PRs.
- Menos friccion con repositorios cliente.
- Mejor separacion entre "historial operativo" y "conocimiento institucional".

### Importante

Este cambio no dice que las sesiones valgan menos. Dice que su rol cambia:

- siguen siendo importantes para Cortex,
- pero no necesariamente deben vivir en Git por defecto.

---

## 5. Setup, templates y experiencia de inicializacion

### Finalidad

El setup tenia que reflejar la politica nueva, no solo el codigo principal.

Si el sistema piensa una cosa y el setup genera otra, la deuda vuelve a aparecer enseguida.

### Archivos modificados

- `cortex/setup/templates.py`
- `cortex/setup/orchestrator.py`

### Que se cambio

#### `cortex/setup/templates.py`

Se actualizaron templates para:

- incluir referencias a `cortex doctor`,
- incluir `cortex validate-docs`,
- documentar mejor quick checks operativos,
- agregar contenido mas enterprise,
- mejorar la narrativa de operacion real.

Tambien se sumaron templates de:

- runbook corporativo,
- politica Git/Vault.

#### `cortex/setup/orchestrator.py`

Se actualizo para:

- crear estos documentos nuevos en el vault,
- y soportar `attach_project_root` para el setup de WebGraph.

### Por que se hizo asi

Porque el setup es donde la filosofia del producto se vuelve accion concreta.

Si la filosofia cambia pero el setup no, el producto sigue naciendo con defaults viejos.

### Que mejora aporta

- Mejor onboarding.
- Menos desviaciones de politica.
- Menos necesidad de explicacion manual.

---

## 6. Workflows CI y cierre del circuito operativo

### Archivos modificados

- `.github/workflows/ci-pull-request.yml`
- `cortex/setup/templates.py`

### Finalidad

La finalidad aqui fue hacer que la capa de CI exprese mejor el modelo Cortex:

- validar entorno,
- verificar docs,
- validar docs,
- y distinguir entre docs existentes y fallback generado.

### Que se cambio

En el workflow real del repositorio se agregaron o alinearon estos conceptos:

- `cortex doctor`
- `cortex verify-docs`
- `cortex validate-docs`
- indexacion de docs existentes cuando aplica
- fallback cuando no hay docs del agente

### Por que se hizo asi

Porque una gobernanza que solo vive en la cabeza del equipo no escala.

La CI es el lugar donde se vuelve verificable y repetible.

### Que mejora aporta

- Menor dependencia de memoria humana.
- Mayor disciplina del proceso.
- Menor probabilidad de merges con documentacion inconsistente.

---

## 7. Documentacion operativa agregada

### Archivos creados

- `docs/ops/Cortex-Enterprise-Runbook.md`
- `docs/ops/Cortex-Git-Vault-Policy.md`

### Finalidad

Explicar:

- como operar Cortex por rol,
- que va a Git y que no,
- y cual es el modelo operativo recomendado.

### Por que se hizo asi

Porque habia material tecnico disperso, pero faltaba una pieza clara de lectura operacional.

### Que mejora aporta

- Mejor entendimiento para perfiles no tecnicos o semitecnicos.
- Mejor consistencia de adopcion.

---

## 8. README y narrativa publica del proyecto

### Archivo modificado

- `README.md`

### Finalidad

Alinear la narrativa publica del repositorio con el comportamiento real del sistema.

### Que se cambio

- Se agregaron referencias a `cortex doctor`.
- Se agregaron referencias a `cortex validate-docs`.
- Se actualizo el bloque de configuracion avanzada con `namespace_mode` y `namespace_value`.
- Se aclaro la politica Git/Vault recomendada.
- Se corrigio la afirmacion anterior de que `vault/` estaba simplemente "gitignored".

### Por que se hizo asi

Porque cuando README y producto divergen, el README deja de ser documentacion y pasa a ser marketing desactualizado.

### Que mejora aporta

- Mayor honestidad tecnica.
- Mejor onboarding.
- Menor confusion.

---

## 9. Tests y verificacion agregada

### Archivos modificados

- `tests/unit/cli/test_main.py`
- `tests/unit/webgraph/test_federation.py`
- `tests/unit/webgraph/test_setup.py`

### Finalidad

Blindar las partes nuevas mas sensibles:

- doctor global,
- validacion de docs,
- workspace de WebGraph,
- attach de project root,
- soporte de rutas explicitas en workspace.

### Por que se hizo asi

Porque estas modificaciones no eran cosmeticas. Tocaban:

- contratos de CLI,
- comportamiento multi-proyecto,
- politica operativa.

Era importante dejar al menos pruebas focalizadas sobre el nuevo comportamiento.

### Verificacion realizada

Se ejecuto:

```bash
pytest tests/unit/cli/test_main.py tests/unit/webgraph/test_setup.py tests/unit/webgraph/test_federation.py tests/unit/test_runtime_context.py tests/unit/webgraph/test_service.py tests/unit/webgraph/test_webgraph_server.py
```

Resultado:

- verificacion focalizada exitosa
- 24 tests pasados

Ademas se corro:

```bash
python -m cortex.cli.main doctor --project-root .
```

Resultado:

- `doctor` paso correctamente sobre el propio repositorio

---

## Archivos tocados y motivo de cada grupo

## Nucleo de contexto y memoria

- `cortex/runtime_context.py`
  - Motivo: detectar mejor rama y repo real.
- `cortex/core.py`
  - Motivo: centralizar metadata runtime, permitir `cross_branch` y exponer mejor estos controles.
- `cortex/services/session_service.py`
  - Motivo: heredar metadata de runtime al guardar sesiones.
- `cortex/services/spec_service.py`
  - Motivo: heredar metadata de runtime al guardar specs.
- `cortex/services/pr_service.py`
  - Motivo: heredar metadata de runtime al guardar PR context.
- `cortex/workitems/service.py`
  - Motivo: heredar metadata de runtime al guardar work items importados.

## WebGraph y federacion

- `cortex/webgraph/semantic_source.py`
  - Motivo: soportar vault explicito por proyecto.
- `cortex/webgraph/episodic_source.py`
  - Motivo: soportar memoria explicita por proyecto.
- `cortex/webgraph/service.py`
  - Motivo: aceptar rutas explicitas e inyectar `project_id` en nodos.
- `cortex/webgraph/federation.py`
  - Motivo: enriquecer `workspace.yaml` y acercarlo al modelo planeado.
- `cortex/webgraph/cli.py`
  - Motivo: resolver mejor el workspace por defecto y reducir friccion de uso.
- `cortex/webgraph/setup.py`
  - Motivo: permitir registrar un proyecto inicial en el workspace de WebGraph.
- `cortex/webgraph/templates/index.html`
  - Motivo: agregar filtros operativos.
- `cortex/webgraph/static/style.css`
  - Motivo: soportar visualmente los nuevos controles.
- `cortex/webgraph/static/app.js`
  - Motivo: implementar filtros analiticos y estado de vista.

## Gobernanza y operacion

- `cortex/doctor.py`
  - Motivo: crear validacion global del estado Cortex.
- `cortex/git_policy.py`
  - Motivo: formalizar la politica Git/Vault.
- `cortex/cli/main.py`
  - Motivo: exponer `doctor`, `validate-docs` y flags utiles para metadata y busqueda.

## Setup, docs y workflows

- `cortex/setup/templates.py`
  - Motivo: alinear templates con la nueva filosofia operativa.
- `cortex/setup/orchestrator.py`
  - Motivo: generar nuevos documentos y soportar attach de proyecto a WebGraph.
- `.github/workflows/ci-pull-request.yml`
  - Motivo: llevar la gobernanza a la CI real del repo.
- `.gitignore`
  - Motivo: separar estado local de conocimiento durable.
- `README.md`
  - Motivo: alinear relato publico y realidad del producto.
- `docs/ops/Cortex-Enterprise-Runbook.md`
  - Motivo: documentacion operativa por rol.
- `docs/ops/Cortex-Git-Vault-Policy.md`
  - Motivo: documentacion clara de politica Git/Vault.

## Verificacion

- `tests/unit/cli/test_main.py`
  - Motivo: cubrir CLI nueva.
- `tests/unit/webgraph/test_federation.py`
  - Motivo: cubrir workspace federado enriquecido.
- `tests/unit/webgraph/test_setup.py`
  - Motivo: cubrir attach y setup WebGraph.

---

## Antes y despues: comparativa funcional

## Antes

- Cortex ya podia trabajar con WebGraph y con multiples proyectos, pero con un workspace mas basico.
- La memoria ya tenia ideas de aislamiento por proyecto/rama, pero no todos los caminos escribian metadata uniforme.
- Existia `webgraph doctor`, pero no existia un `doctor` global del sistema.
- Habia validacion de documentacion y verificacion de docs, pero no estaban consolidadas como capa operativa clara.
- README, setup, `.gitignore` y workflow real no reflejaban del todo la misma politica.

## Ahora

- WebGraph federado soporta mejor la descripcion de cada proyecto.
- La metadata de memoria se guarda de forma mas coherente.
- La busqueda puede hacer override cross-branch cuando se necesita.
- Existe `cortex doctor` como chequeo de salud integral.
- Existe `cortex validate-docs` como chequeo de integridad documental.
- La politica Git/Vault esta expresada en codigo, documentacion, setup y CI.
- La UI de WebGraph se acerca mas al rol de analista multi-proyecto del plan original.

---

## Antes y despues: comparativa conceptual

## Antes: filosofia dominante

Antes de estos cambios, Cortex estaba mas cerca de esta idea:

"Tenemos un motor potente, varias piezas avanzadas y una direccion correcta, pero parte de la disciplina operativa sigue viviendo en el criterio humano o en documentacion dispersa."

Eso implicaba que:

- el sistema era fuerte en capacidades,
- pero todavia no del todo fuerte en clausura operativa,
- habia reglas implicitas,
- y habia una pequena brecha entre "lo que Cortex quiere ser" y "lo que fuerza en la practica".

## Ahora: filosofia dominante

Despues de estos cambios, Cortex se mueve mas hacia esta idea:

"No alcanza con tener capacidades; el producto tambien debe codificar su propia disciplina."

Eso significa:

- el conocimiento durable y el estado local ya no se tratan igual,
- la gobernanza deja de ser solo una recomendacion y pasa a ser verificable,
- la operacion deja de depender tanto de recordar reglas manualmente,
- el sistema se explica mejor a si mismo,
- y la arquitectura queda mas preparada para crecer sin contradicciones.

---

## Antes y despues: como se conectaban las partes

## Antes

### Memoria

- La fachada principal conocia parte del contexto del proyecto.
- Algunos servicios escribian memorias validas, pero no todos heredaban el mismo contexto runtime.
- El resultado era una memoria util, pero menos homogenea de lo ideal.

### WebGraph

- Podia federar proyectos y renderizar el grafo.
- Pero el workspace era menos descriptivo y la UI tenia menos herramientas analiticas.

### Gobernanza

- Habia ideas de gobernanza en docs y templates.
- Pero no habia un unico comando que permitiera validar el estado general.

### Git

- La separacion entre conocimiento durable y estado local no estaba formalizada con suficiente claridad.

## Ahora

### Memoria

- El contexto runtime se detecta de forma mas completa.
- Ese contexto se propaga a varios servicios.
- El retrieval puede decidir si mantenerse dentro de la rama o abrirse a otras.

### WebGraph

- El workspace puede describir mejor a cada proyecto.
- Los nodos preservan mejor identidad de origen.
- La UI permite recortar el analisis por proyecto, tipo y tiempo.

### Gobernanza

- `doctor` y `validate-docs` convierten la salud operativa en algo verificable.
- La CI incorpora mejor ese circuito.

### Git

- Se hace explicita la idea central:
  - el conocimiento durable puede vivir en Git,
  - el estado local de memoria no debe vivir ahi,
  - el historial de sesiones tiene una politica por defecto diferenciada.

---

## Que problema de fondo se resolvio realmente

Mas alla de los archivos puntuales, lo que se resolvio de fondo fue esto:

Cortex antes estaba mas cerca de ser un sistema con muchas capacidades correctas.
Ahora esta mas cerca de ser un sistema coherente.

Y eso importa mucho, porque:

- un sistema con muchas features puede impresionar,
- pero un sistema coherente es el que sobrevive, escala y se puede mantener.

---

## Estado final en el que queda el proyecto

Despues de estas modificaciones, Cortex queda en un estado donde:

- la implementacion previa de multi-proyecto y WebGraph esta mejor cerrada,
- la capa de memoria tiene mejor trazabilidad contextual,
- la capa de gobernanza tiene comandos y politicas concretas,
- el setup y la documentacion ya reflejan mejor la realidad,
- y el proyecto queda listo para pasar a una nueva etapa posterior con menos deuda de alineacion.

---

## Cierre

Este trabajo no fue solo una correccion tecnica. Fue una consolidacion de identidad del producto.

Se tomo a Cortex y se lo llevo desde:

- "producto potente pero con zonas grises entre plan y realidad"

hacia:

- "producto mas consistente, mas explicable, mas gobernable y mejor preparado para evolucionar".

Ese es el valor real de esta iteracion.
