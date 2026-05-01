# SPEC-REFAC-WEBGRAPH
**Fecha:** 2026-05-01  
**Estado:** Propuesta de implementacion por fases  
**Prioridad:** Alta  
**Complejidad estimada:** Media-Alta  
**Riesgo global:** Medio  
**Dependencia estructural:** Debe alinearse con `REFAC-WORKSPACE-STRUCT.md`

## 0. Resumen Ejecutivo
Este documento redefine el plan de mejora de Cortex WebGraph para que deje de ser una lista de ideas UX y pase a ser una especificacion ejecutable.

La conclusion principal del analisis del repo es esta:

1. El bug mas importante no es visual.  
   Es un problema de **contrato entre frontend y backend**.

2. La mejora UX no debe arrancar por el look & feel.  
   Debe arrancar por:
   - contrato JSON uniforme
   - manejo robusto de errores
   - diagnostico claro del servidor

3. Varias mejoras UX del plan original ya existen parcialmente en el codigo actual.  
   Por eso este plan debe enfocarse en:
   - endurecer la base operativa
   - completar lo que hoy esta incompleto
   - refinar el comportamiento visual sin reescribir de cero

4. WebGraph forma parte del layout estructural de Cortex.  
   Su config, workspace y cache deben quedar alineados con el nuevo modelo:

- `cortex/.system/webgraph/config.yaml`
- `cortex/.system/webgraph/workspace.yaml`
- `cortex/.system/webgraph/cache/`

---

## 1. Problema Actual
El plan original detecta correctamente dos familias de problemas:

1. **Errores de carga y apertura**
2. **Ruido visual y falta de foco analitico**

Sin embargo, el codigo actual muestra que el problema critico debe modelarse con mas precision.

### 1.1 El error `Unexpected token '<'`
El error observado:

```text
Failed to open node: Unexpected token '<', "<!doctype "... is not valid JSON
```

no debe describirse solo como "endpoint defectuoso" o "backend devuelve HTML".  
En este repo, el problema probable es mas especifico:

- el frontend intenta hacer `response.json()` de forma optimista
- si el backend devuelve una pagina HTML de error de Flask o una excepcion no manejada, el parseo rompe
- el usuario termina viendo un error de parseo, no el error real de negocio

### 1.2 Backend actual
`cortex/webgraph/server.py` hoy:

- define endpoints `/api/snapshot`, `/api/node/<id>`, `/api/subgraph` y `/api/open`
- exige header `X-Cortex-WebGraph`
- no tiene una capa completa de normalizacion JSON de errores para todo `/api/*`

Ademas:

- `node_detail()` delega directamente a `service.get_node_detail(...)`
- si el nodo no existe puede emerger una `KeyError`
- el test actual incluso asume propagacion de excepciones para ese caso

### 1.3 Frontend actual
`cortex/webgraph/static/app.js` hoy:

- usa `fetch(...)`
- valida `response.ok` en algunos flujos
- pero en `openNode()` hace `await response.json()` antes de validar el resultado
- maneja errores de forma no uniforme

Esto significa que el problema central no es solo "endpoint equivocado", sino **falta de contrato resiliente extremo a extremo**.

---

## 2. Hallazgos Quirurgicos del Repo

## 2.1 Archivos principales
El comportamiento actual de WebGraph vive principalmente en:

- `cortex/webgraph/server.py`
- `cortex/webgraph/cli.py`
- `cortex/webgraph/service.py`
- `cortex/webgraph/semantic_source.py`
- `cortex/webgraph/episodic_source.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/config.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/cache.py`
- `cortex/webgraph/static/app.js`
- `cortex/webgraph/static/style.css`
- `cortex/webgraph/templates/index.html`

Y hoy estan cubiertos por tests como:

- `tests/unit/webgraph/test_webgraph_server.py`
- `tests/unit/webgraph/test_service.py`
- `tests/unit/webgraph/test_federation.py`
- `tests/unit/webgraph/test_setup.py`
- `tests/unit/webgraph/test_webgraph_openers.py`

## 2.2 Mejoras UX que ya existen parcialmente
El plan original planteaba varias mejoras como si no existieran. En el codigo actual ya hay bases parciales:

