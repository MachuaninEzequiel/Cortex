# Plan Experto v2 de `cortex webgraph`

**Version del plan:** 2.0  
**Objetivo de producto:** `webgraph v1.5 robusta`  
**Fecha:** 2026-04-21  
**Estado:** propuesta lista para validacion previa al desarrollo

## 1. Redefinicion del producto

`cortex webgraph` ya no se define como un mapa del `vault/`.

Se define como una **proyeccion visual de la memoria hibrida de Cortex**.

La nueva motivacion es:

- visualizar la memoria de Cortex en su completitud;
- representar semanticamente el "cerebro" del sistema;
- unificar en una misma experiencia visual:
  - artefactos del vault;
  - memorias episodicas persistidas;
  - relaciones estructurales;
  - relaciones derivadas;
  - proximidades semanticas;
- permitir navegar, entender y abrir la documentacion real conectada a cada zona del conocimiento.

La idea de producto es clara:

**cada zona del grafo debe mostrar el trabajo real de Cortex, no solo sus archivos Markdown.**

---

## 2. Por que cambia el alcance

Si `webgraph` se limitara al `vault/`, quedaria demasiado cerca de lo que ya resuelve Obsidian:

- nodos;
- tags;
- backlinks;
- exploracion documental.

Eso puede ser util, pero no diferencia verdaderamente a Cortex.

En cambio, el verdadero valor de Cortex esta en su memoria hibrida:

- memoria semantica documental;
- memoria episodica persistida;
- embeddings compartidos;
- recuperacion fusionada.

Por eso, `webgraph` debe apuntar a visualizar el conocimiento operativo del sistema completo.

---

## 3. Estado real actual de Cortex

Hoy el codigo ya tiene las piezas, pero todavia no las expone como "cerebro" unificado.

### 3.1 Capa semantica

- vive en `cortex/semantic/vault_reader.py`;
- parsea documentos Markdown;
- extrae `links` y `tags`;
- calcula embeddings para documentos del vault.

### 3.2 Capa episodica

- vive en `cortex/episodic/memory_store.py`;
- persiste memorias en Chroma;
- calcula embeddings de recuerdos operativos;
- ya tiene una API publica util: `list_entries()`.

### 3.3 Capa de fusion

- vive en `cortex/retrieval/hybrid_search.py`;
- fusiona resultados de memoria semantica y episodica por RRF;
- produce una vista unificada de resultados, pero no una estructura persistida de grafo.

### 3.4 Implicancia clave

Hoy Cortex tiene **memoria hibrida**, pero no tiene todavia una **representacion grafica canonica de esa memoria**.

`webgraph` sera la capa que construya esa proyeccion.

---

## 4. Principio rector

La regla principal sigue siendo:

**mientras mas separado funcione `webgraph`, mejor.**

Pero ahora con una precision adicional:

**`webgraph` no debe convertirse en el centro de la memoria; debe ser una capa de proyeccion sobre contratos publicos ya existentes o minimos de agregar.**

Eso significa:

- no reescribir `core.py`;
- no meter logica de grafo en `AgentMemory`;
- no acoplar el sistema de agentes con el visualizador;
- no transformar Chroma o VaultReader en modulos de visualizacion;
- mantener a `webgraph` como consumidor de datos, no como dueño del estado principal.

---

## 5. Objetivo de la v1.5 robusta

La primera version publica robusta de `webgraph` debe permitir:

1. visualizar nodos semanticos y episodicos en un mismo grafo;
2. distinguir visualmente tipos de nodo y tipos de relacion;
3. seleccionar un nodo y entender que representa;
4. abrir la documentacion real asociada cuando exista;
5. navegar artefactos relacionados desde una spec hacia su sesion, recuerdos y documentos vinculados;
6. soportar filtros desde el inicio;
7. soportar snapshot cacheado desde el inicio;
8. soportar subgrafos desde el inicio;
9. nacer con contratos preparados para una futura `v2` de escalabilidad fuerte.

---

## 6. No objetivos de esta fase

Para sostener modularidad y evitar sobrediseño, esta fase no intentara:

- construir un motor de conocimiento nuevo dentro del core;
- reestructurar la persistencia de Chroma;
- convertir RRF en un grafo persistente dentro del retrieval;
- introducir GraphQL;
- introducir clustering automatico avanzado;
- introducir renderer WebGL desde el dia 1;
- hacer deducciones semanticamente perfectas sobre "mismo trabajo" si no hay evidencia suficiente.

