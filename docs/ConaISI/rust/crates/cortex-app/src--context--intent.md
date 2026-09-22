# src/context/intent.rs

## Qué tiene adentro

Detector regex de QueryIntent: Episodic (pesos 2.0/0.6), Semantic (0.6/2.0), Mixed (1/1).

Señales episódicas: temporal_ref, change_ref, pr_ref, decision_ref, incident_ref, author_ref. Semánticas: conceptual_q, arch_ref, runbook_ref, spec_ref, concept_ref. Flags `(?i)`.

`detect` umbrales 1,1. Confidence = fracción de señales del lado ganador; mixed 0.5 o 0.3 si cero señales; `redondear(..., 3)`. `matched_signals` = ep luego sem.

## Para qué sirve

Pesos adaptativos de RRF.

## Relaciones

### Recibe de

- Query string.

### Envía a

- `hybrid::search_hybrid` y el bundle (intent metadata).

### Notas de implementación observadas en el código

Lexicón fijo en código; no hay ML.
