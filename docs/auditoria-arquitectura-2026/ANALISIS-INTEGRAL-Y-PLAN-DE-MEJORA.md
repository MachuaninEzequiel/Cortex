# Auditoría integral de Cortex y plan de mejora Pi-first

**Fecha de corte:** 2026-08-05  
**Repositorio analizado:** Cortex  
**Rama observada:** `master`  
**Commit observado:** `a64e350`  
**Estado del documento:** diagnóstico arquitectónico y propuesta; no implica que las mejoras estén implementadas  
**Superficie prioritaria:** Pi Coding Agent como CLI y experiencia principal recomendada de Cortex

---

## 1. Propósito

Este documento registra una auditoría técnica profunda del repositorio Cortex y convierte sus hallazgos en un plan de mejora accionable.

Los objetivos son:

1. Explicar qué es Cortex actualmente y cómo se relacionan sus subsistemas.
2. Identificar fortalezas que conviene preservar.
3. Identificar defectos, inconsistencias, deuda y riesgos operacionales.
4. Responder si Cortex puede reducirse, qué código parece no utilizarse y si una migración a Rust tiene sentido.
5. Definir una arquitectura objetivo y una secuencia de mejora verificable.
6. Dar prioridad explícita a Pi, porque es la interfaz principal recomendada por el creador de Cortex y la integración que más evolucionó.
7. Evitar que el mantenimiento simultáneo de demasiados IDEs vuelva a dispersar el esfuerzo.

Este análisis no propone eliminar capacidades valiosas por el solo hecho de reducir líneas. La meta es que Cortex tenga menos fuentes de verdad, contratos más precisos, operaciones seguras y una experiencia principal confiable.

---

## 2. Decisión de producto que condiciona el plan

### 2.1 Pi es la superficie principal

Pi debe tratarse como el cliente de referencia de Cortex.

Esto significa que:

- Todo flujo nuevo debe validarse primero end-to-end en Pi.
- Los contratos entre prompts Pi, extensiones Pi, herramientas MCP, CLI Cortex y modelos Python deben probarse automáticamente.
- El empaquetado publicado debe garantizar que `cortex inject --ide pi` funciona fuera del checkout del repositorio.
- Setup, actualización, diagnóstico y desinstalación de Pi deben considerarse operaciones de producto, no utilidades auxiliares.
- La experiencia documentada en `docs/guides/ide-pi.md` debe coincidir exactamente con el bundle distribuido.
- La compatibilidad con otros IDEs no debe bloquear la corrección o simplificación de Pi.

### 2.2 El resto de los IDEs entra en modo de portafolio controlado

Mantener muchas integraciones con el mismo nivel de ambición aumenta de forma multiplicativa:

- Los prompts duplicados.
- Los formatos de configuración.
- Las variantes de tool calling.
- Las diferencias de lifecycle y subagentes.
- Los tests end-to-end necesarios.
- El riesgo de documentación desactualizada.

Por lo tanto, hasta decidir qué clientes conservar, se recomienda clasificar los adaptadores en tres niveles:

| Nivel | Significado | Política recomendada |
|---|---|---|
| Reference | Pi | Desarrollo activo, E2E obligatorio, documentación completa y soporte de todos los contratos |
| Supported | Uno o dos IDEs futuros a seleccionar | Correcciones críticas y compatibilidad explícita; no paridad automática con Pi |
| Experimental/Frozen | Resto de los adaptadores actuales | Sin features nuevas; sólo seguridad o roturas graves hasta tomar una decisión de portafolio |

La selección futura debería basarse en adopción, calidad de APIs, capacidad real de MCP/subagentes, costo de mantenimiento y valor estratégico. No debería basarse únicamente en que el adaptador ya existe.

### 2.3 Marco para decidir qué otros IDEs conservar

Pi no necesita competir en esta evaluación: ya fue definido como reference client. Para seleccionar como máximo uno o dos clientes Supported adicionales, se propone puntuar cada adaptador sobre 100:

| Criterio | Peso orientativo | Pregunta |
|---|---:|---|
| Uso real y demanda | 25 | ¿Hay usuarios activos o una necesidad concreta del creador/comunidad? |
| Fidelidad MCP | 20 | ¿Preserva schemas, errores, lifecycle y tool calling sin bridges frágiles? |
| Soporte de agentes/workflow | 15 | ¿Puede representar sync, middle, checkpoints y documenter de forma natural? |
| Instalación segura | 15 | ¿Permite configuración project-local, merge, backup y uninstall conservador? |
| Testabilidad | 10 | ¿Puede automatizarse un E2E reproducible en CI? |
| Valor estratégico | 10 | ¿Aporta distribución, comunidad o capacidades que Pi no cubre? |
| Costo de mantenimiento | 5 | ¿Su API es estable y la adaptación pequeña? Una carga alta reduce el puntaje. |

Regla sugerida:

- `>= 75`: candidato Supported.
- `60–74`: experimental con reevaluación.
- `< 60`: congelar y preparar deprecación.
- Máximo dos Supported además de Pi durante el ciclo de consolidación.

Requisitos mínimos, independientemente del puntaje:

- MCP o integración estructurada equivalente.
- Configuración sin sobrescribir trabajo del usuario.
- Doctor e uninstall verificables.
- Un E2E de sync → Session → documenter.
- Responsable claro de mantenimiento.

Hasta completar esta evaluación, corregir en los demás adapters únicamente seguridad, pérdida de datos o incompatibilidades críticas. Las mejoras de UX y nuevas capacidades deben concentrarse en Pi.

---

## 3. Alcance y metodología

La auditoría cubrió:

- Estructura completa del repositorio y distribución de tamaño.
- Código Python de producción y tests.
- Entry points, CLI, MCP, servicios, modelos y persistencia.
- Session primitive y Documenter.
- Memoria episódica, semántica, embeddings, retrieval y cache vectorial.
- Canonical Documentation.
- Enterprise, CI, autopilot, WebGraph y workitems.
- Adaptadores de IDE, con revisión especialmente detallada de Pi.
- Bundle Pi: agentes, extensiones, settings, MCP bridge, cortex-net, justfile y documentación.
- Workflows de GitHub Actions, packaging y dependencias.
- Documentación actual, histórica y contradicciones entre ambas.

Se parsearon estáticamente los 223 módulos Python de `cortex/` y los 220 archivos Python de tests. No se detectaron errores sintácticos.

### 3.1 Limitación de ejecución

El entorno de auditoría no tenía instalados `pytest`, `chromadb`, `mcp`, `typer`, Ruff ni mypy. No se instalaron dependencias durante esta revisión. Por ello:

- Los hallazgos de wiring y contratos son observaciones directas del código.
- La suite no fue ejecutada y no se afirma que esté verde.
- Los riesgos dependientes del comportamiento específico de Pi se señalan como tales cuando no pueden demostrarse únicamente desde el repositorio.
- Las eliminaciones de archivos propuestas deben confirmarse con telemetría o deprecación, porque puede haber imports dinámicos o consumidores externos.

---

## 4. Radiografía cuantitativa

El repositorio contiene 909 archivos versionados y aproximadamente 10,49 MB de contenido actual.

| Área | Archivos | Tamaño aproximado | Participación |
|---|---:|---:|---:|
| `docs/` | 329 | 4,83 MB | 46,0% |
| `assets/logo.png` | 1 | 1,92 MB | 18,3% |
| `cortex/` | 255 | 1,86 MB | 17,7% |
| `tests/` | 231 | 1,21 MB | 11,5% |
| `cortex-pi/` | 41 | 426 KB | 4,1% |
| `.cortex/` | 19 | 110 KB | 1,0% |
| `.github/` | 5 | 12 KB | 0,1% |

La historia Git comprimida ocupa aproximadamente 9,60 MB adicionales.

### 4.1 Interpretación correcta del tamaño

El runtime Python no es el problema principal de espacio:

- `cortex/` completo pesa aproximadamente 1,86 MB sin comprimir.
- Una estimación mediante compresión zlib deja el contenido de `cortex/` alrededor de 430 KB.
- Documentación más logo representan aproximadamente el 64% del checkout actual.
- El tamaño instalado real está dominado por dependencias como Chroma, ONNX Runtime o PyTorch, no por los `.py` de Cortex.

Por lo tanto, deben distinguirse tres objetivos:

1. **Reducir el checkout Git:** actuar sobre documentación histórica, assets e historia.
2. **Reducir el wheel/sdist:** controlar package-data y separar bundles.
3. **Reducir la instalación:** corregir extras y evitar dependencias pesadas por defecto.

Mezclar esos tres objetivos conduciría a optimizaciones con poco impacto.

---

## 5. Modelo arquitectónico actual

### 5.1 Visión general

Cortex es un monolito modular local-first que une cinco capacidades:

