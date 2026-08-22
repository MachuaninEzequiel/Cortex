# Obra 04 — Vectorización + configuración por idioma

> Estado: PLANIFICANDO · Planificador: plan-embedding · Origen: deep-review #6 (docs/reviews/2026-08-deep-review/6-semantic-retrieval.md)
> Objetivo: reemplazar all-MiniLM-L6-v2 (384d) por modelos mejores, con CONFIG POR IDIOMA (ES/EN/multilingüe),
> corrigiendo antes los bugs silenciosos del stack vectorial que hacen la migración insegura hoy.

## Requisitos duros del usuario
- Modelo más nuevo/mejor/más eficiente que all-MiniLM-L6-v2.
- Config por idioma: modelos mejores en inglés y otros entrenados específicamente para español.
- Todo corre LOCAL en CPU de notebook (sin GPU obligatoria).

## Ejecución incremental
Este documento se completa en orden de fases. Un agente en otra sesión debe poder ejecutarlo sin preguntar nada:
leer sección → cumplir gate de entrada → tachar checkboxes con evidencia (comando + salida) → pasar a la siguiente.

## Criterio de entrada (gate global)
- [ ] TRAMO 0 cerrado: suite de tests verde como línea base (`uv run pytest -q` → 0 failed).
- [ ] Obra 01 no dejó código muerto en `cortex/embedders/`, `cortex/semantic/`, `cortex/retrieval/`.
- [ ] `git status` limpio al empezar cada fase (un commit por fase).

## Criterio de salida (gates finales)
- [ ] Los 5 fixes previos del review #6 verificados por tests que reproducen el bug.
- [ ] Modelo(s) nuevo(s) elegidos con tabla comparativa documentada y justificada.
- [ ] `config.yaml` soporta modelo por idioma + detección opcional; validado por pydantic y tests.
- [ ] Suite de evaluación ES+EN reproducible con métricas recall@k y MRR; el modelo nuevo GANA o empata contra MiniLM baseline en ambas lenguas.
- [ ] Migración de índices documentada y probada (reindex flag, caches viejas invalidadas, cero contaminación cruzada).

---

### Por qué esta fase es bloqueante

La revisión #6 lo dice textualmente: "el subsistema soporta un cambio grande de modelo de embeddings
solo después de endurecer VectorCache". Cambiar de modelo implica dimensión distinta; hoy eso rompe
silenciosamente la búsqueda. Nada de la Fase B–E se ejecuta sin esta fase cerrada.

### A1 — VECTOR_DIM=384 hardcodeada en VectorCache

- **Bug:** `cortex/semantic/vector_cache.py:41` fija `VECTOR_DIM = 384`; `put()` lanza `ValueError` con otra forma (L226-229). Cualquier modelo no-MiniLM (768d, 1024d…) es imposible.
- **Fix:** la dimensión se deriva del modelo activo, no constante global:
  1. `CacheEntry` ya tiene campo `dim` → validar contra `len(vector)` por entrada, no contra 384.
  2. El header del cache (`index.json`) guarda `model_name`, `dim` y `schema_version` derivada de `(modelo, dim)`; al abrir, si no coincide con la config actual → invalidación total automática (ver E2).
  3. Borrar la constante `VECTOR_DIM`; prohibir su reintroducción con test.
- **Test de regresión:** crear cache, escribir vectores de 768d y 384d en dos caches con distinto `model_name`; ambos deben persistir sin error y leerse íntegros.

### A2 — Fallo silencioso a mitad de batch → búsqueda devuelve vacío

- **Bug:** en `vault_reader.py:308-317` (`_embed_batch_with_cache`), si `cache.put()` lanza a mitad del loop, el `except` deja `results[idx]=None` para los índices restantes → vectores `[]` → coseno 0 → filtrados por `score <= 0`. Sin ningún log. Es el bug más grave del repo (búsqueda rota sin ruido).
- **Fix:**
  1. `fail-fast`: cualquier excepción en embed/cache propaga hacia arriba con contexto (`raise RuntimeError(f"embed failed for chunk {cid}") from e`). Nunca devolver vectores vacíos como resultado válido.
  2. Distinguir "sin embedding" (skip explícito + WARNING log) de "error de infra" (excepción).
  3. `batch_put` debe ser transaccional: escribir todo o nada (buffer en memoria + un único flush).
- **Test de regresión:** mock de embedder que falla en el elemento 3 de 10 → `sync()`/`search()` deben lanzar error visible (no devolver vacío).

