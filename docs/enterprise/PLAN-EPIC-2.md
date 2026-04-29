# Plan de Acción: EPIC 2 - Retrieval Multi-Nivel

## Documento

- Fecha: 2026-04-26
- Proyecto: `Cortex`
- Epic objetivo: `E2 - Retrieval multi-nivel`
- Estado: **Planificación detallada (sin implementación aún)**
- Dependencia: `EPIC 1 completada`

---

## 1. Resumen Ejecutivo

### Lo que entendí del contexto actual

Objetivo de la iniciativa `Enterprise Memory Productization`: Transformar Cortex de un sistema con buena memoria híbrida a nivel proyecto a un producto capaz de ofrecer memoria empresarial transversal, gobernada y automatizable.

**Estado actual (EPIC 1 completada):**

- Se creó el paquete [cortex/enterprise/](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/enterprise/) con modelos Pydantic para `.cortex/org.yaml`
- Se implementó configuración organizacional formal con presets (`small-company`, `multi-project-team`, `regulated-organization`)
- `AgentMemory` carga `enterprise_config` sin romper backward compatibility
- `doctor` tiene scope `enterprise` y valida topología
- `setup` genera `.cortex/org.yaml` y `vault-enterprise/` automáticamente
- La metadata organizacional ya viaja con la memoria episódica
- Tests cubren carga, validación y generación de config enterprise

**Brecha actual:** Cortex tiene la topología modelada pero **NO** tiene capacidad operativa de retrieval multi-nivel. Hoy `AgentMemory` trabaja con un `vault_path` principal y una memoria episódica principal. No puede consultar memoria local + corporativa en la misma operación.

---

## 2. Mi Punto de Vista

### Fortalezas de la EPIC 1

- **Arquitectura limpia y separada:** El paquete [cortex/enterprise/](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/enterprise/) está bien aislado del core. No se ensució `AgentMemory` con lógica enterprise pesada.
- **Backward compatibility respetada:** Si no existe `org.yaml`, todo sigue funcionando como antes. Esto es crítico para no romper clientes existentes.
- **Validación robusta:** Pydantic con cross-section rules evita configuraciones inconsistentes (ej: promotion habilitado sin enterprise vault).
- **Presets opinionated:** Los tres presets dan defaults razonables para distintos perfiles de empresa.
- **Integración completa:** La config enterprise está integrada en runtime, CLI, doctor y setup desde el inicio.

### Riesgos que veo para la EPIC 2

- **Complejidad de ranking:** Fusionar resultados de múltiples fuentes (local semantic + enterprise semantic + local episodic + enterprise episodic) con RRF puede generar ranking desbalanceado o ruido.
- **Confusión de origen:** Si los hits no tienen metadata clara de origen (`scope`, `project_id`, `origin_vault`), el usuario no sabrá de dónde viene cada resultado.
- **Performance:** Consultar múltiples vaults y múltiples Chroma collections puede impactar performance si no se maneja bien.
- **Romper el core:** Existe riesgo de sobrecargar `AgentMemory` o `HybridSearch` con lógica enterprise. La recomendación del plan original es crear una capa enterprise por encima, no modificar el core.

### Recomendación arquitectónica

Mantener `AgentMemory` como fachada de proyecto y crear `EnterpriseRetrievalService` como capa superior.

Esto permite:
- No romper consumidores actuales de `AgentMemory`
- Separar responsabilidades claramente
- Evolucionar la capa enterprise sin ensuciar el core
- Testing más aislado

---

## 3. Plan de Acción Ultra Detallado para EPIC 2

### 3.1 Objetivo de la EPIC 2

Permitir que Cortex consulte de forma nativa:
- Memoria local de proyecto (vault local + episodic local)
- Memoria corporativa (`vault-enterprise` + episodic enterprise si está habilitado)
- Ambas fuentes en una sola operación con trazabilidad clara de origen

### 3.2 Definition of Done de la EPIC 2