- `hover: true`
- `tooltipDelay`
- diferenciacion de aristas por `dashes`
- ajuste basico de fisica con `barnesHut`
- etiquetas de `semantic_neighbor` ocultas
- panel lateral de detalle
- filtros por proyecto, tipo y ventana temporal

Por eso, la implementacion correcta no es "crear WebGraph UX desde cero", sino **refinar y endurecer una base ya existente**.

## 2.3 Dependencia con el layout estructural
WebGraph hoy sigue escribiendo y leyendo su infraestructura desde `.cortex/webgraph/...`.  
Este plan debe quedar alineado con el refactor estructural general:

- `config.yaml` de WebGraph
- `workspace.yaml` de federacion
- cache de snapshots

deben migrarse a `.system/webgraph/`.

---

## 3. Objetivos del Refactor
La implementacion correcta de WebGraph debe lograr:

1. Eliminar el error de parseo JSON/HTML en la apertura y carga.
2. Garantizar contrato JSON uniforme en toda la API `/api/*`.
3. Hacer resiliente el frontend ante respuestas invalidas o errores del servidor.
4. Reducir ruido visual en datasets medianos y grandes.
5. Dar foco analitico claro al seleccionar un nodo.
6. Mejorar legibilidad de labels y aristas sin esconder informacion critica.
7. Ajustar la fisica para evitar apelotonamiento y dispersion inutil.
8. Alinear la infraestructura de WebGraph con el nuevo layout `cortex/.system/webgraph/`.
9. Dejar tests y smoke tests suficientes para que el modulo sea confiable.

---

## 4. No Objetivos
Este plan no busca:

- cambiar el modelo conceptual de nodos y relaciones de Cortex
- reemplazar la libreria de grafo en esta iteracion
- rediseñar todo el frontend de Cortex
- eliminar el modo federado
- resolver en este documento toda la estrategia enterprise

---

## 5. Principios de Implementacion
La implementacion debe seguir este orden conceptual:

1. **Contrato antes que estetica**  
   Primero se asegura estabilidad de API y errores.

2. **Backend y frontend deben fallar de forma explicable**  
   Nunca se debe mostrar un error tecnico crudo si puede expresarse mejor.

3. **La visualizacion debe usar progressive disclosure**  
   La informacion detallada debe aparecer cuando el usuario la necesita, no toda al mismo tiempo.

4. **Los grandes datasets deben ser legibles sin destruir contexto**  
   Hay que equilibrar foco local y lectura global.

5. **WebGraph debe obedecer el nuevo contrato de workspace**  
   No debe seguir siendo un subsistema estructuralmente independiente.

---

## 6. Semaforo Global por Fases

### `Rojo`
No hay fases rojas puras en complejidad, pero si hay un gate fuerte entre contrato API y UX.  
No se debe empezar el tuning visual serio hasta cerrar las fases 0 y 1.

### `Amarillo`
- Fase 0: diagnostico y reproduccion precisa
- Fase 1: contrato JSON uniforme
- Fase 4: foco interactivo
- Fase 5: fisica y densidad
- Fase 6: alineacion estructural con workspace

### `Verde`
- Fase 2: resiliencia frontend
- Fase 3: reduccion de ruido visual
- Fase 7: tests y smoke tests finales

---

## 7. Plan de Implementacion por Fases

## Fase 0 - Diagnostico Reproducible del Error
**Semaforo:** Amarillo  
**Objetivo:** transformar el bug observado en casos concretos y reproducibles.

### Alcance
- identificar exactamente que endpoint y que flujo produce HTML o excepcion no manejada
- distinguir:
  - error de ruta
  - error de negocio
  - error de parseo del frontend
  - error de excepcion backend

### Archivos impactados en analisis
- `cortex/webgraph/server.py`
- `cortex/webgraph/static/app.js`
- `tests/unit/webgraph/test_webgraph_server.py`

### Casos que deben reproducirse
1. carga de snapshot
2. detalle de nodo valido
3. detalle de nodo inexistente
4. apertura de nodo valido
5. apertura de nodo sin path local
6. carga de subgrafo