### A3 — Cache sin identidad de modelo

- **Bug:** la clave es fingerprint SHA-256 del texto solamente (`vector_cache.py`); cambiar `embedding_model` reutiliza vectores obsoletos de otro modelo/dimensión. Contaminación silenciosa del ranking.
- **Fix:** fingerprint salado: `sha256(model_name + "\x00" + schema_version + "\x00" + embedding_text)`. Además guardar `model_name` en cada `CacheEntry` (o en header) y rechazar lecturas de otro modelo. La migración (Fase E) depende 100% de esto: dim distinta = cache inválida por construcción.
- **Test de regresión:** mismo texto embebido con modelo A y luego modelo B → cache miss forzado para B.

### A4 — Colisión de chunk_id por slug duplicado

- **Bug:** dos secciones H2/H3 con mismo título slugeado producen el mismo `chunk_id` (`chunker.py:181-182`); en `sync()`/`index_file()` el dict sobrescribe → sección silenciosamente no indexada. Frecuente ("## Decision", "## Context" repetidos).
- **Fix:** sufijo de posición ante colisión local: `{rel_path}#{level}-{slug}-{k}` (k=índice de aparición del slug en el doc, omitido cuando k=0 para mantener IDs existentes estables donde no hay colisión). Alternativa aceptada: siempre sufijo numérico + bump de schema_version (invalida cache una vez, aceptable porque la Fase E ya fuerza reindex).
- **Test de regresión:** doc con dos "## Context" → 2 chunks distintos, ambos recuperables.

### A5 — `update_note` destruye frontmatter + meta BM25 desincronizada