- [ ] Se puede consultar solo memoria local (`--scope local`)
- [ ] Se puede consultar solo memoria enterprise (`--scope enterprise`)
- [ ] Se puede consultar ambas fuentes en una sola operación (`--scope all`)
- [ ] Los resultados identifican su origen (`scope`, `project_id`, `origin_vault`)
- [ ] El ranking es configurable y comprensible (pesos por fuente)
- [ ] Backward compatibility: si no hay enterprise config, comportamiento local funciona igual
- [ ] Tests cubren todos los modos de retrieval
- [ ] CLI expone `--scope` en `cortex search`

---

## 4. Historias Técnicas Detalladas

### E2-S1: Modelar scopes de retrieval
**Prioridad: P0**

**Objetivo:** Definir los modos de retrieval y la metadata de origen que debe viajar con cada hit.

**Entregables:**
- Enum `RetrievalScope` ya existe en `models.py` como `Literal["local", "enterprise", "all"]`. Verificar si alcanza o si necesita extenderse.
- Definir estructura de metadata que debe tener cada hit:
  - `scope`: "local" | "enterprise"
  - `project_id`: identificador del proyecto origen
  - `origin_vault`: path relativo del vault origen
  - `origin_persist_dir`: path relativo del Chroma origen
- Definir cómo se configuran los scopes:
  - Por CLI: `--scope local|enterprise|all`
  - Por runtime: desde `enterprise_config.memory.retrieval_default_scope`
  - Por llamada directa: parámetro en `retrieve()`

**Archivos a tocar:**
- Revisar `cortex/enterprise/models.py` - verificar si `RetrievalScope` alcanza
- Posible extensión de [cortex/models.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/models.py) - agregar metadata fields a `RetrievalHit` o `MemoryEntry`
- Revisar [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py) - entender estructura actual de hits

**Tareas específicas:**
1. Leer código actual de `RetrievalResult` y `RetrievalHit` en [cortex/models.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/models.py)
2. Leer código actual de `HybridSearch.search()` en [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py)
3. Decidir si se extiende `RetrievalHit` o se agrega metadata en un campo adicional
4. Documentar la estructura de metadata de origen en un comment o docstring
5. No implementar nada aún, solo diseñar

**Criterio de aceptación:**
- Documento o comment claro con la estructura de metadata de origen
- Decisión tomada sobre cómo extender (o no) los modelos existentes

### E2-S2: Implementar multi-vault semantic retrieval
**Prioridad: P0**

**Objetivo:** Permitir que `VaultReader` consulte múltiples vaults en lectura y fusione resultados con metadata de origen.

**Análisis de código actual:**
- `VaultReader` en [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py) actualmente recibe un solo `vault_path`
- `AgentMemory` instancia un solo `VaultReader` con `self.config.semantic.vault_path`
- `HybridSearch` compone un solo `VaultReader`

**Estrategia recomendada:** NO modificar `VaultReader` para que soporte múltiples vaults directamente. En su lugar:
1. Crear `MultiVaultReader` en `cortex/enterprise/sources.py` que:
   - Recibe una lista de vault paths con metadata (ej: `[{"path": "vault", "scope": "local"}, {"path": "vault-enterprise", "scope": "enterprise"}]`)
   - Para cada vault, instancia un `VaultReader` separado
   - Ejecuta búsqueda en cada vault
   - Agrega metadata de origen a cada hit
   - Retorna resultados fusionados
2. Opcional: Extender `VaultReader` para aceptar un `origin_metadata` en el constructor que se propague a los hits.

**Archivos a crear:**
- `cortex/enterprise/sources.py` - nuevo módulo con:
  - `class VaultSource`: dataclass con path, scope, project_id
  - `class MultiVaultReader`: facade sobre múltiples `VaultReader`

**Archivos a tocar:**
- [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py) - opcional: agregar `origin_metadata` parameter
- `cortex/enterprise/config.py` - helper para construir lista de `VaultSource` desde `enterprise_config`