1. Memoria híbrida para agentes.
2. Flujo de ingeniería gobernado por Specs y Sessions.
3. Documentación canónica en Markdown.
4. Integración con agentes, IDEs, CLI y MCP.
5. Gobernanza enterprise, CI y promoción de conocimiento.

El flujo deseado puede expresarse así:

```text
Pedido del usuario
    ↓
Pi / cortex-sync
    ↓
Contexto histórico híbrido
    ↓
Propuesta + Spec
    ↓
Session OPEN
    ↓
SDDwork / designer / explorer / implementer
    ↓
Checkpoints + Tasks + artefactos
    ↓
Security auditor + test verifier
    ↓
Documenter: spec + diff + checkpoints + hooks
    ↓
Session note / handoff / ADRs
    ↓
Session CLOSED | HANDOFF | ABANDONED
    ↓
Memoria semántica + episódica para trabajos futuros
```

### 5.2 Memoria híbrida

Cortex combina:

- Memoria episódica persistida en Chroma.
- Memoria semántica basada en documentos Markdown.
- Embeddings ONNX, local y OpenAI.
- Recuperación híbrida y enriquecimiento de contexto.
- Decaimiento temporal, intención, coocurrencia y grafos.
- Multi-vault y promoción de conocimiento enterprise.

La decisión de conservar Markdown como memoria auditable es especialmente buena: permite que el conocimiento no dependa únicamente de una base vectorial opaca.

### 5.3 Session primitive

La Session es el eje de trazabilidad entre intención y resultado. Una sesión mantiene:

- Spec de origen.
- Commit y branch inicial.
- Estado de lifecycle.
- Checkpoints de los agentes.
- Tasks opcionales.
- Resultados de verificación.
- Commit final.
- Nota de sesión y ADRs creados.
- Modo inferido: Managed, Observed, BYO o CI Review.

Este es probablemente el activo arquitectónico más importante de Cortex. Permite desacoplar el motor del agente o IDE específico.

### 5.4 Canonical Documentation

La capa canónica aporta:

- Schemas tipados.
- Routing por tipo documental.
- Templates.
- Fingerprints.
- Writers idempotentes.
- Documentos de sesión, handoff, ADR, incident, postmortem, runbook, arquitectura, changelog, glosario e historias de usuario.

La dirección es correcta: una única escritura canónica debería reemplazar múltiples formatos específicos de agentes o IDEs.

### 5.5 Superficies de ejecución

Cortex expone actualmente:

- CLI Typer.
- Servidor MCP stdio.
- Adaptadores para varios IDEs.
- Bundle especializado para Pi.
- WebGraph Flask.
- Workitems/Jira.
- Autopilot y comandos CI.

Esta amplitud demuestra capacidad, pero también genera demasiados lugares donde un mismo contrato puede duplicarse o desviarse.

---

## 6. Fortalezas que deben preservarse

### 6.1 Visión de producto diferenciadora

Cortex no es solamente RAG. Intenta preservar el ciclo completo:

```text
intención → diseño → implementación → evidencia → documentación → memoria futura
```

Esa visión tiene más valor que cualquiera de sus implementaciones individuales.

### 6.2 Local-first y auditable

La combinación de Chroma local, archivos Markdown y Git permite trabajar sin depender obligatoriamente de una plataforma externa y conservar trazabilidad humana.

### 6.3 Modelos e invariantes

Existe buen uso de:

- Pydantic.
- Enums cerrados.
- Modelos congelados.
- IDs validados.
- Timestamps UTC.
- Estados terminales explícitos.
- SHA y paths validados.

Estos mecanismos reducen corrupción silenciosa y deben fortalecerse, no retirarse.

### 6.4 Persistencia defensiva

La escritura YAML utiliza temporal, `fsync` y `os.replace`. También existen:

- Retry ante errores transitorios.
- Fallback gitless.
- Resolución mediante `WorkspaceLayout`.
- Writers idempotentes por fingerprint.

### 6.5 Aprendizaje a partir de incidentes

Los comentarios y documentos de incidentes muestran que timeouts, doble dispatch, gitless y problemas de layout se endurecieron a partir de fallas reales. Esta práctica debería formalizarse mediante tests de regresión y ADRs.

### 6.6 Densidad de tests

Hay más de dos mil funciones de test detectadas. La cobertura conceptual abarca modelos, sesiones, CLI, adapters, documentación, enterprise, WebGraph, cache y E2E.

El problema no es ausencia de tests, sino que ciertos tests fijan contratos débiles o no cubren los cruces entre prompts, schema y runtime.

### 6.7 Arquitectura enterprise con sustancia

Multi-vault, promoción, governance profiles y review sessions tienen modelos y servicios propios. No parecen simples flags decorativos.

---

## 7. Escala de prioridades

Los hallazgos se clasifican así:

| Prioridad | Significado |
|---|---|
| P0 | Puede causar pérdida de datos, falsa verificación, instalación destructiva, rotura del flujo principal o exposición de información |
| P1 | Degrada confiabilidad, rendimiento, mantenibilidad o coherencia del producto |
| P2 | Deuda, limpieza, experiencia de desarrollo o documentación |
| P3 | Optimización opcional o evolución futura |

---

## 8. Hallazgos del núcleo Session y Documenter

### SESS-001 — Fuentes oficiales de checkpoint inválidas

**Prioridad:** P0  
**Confianza:** alta

`CheckpointSource` no contiene:

- `cortex-security-auditor`
- `cortex-test-verifier`

Los agentes oficiales de Pi están obligados por sus prompts a emitir exactamente esos valores. El servidor MCP deriva su schema del enum, de modo que el flujo oficial puede rechazar sus checkpoints.

**Impacto:**

- La auditoría de seguridad no queda asociada a la Session.
- La verificación de tests no queda asociada a la Session.
- El Documenter recibe evidencia incompleta.
- Una sesión puede cerrar sin los dos checkpoints finales esperados.

**Mejora recomendada:**

1. Definir una fuente canónica para roles/agentes.
2. Generar o validar `CheckpointSource`, prompts y schemas MCP contra esa fuente.
3. Agregar ambos roles o modelar `source` como identificador extensible validado por registry.
4. Añadir tests contractuales que recorran todos los prompts oficiales y comprueben que cada `source="..."` es aceptado.

**Criterios de aceptación:**

- Todos los agentes distribuidos pueden emitir su checkpoint real.
- Un E2E Pi Deep Track conserva checkpoints de sync, SDDwork, designer, explorer, implementer, security y test verifier.
- El Documenter lista esas evidencias al cerrar.

### SESS-002 — Designer inferido como Observed

**Prioridad:** P1  
**Confianza:** alta

`CORTEX_CODE_DESIGNER` existe en el enum, pero falta en `_CORTEX_SOURCES`. Una sesión cuyos checkpoints incluyan al designer puede inferirse como Observed en vez de Managed.

**Mejora recomendada:**

- Evitar mantener un segundo conjunto manual de fuentes Cortex.
- Añadir una propiedad de clasificación al registry de agentes o al enum.
- Cubrir cada fuente individual y combinaciones válidas en tests de `infer_mode`.

### SESS-003 — Carrera de último escritor

**Prioridad:** P0  
**Confianza:** alta

El lock de `SessionStorage` protege la escritura física, pero no toda la operación:

```text
load → validar → modificar → save
```

Dos workers pueden leer la misma versión y guardar actualizaciones distintas. La última escritura elimina la anterior.

**Impacto:**

- Checkpoints perdidos.
- Tasks revertidas.
- Cierre compitiendo con un checkpoint.
- Resultados diferentes según timing.

**Alternativas:**

1. Lock por `session_id` en `SessionService` alrededor de la mutación completa.
2. Campo `revision` y compare-and-swap con retry.
3. SQLite con transacciones y WAL.

**Recomendación:**

- Corto plazo: lock de mutación completo más `revision`.
- Mediano plazo: evaluar SQLite para Sessions, tool audit y metadata operacional. Mantener YAML como export legible si es un requisito de producto.

**Criterios de aceptación:**

- Un test con múltiples threads agrega N checkpoints y persiste exactamente N.
- Actualizaciones concurrentes de tasks diferentes no se pierden.
- Close y checkpoint concurrentes tienen un resultado determinista.

### SESS-004 — Mapa global de locks sin liberación

**Prioridad:** P2

`_PATH_LOCKS` conserva un lock por path durante toda la vida del proceso. Normalmente será pequeño, pero un servidor que toque muchas sesiones acumulará entradas.

**Mejora recomendada:** usar weak references, locks administrados por SessionService o un store transaccional que elimine la necesidad del mapa.

### DOC-001 — `required` se pierde al ejecutar hooks

**Prioridad:** P0  
**Confianza:** alta

`VerificationHook` posee `required`, pero `VerificationHookResult` no. El reconstructor trata todos los resultados como obligatorios.

**Impacto:** un hook declarado opcional puede forzar HANDOFF incorrectamente y el agente Documenter espera un campo que no recibe.