### Riesgos
- corregir solo el sintoma observado en `openNode()` y dejar otros endpoints vulnerables
- asumir que el bug es solo 404 cuando puede ser una excepcion de servicio

### Gate de salida
- existe una matriz clara de fallas por endpoint
- el equipo sabe exactamente donde se produce la respuesta no JSON

### Rollback
- no aplica; es una fase de cierre diagnostico

---

## Fase 1 - Contrato JSON Uniforme en la API
**Semaforo:** Amarillo  
**Objetivo:** asegurar que toda ruta `/api/*` devuelva JSON consistente tanto en exito como en error.

### Alcance
- normalizar errores HTTP y errores Python
- evitar paginas HTML de Flask para clientes WebGraph
- unificar payload de error

### Archivos impactados
- `cortex/webgraph/server.py`
- `tests/unit/webgraph/test_webgraph_server.py`

### Requisitos de contrato
Todos los endpoints `/api/*` deben devolver:

```json
{
  "error": {
    "code": "node_not_found",
    "message": "Selected node does not exist",
    "details": {}
  }
}
```

o un formato equivalente estable y documentado.

### Casos minimos a cubrir
- `400` por input invalido
- `403` por header faltante
- `404` por nodo inexistente o path ausente
- `422` si corresponde a validacion de argumentos
- `500` para excepciones no controladas

### Recomendaciones de implementacion
- agregar manejo central para errores de API en `server.py`
- detectar `request.path.startswith("/api/")`
- devolver `jsonify(...)` tambien en fallas
- capturar errores de dominio frecuentes:
  - `KeyError`
  - `ValueError`
  - `FileNotFoundError`

### Riesgos
- cambiar el contrato sin actualizar tests
- devolver errores JSON solo en algunas rutas
- mezclar formatos de error entre endpoints

### Gate de salida
- ningun endpoint `/api/*` devuelve HTML ante fallo
- el frontend puede asumir un contrato de error estable

### Rollback
- mantener solo un wrapper de compatibilidad de error si algun caso limite falla, pero nunca volver a HTML para API

---

## Fase 2 - Resiliencia del Frontend ante Errores
**Semaforo:** Verde  
**Objetivo:** hacer que el frontend trate la red y el parseo como operaciones no confiables.

### Alcance
- reemplazar parseo optimista por un helper comun
- mejorar mensajes al usuario
- impedir que un error de una accion rompa toda la app

### Archivos impactados
- `cortex/webgraph/static/app.js`

### Requisitos
1. Ningun flujo debe hacer `response.json()` ciegamente sin validar:
   - `response.ok`
   - `content-type`
   - fallback a texto si el payload no es JSON

2. Debe existir una rutina unica para fetch API, por ejemplo:
   - parsear JSON si corresponde
   - recuperar mensaje de error del payload
   - si no hay JSON, usar fragmento de texto
   - lanzar error de dominio entendible

3. El usuario debe ver toasts claros como:
   - "No se pudo cargar el grafo"
   - "El nodo seleccionado ya no existe"
   - "No se pudo abrir el documento"
   - "No se pudo comunicar con el servidor local"

### Riesgos
- tratar mejor el error pero seguir ocultando demasiada informacion de diagnostico
- duplicar logica de manejo en varios puntos

### Gate de salida
- snapshot, node detail, open y subgraph comparten la misma estrategia de manejo de error
- el bug `Unexpected token '<'` deja de ser visible para el usuario

### Rollback
- no volver al parseo optimista; si algo falla, conservar helper central y ajustar el mensaje

---

## Fase 3 - Reduccion de Ruido Visual
**Semaforo:** Verde  
**Objetivo:** hacer legible el grafo sin perder informacion.

### Alcance
- labels de nodos
- labels de aristas
- truncado
- zoom semantico

### Archivos impactados
- `cortex/webgraph/static/app.js`
- `cortex/webgraph/static/style.css`
- `cortex/webgraph/templates/index.html`

### Estado actual
Hoy ya existe:

- tooltip de nodos
- labels completos por defecto
- edge labels parcialmente ocultos para `semantic_neighbor`

### Mejoras exactas esperadas
1. **Zoom semantico**
   - labels visibles solo por encima de un umbral de zoom razonable
   - por debajo del umbral, se prioriza densidad visual limpia