La `v1.5` debe ser robusta, no maximalista.

---

## 7. Cambio conceptual mas importante

La unidad visual principal ya no sera "documento del vault".

La unidad visual principal sera una **entidad de memoria**.

Eso nos obliga a definir dos capas:

### 7.1 Capa de nodos base

Representa entidades reales existentes hoy:

- `semantic_doc`
- `episodic_memory`

### 7.2 Capa de nodos compuestos o vistas agregadas

Representa agrupaciones construidas por `webgraph`:

- `work_cluster`
- `spec_cluster`
- `topic_cluster`

La recomendacion para `v1.5` es:

- implementar primero nodos base reales;
- agregar una vista de agrupacion simple;
- no empezar con nodos compuestos como unica representacion canonica.

Esto evita inventar una ontologia que el codigo todavia no posee.

---

## 8. Modelo de producto recomendado

En `v1.5`, `webgraph` deberia mostrar un grafo mixto con:

- nodos de especificacion;
- nodos de documentacion de sesion;
- nodos de otros documentos semanticos;
- nodos de memoria episodica;
- relaciones entre ellos.

La UI puede dar la sensacion de "cerebro" sin falsear el modelo interno.

Ejemplo:

- una spec del vault;
- una session note que menciona esa spec;
- una memoria episodica tipo `spec`;
- una memoria episodica tipo `session`;
- documentos vecinos por wikilink;
- relaciones derivadas por coincidencia fuerte.

Eso ya construye una visualizacion mucho mas propia de Cortex que la de Obsidian.

---

## 9. Arquitectura general propuesta

## 9.1 Principio de arquitectura

`webgraph` debe construir un **grafo derivado** a partir de multiples fuentes.

No debe depender de una sola fuente documental.

## 9.2 Fuentes de datos del grafo

Se proponen tres adaptadores internos dentro de `webgraph`:

1. `semantic_source`
   - consume `VaultReader`;
   - expone documentos semanticos;
   - expone links estructurales.

2. `episodic_source`
   - consume `EpisodicMemoryStore`;
   - expone memorias episodicas;
   - expone metadata util como `memory_type`, `tags`, `files`, `timestamp`, `entities`.

3. `relation_source`
   - no persiste nada nuevo;
   - deriva relaciones entre semantico y episodico;
   - aplica heuristicas controladas.

---

## 10. Arbol del modulo

```text
cortex/webgraph/
|-- __init__.py
|-- contracts.py
|-- config.py
|-- semantic_source.py
|-- episodic_source.py
|-- relation_builder.py
|-- graph_builder.py
|-- cache.py
|-- service.py
|-- server.py
|-- openers.py
|-- setup.py
|-- templates/
|   `-- index.html
`-- static/
    |-- app.js
    `-- style.css
```

### Responsabilidad de cada pieza

- `contracts.py`
  - define nodos, aristas, snapshots, filtros, detalles y subgrafos.
- `config.py`
  - configuracion propia de `webgraph`.
- `semantic_source.py`
  - adaptador a documentos del vault.
- `episodic_source.py`
  - adaptador a memorias episodicas.
- `relation_builder.py`
  - correlaciones entre fuentes.
- `graph_builder.py`
  - ensamblado del grafo final.
- `cache.py`
  - snapshots persistentes y fingerprints.
- `service.py`
  - casos de uso: snapshot, filtros, detalle de nodo, subgrafo.
- `server.py`
  - API HTTP local.
- `openers.py`
  - apertura segura de archivos.

---

## 11. Contratos publicos requeridos del core

Este punto es crucial para sostener la modularidad maxima.

## 11.1 Lo que ya existe y sirve

`EpisodicMemoryStore.list_entries()` ya da una base publica util.

Eso evita tocar mas de la cuenta la capa episodica.

## 11.2 Lo que falta agregar

En `VaultReader` hace falta una API publica minima como:

```python
def iter_documents(self) -> Iterable[tuple[str, SemanticDocument]]:
    ...