**Mejora recomendada:**

- Persistir `required` y, preferentemente, un `hook_id` estable en el resultado.
- Evitar inferencias por nombre.
- Hacer que el CI validator y Documenter consuman la misma función de decisión.

### DOC-002 — Cierre potencialmente exitoso sin hooks ejecutados

**Prioridad:** P0  
**Confianza:** alta

`cortex_documenter_briefing` usa `run_hooks=false` por defecto. Con resultados vacíos y sin archivos pendientes, `all([])` permite sugerir CLOSED.

**Mejora recomendada:** distinguir estados de evidencia:

```text
not-declared | not-run | passed | failed | timed-out
```

Una política segura podría ser:

- Hooks declarados y todos los required pasaron → elegible para CLOSED.
- Hooks declarados pero no ejecutados → HANDOFF o `verification_pending`.
- Ningún hook declarado en spec legacy → CLOSED sólo con override explícito y razón, o un perfil de compatibilidad claramente señalado.

**Criterios de aceptación:**

- El sistema nunca presenta “verificado” cuando no ejecutó evidencia.
- El briefing devuelve explícitamente qué hooks fueron omitidos.
- Pi muestra al usuario si cerrar requiere ejecutar hooks o aceptar un override.

### DOC-003 — ID de nota desconectado de la Session

**Prioridad:** P0  
**Confianza:** alta

`DocumenterPersister` delega en `NoteService`, que crea un `session_id` aleatorio. La nota y el `SessionRecord` pierden el mismo identificador de linaje.

**Impacto:**

- Filename y frontmatter no corresponden a la sesión.
- Búsquedas por session ID fallan o devuelven artefactos desconectados.
- Auditoría y navegación WebGraph pierden trazabilidad.

**Mejora recomendada:**

- Hacer `session_id` obligatorio para escrituras de tipo session provenientes del Documenter.
- Separar la creación manual de notas genéricas de la persistencia de una Session real.
- Validar al cerrar que el frontmatter de la nota contiene el mismo ID.

### DOC-004 — `forced_reason` se captura pero no se persiste

**Prioridad:** P1

CLI, MCP e interactive recolectan una razón para forzar HANDOFF/ABANDONED, pero el persister no la incorpora a la nota ni al SessionRecord.

**Mejora recomendada:** añadir `closure_reason` estructurado al record y renderizarlo en la nota/handoff.

### DOC-005 — Diff incompleto para cambios sin commit

**Prioridad:** P1

La reconstrucción compara `start_commit..HEAD`. Cambios no commiteados no aparecen salvo que el agente los haya declarado correctamente en checkpoints.

**Mejora recomendada:** reconstruir tres vistas:

1. Commits desde `start_commit` a `HEAD`.
2. Index/staged.
3. Working tree.

Cada archivo debería conservar procedencia y nivel de confianza.

### DOC-006 — Scope sólo por igualdad exacta

**Prioridad:** P2

`files_in_scope` se compara como paths exactos. No hay semántica de directorios, patrones o globs.

**Mejora recomendada:** definir explícitamente un mini-contrato de scope:

- Archivo exacto.
- Directorio recursivo.
- Glob controlado.
- Exclusiones.

Debe evitarse interpretar patrones ambiguos de forma distinta entre Spec, CI y Documenter.

### DOC-007 — Persistencia multi-artefacto parcialmente transaccional

**Prioridad:** P1

La nota y ADRs pueden escribirse antes del cierre. Una falla posterior deja artefactos parciales. Algunos errores de ADR pueden ser tolerados silenciosamente.

**Mejora recomendada:**

- Preparar todos los artefactos.
- Validar y escribir a temporales.
- Registrar una operación de finalización con ID.
- Publicar artefactos y cerrar en pasos idempotentes.
- Permitir resume/retry de una finalización parcial.

### DOC-008 — Resultado booleano de indexado ignorado

**Prioridad:** P1

`NoteService` y `SpecService` llaman `index_file` sin validar su resultado. La promesa de transacción no se cumple si el indexador atrapa la excepción y retorna `False`.

**Mejora recomendada:** elegir y documentar uno de dos modelos:

1. **Fuerte:** la operación falla y compensa todos los side effects.
2. **Eventual:** el documento queda persistido con estado `index_pending`, existe una cola/reconciliador y la API informa el estado parcial.

La segunda opción probablemente sea más realista para embeddings y stores externos.

---

## 9. Auditoría Pi-first

Pi es la superficie más importante y también la que concentra más personalización. Por eso debe recibir una arquitectura de distribución, seguridad y contratos propia.

### 9.1 Estado actual del bundle

El bundle contiene:

- `.pi/settings.json`.
- `.pi/mcp.json`.
- Ocho agentes.
- Diez extensiones cargadas por defecto.
- Dos skills de Obsidian.
- Tema.
- `justfile`.
- `README.md` y `AGENTS.md`.
- Cuatro extensiones antiguas fuera de `.pi/extensions/`.

La integración implementa bastante más que un adapter tradicional:

- MCP dinámico.
- Bridge CLI.
- Cockpit y panel.
- Autopilot.
- Coordinación cortex-net.
- Team orchestration.
- Selección de sistema/modelo.
- Damage control.
- Footer y UI.

En la práctica, Pi es un producto dentro del producto. Debe tratarse como tal.

### PI-001 — Bundle ausente del wheel

**Prioridad:** P0  
**Confianza:** alta para wheel/pipx

Setuptools descubre únicamente paquetes `cortex*`. `cortex-pi/` es un directorio top-level. `PiAdapter` intenta encontrarlo subiendo desde `cortex/ide/adapters/pi.py` hasta la raíz del checkout.

En una instalación publicada, esa raíz no tiene por qué contener `cortex-pi/`.

**Impacto:** `cortex inject --ide pi` puede funcionar en desarrollo editable y fallar desde PyPI/pipx.

**Mejora recomendada:** elegir una estrategia explícita:

#### Opción A — Bundle dentro del paquete Python

```text
cortex/
  resources/
    pi/
      bundle-manifest.json
      .pi/...
      justfile
      AGENTS.md
```

Usar `importlib.resources` para localizarlo.

#### Opción B — Distribución separada

Publicar un artefacto/versionado `cortex-pi-bundle` y hacer que Cortex lo instale/resuelva de forma explícita.

**Recomendación:** Opción A mientras Pi y el engine deban versionarse juntos. Opción B sólo si Pi adquiere lifecycle independiente.

**Criterios de aceptación:**

- Construir wheel limpio.
- Instalarlo en un entorno sin checkout.
- Ejecutar `cortex inject --ide pi` sobre un proyecto temporal.
- Iniciar Pi y comprobar `cortex_ping`.

### PI-002 — Instalación sobrescribe archivos del adopter

**Prioridad:** P0

La inyección copia el bundle completo sobre la raíz del proyecto y puede sobrescribir:

- `README.md`.
- `AGENTS.md`.
- `justfile`.
- `.pi/`.
- `extensions/`.

El CLI general promete safe merge y backup automático, pero Pi no utiliza esas utilidades.

**Arquitectura objetivo de instalación:**

1. `plan`: calcular cambios sin escribir.
2. `backup`: respaldar cada target existente.
3. `apply`: escribir de forma atómica.
4. `manifest`: registrar propiedad, hash previo, hash instalado y backup.
5. `verify`: comprobar que el estado final coincide con el manifest.

Manifest sugerido:

```text
.cortex/install-manifests/pi.json
```

El manifest debería distinguir:

- Archivo creado íntegramente por Cortex.
- Archivo fusionado.
- Archivo existente no modificado.
- Backup asociado.
- Versión del bundle.

**Criterios de aceptación:**

- Nunca se sobrescribe contenido del adopter sin backup.
- `--dry-run` muestra create/update/merge/conflict.
- Una segunda instalación idéntica es idempotente.
- Un conflicto manual produce una acción explícita, no overwrite silencioso.

### PI-003 — Desinstalación inconsistente y potencialmente destructiva

**Prioridad:** P0

El método directo puede eliminar `.pi/`, `README.md`, `AGENTS.md`, `justfile` y `extensions/` completos. Esos targets pueden contener trabajo del adopter.

Al mismo tiempo, el facade público llama `adapter.uninstall()` sin `project_root`, por lo que Pi devuelve una lista vacía y la desinstalación normal no hace nada.

**Mejora recomendada:**

- Desinstalar únicamente archivos registrados como propiedad de Cortex.
- Si un archivo cambió desde la instalación, no borrarlo: presentar conflicto o restaurar mediante estrategia explícita.
- Restaurar backups sólo con confirmación o flag dedicado.
- Nunca borrar un directorio completo por nombre sin inspeccionar el manifest.

### PI-004 — Dos proveedores registran herramientas con los mismos nombres

**Prioridad:** P0/P1  
**Confianza:** alta sobre la colisión nominal; el resultado exacto depende de Pi