2. **Truncado inteligente**
   - labels largos truncados visualmente
   - nombre completo disponible via tooltip o panel lateral

3. **Aristas con menor ruido**
   - labels de relaciones ocultos por defecto
   - tipos distinguidos por estilo visual:
     - color
     - dashed/solid
     - grosor

4. **No esconder el significado**
   - si una arista no muestra texto por defecto, debe seguir siendo interpretable por color/estilo/tooltip

### Riesgos
- sobre-ocultar hasta volver el grafo cripto
- truncar demasiado y hacer dificil encontrar nodos

### Gate de salida
- dataset mediano legible sin solapamiento textual fuerte
- la informacion detallada sigue disponible por hover o seleccion

### Rollback
- relajar umbral de zoom o truncado, pero mantener la idea de disclosure progresivo

---

## Fase 4 - Foco Interactivo y Contexto
**Semaforo:** Amarillo  
**Objetivo:** guiar la atencion del usuario cuando selecciona un nodo.

### Alcance
- resaltado de nodo
- vecinos de primer grado
- atenuacion del resto del grafo
- persistencia de seleccion al aplicar filtros o subgrafos

### Archivos impactados
- `cortex/webgraph/static/app.js`
- `cortex/webgraph/static/style.css`

### Mejoras exactas esperadas
1. Al seleccionar un nodo:
   - el nodo seleccionado queda a maxima prominencia
   - vecinos directos se mantienen visibles
   - el resto del grafo se atenúa de forma clara pero no desaparece

2. La seleccion no debe perderse innecesariamente cuando:
   - se recarga snapshot
   - cambian filtros compatibles
   - se vuelve desde subgraph a root snapshot

3. El panel lateral debe reforzar el foco:
   - tipo de nodo
   - proyecto
   - path
   - resumen
   - relaciones
   - vecinos

### Riesgos
- volver demasiado tenue el contexto general
- producir estados inconsistentes entre lo seleccionado en canvas y lo mostrado en sidebar

### Gate de salida
- seleccionar un nodo hace evidente "que mirar" y "que esta conectado"

### Rollback
- si la atenuacion total resulta agresiva, bajar intensidad pero no abandonar el foco interactivo

---

## Fase 5 - Fisica, Colision y Densidad
**Semaforo:** Amarillo  
**Objetivo:** mejorar el acomodo visual del grafo para datasets reales.

### Alcance
- parametros de fisica
- colision
- estabilizacion
- comportamiento en grafos grandes

### Archivos impactados
- `cortex/webgraph/static/app.js`

### Estado actual
Hoy ya existe:

- `barnesHut`
- `stabilization`
- desactivacion de fisica en grafos grandes

### Mejoras exactas esperadas
1. Reducir apelotonamiento del centro.
2. Evitar dispersion excesiva de componentes desconectados.
3. Ajustar heuristica de "grafo grande" para no desactivar demasiado pronto o demasiado tarde.
4. Balancear:
   - tiempo de estabilizacion
   - legibilidad final
   - sensibilidad al drag/manual navigation

### Riesgos
- empeorar la performance
- mejorar la separacion pero volver inestable la experiencia de navegacion

### Gate de salida
- grafos chicos y medianos se estabilizan bien
- grafos grandes no colapsan visualmente ni quedan inutilmente dispersos

### Rollback
- preservar configuracion anterior como fallback parametrico mientras se ajusta la nueva

---

## Fase 6 - Alineacion Estructural con el Nuevo Workspace
**Semaforo:** Amarillo  
**Objetivo:** mover la infraestructura de WebGraph al nuevo contrato de layout.

### Alcance
- config de WebGraph
- workspace federado
- cache
- setup
- doctor
- CLI

### Archivos impactados
- `cortex/webgraph/config.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/cache.py`
- `cortex/webgraph/cli.py`
- `cortex/setup/orchestrator.py`
- `cortex/doctor.py`

### Nuevo layout esperado

```text
cortex/
  .system/
    webgraph/
      config.yaml
      workspace.yaml
      cache/
```

