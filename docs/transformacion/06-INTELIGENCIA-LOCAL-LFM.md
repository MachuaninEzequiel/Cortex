# Obra 06 — Inteligencia local: LFM2.5-1.2B (Liquid) [FUTURO]

> Estado: PLANIFICACIÓN TEMPRANA — no iniciar sin la investigación profunda descripta abajo.
> Investigación de contexto: 2026-08-22 (verificado contra HF Hub).

## Qué es

`LiquidAI/LFM2.5-1.2B-Instruct` — LLM generativo instruct de 1.17B parámetros
(arquitectura Liquid híbrida conv+atención), orientado a edge/CPU.

Datos verificados (HF API + model card):
- **Velocidad**: 239 tok/s decode en CPU AMD; corre bajo 1GB de memoria cuantizado.
- **Contexto**: 65,536 tokens.
- **Multilingüe**: EN, ES, AR, ZH, FR, DE, JA, KO.
- **Formatos oficiales**: safetensors (transformers), GGUF (llama.cpp), MLX,
  **ONNX** (`LiquidAI/LFM2.5-1.2B-Instruct-ONNX`) → encaja con nuestra stack ONNX.
- **Licencia LFM1.0** ⚠️: uso comercial libre SOLO bajo el umbral de
  US$10M/año de ingresos brutos anuales. Arriba del umbral requiere licencia
  separada. Para uso personal/pymes: sin problema. Revisar antes de escalar.
- Popularidad: ~512K descargas, 655 likes.

## Por qué NO reemplaza a los embedders (decisión arquitectónica)

Los embedders (MiniLM/e5) producen **vectores** para similitud coseno/RRF.
LFM2.5 genera **texto**. No hay adaptación posible que lo vuelva un embedder:
usar sus estados internos como vectores daría calidad de retrieval inferior a
un modelo contrastivo dedicado. La búsqueda vectorial queda en Obra 04.

## Uso que le vamos a dar (3 capas)

1. **Reranker generativo** — tras el retrieval híbrido (top-k), LFM2.5 lee
   query + fragmentos y reordena/filtra por relevancia real. Sube precisión
   SIN tocar los embeddings. Costo: 1 llamada LLM por búsqueda (~0.5-2s local).
2. **Summarizer local offline** — `LLMConfig` ya tiene providers
   (none/openai/anthropic/ollama); agregar provider `local-liquid` para
   resúmenes de sesión y notas sin API keys ni nube.
3. **Cerebro del ActionEngine (Obra 05)** — proponer acciones priorizadas,
   clasificar intención del usuario, redactar drafts de session notes.
   Es exactamente el perfil "liviano pero capaz, corriendo 100% local".

## Presupuesto de recursos estimado

| Recurso | Estimación |
|---|---|
| RAM (Q4 GGUF / ONNX int8) | 0.6–1 GB residente cuando se usa |
| Disco | ~0.7–2.4 GB según formato |
| Latencia por generación | segundos (no ms); solo en llamadas eventuales |
| Batería | impacto solo durante llamadas; no hay polling continuo |

Regla dura propuesta: NINGÚN componente de Cortex puede invocar al LLM en
hot-path de búsqueda salvo el reranker opt-in; todo uso debe ser explícito
o asíncrono.

## BRAIN v1 — `cortex brain` (diseño CERRADO por el dueño, 2026-08-23)

> El dueño activó esta obra con decisiones explícitas. Esto ya no es "futuro":
> es el spec ejecutable del asistente local.

### Decisiones cerradas (dueño)
1. Runtime: **llama.cpp + GGUF** (llama-cpp-python), sin Ollama ni PyTorch.
2. Comando: **`cortex brain`** — nivel-0, experto de LA CARPETA donde se ejecuta.
3. Permisos ESTRICTOS en dos niveles:
   - `READ` (default): search, doctor, stats, sesión, webgraph info. Solo lectura.
   - `SAFE_ACTION`: webgraph serve, acciones ActionEngine reversibles+instant.
     **Mutantes NUNCA se ejecutan desde el brain**: se PROPONEN con el comando
     CLI exacto para que el usuario lo corra ("propone, no ejecuta").