`.pi/settings.json` carga simultáneamente:

- `cortex-tools.ts`, que registra herramientas directas mediante CLI.
- `cortex-mcp.ts`, que descubre las herramientas MCP y colapsa nombres como `mcp_cortex_cortex_search` a `cortex_search`.

Existen al menos estas colisiones:

- `cortex_search`
- `cortex_context`
- `cortex_create_spec`
- `cortex_save_session`
- `cortex_sync_vault`

Los schemas no son equivalentes. Por ejemplo, el bridge CLI modela create-spec como un único string `content`, mientras MCP espera campos estructurados.

Además, las dos tools mutantes principales del bridge CLI no construyen una invocación válida del CLI actual:

- `cortex_save_session(content)` ejecuta `cortex save-session <content>`, pero el comando exige las opciones `--title` y `--spec-summary`.
- `cortex_create_spec(content)` ejecuta `cortex create-spec <content>`, pero el comando exige `--title` y `--goal`.

Typer no interpreta ese string posicional como las opciones requeridas. Por lo tanto, incluso si Pi resolviera la colisión a favor de `cortex-tools.ts`, esos dos caminos pueden fallar antes de llegar al servicio.

**Riesgos:**

- Una extensión pisa a la otra.
- El agente ve un schema distinto según orden de carga.
- El flujo de proposal/spec/session puede evitar el guard MCP.
- Los prompts se escriben contra una herramienta que no es la realmente ejecutada.

**Decisión recomendada:** MCP debe ser el canal canónico de operaciones Cortex en Pi.

`cortex-tools.ts` debería quedar limitado a:

- Diagnóstico de disponibilidad.
- Bootstrap.
- Comandos con nombres no superpuestos.
- Fallback manual explícito, desactivado por defecto.

No debería registrar alternativas con el mismo nombre.

### PI-005 — Schemas complejos degradados a strings JSON

**Prioridad:** P1

El bridge MCP convierte arrays y objetos en strings opcionales y luego intenta `JSON.parse`. Esto:

- Pierde requeridos internos.
- Pierde enums y defaults.
- Debilita la asistencia del modelo.
- Aumenta errores de quoting y serialización.
- Oculta incompatibilidades de contrato.

**Mejora recomendada:**

- Preservar JSON Schema recursivamente si Pi/TypeBox lo permite.
- Si existe una limitación de Pi, generar wrappers tipados específicos para las tools críticas.
- Agregar contract tests schema MCP → schema Pi.

Tools críticas que no deberían degradarse:

- `cortex_create_spec`.
- `cortex_session_checkpoint`.
- `cortex_session_task_update`.
- `cortex_write_doc`.
- `cortex_emit_proposal`.
- `cortex_validate_handoff` mientras siga soportada.

### PI-006 — Prompts y schemas no se validan juntos

**Prioridad:** P0

Además de los `source` inválidos:

- Test verifier muestra `artifacts_produced`, que no forma parte del contrato de checkpoint.
- Documenter espera `verification_results[i].required`, campo ausente.
- La guía Pi describe AgentHandoff en lugares donde los prompts actuales indican que está deprecated.
- La guía afirma que el sync canónico está activo, pero el adapter neutraliza el flag.

**Mejora recomendada:** crear un linter de prompts de producto que valide:

1. Nombres de tools existentes.
2. Argumentos mostrados en ejemplos.
3. Enums literales.
4. Campos que el prompt espera leer del output.
5. Agentes incluidos en settings.
6. Referencias a recipes del justfile.

Este linter debería ejecutarse en CI y fallar ante drift.

### PI-007 — Justfile globalmente atado a PowerShell

**Prioridad:** P1

El bundle publicita macOS, Linux y Windows, pero define:

```text
set shell := ["powershell", "-Command"]
```

Las recipes de roles usan sintaxis `$env:...`, por lo que no son portables a Linux/macOS sin PowerShell.

**Mejora recomendada:**

- Usar recipes neutrales que invoquen una utilidad Python/Bun incluida.
- O dividir recipes por OS usando capacidades de Just.
- Validar el justfile en una matriz Windows/Linux/macOS.

### PI-008 — Bundle TypeScript sin toolchain verificable

**Prioridad:** P1

No se encontró `package.json`, lockfile, `tsconfig` ni tests del bundle. Pi/Bun transpila las extensiones en runtime.

La extensión más grande, `cortex-net.ts`, supera las 2.300 líneas. Una rotura de tipos o import puede llegar directamente al usuario.

**Mejora recomendada:**

- `package.json` privado para desarrollo.
- Lockfile.
- `tsconfig` compatible con Pi/Bun.
- Typecheck de todas las extensiones.
- Tests unitarios para schema mapping, paths, roles, manifest e instalación.
- E2E mínimo levantando el bundle desde un proyecto limpio.

### PI-009 — Extensiones legacy fuera del runtime activo

**Prioridad:** P2

`cortex-pi/extensions/` contiene cuatro extensiones antiguas, aproximadamente 39 KB, no cargadas por settings ni justfile. `cortex-subagent-widget.ts` importa un `themeMap.ts` inexistente.

**Mejora recomendada:**

- Marcar la carpeta como legacy inmediatamente.
- Confirmar que ningún flujo/documentación la usa.
- Moverla a archivo histórico o eliminarla en una release mayor.
- Mantener sólo `.pi/extensions/` como runtime del bundle.

### PI-010 — Documentación Pi desactualizada

**Prioridad:** P1

Ejemplos de drift:

- README muestra menos extensiones de las que settings carga.
- La guía menciona dashboard antiguo mientras settings usa cockpit.
- Se documentan `just sdd`, `just hotfix` y `just audit`, inexistentes en el justfile actual.
- Se promete backup automático que Pi no realiza.
- Se documenta sync canonical que está neutralizado.
- Se describe AgentHandoff donde los prompts actuales usan checkpoints.

**Mejora recomendada:** generar tablas de agentes, extensiones, tools y recipes a partir del bundle o verificarlas en CI.

### PI-011 — SSoT ambiguo entre `.cortex` y `cortex-pi`

**Prioridad:** P1

El adapter conserva listas y más de cien líneas comentadas de un mecanismo que sincronizaba `.cortex/{skills,subagents}` con Pi. El flag CLI sigue visible pero se ignora.

**Decisión recomendada:**

- Pi debe tener su propia fuente de verdad si necesita prompts adaptados.
- Los contratos compartidos no deben copiarse manualmente; deben generarse desde assets comunes o validarse entre superficies.
- Eliminar el flag inerte en la siguiente release con breaking changes.
- Retirar el bloque comentado una vez documentado en ADR/historia.

### PI-012 — cortex-net persiste transcript completo

**Prioridad:** P1 seguridad/privacidad

El audit log evita cuerpos, pero el transcript guarda mensajes completos para que el Documenter reconstruya decisiones.

El directorio `.pi/agent-sessions/` no está incluido en el `.gitignore` raíz; el README pide agregarlo manualmente.

**Riesgos:**

- Commit accidental de conversaciones o secretos.
- Retención indefinida si cleanup no ocurre.
- Lectura por otros procesos locales con acceso al workspace.

**Mejora recomendada:**

- Añadir el path a gitignore durante instalación segura.
- Permisos restrictivos.
- Política de retención configurable.
- Redacción de secretos antes de persistir.
- Opción `transcript_mode=off|metadata|full`, con `metadata` como default razonable.
- Doctor debe alertar si el transcript está trackeado o world-readable.

### PI-013 — cortex-net no autentica peers

**Prioridad:** P1

Los roles y session IDs son autoafirmados sobre sockets/pipes locales. El threat model local reduce la exposición, pero no existe autenticación fuerte.

**Mejora recomendada:**

- Token aleatorio por Session en archivo con permisos restrictivos.
- Challenge simple al registrar peers.
- Rechazar peers con otra raíz de workspace.
- Límites de mensajes, peers y colas.
- Mantener confirmación humana para envíos salientes.

### PI-014 — Riesgo de monolito en `cortex-net.ts`

**Prioridad:** P2

La extensión combina:

- Paths y compatibilidad de OS.
- Hub.
- Cliente.
- Protocolo.
- Transcript/audit.
- UI.
- Tool registration.
- Lifecycle Pi.

**Mejora recomendada:** separar módulos internos de build:

```text
net/protocol.ts
net/transport.ts
net/hub.ts
net/client.ts
net/persistence.ts
net/pi-extension.ts
```

La distribución puede seguir generando un único archivo si Pi lo requiere.

### PI-015 — Falta una suite E2E de producto

**Prioridad:** P0/P1

La suite Python cubre adapters y artefactos, pero Pi necesita un E2E que pruebe la experiencia recomendada completa.

**Escenarios mínimos:**

