# Escritura de memoria (`remember`)

Módulos: `AgentMemory.remember` / `store_memory`, `episodic/memory_store.py`, `cortex-app::episodic` JSONL, CLI `remember` / `forget`, MCP no tiene un “remember libre” tan visible como search (el flujo de escritura fuerte es finish/documenter). `MemoryEntry` en `models.py`.

## Modelo actual

`MemoryType`: general, session, hu, adr, incident, changelog, security, pr_summary, ci_failure, conversation.

Campos: id `mem_<8 hex>`, content, tags, files, timestamp UTC, metadata (project_id, branch, repo, org), `confidence` tri-estado opcional.

Decay: fórmula, tipos permanentes. Forget: CLI. Stats: CLI.

Summarizer: LLM, no Jev.

## Hueco

`remember` acepta contenido libre. El tipo, tags y files dependen del caller (agente, CLI). Un agente puede guardar un dump como `general` sin tags, sin files, sin contraste con recuerdos verified. El ContradictionDetector NoOp no corre acá.

## TypeSafe en el write path (opt-in, nunca bloquear remember offline)

State: `{content, files_hint, existing_near_hits: [{id, type, snippet}]}` donde `existing_near_hits` sale de un search híbrido **barato** (top 5) en código — prefiltro.

```text
Choice memory_type
  criterios = el enum MemoryType (closed set; Jev no inventa tipos)

Choice primary_tag  (vocabulario cerrado del vault / config, no tags libres)
  o Noul por tag candidato si el vocabulario es largo — fan-out

Noul contradicts_verified
  "Does this new memory contradict a verified prior hit in existing_near_hits?"

Score specificity
  0: Vague / not actionable
  1: Concrete but missing files or decision
  2: Concrete, scoped to files, and states an outcome
```

Código:

```text
tipo = memory_type.choice si confidence >= 0.5 else "general"
si contradicts_verified.noul >= 0.7 → persistir con confidence=contradicted y NO borrar el verified (humano / finish)
si specificity.score < 0.5 y no hay files → persistir igual (remember no se niega) pero tag `thin` para decay más agresivo (eso sí es política de DecayConfig, no de Jev)
```

`forget` no usa Jev. Es un id.

## Relación con documenter

Finish es el write path de alta calidad (notas + confidence). `remember` es el write path informal. No duplicar el ContradictionDetector completo acá: solo contra top 5 near hits. El detector serio vive en finish.

## Qué no hacer

- Generar el `content` (el caller lo trae).
- Autotaguear con tags abiertos (Jev inventaría vocabulario; Choice closed-set).
- Rechazar el remember por noul bajo (el producto es “el agente puede recordar”; el juicio es metadata, no un muro).