### Requisitos
1. `WebGraphConfig.default_path()` debe resolver a `cortex/.system/webgraph/config.yaml`.
2. `default_workspace_file()` debe resolver a `cortex/.system/webgraph/workspace.yaml`.
3. el cache debe vivir bajo `cortex/.system/webgraph/cache/`.
4. `setup webgraph` debe escribir solo en el layout nuevo.
5. `webgraph doctor` debe diagnosticar rutas nuevas.
6. durante la transicion, la lectura legacy debe poder seguir funcionando.

### Riesgos
- dejar el backend funcional pero escribir snapshots o cache en rutas viejas
- romper modo federado por workspace file mal resuelto

### Gate de salida
- WebGraph funciona dentro del contrato estructural nuevo y puede leer layout legacy temporalmente

### Rollback
- mantener discovery legacy de `workspace.yaml` y `config.yaml` mientras dure la compatibilidad global

---

## Fase 7 - Leyenda, Affordances y Terminacion UX
**Semaforo:** Verde  
**Objetivo:** completar la capacidad de lectura del grafo para un usuario nuevo.

### Alcance
- leyenda fija
- explicacion visual de tipos de nodos
- explicacion visual de relaciones
- pulido del panel y toolbar

### Archivos impactados
- `cortex/webgraph/templates/index.html`
- `cortex/webgraph/static/style.css`
- `cortex/webgraph/static/app.js`

### Mejoras exactas esperadas
1. Leyenda fija y discreta.
2. Correspondencia clara entre:
   - tipo de nodo
   - color
   - forma
3. Correspondencia clara entre:
   - tipo de arista
   - color
   - dashed/solid
4. UI entendible sin abrir el codigo ni depender de filtros para comprender lo basico.

### Riesgos
- agregar demasiada UI y volver pesado el canvas

### Gate de salida
- un usuario nuevo entiende el grafo en pocos segundos

### Rollback
- si la leyenda estorba, hacerla colapsable, no eliminarla

---

## Fase 8 - Tests y Smoke Tests Finales
**Semaforo:** Verde  
**Objetivo:** dejar WebGraph verificable y estable.

### Tests backend esperados
- snapshot OK
- snapshot error
- node detail OK
- node detail missing
- open OK
- open missing node
- open node without local path
- subgraph OK
- error payload JSON uniforme
- header de seguridad

### Tests frontend minimos esperados
Si no se incorporan tests browser completos, al menos dejar smoke manual formalizado:

1. Cargar snapshot.
2. Cambiar modo.
3. Filtrar por tipo/proyecto.
4. Buscar nodo.
5. Seleccionar nodo.
6. Abrir nodo.
7. Cargar subgraph.
8. Forzar error de servidor y validar toast correcto.

### Tests de estructura
- config path nuevo
- workspace path nuevo
- cache dir nuevo
- compatibilidad legacy durante transicion

### Gate de salida
- WebGraph backend devuelve errores predecibles
- WebGraph frontend no muestra parse errors crudos
- modo federado sigue funcionando
- layout nuevo queda alineado con el refactor general

### Rollback
- si una mejora UX es inestable, preservar contrato API y resiliencia como minimo innegociable

---

## 8. Cambios Exactos Esperados por Archivo / Area

## 8.1 `cortex/webgraph/server.py`
### Debe quedar responsable de
- contrato API consistente
- respuestas JSON en exito y error
- separacion clara entre error de input, error de negocio y error inesperado

### Cambios esperados
- capa central de manejo de errores para `/api/*`
- normalizacion de payloads
- mensajes mas utiles para el frontend

---

## 8.2 `cortex/webgraph/static/app.js`
### Debe quedar responsable de
- fetch resiliente
- progressive disclosure visual
- foco interactivo
- UX clara ante error

### Cambios esperados
- helper unico para llamadas API
- `response.json()` solo cuando corresponde
- truncado y zoom semantico
- atenuacion de contexto
- leyenda y affordances
- fisica ajustada

---

## 8.3 `cortex/webgraph/templates/index.html`
### Debe quedar responsable de
- estructura estable del canvas, toolbar, sidebar y leyenda

### Cambios esperados
- espacio para leyenda fija
- mejor semantica visual del layout
- no sobrecargar el canvas panel