```

No queremos que `webgraph` dependa de `_index`.

## 11.3 Lo que NO conviene hacer

No conviene meter una API tipo "build_webgraph()" dentro de `AgentMemory`.

Eso acoplaria demasiado el visualizador al nucleo.

`webgraph` debe ensamblar sus datos por fuera.

---

## 12. Tipos de nodo

Se proponen estos tipos de nodo para `v1.5`:

- `semantic_spec`
- `semantic_session`
- `semantic_doc`
- `episodic_spec`
- `episodic_session`
- `episodic_general`

Cada nodo debe tener:

- `id`
- `node_type`
- `label`
- `summary`
- `source`
- `rel_path` opcional
- `memory_id` opcional
- `tags`
- `files`
- `timestamp` opcional
- `degree`

### Regla importante

Un nodo no debe pretender ser "spec + session + embedding" al mismo tiempo si esa unificacion no existe de forma verificable.

La fusion visual debe surgir de relaciones, no de mezclar entidades a la fuerza.

---

## 13. Tipos de arista

Se proponen estos tipos iniciales:

- `wikilink`
- `same_file_reference`
- `same_title_family`
- `same_spec_reference`
- `shared_tag`
- `shared_entity`
- `semantic_neighbor`
- `derived_relation`

### Prioridad de interpretacion

No todas las aristas tienen el mismo peso explicativo.

Se recomienda esta jerarquia:

1. `wikilink`
2. `same_spec_reference`
3. `same_file_reference`
4. `shared_entity`
5. `shared_tag`
6. `semantic_neighbor`

Esto permite mostrar relaciones mas confiables primero.

---

## 14. Criterio de relacion entre memoria semantica y episodica

Este es el nucleo intelectual del nuevo plan.

`webgraph` necesita una forma de relacionar documentos del vault con recuerdos episodicos.

La recomendacion para `v1.5` es usar **heuristicas auditables y simples**, no magia negra.

### 14.1 Heuristicas permitidas

Una memoria episodica y un documento semantico pueden relacionarse si comparten alguno de estos indicadores fuertes:

- mismo archivo mencionado;
- mismo titulo o fragmento fuerte de titulo;
- referencia explicita de spec en una session;
- tags significativos en comun;
- entidades extraidas en comun;
- cercania temporal relevante;
- similitud semantica suficiente usando embeddings ya disponibles.

### 14.2 Heuristica estrella para Cortex

Hay una relacion especialmente valiosa ya sugerida por el codigo actual:

- una `spec` del vault;
- una `session` del vault que menciona la especificacion;
- una memoria episodica de tipo `spec`;
- una memoria episodica de tipo `session`.

Ese conjunto puede formar una constelacion muy significativa del mismo trabajo.

### 14.3 Regla de prudencia

Si la relacion no es explicable, no debe convertirse en una arista fuerte.

`webgraph` debe priorizar trazabilidad antes que espectacularidad.

---

## 15. Vista "cerebro Cortex"

La experiencia objetivo no es un canvas caotico de puntos.

La experiencia debe permitir entender:

- que artefactos existen;
- como se conectan;
- que parte del conocimiento pertenece a una misma pieza de trabajo;
- donde vive la documentacion real;
- como una decision o implementacion quedo registrada en ambas memorias.

### Interaccion recomendada

#### Click simple

- selecciona nodo;
- abre panel lateral;
- muestra tipo, origen, tags, fecha y resumen;
- lista relaciones relevantes;
- lista documentos o recuerdos asociados.

#### Doble click

- abre el archivo si el nodo tiene path real;
- si el nodo es episodico puro, muestra detalle ampliado o centra su vecindario.

#### Acciones del panel

- abrir documento;
- cargar subgrafo;
- resaltar relacionados;
- cambiar entre vista "documental", "episodica" y "hibrida".

---

## 16. Contrato estable de API

El contrato debe quedar listo desde `v1.5` para crecer sin romper.

## 16.1 Snapshot principal

`GET /api/snapshot`

Devuelve:

- metadata de version;
- fingerprint;
- estadisticas;
- nodos;
- aristas;
- capacidades.

## 16.2 Snapshot por modo

`GET /api/snapshot?mode=hybrid`
`GET /api/snapshot?mode=semantic`
`GET /api/snapshot?mode=episodic`

Esto es clave.

Permite que `webgraph` sirva:

- solo documental;
- solo episodico;
- mezcla completa.

### Beneficio

La modularidad no se rompe: el modulo puede funcionar incluso si una de las capas esta vacia o temporalmente deshabilitada.

## 16.3 Detalle de nodo

`GET /api/node/{node_id}`

Debe incluir:

- datos propios del nodo;
- lista de relaciones;
- nodos vecinos principales;
- posibilidad de apertura;
- evidencia de por que esta conectado con otros.

## 16.4 Subgrafo

`GET /api/subgraph?node_id=<id>&depth=1&edge_types=wikilink,same_spec_reference`

Este endpoint ya debe existir en `v1.5`.

## 16.5 Apertura

`POST /api/open`

Body:

```json
{
  "node_id": "semantic:vault/specs/auth.md"
}
```

El frontend nunca manda un path arbitrario.

---

## 17. Estrategia de construccion del grafo

La construccion del grafo deberia ocurrir en cuatro pasos.

### Paso 1. Extraer nodos semanticos

Desde `VaultReader`, obtener:

- specs;
- sessions;
- docs generales;
- tags;
- links;
- embeddings documentales disponibles.

### Paso 2. Extraer nodos episodicos

Desde `EpisodicMemoryStore`, obtener:

- memorias;
- `memory_type`;
- tags;
- archivos mencionados;
- metadata;
- timestamp;
- entidades extraidas.

### Paso 3. Construir relaciones explicables

Usando:

- wikilinks;
- referencias cruzadas;
- tags;
- archivos;
- entidades;
- tiempo;
- similitud semantica configurable.

### Paso 4. Ensamblar snapshot estable

Generar:

- nodos serializados;
- aristas serializadas;
- stats;
- indices auxiliares;
- cache persistente.

---

## 18. Cache y fingerprint

El cache sigue siendo obligatorio desde el inicio.

## 18.1 Ubicacion

```text
.cortex/webgraph/cache/
|-- snapshot-hybrid.json
|-- snapshot-semantic.json
|-- snapshot-episodic.json
|-- meta.json
`-- subgraphs/
```