1. Instalar wheel limpio.
2. Inyectar Pi sin archivos previos.
3. Inyectar sobre proyecto con README/AGENTS/justfile propios.
4. Reinjection idempotente.
5. Upgrade de una versión de bundle a otra.
6. Uninstall conservador.
7. Inicio MCP y `cortex_ping`.
8. Sync → proposal → spec → session.
9. Deep Track con todos los checkpoints.
10. Hooks required/optional.
11. Documenter con Session ID correcto.
12. cortex-net en Linux y Windows.
13. Cierre y limpieza sin secretos trackeados.

---

## 10. Arquitectura objetivo para Pi

### 10.1 Principios

1. Pi es el cliente de referencia.
2. MCP es el plano canónico de operaciones Cortex.
3. El bridge CLI no compite con MCP usando los mismos nombres.
4. El bundle se distribuye como artefacto versionado e incluido en el paquete.
5. Instalación y desinstalación se basan en manifest de propiedad.
6. Prompts, tools y schemas se validan automáticamente.
7. La red local tiene identidad, límites y retención explícita.
8. El bundle TypeScript se typecheckea y testea antes de publicarse.

### 10.2 Componentes propuestos

```text
cortex Python package
├── engine y servicios
├── MCP registry canónico
├── schemas exportables
├── resources/pi/
│   ├── bundle-manifest.json
│   ├── .pi/
│   ├── justfile
│   └── AGENTS.md
└── installer/pi/
    ├── planner
    ├── merger
    ├── backup
    ├── manifest
    └── verifier

Pi runtime
├── cortex-mcp          plano de datos y mutaciones
├── cortex-cockpit      experiencia visual
├── cortex-team         orquestación
├── cortex-net          coordinación local autenticada
├── damage-control      protección
└── bootstrap-tools     sólo diagnóstico, sin nombres duplicados
```

### 10.3 Registry canónico de agentes

Cada agente debería declarar en un único descriptor:

- `id`.
- Nombre visible.
- Rol cortex-net.
- Checkpoint source.
- Tools permitidas.
- Si participa en Fast/Deep Track.
- Si puede modificar producción/tests/documentación.
- Prompt asset.
- Reglas de salida.

De ese registry pueden derivarse:

- Valores de schema.
- Settings Pi.
- Validación de prompts.
- Documentación.
- Tests de inferencia de SessionMode.

### 10.4 Registry canónico de tools MCP

El servidor MCP no debería mantener por separado:

- Schema.
- Descripción.
- Timeout.
- Branch de dispatch.
- Logging policy.
- Mutabilidad/idempotencia.

Un descriptor debería contener al menos:

- Nombre.
- Input model.
- Output model.
- Handler.
- Timeout.
- Clase de mutación.
- Clave de idempotencia.
- Política de redacción.
- Requisitos de Session/ticket/proposal.

Esto permitiría generar el schema Pi sin degradación y comprobar que prompts y runtime coinciden.

### 10.5 Lifecycle de instalación

```text
cortex inject --ide pi --dry-run
    ↓
Plan de create / merge / conflict / unchanged
    ↓
Backup de targets existentes
    ↓
Apply atómico
    ↓
Manifest con ownership + hashes
    ↓
Doctor de instalación
    ↓
Smoke MCP + Pi assets
```

### 10.6 Política de actualización

Un upgrade debe clasificar cada archivo:

- Sin cambios locales: actualizar automáticamente.
- Modificado por usuario y nuevo upstream idéntico al anterior: conservar usuario.
- Modificado por usuario y upstream también cambió: conflicto explícito.
- Generado: regenerar desde fuente.
- Owned y obsoleto: eliminar sólo si su hash coincide con la versión instalada.

---

## 11. MCP y runtime

### MCP-001 — Servidor monolítico

**Prioridad:** P1

`cortex/mcp/server.py` tiene aproximadamente 139 KB y 2.977 líneas. Combina registro, schemas, dispatch, timeouts, logging, gobierno, tools de memoria, docs, sessions y workitems.

**Mejora recomendada:** separar por dominio después de introducir el registry:

```text
mcp/
  registry.py
  runtime.py
  policies.py
  tools/memory.py
  tools/sessions.py
  tools/documentation.py
  tools/workitems.py
  tools/autopilot.py
```

### MCP-002 — Timeout no cancela el trabajo real

**Prioridad:** P0/P1

`wait_for(run_in_executor)` cancela la espera, no el thread subyacente. El handler puede continuar mutando estado después de que el cliente recibió timeout.

**Mejora recomendada:**

- Operaciones externas en procesos cancelables cuando sea posible.
- Tokens de cancelación cooperativa.
- Idempotency keys para mutaciones.
- Estado `operation_id` consultable para tareas largas.
- Evitar reintentar a ciegas tras timeout.

### MCP-003 — Logging sensible y sin límites

**Prioridad:** P0/P1

Se guardan argumentos y resultados completos en memoria y log. Esto puede incluir specs, queries, cuerpos documentales o secretos. El historial crece sin límite y cada operación normal se registra dos veces.

**Mejora recomendada:**

- Ring buffer acotado.
- Redacción por schema.
- No guardar bodies completos por defecto.
- Rotación y retención.
- Una entrada estructurada por call con fases y duración.
- Correlation ID.

### MCP-004 — Gobierno global en vez de contextual

**Prioridad:** P0/P1

`_called_tools` y `_last_proposal_emitted_at` viven durante todo el servidor. Una llamada antigua puede satisfacer el guard de una operación futura no relacionada.

**Mejora recomendada:** emitir tokens/capabilities correlacionados:

- `sync_ticket_id`.
- `proposal_id`.
- `session_id`.
- Expiración.
- Hash del pedido o spec propuesta.

`cortex_create_spec` debería recibir y validar esos IDs, no inspeccionar historial global.

### MCP-005 — Taxonomía de versiones inconsistente

**Prioridad:** P2

Se observan referencias a servidor 2.0, 2.1, 2.2 y 3.0, paquete 0.5.0 y bundle Pi 2.5.

**Mejora recomendada:** distinguir formalmente:

- Versión del paquete Cortex.
- Versión del protocolo MCP Cortex.
- Versión del schema de Session.
- Versión del bundle Pi.

El ping debe exponerlas por separado.

### MCP-006 — `with_tasks` ausente en create-spec MCP

**Prioridad:** P1

CLI, core y SpecService soportan `with_tasks`, pero la herramienta MCP no lo expone. Pi, como cliente principal MCP, no puede pedir el mismo comportamiento.

**Mejora recomendada:** generar tools desde modelos/servicios para evitar diferencias entre CLI y MCP.

### MCP-007 — Full sync por defecto

**Prioridad:** P1 rendimiento

`SpecService` usa `sync_vault=False` por defecto, pero CLI y MCP pasan `not no_sync`, convirtiendo el comportamiento normal en full sync.

**Impacto:** creación de spec lenta, timeouts y embeddings innecesarios.

**Mejora recomendada:**

- Indexado selectivo por defecto.
- Full sync como operación explícita de mantenimiento.
- Reconciliación incremental basada en fingerprint.

---

## 12. Memoria, retrieval y embeddings

### MEM-001 — RRF no fusiona identidad cross-source

**Prioridad:** P1

Los candidatos episódicos y semánticos usan namespaces disjuntos. Por diseño actual, un mismo conocimiento no suma evidencia desde las dos fuentes.

**Mejora recomendada:** definir `knowledge_identity` compartida:

- Session ID.
- Canonical document ID.
- Fingerprint estable.
- Relación `derived_from`.

Luego se puede:

- Fusionar evidencia de ambas fuentes.
- Deduplicar.
- Presentar procedencia combinada.
- Penalizar contradicciones.

### MEM-002 — Intent detector monolingüe y ejecutado dos veces

**Prioridad:** P1/P2

Los patrones de intención son principalmente ingleses. Además, `detect(query)` se llama dos veces consecutivas en una búsqueda adaptativa.

**Mejora recomendada:**

- Corregir doble ejecución.
- Soportar al menos español e inglés.
- Medir precisión con un corpus real de consultas Cortex.
- Permitir fallback por embeddings/clasificador ligero.

### MEM-003 — Dos stacks de embeddings

**Prioridad:** P1

Existe una Factory/Protocol moderna en `cortex/embedders`, pero producción continúa usando mayormente `cortex.episodic.embedder.Embedder`. ONNX delega parcialmente a la implementación nueva, mientras local/OpenAI mantienen lógica duplicada.

**Mejora recomendada:**

1. Elegir `EmbedderProtocol` como contrato único.
2. Adaptar legacy detrás del protocolo.
3. Migrar consumidores por etapas.
4. Deprecar la fachada antigua.
5. Centralizar batching, retries, modelo, dimensión y métricas.

### MEM-004 — VectorCache implementado pero no conectado al composition root

**Prioridad:** P1

`AgentMemory` crea `VaultReader` sin `VectorCache`. La CLI de cache administra una ubicación que el runtime principal no usa.