**Tareas específicas:**
1. Leer código completo de `VaultReader` para entender su API interna
2. Diseñar `VaultSource` dataclass
3. Diseñar `MultiVaultReader` con método `search(query, top_k)` que:
   - Distribuye `top_k` entre fuentes (ej: si `top_k=10` y hay 2 fuentes, busca 5 en cada)
   - O busca `top_k` completo en cada y luego fusiona
   - Agrega metadata de origen a cada hit
4. Escribir tests unitarios para `MultiVaultReader`
5. Integrar con `enterprise_config` para construir lista de fuentes automáticamente

**Criterio de aceptación:**
- `MultiVaultReader` busca en múltiples vaults
- Cada hit tiene metadata de origen
- Tests unitarios pasan
- No rompe `VaultReader` existente

### E2-S3: Implementar multi-source episodic retrieval
**Prioridad: P0**

**Objetivo:** Permitir consultar memoria episódica local y enterprise si está habilitado.

**Análisis de código actual:**
- `EpisodicMemoryStore` en [cortex/episodic/memory_store.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/episodic/memory_store.py) recibe un solo `persist_dir`
- `AgentMemory` instancia un solo `EpisodicMemoryStore` con `self._runtime_episodic_dir`
- `namespace_mode` permite aislar por rama o por proyecto, pero solo dentro de un Chroma collection

**Estrategia recomendada:** Similar a semantic retrieval:
1. Crear `MultiEpisodicReader` en `cortex/enterprise/sources.py` que:
   - Recibe una lista de persist dirs con metadata
   - Para cada dir, instancia un `EpisodicMemoryStore` separado
   - Ejecuta búsqueda en cada store
   - Agrega metadata de origen a cada hit
   - Retorna resultados fusionados
2. Solo habilitar episodic enterprise si `enterprise_config.memory.enterprise_episodic_enabled == True`

**Consideraciones especiales:**
- `EpisodicMemoryStore` usa Chroma con `collection_name`. Si hay múltiples stores, ¿usamos el mismo collection name o diferentes?
- **Recomendación:** usar diferentes collection names (ej: `cortex_episodic_local`, `cortex_episodic_enterprise`) para evitar colisiones
- Mantener compatibilidad con `namespace_mode`: cada respeta su configuración

**Archivos a tocar:**
- `cortex/enterprise/sources.py` - agregar `class MultiEpisodicReader`
- `cortex/enterprise/config.py` - helper para construir lista de episodic sources

**Tareas específicas:**
1. Leer código completo de `EpisodicMemoryStore` para entender su API
2. Diseñar `EpisodicSource` dataclass con `persist_dir`, `scope`, `project_id`, `collection_name`
3. Diseñar `MultiEpisodicReader` con método `search(query, top_k)`
4. Decidir estrategia de collection names (único vs compartido)
5. Escribir tests unitarios
6. Integrar con `enterprise_config` para construir lista solo si `enterprise_episodic_enabled`

**Criterio de aceptación:**
- `MultiEpisodicReader` busca en múltiples Chroma collections
- Cada hit tiene metadata de origen
- Tests unitarios pasan
- Solo se usa si enterprise episodic está habilitado en config

### E2-S4: Fusión unificada multi-nivel
**Prioridad: P0**

**Objetivo:** Crear un servicio que compose multi-vault semantic + multi-source episodic y fusione todo con RRF y pesos configurables.

**Análisis de código actual:**
- `HybridSearch` en [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py) ya implementa RRF entre episodic y semantic
- Recibe pesos `episodic_weight` y `semantic_weight`
- Retorna `RetrievalResult` con `episodic_hits`, `semantic_hits`, `unified_hits`

**Estrategia recomendada:** NO modificar `HybridSearch`. Crear `EnterpriseRetrievalService` en `cortex/enterprise/retrieval_service.py` que:
1. **Recibe:**
   - `enterprise_config`: para saber qué fuentes habilitar
   - `local_vault_path`, `local_episodic_dir`: fuentes locales
   - `top_k`, pesos configurables
