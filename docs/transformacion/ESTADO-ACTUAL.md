# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-22 (cont.) — OBRA 04: Fases A, B(parcial), C, D completas

- Sello: v0.5.0-baseline-seal @ a64e350. Rama: feature/transformacion-2026-08. Suite VERDE.
- Obra 02 cerrada (fases 0-3). Ver histórico en git.
- OBRA 04:
  - Fase A fixes A1-A6 (2df3ce2, 73cdde5, 92383ce): stack vectorial sin fallos silenciosos.
  - Backend 'fastembed' genérico (b9ccd43): modelos no-MiniLM vía ONNX sin PyTorch.
  - Fase D eval suite + BASELINE (c5f40a7): MiniLM EN MRR@10=1.0 / ES=0.8821.
  - Fase B/D corrida de candidatos: ELEGIDO intfloat/multilingual-e5-large
    (ES MRR@10 0.9615 = R@1 ES +14%; EN intacto). Decisión documentada en doc 04.
  - Fase C (065fed5): bloque embedding {model, backend, language_detection,
    per_language} con retrocompat estricta, heurística ES/EN pura,
    cortex embedding-status. 17 tests nuevos.
- NUEVA obra documentada: 06-INTELIGENCIA-LOCAL-LFM.md (LFM2.5 como capa local
  futura: reranker/summarizer/ActionEngine; investigación profunda pendiente).
- MrBERT-es anotado como futuro embedder custom (fine-tune contrastivo).

## Próximo paso

- OBRA 04 FASE E (migración): default del modelo → e5-large para ES
  (`embedding.per_language.es` o single-model), comando `cortex reindex`
  (+--prune-old-caches), procedimiento con backup y rollback, docs+CHANGELOG.
- Después: P3 golden tests MCP + split server.py; P4 adelgazar main.py;
  Tramo 4 = Obra 05 UX/ActionEngine (ahora con LFM2.5 documentado como su cerebro).