Además, la resolución actual puede producir `.cortex/.cortex/vectors` en el layout nuevo.

**Antes de conectarlo deben corregirse:**

- Dimensión fija 384.
- Fingerprint sólo por texto.
- Falta de backend/model/version en la clave.
- Reescritura del índice JSON por cada vector durante batch.
- Atomicidad y recuperación.

**Clave sugerida:**

```text
sha256(schema_version | backend | model | dimension | normalized_text)
```

### MEM-005 — `confidence` es una capacidad incompleta

**Prioridad:** P1

`MemoryEntry.confidence` puede mostrar `verified`, `asserted` o `contradicted`, pero la producción no lo establece ni lo persiste en Chroma.

**Mejora recomendada:**

- Definir quién asigna confianza.
- Persistirla.
- Mantener evidencia/provenance asociada.
- Evitar que `verified` sea una etiqueta libre del agente sin prueba.

### MEM-006 — Feedback loop sin aprendizaje persistente

**Prioridad:** P2

ContextEnricher crea un `FeedbackCollector` nuevo por llamada. El estado no sobrevive y no existe una API explícita conectada para feedback de usuario.

**Mejora recomendada:** renombrar la capacidad como boost implícito de contexto hasta que exista persistencia. Si se implementa aprendizaje real, registrar eventos auditables y permitir reset/export.

### MEM-007 — Índice semántico generado puede ensuciar repositorios

**Prioridad:** P2

`.cortex_index.json` no está cubierto claramente por la política gitignore distribuida.

**Mejora recomendada:** todo artefacto runtime debe vivir bajo layout de datos ignorado o ser agregado a gitignore mediante instalación segura.

---

## 13. Packaging y dependencias

### PKG-001 — `requirements.txt` contradice `pyproject.toml`

**Prioridad:** P1

`pyproject.toml` excluye intencionalmente sentence-transformers/PyTorch del core y lo mueve al extra `local`. `requirements.txt` lo instala como dependencia normal.

**Impacto:** instalaciones mucho más pesadas y experiencia distinta según la guía/comando usado.

**Mejora recomendada:**

- Declarar `pyproject.toml` como única fuente de dependencias.
- Generar requirements bloqueados para desarrollo/CI cuando sea necesario.
- No mantener listas manuales divergentes.

### PKG-002 — Import raíz eager

**Prioridad:** P1

`cortex/__init__.py` importa `AgentMemory`, Chroma, pipeline, services y retrieval. Un simple `import cortex` requiere buena parte del stack pesado.

**Mejora recomendada:**

- `__init__` mínimo.
- Exports lazy o imports desde módulos concretos.
- CLI/Pi doctor debe poder iniciar sin cargar modelos ni Chroma.

### PKG-003 — Alias `SessionService` ambiguo

**Prioridad:** P2

`cortex.SessionService` es un alias deprecated de `NoteService`, mientras el Session primitive real vive en `cortex.session.service.SessionService`.

**Mejora recomendada:** deprecar con warning y eliminar en release mayor. Dos conceptos centrales no deben compartir el mismo nombre.

---

## 14. WebGraph

### WEB-001 — Header estático no es autenticación

**Prioridad:** P1 seguridad

El default loopback es correcto. Pero si el usuario configura `0.0.0.0`, cualquiera que conozca `X-Cortex-WebGraph: 1` puede acceder y potencialmente activar `/api/open`.

**Mejora recomendada:**

- Rechazar bind no-loopback sin token aleatorio.
- CSRF/origin policy apropiada.
- Deshabilitar `/api/open` en modo remoto.
- Mostrar warning explícito en CLI.

### WEB-002 — Cache ignora scope

**Prioridad:** P1

El snapshot se filtra por scope antes de guardarse, pero cache y metadata se identifican sólo por mode/fingerprint. Una consulta local puede contaminar otra all/enterprise.

**Mejora recomendada:** incluir scope y topología/federación en key y filename.

### WEB-003 — Fingerprint costoso antes de cache

**Prioridad:** P2

Cada request recorre árboles completos para decidir si el cache sirve. El cache evita build, pero no evita el costo O(n) del scan.

**Mejora recomendada:** journal incremental, mtimes por directorio o metadata persistida por archivo.

### WEB-004 — Errores de API poco controlados

**Prioridad:** P2

Node ID inválido puede propagarse como KeyError/500. Mode y depth tienen validación débil.

**Mejora recomendada:** modelos de request, 404/400 consistentes y límites de profundidad.

---

## 15. Autopilot, Enterprise y workitems

### AUTO-001 — Dos semánticas de cierre incompatibles

**Prioridad:** P1

Autopilot fue refactorizado para reutilizar la Session primitive y, cuando usa `finish(auto=True)`, invoca la pipeline canónica del Documenter. Esa convergencia es positiva.

Sin embargo, `finish(auto=False)` cierra directamente el `SessionRecord` sin documentar y su docstring indica que el usuario puede ejecutar `cortex finish-session` después. Una Session cerrada ya no puede pasar normalmente por la finalización canónica, por lo que la promesa es contradictoria.

**Mejora recomendada:** elegir una semántica inequívoca:

- `finish(auto=False)` no cierra; deja la Session OPEN y devuelve `documentation_pending`.
- O cierra como HANDOFF con estado explícito y ofrece una operación idempotente de documentación post-cierre.
- No usar `documented=True` si no existe el archivo físico o no fue indexado.

**Criterios de aceptación:**

- Cada resultado `documented=True` apunta a un archivo existente con Session ID correcto.
- Un cierre manual puede completar documentación posteriormente mediante una operación soportada y testeada.
- README, docs Autopilot y runtime describen la misma semántica.

### AUTO-002 — Documentación histórica de Autopilot contradice el runtime actual

**Prioridad:** P2

Parte de `docs/autopilot/evals.md` describe una implementación anterior donde `finish --auto` devolvía un path sin persistir el archivo. El servicio actual sí delega en `DocumenterPersister` para el camino automático.

**Mejora recomendada:** marcar evals y fases con versión/fecha y mover resultados obsoletos a archivo histórico. Los evals vigentes deben ejecutarse nuevamente contra el runtime actual.

### ENT-001 — Dos caminos de promoción de conocimiento

**Prioridad:** P1/P2

Coexisten `KnowledgePromotionService` y el camino DocType-aware de `promotion_doctype`, además de comandos de review legacy. Ambos tienen valor y uso parcial, pero sostener dos modelos de lifecycle aumenta reglas, registros y documentación.

**Mejora recomendada:**

1. Definir el modelo de promoción canónico.
2. Adaptar el camino legacy detrás de ese modelo.
3. Migrar registros existentes.
4. Unificar review, approve/reject, fingerprint y eventos.
5. Deprecar comandos duplicados.

### ENT-002 — Retention maintenance sin entrypoint operacional

**Prioridad:** P2

`cortex.enterprise.maintenance` tiene implementación y tests, pero declara que la ejecución automática y el wrapper CLI quedan fuera del módulo. La capacidad existe como librería, no como feature completa.

**Mejora recomendada:** decidir entre:

- Exponer `cortex docs maintenance scan|archive --dry-run` con reporte y confirmación.
- Integrarlo a un scheduler/CI enterprise.
- O retirarlo temporalmente de la superficie prometida.

El archivado debe usar manifest o log de movimientos y nunca mover documentos sin dry-run revisable.

### WORK-001 — Workitems es pequeño y bien delimitado

La integración Jira es read-only, lazy, usa provider abstractions y resolución segura de paths. No es candidata a una reescritura o eliminación prioritaria.

La mejora más valiosa sería alinearla con identidad canónica de documentos y Session, no expandir proveedores antes de que exista demanda.

---

## 16. Pipeline, CI, seguridad y release

### CI-001 — Pipeline Python expuesto pero no conectado

**Prioridad:** P2

`cortex/pipeline/` contiene 13 archivos y cerca de 60 KB. Está exportado desde el paquete, pero no se encontraron consumidores de producción. Los workflows reales se generan desde setup/templates por otro camino.

**Decisión necesaria:**

- Convertirlo en la fuente de verdad de pipelines.
- O deprecarlo y eliminarlo gradualmente.

Mantener dos arquitecturas de pipeline es peor que cualquiera de las dos por separado.

### CI-002 — Calidad en modo observabilidad

**Prioridad:** P1

Ruff, mypy y pytest usan `continue-on-error: true` en PR. Sólo mypy estricto de documentación y validación documental bloquean.

**Impacto:** main puede degradarse aunque los agentes prometan lint, tipos, tests y cobertura.

**Mejora recomendada:** progresión controlada:

1. Baseline actual y deuda conocida.
2. Gate sobre archivos cambiados.
3. Gate global de Ruff/tests.
4. Mypy estricto por módulos.
5. Cobertura mínima real.