---

## 8.4 `cortex/webgraph/static/style.css`
### Debe quedar responsable de
- legibilidad del shell UI
- jerarquia visual clara
- soporte de elementos auxiliares como toasts y leyenda

### Cambios esperados
- estilos para leyenda
- refinamiento del panel de detalle
- refinamiento de estados vacios, errores y acciones

---

## 8.5 `cortex/webgraph/config.py`, `federation.py`, `setup.py`, `cache.py`, `cli.py`
### Deben quedar responsables de
- obedecer el nuevo contrato de workspace
- no depender de `.cortex/webgraph/`

### Cambios esperados
- paths nuevos
- compatibilidad legacy temporal
- doctor alineado
- setup alineado

---

## 9. Matriz de Riesgos

| Riesgo | Severidad | Probabilidad | Mitigacion |
|---|---|---:|---|
| Corregir solo `openNode()` y dejar otros parseos fragiles | Alta | Alta | helper unico de fetch API |
| El backend sigue devolviendo HTML de error | Alta | Media | manejo central JSON para `/api/*` |
| Mejorar UX sin cerrar contrato API | Alta | Media | no avanzar a fases 3-5 sin cerrar 0-1 |
| Ocultar demasiada informacion visual | Media | Media | usar tooltip/sidebar como disclosure |
| Afinar fisica y degradar performance | Media | Media | ajuste incremental y smoke tests con varios tamanos |
| Romper modo federado al mover `workspace.yaml` | Media | Media | alinear con layout resolver y mantener fallback legacy |
| Mantener tests anclados a comportamiento viejo | Media | Alta | actualizar test server y test setup en la misma iteracion |

---

## 10. Matriz de Validacion Minima
Antes de considerar completo el refactor de WebGraph deben validarse al menos estos casos:

1. `cortex webgraph doctor --project-root .` funciona en layout nuevo.
2. `cortex webgraph serve --project-root .` funciona en layout nuevo.
3. `cortex webgraph export --project-root .` funciona en layout nuevo.
4. El backend devuelve JSON en todos los errores de API.
5. El frontend no muestra `Unexpected token '<'` ni errores crudos equivalentes.
6. El usuario puede abrir un documento valido.
7. El usuario recibe mensaje claro si el nodo no existe.
8. El usuario recibe mensaje claro si el nodo no tiene documento local.
9. El grafo es legible con datasets chicos.
10. El grafo es razonablemente legible con datasets medianos.
11. El modo federado sigue funcionando.
12. La infraestructura de WebGraph se escribe en `.system/webgraph/`.

---

## 11. Orden Recomendado respecto al Refactor de Workspace
WebGraph no debe implementarse aisladamente del cambio estructural.  
El orden correcto es:

1. cerrar fases 0, 1 y 2 de `REFAC-WORKSPACE-STRUCT.md`
2. ejecutar Fase 0 y Fase 1 de este plan WebGraph
3. continuar con runtime estructural
4. alinear WebGraph con `.system/webgraph/`
5. despues hacer el tuning UX/UI final

Esto evita rehacer dos veces rutas, config y setup.

---

## 12. Recomendacion Final
WebGraph no necesita un rediseño heroico. Necesita una secuencia disciplinada:

1. contrato JSON estable
2. frontend resiliente
3. alineacion estructural
4. pulido UX/UI

Si se respeta ese orden, el riesgo baja mucho y las mejoras visuales pasan a apoyarse sobre una base confiable.

---

## 13. Checklist de Cierre
- [ ] El error `Unexpected token '<'` deja de ser visible para el usuario.
- [ ] Toda la API `/api/*` devuelve JSON estable.
- [ ] El frontend maneja errores con helper unico y mensajes claros.
- [ ] Los labels del grafo usan disclosure progresivo.
- [ ] El foco interactivo esta implementado.
- [ ] La fisica del grafo esta ajustada para datasets reales.
- [ ] Existe leyenda visual fija o equivalente claro.
- [ ] WebGraph usa `cortex/.system/webgraph/`.
- [ ] El modo federado sigue funcionando.
- [ ] Los tests backend estan alineados.
- [ ] Los smoke tests manuales estan definidos y pasan.
