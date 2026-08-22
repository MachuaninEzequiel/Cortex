# Eval de Retrieval ES/EN (Obra 04)

Suite que mide la calidad del retrieval real (VaultReader: BM25 + vector cosine)
contra un dataset sintético con relevancia humana-ordenada. Es el gate objetivo
para decidir cambios de modelo de embeddings.

## Uso

```bash
# Baseline / candidato:
.venv/bin/python eval/retrieval/run_eval.py --model all-MiniLM-L6-v2

# Comparar un modelo nuevo:
.venv/bin/python eval/retrieval/run_eval.py --model multilingual-e5-base

# Smoke rápido:
.venv/bin/python eval/retrieval/run_eval.py --lang es --limit 5
```

## Dataset

`dataset/{es,en}/*.md` — vault sintético de un e-commerce ficticio (34 docs,
frontmatter estilo Cortex, decisiones/specs/runbooks).
`dataset/queries.{es,en}.yaml` — 26/25 queries con docs relevantes ordenados.
Regenerar: `python eval/retrieval/generate_dataset.py`.

## Métricas

- **MRR@10** — posición recíproca del primer doc relevante (métrica principal).
- **Recall@5** — fracción de relevantes encontrados en el top-5.
- **Recall@1** — precisión del primer resultado.

## Baseline commiteado (all-MiniLM-L6-v2, backend ONNX)

| Idioma | MRR@10 | R@5 | R@1 |
|---|---|---|---|
| en | 1.0000 | 1.0000 | 0.9800 |
| es | 0.8821 | 0.9038 | 0.8077 |

**Lectura**: el modelo default es excelente en inglés y claramente más débil en
español (~12% peor en MRR). Cualquier modelo candidato debe superar este baseline
en ES sin empeorar EN (±2%).

## Gates para adoptar un modelo nuevo (Fase E del spec Obra 04)

- MRR@10 ES ≥ baseline +10% relativo.
- MRR@10 EN ≥ baseline -2% relativo.
- p50 de query ≤ 2s CPU (backend ONNX int8 si aplica).