### CI-003 — Umbral de 85% no aplicado

**Prioridad:** P1

Los prompts Pi exigen más de 85%, pero `pyproject.toml` y CI no usan `--cov-fail-under=85`.

**Mejora recomendada:** decidir si 85% es contrato real. Si lo es, aplicarlo y publicar cobertura por módulo; si no, corregir prompts.

### CI-004 — Workflow security llama Bandit sin instalarlo

**Prioridad:** P1

El extra `dev` no incluye Bandit, pero el workflow ejecuta `bandit` después de instalar `.[dev]`.

**Mejora recomendada:** extra `security` o instalación explícita/versionada.

### CI-005 — Permisos amplios en PR

**Prioridad:** P1 seguridad

El workflow PR solicita write para contents, pull requests, issues y security events.

**Mejora recomendada:** mínimo privilegio por job/step. La mayoría de los checks sólo necesita `contents: read`.

### CI-006 — Release no publica realmente

**Prioridad:** P2

El workflow construye, pero `twine upload` está comentado. Tampoco hay verificación visible de artefacto, SBOM, firma o smoke desde wheel.

**Mejora recomendada:** release reproducible con:

- Test desde wheel.
- Verificación Pi bundle incluido.
- `twine check`.
- Trusted Publishing de PyPI.
- Changelog/version consistentes.
- Checksums/SBOM si el producto lo requiere.

### CI-007 — Actions por tags móviles

**Prioridad:** P2 seguridad supply-chain

Los workflows usan `@v4`, `@v5`, etc. Para hardening fuerte, fijar SHAs y automatizar updates.

---

## 17. Documentación y versionado

### DOCS-001 — Histórico y referencia compiten

**Prioridad:** P1/P2

`docs/` contiene arquitectura vigente, planes, conversaciones, fases, realización, avances e incidentes. Todo es útil, pero no todo debe actuar como fuente de verdad actual.

**Taxonomía recomendada:**

```text
docs/
  reference/       comportamiento vigente
  architecture/    arquitectura actual y ADRs
  guides/          procedimientos soportados
  product/         visión y decisiones de producto
  incidents/       incidentes cerrados
  archive/         planes, fases y conversaciones históricas
```

Cada documento histórico debería mostrar status y reemplazo actual.

### DOCS-002 — Prompts duplicados como strings embebidos

**Prioridad:** P1

Existen copias semánticas en:

- `.cortex/`.
- `cortex/setup/cortex_workspace.py`.
- Bundle Pi.
- Adapters.
- Guías.

Los bytes no siempre son idénticos, por lo que deduplicación tradicional no ayuda.

**Mejora recomendada:** assets canónicos + render/generación + validación de markers cuando Pi necesite variantes.

### DOCS-003 — Versiones y changelog

**Prioridad:** P2

El changelog contiene múltiples bloques Unreleased y las superficies declaran versiones distintas.

**Mejora recomendada:** release train único, changelog por versión y matriz de compatibilidad engine/protocol/Pi bundle.

---

## 18. Archivos potencialmente no usados o consolidables

No se encontró una gran cantidad de código inequívocamente muerto. Los candidatos más claros son:

| Candidato | Estado | Acción sugerida |
|---|---|---|
| `cortex-pi/extensions/` | Cuatro extensiones legacy; una rota por import inexistente | Archivar o eliminar tras confirmar que no se distribuye |
| `cortex/pipeline/` | API pública sin wiring de producción encontrado | Decidir SSoT, deprecar o conectar |
| `cortex/enterprise/maintenance.py` | Tests, pero sin entrypoint operacional | Exponer como CLI/scheduler o retirar del scope actual |
| `cortex/services/session_service.py` | Alias deprecated | Eliminar en release mayor |
| Stack legacy de embeddings | En uso real | Migrar, no borrar directamente |
| Clases auxiliares de decay | Sin consumidores claros | Confirmar y simplificar |
| Sync canónico Pi comentado | Código inerte | Reemplazar por ADR y eliminar comentarios extensos |
| Documentación histórica | Valiosa, no runtime | Mover a archive; no tratar como referencia vigente |

### 17.1 Política segura de eliminación

Antes de borrar una superficie pública:

1. Buscar imports estáticos y dinámicos.
2. Revisar docs y ejemplos.
3. Añadir warning de deprecación.
4. Observar al menos una release.
5. Eliminar en versión mayor o ventana anunciada.
6. Conservar guía de migración.

---

## 19. Estrategia de reducción de tamaño

### 18.1 Acciones de alto impacto

1. Optimizar/reemplazar `assets/logo.png`.
2. Mover documentación histórica a `docs/archive` o repositorio histórico.
3. Controlar qué entra en wheel y sdist.
4. Separar el bundle Pi como resource versionado, sin incluir material de desarrollo innecesario.
5. Corregir dependencias opcionales.

### 18.2 Acciones de bajo impacto

La deduplicación exacta recuperaría aproximadamente 47 KB. No merece ser prioridad.

### 18.3 Historia Git

Existen blobs históricos grandes, incluido un HTML eliminado de más de 2 MB y logos anteriores. Reescribir historia puede reducir clone, pero:

- Cambia SHAs.
- Obliga a rebase/reclone.
- Afecta forks y links.

Sólo debería hacerse si el tamaño de clone se convierte en objetivo explícito y antes de una expansión grande de colaboradores.

---

## 20. Arquitectura objetivo del engine

### 19.1 Modular monolith consciente

Python sigue siendo apropiado, pero las fronteras deben ser más nítidas:

```text
Domain
├── models de Session, Spec, docs, memory identity
├── policies de cierre y gobierno
└── protocolos

Application
├── create spec
├── mutate session
├── finalize session
├── retrieve context
└── promote knowledge

Infrastructure
├── Chroma
├── Markdown vault
├── Git
├── embeddings
├── SQLite/YAML store
└── process runner

Interfaces
├── MCP
├── CLI
├── Pi
├── WebGraph
└── adapters seleccionados
```

Las interfaces no deberían reimplementar defaults o reglas de negocio.

### 19.2 Composition root liviano

`AgentMemory` es llamado fachada, pero tiene aproximadamente 905 líneas y conoce demasiada infraestructura. Debe quedar como composition root que:

- Resuelve config/layout.
- Construye adapters.
- Inyecta servicios.
- No reimplementa lógica de dominio.

### 19.3 Persistencia operacional

Recomendación de mediano plazo:

- Markdown sigue siendo conocimiento humano/canónico.
- Chroma sigue siendo índice vectorial episódico.
- SQLite WAL maneja Sessions, operaciones MCP, manifest de instalación y colas/reconciliación.
- YAML puede mantenerse como export/interoperabilidad si es valioso.

Esto resuelve concurrencia sin abandonar la filosofía local-first.

---

## 21. ¿Tiene sentido migrar a Rust?

### 20.1 Reescritura total: no

No se recomienda migrar Cortex completo a Rust.

Razones:

- El valor está en contratos, workflows y documentación, no en loops de CPU.
- Los cuellos principales son embeddings, modelos, Chroma, filesystem, subprocess y red.
- Python encaja bien con Pydantic, MCP, Typer, ML y el ecosistema de agentes.
- Reescribir casi 48.000 líneas congelaría evolución y reproduciría defectos de dominio.
- La suite y compatibilidad acumuladas tendrían que reconstruirse.

### 20.2 Uso selectivo futuro: sí, sujeto a profiling

Rust podría ser útil para componentes aislados:

- Scanner/fingerprinter incremental.
- Cache vectorial robusto.
- Supervisor cancelable de procesos.
- Daemon cortex-net multiplataforma.
- Build de grafos grandes.

El patrón recomendado sería:

- Sidecar con protocolo estable.
- O módulo PyO3/maturin pequeño.
- Benchmarks antes y después.
- Fallback Python durante adopción.

### 20.3 Condiciones previas

No iniciar Rust hasta:

1. Corregir contratos Pi/Session/Documenter.
2. Medir perfiles reales.
3. Conectar cache correctamente.
4. Eliminar full sync innecesario.
5. Definir la interfaz estable del componente candidato.

---

## 22. Roadmap propuesto

### Ola 0 — Congelamiento de contratos y baseline

**Objetivo:** dejar de agregar drift mientras se corrige la base.

**Trabajo:**

- Declarar Pi como reference client.
- Congelar features nuevas en adapters no seleccionados.
- Capturar baseline de tests, cobertura, Ruff, mypy, tiempos y tamaño.
- Crear inventario canónico de agentes/tools.
- Definir versiones engine/MCP/Pi/schema.

**Salida:** un baseline reproducible y una política de portafolio.

### Ola 1 — Integridad P0 de Sessions y Documenter

**Trabajo:**

- Fuentes security/test y designer.
- Concurrencia Session.
- `required` en hook results.
- No CLOSED sin evidencia.
- Session ID canónico.
- `forced_reason` persistido.
- Indexado con estado fuerte/eventual explícito.

