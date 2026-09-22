# src/context/domain_detector.rs

## Qué tiene adentro

`DomainMatch`, `DomainRules`, `DomainDetector`. Scoring: patrones de archivo 0.6 + keywords de contenido 0.4. Fallback cosine contra centroides precomputados all-MiniLM-L6-v2 si no llega al umbral. `default_model_dir()`.

## Para qué sirve

Etiquetar el dominio temático del trabajo en curso (`detected_domain` / `domain_confidence`).

## Relaciones

### Recibe de

- Files + contenido del observer; OnnxEmbedder/centroides.

### Envía a

- `WorkContext` y filtros posteriores.

### Notas de implementación observadas en el código

Replica el pipeline chroma ONNXMiniLM_L6_V2 del embedder Python con la misma tabla de descripciones (en el fuente).