- **Bug:** `vault_reader.py:630` escribe `new_content` crudo sobre todo el archivo (título/tags originales perdidos) y no llama `_save_index_meta()` (que `index_file` sí llama, L559) → índice desincronizado.
- **Fix:**
  1. Parsear frontmatter existente, hacer merge (nuevo contenido gana en cuerpo; frontmatter preservado salvo campos explícitamente editados), serializar con `yaml_dump_safe` de `cortex.documentation.common` (de paso se elimina el duplicado local L654, deuda #6 del review).
  2. Llamar `_save_index_meta()` al final de toda escritura (`create_note`, `update_note`, `index_file`) — extraer helper `_persist_after_write()` para que no vuelva a olvidarse.
  3. Decidir el destino de `_load_index_meta()` (L454-466, nunca llamada): implementar su carga en cold-start o borrarla junto con `_save_index_meta` si se opta por recomputar BM25 siempre. No dejar la mitad muerta.
- **Test de regresión:** nota con frontmatter (título, tags, custom keys) → `update_note` → frontmatter intacto, meta en disco == meta en memoria.

### A6 — Consolidar el doble stack de embedders (pre-requisito de Fase C)

- **Deuda:** `cortex/episodic/embedder.py::Embedder` duplica Onnx/Local/OpenAI de `cortex/embedders/*`, define su propio Literal, y su path OpenAI hace un HTTP request por texto (embedder.py:79) vs batching nativo de `OpenAIEmbedder.embed_batch`.
- **Fix:** `Embedder` delega 100% en `EmbedderFactory.create(backend, model_name)`; se borra la lógica duplicada. Un solo punto donde "elegir modelo" existe — sin esto, la config por idioma habría que implementarla dos veces.
- **Test:** tests existentes de episodic siguen verdes; nuevo test verifica que episodic y semantic usan la misma instancia/clase de backend para igual config.

### Gate de salida Fase A
- [ ] Tests nuevos A1-A5 reproducen el bug antes del fix (se escriben primero, rojos) y quedan verdes después.
- [ ] `uv run pytest tests/ -q -k "vector_cache or vault_reader or chunk"` → 0 failed.
- [ ] Grep negativo: `VECTOR_DIM` ya no aparece en `cortex/`; `grep -rn "384" cortex/semantic/` solo en comentarios justificados.
- [ ] Commit único: `fix(semantic): harden vector stack before model migration (A1-A6)`.

> **Nota sobre fuentes:** el skill `websearch` no está configurado en esta sesión (sin API key Serper).
> Los números vienen del conocimiento de model cards y leaderboard MTEB (corte 2025). Antes de decidir,
> re-verificar contra https://hmqkhlplht.execute-api.eu-central-1.amazonaws.com/test2 (leaderboard MTEB)
> y las model cards de HuggingFace. **La decisión final la toma la suite de evaluación de Fase D, no la tabla.**

### Requisito de entorno: LOCAL, CPU notebook, sin GPU

Consecuencias prácticas:
- Modelos ≥1B parámetros quedan descartados por latencia (Qwen3-4B/8B solo como referencia teórica).
- El rango útil es 100M–600M parámetros con cuantización int8 vía ONNX Runtime (≈4× menos RAM, 2–4× más rápido que fp32).
- Hoy el backend `onnx.py` envuelve `chromadb.ONNXMiniLM_L6_V2`, que SOLO sabe cargar MiniLM → hay que reemplazarlo
  por un embedder ONNX genérico. Camino recomendado: librería [`fastembed`](https://github.com/qdrant/fastembed)
  (ONNX Runtime puro-CPU, modelos pre-cuantizados, soporta e5/bge-m3/arctic/Qwen3/nomic) o `optimum[onnxruntime]`.
  Se integra como un backend nuevo `"onnx-generic"` dentro del registry de `EmbedderFactory` (ya consolidado en A6).

### Tabla comparativa (candidatos realistas para CPU)

| Modelo | Dims | Params | Tamaño aprox (fp32/int8) | MTEB multilingüe/retrieval (aprox) | Velocidad CPU vs MiniLM* | Licencia | Notas |
|---|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 (baseline hoy) | 384 | 22M | 90 MB / 90 MB | débil fuera de EN | 1× | Apache-2.0 | rápido pero malo en ES |
| multilingual-e5-base | 768 | 278M | 1.1 GB / ~280 MB | sólido (MMREC ~62-65) | ~8-12× (int8 ~3-5×) | Apache-2.0 | requiere prefijos `query:`/`passage:` |
| multilingual-e5-large | 1024 | 560M | 2.2 GB / ~560 MB | muy sólido (~66-68) | ~20× (int8 ~6-9×) | Apache-2.0 | mismo prefijo; mejor calidad ES |
| bge-m3 | 1024 | 568M | 2.2 GB / ~570 MB | muy sólido; 100+ lenguas | ~20× (int8 ~6-9×) | MIT | dense+sparse+multi-vector (solo usaremos dense al inicio) |
| Qwen3-Embedding-0.6B | 1024 | 595M | 1.2 GB bf16 / ~600 MB int8 | top de su clase (~65 MMREC, instrucciones opcionales) | ~20× (int8 ~6-9×) | Apache-2.0 | 32k contexto; ONNX/GGUF comunitarios |
| nomic-embed-text-v2-moe | 768 | 475M MoE (~54M activos/token) | ~1.9 GB / ~480 MB | sólido (~61-63) | ~3-6× gracias a esparsidad MoE | Apache-2.0 | mejor ratio calidad/CPU del grupo |
| snowflake-arctic-embed-m | 768 | 110M | 450 MB / ~115 MB | bueno en EN, medio en ES | ~3-4× | Apache-2.0 | perfil EN barato |
| snowflake-arctic-embed-l-v2.0 | 1024 | 568M | 2.2 GB / ~560 MB | muy sólido EN+ES | ~20× (int8 ~6-9×) | Apache-2.0 | fuerte específicamente en retrieval ES |
| LaBSE | 768 | 471M | 1.9 GB / ~470 MB | débil en retrieval moderno (bitext 2020) | ~15× | Apache-2.0 | descartado: generación vieja |
| jina-embeddings-v3 | 1024 | 572M | 2.3 GB / — | muy sólido | ~20× | **CC-BY-NC 4.0 (no comercial)** | descartado por licencia salvo uso personal explícito |

\* Estimaciones relativas por token en CPU x86 con ONNX Runtime; medir en Fase D con benchmark propio antes de creerlas.

### Recomendaciones por perfil (vault local en notebook)

- **Perfil ES (mayoría del vault en español) — RECOMENDADO DEFAULT:** `snowflake-arctic-embed-l-v2.0` (calidad máxima en ES) si el usuario acepta ~0.5-1 s/query con int8; sino **`multilingual-e5-base`** como opción rápida (mejor que MiniLM en ES con coste moderado).
- **Perfil EN:** `nomic-embed-text-v2-moe` (rápido por MoE, multilingüe igualmente) o `snowflake-arctic-embed-m` si el vault es casi 100% EN y se quiere mínimo coste.
- **Perfil multilingüe mixto:** `multilingual-e5-base` (equilibrado) o `bge-m3` / `arctic-embed-l-v2.0` si prima calidad sobre latencia.
- **Descartes justificados:** LaBSE (generación vieja), jina-v3 (licencia NC), Qwen3-4B/8B (>1B params, inviable CPU notebook), OpenAI text-embedding-* (no local).

### Decisión final
- [ ] Ejecutar suite Fase D con 3 finalistas: `multilingual-e5-base`, `nomic-embed-text-v2-moe`, `arctic-embed-l-v2.0`.
- [ ] Elegir por regla: mejor MRR@10 promedio ES+EN que supere al baseline MiniLM por ≥10% relativo; empate técnico → el más rápido.
- [ ] Registrar elección + métricas aquí:

| Finalista | recall@5 ES | MRR@10 ES | recall@5 EN | MRR@10 EN | p50 latencia CPU | Elección |
|---|---|---|---|---|---|---|
| MiniLM-L6-v2 (baseline) | | | | | | obligatorio correr |
| multilingual-e5-base | | | | | | |
| nomic-embed-text-v2-moe | | | | | | |
| arctic-embed-l-v2.0 | | | | | | |

### Gate de salida Fase B
- [ ] Números de la tabla re-verificados contra model cards/MTEB actuales (la tabla inicial es orientativa).
- [ ] Backend ONNX genérico (`fastembed` u `optimum`) integrado y probado con al menos 2 modelos de dims distintas.

### Decisión de diseño clave: espacios vectoriales por idioma

Un modelo ES y un modelo EN distintos NO comparten espacio vectorial. Dos modos soportados:

- **Modo single-model (default, hoy):** `per_language` vacío → un solo modelo para todo. Query embebida una vez.
  Es el modo seguro; la config por idioma es opcional, no obligatoria.
- **Modo dual-index (opt-in):** si `per_language` tiene entradas → cada idioma activo tiene su PROPIO
  subíndice vectorial (`model_name` entra en el cache key por A3). La query se detecta y se busca en el
  índice de ese idioma con el modelo correspondiente. Buscar "en todos los idiomas" = embeder la query N veces
  (barato: 1 texto) y fusionar por RRF con `HybridSearch`. El costo extra es solo reindexar por idioma.

### Schema propuesto en `config.yaml`

```yaml
# ── Embeddings (compartido semantic + episodic) ──────────────
embedding:
  default_model: intfloat/multilingual-e5-base   # reemplaza a all-MiniLM-L6-v2
  backend: onnx-generic        # onnx (legacy MiniLM) | onnx-generic | local | openai
  batch_size: 32

  # Detección de idioma (solo necesaria si per_language no está vacío)
  language_detection: off      # off | heuristic   (frontmatter `lang:` siempre gana)

  # Config por idioma — vacío = modo single-model
  per_language:
    # es:
    #   model: Snowflake/snowflake-arctic-embed-l-v2.0
    #   backend: onnx-generic          # opcional, hereda el global
    # en:
    #   model: nomic-embed-text-v2-moe
```

Retro-compatible: `episodic.embedding_model` / `episodic.embedding_backend` siguen funcionando;
un validator de `CortexConfig` los migra al nuevo bloque `embedding` con un WARNING de deprecación.

### Cambios en `cortex/core.py`

```python
class EmbeddingLanguageConfig(BaseModel):
    model: str
    backend: Optional[Literal["onnx", "onnx-generic", "local", "openai"]] = None

class EmbeddingConfig(BaseModel):
    default_model: str = "intfloat/multilingual-e5-base"
    backend: Literal["onnx", "onnx-generic", "local", "openai"] = "onnx-generic"
    batch_size: int = Field(default=32, ge=1)
    language_detection: Literal["off", "heuristic"] = "off"
    per_language: Dict[str, EmbeddingLanguageConfig] = Field(default_factory=dict)
```

- `EpisodicConfig.embedding_model/backend` → campos deprecados (se mantienen un release, migrados por validator).
- `EmbedderFactory.create(backend, model_name)` pasa a ser LA única puerta de creación de embedders (A6).
- Resolución de embedder por texto:
  1. frontmatter del doc tiene `lang:` → usa `per_language[lang]` si existe, sino default.
  2. sino `language_detection == "heuristic"` → detector por stopwords+diacríticos (~30 líneas, sin deps nuevas,
     umbral configurable; langdetect queda como upgrade posterior opcional).
  3. sino → default_model.
- Cache/índices: el `model_name` resuelto acompaña a cada chunk hasta `VectorCache` (salado por A3) y al
  `.cortex_index.json` como metadato por documento.

### Detección heurística de idioma (ES vs EN, sin dependencias)

Señales: ratio de vocales acentuadas (áéíóúüñ¿¡) sobre letras; frecuencia de stopwords ES
("de la que el en y a los se del las un por con no...") vs EN ("the of and to in is that for...").
Score normalizado; empate o texto <20 palabras → default_model (nunca adivinar en corto).

### Tareas

- [ ] C1: agregar `EmbeddingConfig` + validator de retrocompat en core.py; test con config vieja (solo episodic.*) y nueva.
- [ ] C2: backend `onnx-generic` en `cortex/embedders/onnx_generic.py` vía fastembed/optimum; registro en factory; test carga e5-base y nomic-v2 dims distintas.
- [ ] C3: resolución de idioma (frontmatter > heurística > default) como módulo puro `cortex/embedders/language.py` con tests unitarios (10 casos ES, 10 EN, textos cortos ambiguos).
- [ ] C4: `VaultReader._chunks_for_doc` adjunta model resuelto por chunk; `VectorCache` lo usa en el key salado; `.cortex_index.json` registra modelo por doc.
- [ ] C5: query path: detectar idioma de la query → elegir modelo(s) → búsqueda dual-index con fusión RRF si hay >1 índice activo.
- [ ] C6: CLI: `cortex embedding-status` muestra modelo(s) activos, dims, tamaño de cache por modelo (diagnóstico post-migración).

### Gate de salida Fase C
- [ ] `uv run pytest -q -k "embedding or language or vault_reader"` → 0 failed.
- [ ] Config vieja (sin bloque embedding) sigue validando sin error, solo WARNING.
- [ ] Demo manual reproducible: vault con docs ES+EN, `per_language` configurado, query ES matchea doc ES con el modelo ES (verificado por `matched_chunk_id` y log del modelo usado).

### Propósito

Hoy NO existe ninguna medición de calidad de retrieval. Sin esta suite, "el modelo nuevo es mejor" es una
opinión. Con ella, es un número. Es el gate que decide la elección de modelo de Fase B y valida la migración
de Fase E.

### D1 — Dataset de evaluación

- Ubicación: `eval/retrieval/` (nueva carpeta, NO dentro del paquete instalable).
  - `queries.es.yaml`, `queries.en.yaml` — casos de prueba.
  - `run_eval.py` — script reproducible.
  - `results/` — salidas con timestamp + git SHA (commitear la corrida que decide la elección).
- Formato de cada caso:

```yaml
- id: es-001
  query: "cómo configuro el backend de embeddings para no usar OpenAI"
  relevant:            # rel_paths del vault considerados respuesta correcta
    - docs/guias/embeddings.md
    - examples/config-openai.yaml
  must_match_chunk: null   # opcional: exigir sección específica
```

- **Cómo construirlo sin anotadores externos:** sobre el vault real de Cortex (~docs/, examples/, templates/):
  1. Listar los 40-60 documentos más representativos.
  2. Por documento, escribir 1-2 queries como las escribiría un usuario real (no copiar frases literales del doc).
     Mitad en ES, mitad en EN; incluir queries multi-intención y negativas ("qué NO soporta X").
  3. `relevant` = el doc fuente + hasta 2 vecinos temáticos (revisión cruzada rápida).
  4. Mínimo aceptable para decidir: ≥25 queries por idioma. Meta: 40 por idioma.
- [ ] D1 hecho cuando existen ambos YAML con ≥25 queries c/u y otro agente pudo correrlos sin instrucción extra.

### D2 — Métricas

A nivel documento (agregación max-score ya existente), k = {1, 3, 5, 10}:

- **recall@k:** fracción de queries donde al menos un `relevant` aparece en top-k.
- **MRR@10:** media del recíproco del primer hit relevante en top-10 (métrica principal de decisión).
- **latencia p50/p95** de query completa (embed + búsqueda) en CPU local — se reporta, no decide sola.

Definición exacta en código compartido `eval/retrieval/metrics.py` con tests unitarios propios
(casos conocidos a mano: ranking perfecto → MRR 1.0; hit en posición 3 → 0.333).

### D3 — Script reproducible

```bash
# desde la raíz del repo, entorno del proyecto:
uv run python eval/retrieval/run_eval.py \
  --model sentence-transformers/all-MiniLM-L6-v2 --backend onnx \
  --queries eval/retrieval/queries.es.yaml eval/retrieval/queries.en.yaml \
  --vault vault --k 10 --out eval/retrieval/results/
```

Requisitos del script:
- Indexa una COPIA temporal del vault (nunca muta el vault real ni sus caches: usar workspace tmp).
- Un índice fresco por corrida (sin cache heredada) → comparación justa entre modelos.
- Salida: JSON + tabla Markdown impresa (mismo formato que la tabla de decisión de Fase B).
- Determinista: seed fija, misma versión de dependencias (`uv.lock`); registra git SHA y modelo hash.

### Gates numéricos de decisión

- [ ] El finalista elegido logra MRR@10 ≥ baseline MiniLM +10% relativo en ES (el problema real del usuario).
- [ ] En EN no empeora vs MiniLM (≥ igualdad dentro de ±2%).
- [ ] p50 latencia ≤ 2 s/query en CPU del notebook de referencia con int8.
- [ ] Si ningún finalista cumple todo → elegir el mejor compromiso y registrar aquí la decisión y su racional:

| Fecha | Modelo elegido | MRR@10 ES/EN | recall@5 ES/EN | p50 | Racional |
|---|---|---|---|---|---|

### Gate de salida Fase D
- [ ] `uv run python eval/retrieval/run_eval.py --model ... ` corre end-to-end verde para 4 modelos (baseline + 3 finalistas) y deja resultados commiteados en `eval/retrieval/results/`.
- [ ] Métricas tienen tests unitarios verdes.

### Principio

Gracias a A1+A3, la identidad de modelo vive en el cache key y en el header del índice. Por lo tanto la
migración NO requiere convertir nada: un modelo distinto invalida por construcción. Lo que hay que dar es
un camino seguro y explícito para el usuario.

### E1 — Invalidación automática (ya garantizada por A3)

- Cache key salado con `model_name` + `schema_version = hash(modelo, dim)` → vectores de MiniLM jamás
  se leen como si fueran de e5.
- Al abrir `index.json` con header de otro modelo → log WARNING claro ("cache built with X, configured Y;
  rebuilding") + rebuild transparente. Nunca error crudo ni silencio.

### E2 — Flag de reindex y comando explícito

```bash
cortex reindex --vault vault            # fuerza sync() completo con el modelo actual de config
cortex embedding-status                  # muestra modelo activo vs modelos presentes en cache/índices
```

- [ ] E2a: comando `cortex reindex` (wrapper del `sync()` existente + purge de chunks huérfanos; cubre también deuda #12: delete_note stale).
- [ ] E2b: `embedding-status` (C6) lista: modelo configurado, dims, entradas de cache por modelo, docs indexados por modelo.
- [ ] E2c: test integración: cambiar `default_model` en config → correr `reindex` → búsqueda funciona; correr SIN reindex → o bien rebuild automático correcto o mensaje claro que diga exactamente qué comando correr (nunca resultados contaminados).

### E3 — Compatibilidad de caches viejas

- Estrategia elegida: **coexistencia por modelo** — el directorio `.cortex/vectors/` pasa a ser
  `index-{model_slug}.json` + `chunks-{model_slug}.bin` (`model_slug` = nombre sanitizado). Ventajas:
  rollback instantáneo (volver a config vieja = volver a los archivos viejos), comparación A/B barata en Fase D.
  Costo: hasta 2× disco durante transición; `compact()` puede borrar caches de modelos ausentes de config
  tras 30 días (flag `--prune-old-caches`).
- ChromaDB episodic: colección nueva `{collection_name}-{model_slug}` al cambiar de modelo; la vieja queda intacta.
  Documentar que episodic se re-embebe lazy (los nuevos recuerdos ya van al nuevo espacio) y que `reindex`
  tiene flag `--episodic` para migrar todo de una vez.

### E4 — Procedimiento de migración (ejecutable paso a paso)

```bash
# 0. Backup previo
cp -r .cortex .cortex.bak-pre-migracion && cp -r .memory .memory.bak-pre-migracion
# 1. Editar config.yaml: bloque embedding con el modelo ganador de Fase B/D
# 2. Verificar estado
cortex embedding-status          # debe mostrar mismatch esperado (cache de MiniLM)
# 3. Reindexar
cortex reindex --vault vault     # o dejar que el auto-rebuild de E1 actúe
# 4. Validar calidad con la suite (ahora contra el índice real)
uv run python eval/retrieval/run_eval.py --model <ganador> ...
# 5. Rollback si algo falla
#    restaurar config anterior + rm -rf .cortex/vectors && mv .cortex.bak-pre-migracion/vectors .cortex/
```

### E5 — Documentación

- [ ] Actualizar `README.md` (sección embeddings) y `docs/guias/` con: tabla de perfiles ES/EN/multilingüe, ejemplo de `per_language`, cómo leer `embedding-status`.
- [ ] CHANGELOG: entry destacado "breaking-ish: default embedding model changed from all-MiniLM-L6-v2 to X; first run triggers full reindex".
- [ ] Nota de migración en este doc con fecha, modelo elegido y métricas finales (tabla de Fase B).

### Gate de salida Fase E
- [ ] Migración ejecutada en una copia real del vault siguiendo E4 sin errores y con suite D verde sobre el nuevo modelo.
- [ ] Rollback probado (restaurar backup → todo vuelve a funcionar con MiniLM).
- [ ] Docs actualizadas commiteadas.

## Riesgos y mitigaciones
| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Latencia inaceptable en CPU con modelos 560M (e5-large/bge-m3/arctic-l) | Alta | Medio | Preferir int8 vía fastembed; fallback documentado a e5-base/nomic-v2-moe; el gate D exige p50 ≤ 2 s. Medir ANTES de elegir, no después. |
| fastembed no soporta algún modelo finalista (p.ej. nomic MoE) | Media | Bajo | Fallback a `optimum[onnxruntime]` export manual; el backend `onnx-generic` abstrae la librería. |
| Números MTEB/model cards desactualizados o mal recordados (websearch caído en planificación) | Media | Medio | La tabla de Fase B es orientativa; la decisión la fija la suite D sobre el vault real. Re-verificar model cards al ejecutar. |
| Dataset de eval pequeño/biased (anotación por un solo agente) | Media | Medio | ≥25 queries/idioma mínimo; incluir queries negativas y multi-intención; segunda pasada de revisión cruzada si hay tiempo. |
| Dual-index duplica disco y confunde al usuario | Media | Bajo | Modo dual es opt-in; default single-model; `embedding-status` muestra qué espacio usa cada doc. |
| Cambio de modelo rompe usuarios existentes (cache gigante regenerada en frío) | Alta | Medio | Coexistencia por modelo_slug + auto-rebuild transparente con WARNING; backup en E4 paso 0; CHANGELOG claro. |
| Prefijos requeridos no aplicados (e5 exige `query:`/`passage:`) → calidad degradada silenciosamente | Media | Alto | El wrapper del modelo encapsula prefijos por tipo (query vs passage); test unitario verifica que embed() y search() usen el prefijo correcto para modelos que lo requieren. |
| Regresión en bugs ya corregidos (A1-A5) | Baja | Alto | Los tests de regresión escritos primero quedan permanentes; grep negativo de VECTOR_DIM en CI. |
| Colisión de nombres sanitizados en model_slug (dos modelos → mismo slug) | Baja | Bajo | slug incluye hash corto del nombre completo si difiere tras sanitizar. |

Orden estricto; cada fase tiene su propio gate de salida. Entre fases: commit + actualizar `ESTADO-ACTUAL.md`.

```
A1 → A2 → A3 → A6 (consolidar embedders) → A4 → A5     [Fase A, bloqueante]
   ↓
C2 (backend onnx-generic) → C3 (detección idioma) → C1 (schema config)   [Fase C infra]
   ↓
D1+D2+D3 (suite de evaluación con el modelo VIEJO como baseline)         [Fase D primero con MiniLM]
   ↓
B (correr 3 finalistas en la suite → tabla de decisión → elegir)        [Fase B decisión]
   ↓
C4 → C5 → C6 (conectar config por idioma al reader/cache/query)
   ↓
E1-E4 (migración del modelo elegido) → E5 (documentación)
```

Racional del entrelazado C/D/B:
- La suite D se construye ANTES de elegir modelo y corre primero contra MiniLM → baseline medido, no asumido.
- La Fase B "investigación" se cierra con la corrida real de finalistas, no con la tabla teórica.
- El schema de config (C1) puede avanzar antes de elegir modelo porque es agnóstico del ganador.

## Checklist maestro

- [ ] Fase A cerrada (gate: tests de regresión verdes, sin VECTOR_DIM).
- [ ] Fase C infra (C1-C3) cerrada.
- [ ] Fase D suite construida y corriendo baseline.
- [ ] Fase B decisión tomada con métricas reales registradas.
- [ ] Fase C completa (C4-C6).
- [ ] Fase E migración ejecutada + rollback probado + docs.
- [ ] ESTADO-ACTUAL.md actualizado con cierre de la Obra 04.

> Nota para el ejecutor: si algo de esto ya está hecho por otra obra (p.ej. A6 por la poda de Obra 01),
> verificar el gate correspondiente y marcar sin repetir trabajo. Ante duda entre dos opciones técnicas,
> elegir la que mantenga retrocompatibilidad con configs existentes.


## DECISIÓN DE MODELO (2026-08-22, medida con eval/retrieval)

Corrida real del pipeline sobre dataset ES/EN (34 docs, 51 queries). Resultados:

| Modelo | Tamaño | Dim | ES MRR@10 | EN MRR@10 | ES R@1 | ms/query |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 (baseline) | 0.09GB | 384 | 0.8821 | 1.0000 | 0.808 | 21.6 |
| paraphrase-multilingual-MiniLM-L12-v2 | 0.22GB | 384 | 0.9038 (+2.5%) | 0.9800 | 0.808 | 54.1 |
| paraphrase-multilingual-mpnet-base-v2 | 1.0GB | 768 | 0.9167 (+3.9%) | 0.9533 | 0.865 | 17.0 |
| **intfloat/multilingual-e5-large** ✅ | 2.24GB | 1024 | **0.9615 (+9.0%)** | **1.0000** | **0.923** | 61.2 |

**ELEGIDO: intfloat/multilingual-e5-large** como default para español.
- R@1 en español +14% relativo (0.808→0.923): la métrica de mayor impacto UX.
- Empata el baseline perfecto de inglés; los otros candidatos quedan descartados.
- +9% vs gate de +10%: aceptado explícitamente porque domina todas las demás
  métricas y el costo (61ms/query) está muy lejos del gate de 2s.
- Backend nuevo `fastembed` agregado a EmbedderFactory (ONNX puro, sin PyTorch).
- Pendiente Fase E: considerar cuantización int8 y evaluarla con la misma suite.

### RECOMENDACIÓN default global (2026-08-23, sesión P-bugs/P4-P8)

**Mantener PER-LANGUAGE como política por defecto** (EN=all-MiniLM-L6-v2 onnx ·
ES=intfloat/multilingual-e5-large fastembed), NO flip a single-model global.

Fundamento medido:
- EN-only con MiniLM: MRR@10=1.0 y R@1 perfecto en el dataset — forzar e5-large
  global cobraría 2.2GB RAM + dim 1024 (×2.7 de store) + ~61ms/query a proyectos
  que no lo necesitan.
- ES con MiniLM era EL dolor del dueño (MRR 0.8821); per-language ya lo resuelve
  (0.9615). El template de proyectos nuevos ya genera el bloque per-language.
- Single-model e5-large queda como OPCIÓN documentada para proyectos
  multilingüe-first (misma config, un solo modelo): cambiar
  `embedding.model` global; el código ya lo soporta.

**Flip final + reindex del vault real: requieren al dueño** (validación de
percepción de calidad). Comando listo: `cortex reindex --prune-old-caches`.

### int8 — plan concreto de seguimiento (NO ejecutado aún)

fastembed no publica variante int8 de e5-large (catálogo: solo fp32 2.24GB).
Pasos cuando se ejecute:
1. `onnxruntime.quantization.quantize_dynamic` sobre el ONNX descargado
   (~560MB esperado) → modelo local.
2. Nuevo backend `fastembed-int8` o carga directa ORT en EmbedderFactory
   (dim 1024, prefijos query:/passage:).
3. Correr `eval/retrieval/run_eval.py` con ese backend; gate: ES MRR ≥ 0.93
   (-3% tolerado vs fp32) y latencia p50 ≤ 61ms×0.5.
4. Decidir adopción con la tabla comparativa nueva junto a esta sección.


Descartados también (investigación 2026-08-22):
- LiquidAI/LFM2.5-1.2B-Instruct: es LLM generativo, no embedder → capa futura
  de inteligencia local (ver docs/transformacion/06-INTELIGENCIA-LOCAL-LFM.md).
- BSC-LT/MrBERT-es: encoder base MLM sin entrenamiento contrastivo → obra futura
  de fine-tuning como embedder custom español-first (apéndice en doc 06).