2. **Internamente:**
   - Construye lista de fuentes semánticas (local + enterprise si habilitado)
   - Construye lista de fuentes episódicas (local + enterprise si habilitado)
   - Usa `MultiVaultReader` para semantic
   - Usa `MultiEpisodicReader` para episodic
   - Implementa RRF extendido para más de 2 fuentes
3. **Retorna:**
   - `RetrievalResult` extendido con metadata de origen en cada hit
   - Posible nuevo campo `source_breakdown` con stats por fuente

**Desafío técnico: RRF para más de 2 fuentes**
RRF tradicional: `score = 1 / (k + rank)` donde `k` es constante (usualmente 60)

Para múltiples fuentes:
- **Opción A:** Fusionar todos los hits de todas las fuentes y aplicar RRF global
- **Opción B:** Aplicar RRF por fuente y luego fusionar con pesos por fuente
**Recomendación:** Opción B, permite configurar pesos por fuente (ej: `enterprise_weight=0.7`, `local_weight=0.3`)

**Archivos a crear:**
- `cortex/enterprise/retrieval_service.py` - nuevo módulo con:
  - `class EnterpriseRetrievalService`: servicio principal
  - `class RetrievalSourceConfig`: config de pesos por fuente

**Archivos a tocar:**
- [cortex/retrieval/hybrid_search.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/retrieval/hybrid_search.py) - leer para entender implementación de RRF actual
- `cortex/enterprise/config.py` - agregar config de pesos por fuente si no existe

**Tareas específicas:**
1. Leer implementación actual de RRF en `HybridSearch`
2. Diseñar `EnterpriseRetrievalService.search(query, scope, top_k)`:
   - Si `scope == "local"`: solo fuentes locales (comportamiento actual)
   - Si `scope == "enterprise"`: solo fuentes enterprise
   - Si `scope == "all"`: todas las fuentes
3. Implementar RRF extendido para múltiples fuentes con pesos
4. Agregar metadata de origen a cada hit en el resultado
5. Escribir tests unitarios para cada modo de scope
6. Escribir tests de integración con `MultiVaultReader` y `MultiEpisodicReader`

**Criterio de aceptación:**
- `EnterpriseRetrievalService` funciona en los 3 scopes
- RRF funciona con más de 2 fuentes
- Pesos son configurables
- Cada hit tiene metadata de origen
- Tests cubren todos los casos

### E2-S5: CLI ejecutable para retrieval enterprise
**Prioridad: P0**

**Objetivo:** Exponer `--scope` en `cortex search` y salida JSON enriquecida con origen.

**Análisis de código actual:**
- `cortex/cli/main.py` tiene comando `search` alrededor de la línea 800+
- `AgentMemory.retrieve()` ya existe, necesita extenderse para aceptar `scope`

**Estrategia recomendada:**
1. Extender `AgentMemory.retrieve()` para aceptar parámetro `scope`:
   - Si `scope == None` o `"local"`: usar comportamiento actual (`HybridSearch`)
   - Si `scope == "enterprise"` o `"all"`: delegar a `EnterpriseRetrievalService`
2. Extender `cortex search` CLI:
   - Agregar `--scope` option con choices `["local", "enterprise", "all"]`
   - Agregar `--show-scores` para ver score por fuente
   - Agregar `--json` para salida JSON enriquecida
3. Mantener backward compatibility:
   - Si no se pasa `--scope`, comportamiento actual (local)
   - Si no hay `enterprise_config`, "enterprise" y "all" fallan con error claro

**Archivos a tocar:**
- `cortex/core.py` - extender `AgentMemory.retrieve()` con parámetro `scope`
- `cortex/cli/main.py` - extender comando `search` con nuevas opciones