**Salida:** una Session no pierde datos ni afirma verificaciones inexistentes.

### Ola 2 — Productización Pi

**Trabajo:**

- Bundle incluido en wheel.
- Installer por plan/backup/manifest.
- Uninstall conservador.
- MCP como canal canónico.
- Eliminar colisiones con CLI bridge.
- Schema mapping tipado.
- Justfile multiplataforma.
- Typecheck y tests TypeScript.
- E2E Pi limpio/upgrade/uninstall.
- Gitignore, retención y auth de cortex-net.

**Salida:** Pi funciona desde paquete publicado y es seguro sobre proyectos reales.

### Ola 3 — MCP resiliente y modular

**Trabajo:**

- Registry de tools.
- Estado correlacionado por operation/ticket/proposal/session.
- Idempotencia.
- Cancelación o jobs consultables.
- Logging acotado/redactado.
- División del monolito.

**Salida:** timeouts y retries no provocan mutaciones fantasma.

### Ola 4 — Memoria y rendimiento real

**Trabajo:**

- EmbedderProtocol único.
- VectorCache corregido y conectado.
- Indexado selectivo.
- Identidad cross-source.
- Intent multilingüe.
- Confidence persistida.
- Benchmarks de cold/warm path.

**Salida:** mejoras de velocidad medibles y retrieval con provenance coherente.

### Ola 5 — CI, release y documentación

**Trabajo:**

- Gates graduales.
- Cobertura contractual.
- Security workflow válido.
- Permisos mínimos.
- Release desde wheel con smoke Pi.
- Taxonomía docs/archive.
- Guías generadas/verificadas.

**Salida:** el repositorio impide que los contratos vuelvan a divergir.

### Ola 6 — Simplificación y portafolio de IDEs

**Trabajo:**

- Medir uso/adopción.
- Seleccionar adaptadores Supported.
- Deprecar el resto.
- Resolver pipeline duplicado.
- Eliminar aliases y extensiones legacy.
- Considerar componentes Rust sólo con profiling.

**Salida:** menor superficie de mantenimiento sin sacrificar Pi.

---

## 23. Backlog priorizado resumido

| ID | Prioridad | Resultado esperado |
|---|---|---|
| SESS-001 | P0 | Todos los agentes Pi pueden emitir checkpoint |
| SESS-003 | P0 | Mutaciones concurrentes no pierden información |
| DOC-001/002 | P0 | El cierre refleja evidencia real y required/optional |
| DOC-003 | P0 | Nota y Session comparten ID |
| PI-001 | P0 | Bundle Pi funciona desde wheel/pipx |
| PI-002/003 | P0 | Inject/uninstall no dañan archivos del adopter |
| PI-004 | P0 | Una sola implementación por nombre de tool |
| PI-006 | P0 | Prompts y schemas se validan automáticamente |
| PI-015 | P0/P1 | Flujo Pi completo probado end-to-end |
| MCP-002 | P0/P1 | Timeout no genera mutaciones fantasma |
| MCP-003/004 | P0/P1 | Logs seguros y gobierno contextual |
| MCP-007 | P1 | Spec usa indexado selectivo por defecto |
| MEM-003/004 | P1 | Un embedder stack y cache conectado correctamente |
| CI-002/003/004 | P1 | Calidad declarada coincide con gates reales |
| WEB-001/002 | P1 | WebGraph remoto protegido y cache correcto |
| DOCS-001/002 | P1/P2 | Referencia vigente separada del histórico |

---

## 24. Métricas de éxito

### 23.1 Confiabilidad

- Cero checkpoints perdidos en test concurrente.
- Cero CLOSED sin estado de verificación explícito.
- 100% de notas de Session con ID coincidente.
- 100% de prompts oficiales válidos contra schemas.

### 23.2 Pi

- Instalación desde wheel en proyecto limpio: exitosa.
- Instalación sobre archivos existentes: cero pérdida.
- Reinjection: idempotente.
- Uninstall: elimina sólo ownership Cortex.
- E2E Deep Track: verde en sistema operativo soportado.
- Cero tool names duplicados.
- Cero imports TypeScript rotos.

### 23.3 Rendimiento

- Tiempo de `cortex_ping` sin carga de modelos.
- Tiempo create-spec cold/warm.
- Número de documentos re-embebidos por spec nueva.
- Hit rate real del VectorCache.
- Tiempo de briefing con y sin hooks.
- Workers activos después de timeout.

### 23.4 Calidad

- Ruff bloqueante.
- Tests bloqueantes.
- Cobertura con umbral decidido y aplicado.
- Mypy estricto creciendo por módulos.
- Security workflow reproducible.

### 23.5 Tamaño

- Tamaño de wheel.
- Tamaño de instalación core.
- Tamaño de bundle Pi.
- Tamaño de checkout actual vs archive.

---

## 25. Definition of Done para una mejora Cortex

Una mejora que afecta el flujo principal no debería considerarse terminada hasta cumplir:

1. Contrato de dominio actualizado.
2. Tool schema actualizado.
3. Prompt Pi actualizado.
4. Guía Pi actualizada.
5. Test unitario.
6. Test contractual prompt/schema.
7. E2E Pi relevante.
8. Migración/deprecación documentada si cambia compatibilidad.
9. Observabilidad suficiente para diagnosticar fallos.
10. Sin duplicar la misma regla en otra interfaz.

---

## 26. Respuestas directas a las preguntas iniciales

### 25.1 ¿Es posible reducir Cortex en tamaño?

Sí. La mayor reducción vendrá de documentación histórica, logo, packaging y dependencias. No de eliminar masivamente Python.

### 25.2 ¿Hay muchos archivos no usados?

No se detectó una gran masa de código muerto. Hay candidatos pequeños y concretos, además de arquitecturas duplicadas que deben consolidarse con deprecación.

### 25.3 ¿Cuál es la mejor forma de mejorarlo?

Primero corregir integridad y contratos; luego productizar Pi; después modularizar MCP/memoria; finalmente limpiar adapters, documentación y código legacy.

### 25.4 ¿Tiene sentido migrar a Rust?

No como reescritura total. Sí podría tener sentido para componentes aislados después de profiling y una vez estabilizados sus contratos.

---

## 27. Veredicto final

Cortex tiene una visión sólida, una cantidad importante de capacidades reales y una base de dominio que vale la pena preservar. Su principal problema no es Python, el tamaño del código ni la falta de features.

El principal problema es la multiplicación de fuentes de verdad:

- Prompt vs schema.
- CLI vs MCP.
- `.cortex` vs Pi.
- Pipeline público vs workflows reales.
- Docs vigentes vs planes históricos.
- Cache implementado vs cache conectado.
- Confidence declarada vs confidence persistida.

La estrategia de máximo impacto es:

```text
Pi como reference client
    ↓
contratos canónicos generados y testeados
    ↓
Sessions transaccionales y cierres verificables
    ↓
instalación Pi segura y reproducible
    ↓
MCP modular, idempotente y observable
    ↓
retrieval y cache realmente conectados
    ↓
CI que impide volver a divergir
    ↓
recién entonces simplificación adicional o componentes Rust
```

La meta no debería ser que Cortex tenga la menor cantidad posible de archivos. Debería ser que cada promesa importante tenga exactamente:

1. Una fuente de verdad.
2. Un contrato ejecutable.
3. Una implementación.
4. Un test end-to-end en Pi.

Con esa disciplina, Cortex puede volverse considerablemente más pequeño en complejidad, aunque conserve gran parte de sus capacidades.

---

## 28. Archivos de referencia principales

Los hallazgos de este documento se concentran especialmente en:

- `pyproject.toml`
- `requirements.txt`
- `cortex/__init__.py`
- `cortex/core.py`
- `cortex/mcp/server.py`
- `cortex/session/models.py`
- `cortex/session/storage.py`
- `cortex/session/service.py`
- `cortex/session/verification.py`
- `cortex/documenter/reconstruction.py`
- `cortex/documenter/persistence.py`
- `cortex/services/note_service.py`
- `cortex/services/spec_service.py`
- `cortex/retrieval/hybrid_search.py`
- `cortex/semantic/vector_cache.py`
- `cortex/semantic/vault_reader.py`
- `cortex/episodic/memory_store.py`
- `cortex/ide/adapters/pi.py`
- `cortex/webgraph/service.py`
- `cortex/webgraph/server.py`
- `cortex-pi/.pi/settings.json`
- `cortex-pi/.pi/mcp.json`
- `cortex-pi/.pi/extensions/cortex-tools.ts`
- `cortex-pi/.pi/extensions/cortex-mcp.ts`
- `cortex-pi/.pi/extensions/cortex-net.ts`
- `cortex-pi/.pi/agents/`
- `cortex-pi/justfile`
- `docs/guides/ide-pi.md`
- `.github/workflows/`