## 18.2 Fingerprint minimo

Debe contemplar:

- estado del vault;
- estado de la memoria episodica;
- configuracion de `webgraph`.

### Vault

- paths;
- `mtime`;
- tamanio.

### Episodico

Como primera version pragmatica, puede usarse:

- `count()`;
- `cache_token` de `EpisodicMemoryStore`;
- opcionalmente timestamps extremos.

Eso es suficiente para invalidacion razonable sin meter cambios profundos.

---

## 19. Escalabilidad en este nuevo enfoque

La escalabilidad ahora es mas desafiante porque el grafo puede crecer por dos fuentes.

Por eso la `v1.5` robusta debe incluir desde el arranque:

- modos de vista;
- filtros;
- subgrafos;
- limites configurables;
- carga parcial por modo;
- panel lateral como centro de exploracion.

### Regla de oro

La vista hibrida completa debe existir, pero no siempre debe ser la vista inicial por defecto.

La UI puede:

- abrir en modo `semantic`;
- abrir en modo `hybrid` si el tamaño lo permite;
- sugerir subgrafo si el conjunto es demasiado grande.

---

## 20. Frontend recomendado para `v1.5`

Se mantiene la misma estrategia que en el plan anterior:

- HTML;
- CSS;
- JavaScript;
- `vis-network` como renderer inicial;
- sin `pyvis`.

Pero ahora el frontend debe ser mas expresivo.

### Funcionalidades obligatorias

- selector de modo: `semantic`, `episodic`, `hybrid`;
- leyenda de tipos de nodo;
- leyenda de tipos de arista;
- panel de detalle;
- buscador;
- filtros por tipo y tag;
- accion de abrir documento;
- accion de cargar subgrafo;
- explicacion de relaciones.

### Razon de esta decision

Como el producto ya no es solo documental, la legibilidad es tan importante como el render.

---

## 21. Cambios minimos permitidos fuera de `cortex/webgraph/`

La filosofia sigue siendo de minima invasion.

## 21.1 `pyproject.toml`

- agregar extra opcional `webgraph`.

## 21.2 `cortex/semantic/vault_reader.py`

- agregar `iter_documents()`.

## 21.3 `cortex/cli/main.py`

- agregar grupo `webgraph`;
- agregar `cortex webgraph serve`;
- agregar `cortex webgraph export`;
- agregar `cortex setup webgraph`.

## 21.4 `cortex/setup/orchestrator.py`

- agregar `SetupMode.WEBGRAPH`;
- agregar flujo de bootstrap del modulo.

## 21.5 Capa episodica

No deberia requerir cambios obligatorios adicionales si reutilizamos `list_entries()`, `count()` y `cache_token`.

---

## 22. Setup y CLI

## 22.1 Comandos

Se proponen:

- `cortex webgraph serve`
- `cortex webgraph export`

Opcional despues:

- `cortex webgraph doctor`

## 22.2 Setup

Se propone:

- `cortex setup webgraph`

### Regla importante

`cortex setup full` no debe instalar `webgraph` por defecto.

Como mucho:

- opt-in interactivo;
- o flag explicito.

---

## 23. Fases de implementacion recomendadas

## Fase A - Contratos y adaptadores

Objetivo:

- dejar definida la arquitectura hibrida.

Entregables:

- `contracts.py`
- `semantic_source.py`
- `episodic_source.py`
- `VaultReader.iter_documents()`

## Fase B - Correlacion y armado del grafo

Objetivo:

- convertir fuentes heterogeneas en un grafo coherente.

Entregables:

- `relation_builder.py`
- `graph_builder.py`
- tipos de arista
- tipos de nodo

## Fase C - Snapshot y cache

Objetivo:

- obtener salidas reutilizables, reproducibles y escalables.

Entregables:

- `cache.py`
- snapshots por modo
- fingerprints
- `export`

## Fase D - API y servidor

Objetivo:

- exponer el cerebro Cortex localmente sin acoplarlo al resto.

Entregables:

- `server.py`
- `/api/snapshot`
- `/api/node/<id>`
- `/api/subgraph`
- `/api/open`

## Fase E - Frontend v1.5 robusto

Objetivo:

- convertir el grafo en una herramienta de exploracion real.

Entregables:

- `index.html`
- `app.js`
- `style.css`
- panel de detalle
- selector de modo
- filtros
- apertura de documentos
- subgrafos

## Fase F - Integracion CLI y setup

Objetivo:

- volver utilizable el modulo sin invadir otros componentes.

Entregables:

- `cortex webgraph serve`
- `cortex webgraph export`
- `cortex setup webgraph`

## Fase G - Pruebas

Objetivo:

- garantizar que el modelo hibrido sea estable y explicable.

Entregables:

- tests de adaptadores;
- tests de correlacion;
- tests de snapshot;
- tests de subgrafo;
- tests de apertura segura;
- tests de CLI.

---

## 24. Plan de pruebas minimo

Debe cubrir al menos:

1. `VaultReader.iter_documents()` funciona sin exponer estado interno mutable.
2. `episodic_source` serializa bien memorias desde `list_entries()`.
3. `relation_builder` crea relaciones correctas por archivo, tag y referencia de spec.
4. los enlaces semanticos siguen funcionando por wikilink.
5. los snapshots por modo devuelven solo lo esperado.
6. `hybrid` mezcla ambas fuentes sin colapsar el contrato.
7. `subgraph()` devuelve vecindarios coherentes.
8. `open(node_id)` no abre nada fuera del vault.
9. si un nodo no tiene archivo real, la UI no intenta abrirlo.

---

## 25. Criterios de aceptacion

La `v1.5` podra considerarse exitosa si:

1. `webgraph` deja de ser solo un grafo documental.
2. visualiza memoria semantica y episodica en una experiencia comun.
3. permite abrir documentacion real asociada.
4. permite navegar relaciones entre spec, session y memorias relacionadas.
5. mantiene cache, filtros y subgrafos desde el inicio.
6. conserva un aislamiento fuerte respecto del resto del sistema.
7. deja lista la base para una `v2` con mayor escala y mejor renderer.

---

## 26. Camino limpio hacia la futura v2 del producto

Si este plan se implementa bien, la `v2` podra crecer en estas direcciones:

- renderer WebGL;
- clustering automatico;
- comunidades;
- mejores relaciones semanticas entre nodos;
- vistas agregadas tipo "work cluster";
- exploracion explicable de constelaciones de memoria;
- overlays por embeddings y proximidad.

Lo importante es que ese crecimiento deberia ocurrir:

- sobre el contrato ya definido;
- dentro de `cortex/webgraph/`;
- sin romper el core.

---

## 27. Decision final recomendada

La recomendacion experta definitiva es esta:

`cortex webgraph` debe construirse como un **visualizador de memoria hibrida**, no como un simple mapa del vault.

Debe nacer ya como `v1.5 robusta`, con:

- modos `semantic`, `episodic` y `hybrid`;
- nodos explicables;
- relaciones auditables;
- apertura de documentacion real;
- snapshot cacheado;
- filtros;
- subgrafos;
- minima invasion del resto del repositorio.

En resumen:

**el producto correcto no es "el mapa de los Markdown", sino "el cerebro visible de Cortex".**