4. Embeddings OPT-IN por consulta: ante búsquedas de relación, el brain pregunta
   ¿preciso (e5-large, ~2GB RAM) o rápido (MiniLM, liviano)? y usa lo elegido
   solo para esa sesión.

### Arquitectura
- Proceso corto: modelo carga a RAM al abrir la terminal y muere con ella
  (sin daemon — coherente con §reglas del programa).
- Fallback determinista SIN modelo (`--no-model`): router por keywords mapea
  intents a las mismas herramientas; cero RAM, respuesta instantánea.
- Tool-calling con contrato: el LLM elige entre herramientas YA gobernadas;
  anti-alucinación estructural: toda respuesta cita rutas reales del retrieval;
  sin hits ⇒ "no encontré nada en este repo". Nunca opina sin herramienta.
- Slash commands: /help /doctor /search <q> /webgraph /stats /session /actions /quit.

### Herramientas v1 (todas read/safe sobre servicios existentes)
| tool | tier | delega en |
|---|---|---|
| memory.search | READ | mem.retrieve (RRF híbrido) |
| docs.related | READ | VaultReader.search (embeddings opt-in) |
| cortex.health | READ | doctor-lite (config/git/vault/sesión) |
| vault.stats | READ | conteos vault |
| session.current | READ | SessionService |
| webgraph.serve | SAFE_ACTION | spawn detached + reporta puerto |
| actions.propose | READ | ActionEngine scheduler (lista + comando CLI exacto) |

### Fases
- **BRAIN-1** (esta entrega): núcleo sin LLM — tools + router determinista +
  chat loop + banner + slash commands. Testeable sin TTY y sin modelo.
- **BRAIN-2**: backend llama.cpp/GGUF (LFM2.5) + tool-calling + carga/descarga
  por ciclo de vida. CI testea con backend falso scriptado.
- **BRAIN-3**: lanzador de ventana dedicada multiplataforma + logo cerebro
  (banner rich v1) + i18n completo.

### Investigación que sigue abierta (para BRAIN-2)
1. Eval reranker medible (MRR@10 post-rerank vs latencia).
2. GGUF Q4 exacto a usar + benchmark tok/s en hardware del dueño.
3. Licencia LFM1.0: releer LICENSE completo antes de distribuir.

## Investigación profunda pendiente (ANTES de implementar)

1. **Eval de reranking medible**: extender eval/retrieval/ con métrica
   "MRR@10 post-rerank" y medir ganancia real vs costo en latencia.
2. **Runtime elegido**: llama.cpp (GGUF Q4) vs ONNX Runtime (oficial LiquidAI)
   — comparar RAM/tok-s/calidad en nuestro hardware.
3. **Licencia**: leer LICENSE completo y registrar la condición de umbral;
   decidir política si Cortex crece.
4. **Detección de idioma por query** para prompts ES/EN.
5. **Diseño del contrato Action<->LLM** con Obra 05 (salida estructurada JSON,
   no texto libre).
6. **Costo energético medido** (CPU-time por tarea típica) para validar la
   promesa "liviano".

## Relación con otras obras

- Depende de: nada (es opt-in).
- Alimenta a: Obra 05 (ActionEngine), Fase C/E de Obra 04 (solo convive).
- Alternativa futura si la licencia molesta: Qwen3-1.7B / Gemma-3-1B (Apache-2.0),
  a evaluar en la investigación profunda.

## Apéndice — MrBERT-es como embedder custom futuro (evaluado 2026-08-22)

`BSC-LT/MrBERT-es`: encoder base bilingüe ES/EN, 150M params, ModernBERT,
contexto 8192, Apache-2.0, mejor STS de su familia (85.23). Verificado: BSC-LT
NO publica versión sentence-embedding derivada (revisión de su catálogo completo).

Es un modelo fundacional MLM, NO entrenado para similitud/retrieval → no usable
out-of-the-box como embedder. **Obra futura candidata**: fine-tuning contrastivo
sobre datos de vaults Cortex para crear un embedder propio español-first
(liviano, Apache-2.0, contexto 8192). Proyecto de entrenamiento, no integración.