**Tareas específicas:**
1. Leer implementación actual de `AgentMemory.retrieve()`
2. Diseñar firma extendida con parámetro `scope`
3. Implementar lógica de delegación:
   - Local: usa `self.retriever` (`HybridSearch` actual)
   - Enterprise/All: instancia `EnterpriseRetrievalService` y delega
4. Extender CLI `search` con nuevas opciones
5. Agregar tests de CLI para cada modo
6. Probar manualmente con un proyecto con y sin `org.yaml`

**Criterio de aceptación:**
- `cortex search --scope local` funciona (comportamiento actual)
- `cortex search --scope enterprise` funciona si hay config
- `cortex search --scope all` funciona si hay config
- `--show-scores` muestra scores por fuente
- `--json` muestra metadata de origen
- Backward compatibility sin `org.yaml`

---

## 5. Orden de Implementación Recomendado

### Fase 1: Fundaciones (sin tocar runtime aún)
- **E2-S1:** Modelar scopes de retrieval (diseño solo, documentación)
- Leer y entender código actual de `VaultReader`, `EpisodicMemoryStore`, `HybridSearch`

### Fase 2: Multi-source readers (aislados)
- **E2-S2:** Implementar `MultiVaultReader` en `sources.py`
- **E2-S3:** Implementar `MultiEpisodicReader` en `sources.py`
- Tests unitarios de ambos

### Fase 3: Servicio de fusión
- **E2-S4:** Implementar `EnterpriseRetrievalService` con RRF extendido
- Tests de integración de retrieval enterprise

### Fase 4: Integración con runtime y CLI
- **E2-S5:** Extender `AgentMemory.retrieve()` con `scope`
- **E2-S5:** Extender CLI `search` con opciones nuevas
- Tests end-to-end de CLI

### Fase 5: Validación y hardening
- Tests de backward compatibility
- Tests con proyectos sin `org.yaml`
- Tests de performance (opcional pero recomendado)
- Documentación de uso

---

## 6. Archivos a Crear

- `cortex/enterprise/sources.py` - nuevo módulo
  - `class VaultSource`
  - `class EpisodicSource`
  - `class MultiVaultReader`
  - `class MultiEpisodicReader`
- `cortex/enterprise/retrieval_service.py` - nuevo módulo
  - `class EnterpriseRetrievalService`
  - `class RetrievalSourceConfig`
  - Funciones de RRF extendido
- `tests/unit/enterprise/test_sources.py` - tests de multi-source readers
- `tests/unit/enterprise/test_retrieval_service.py` - tests del servicio
- `tests/integration/enterprise/test_retrieval_e2e.py` - tests end-to-end

---

## 7. Archivos a Modificar

- `cortex/enterprise/models.py` - posible extensión de `RetrievalScope` o agregado de config de pesos
- `cortex/enterprise/config.py` - helpers para construir listas de sources
- `cortex/core.py` - extender `AgentMemory.retrieve()` con parámetro `scope`
- `cortex/cli/main.py` - extender comando `search`
- [cortex/semantic/vault_reader.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/semantic/vault_reader.py) - opcional: agregar `origin_metadata`
- [cortex/models.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/models.py) - posible extensión de `RetrievalHit` con metadata fields

---

## 8. Tests Requeridos

### Unitarios
- `MultiVaultReader` con 1, 2, 3 vaults
- `MultiEpisodicReader` con 1, 2 collections
- `EnterpriseRetrievalService` con cada scope (local, enterprise, all)
- RRF extendido con pesos diferentes
- Helpers de config para construir sources

### Integración
- `EnterpriseRetrievalService` + `MultiVaultReader` + `MultiEpisodicReader`
- `AgentMemory.retrieve()` con scope delegando a servicio enterprise

### End-to-end
- CLI `cortex search --scope local`
- CLI `cortex search --scope enterprise`
- CLI `cortex search --scope all`
- CLI con y sin `org.yaml`

### Backward compatibility
- Proyecto sin `org.yaml` sigue funcionando igual
- Llamadas a `retrieve()` sin `scope` usan comportamiento local

---

## 9. Riesgos y Mitigaciones

- **Riesgo 1: Performance**
  - **Problema:** Consultar múltiples vaults y Chroma collections puede ser lento.
  - **Mitigación:**
    - Usar búsqueda paralela (`asyncio` o `threads`) para múltiples fuentes
    - Configurar `top_k` por fuente para limitar resultados
    - Agregar cache opcional para búsquedas repetidas

- **Riesgo 2: Ranking confuso**
  - **Problema:** RRF con múltiples fuentes puede generar ranking desbalanceado.
  - **Mitigación:**
    - Pesos configurables por fuente en `org.yaml`
    - `--show-scores` en CLI para debug
    - Observabilidad de pesos efectivos en logs

- **Riesgo 3: Romper core**
  - **Problema:** Modificar `AgentMemory` o `HybridSearch` puede romper consumidores.
  - **Mitigación:**
    - **NO** modificar `HybridSearch`
    - Extender `AgentMemory.retrieve()` con parámetro opcional (default `None` = local)
    - Crear capa enterprise separada (`EnterpriseRetrievalService`)
    - Tests exhaustivos de backward compatibility

- **Riesgo 4: Metadata inconsistente**
  - **Problema:** Hits de diferentes fuentes pueden tener metadata diferente.
  - **Mitigación:**
    - Estandarizar estructura de metadata en `VaultSource` y `EpisodicSource`
    - Validar que todos los hits tengan campos obligatorios (`scope`, `origin`)
    - Tests de validación de metadata en resultados

---

## 10. Decisiones Pendientes

1. **Estrategia de collection names para episodic enterprise:**
   - **Opción A:** Mismo collection name, diferente namespace (puede colisionar)
   - **Opción B:** Diferentes collection names (más limpio, pero más collections)
   - **Recomendación:** Opción B con nombres explícitos
2. **Distribución de top_k entre fuentes:**
   - **Opción A:** Dividir `top_k` equitativamente (ej: `top_k=10`, 2 fuentes → 5 cada una)
   - **Opción B:** Buscar `top_k` completo en cada y luego fusionar
   - **Recomendación:** Opción B con configurable en `org.yaml`
3. **Extensión de RetrievalHit vs metadata adicional:**
   - **Opción A:** Agregar campos `scope`, `origin_vault` a `RetrievalHit`
   - **Opción B:** Usar campo `extra_metadata` dict ya existente
   - **Recomendación:** Opción A para type safety y claridad
4. **Instancia de EnterpriseRetrievalService:**
   - **Opción A:** Instanciar en `AgentMemory.__init__()` si hay enterprise config
   - **Opción B:** Instanciar on-demand en `retrieve()` cuando se pide scope enterprise
   - **Recomendación:** Opción B para no penalizar proyectos sin enterprise

---

## 11. Checklist de Validación Final

Antes de considerar EPIC 2 completada:
- [ ] Todos los tests unitarios pasan
- [ ] Todos los tests de integración pasan
- [ ] Todos los tests end-to-end pasan
- [ ] Backward compatibility verificada (proyectos sin `org.yaml`)
- [ ] CLI funciona en los 3 scopes
- [ ] Metadata de origen visible en cada hit
- [ ] RRF funciona con pesos configurables
- [ ] Documentación de uso actualizada
- [ ] Performance aceptable (no degradación significativa vs local)
- [ ] Código revisado y limpio
- [ ] No warnings en `cortex doctor --scope enterprise`

---

## 12. Próximos Pasos Después de EPIC 2

Una vez completada EPIC 2, el siguiente paso natural según el backlog es:

**EPIC 3 - Promotion pipeline de conocimiento**

Con retrieval multi-nivel operativo, se puede:
1. Identificar documentos promovibles en vault local
2. Promoverlos a `vault-enterprise`
3. Consultarlos desde retrieval enterprise

Esto completa el ciclo: topología modelada (E1) → retrieval operativo (E2) → promoción de conocimiento (E3).