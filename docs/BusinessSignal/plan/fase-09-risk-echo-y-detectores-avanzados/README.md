# Fase 9 - Risk Echo y Detectores Avanzados

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Agrega detectores de riesgo y similitud de secuencia. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Cada detector es un archivo independiente que implementa el protocol.
- Registrar cada detector en el registry.
- Agregar tests unitarios por detector.
- Los detectores deben ser conservadores: preferir falsos negativos a falsos positivos.

## Archivos a crear

```text
cortex/business_signal/detectors/risk_echo.py
cortex/business_signal/detectors/sequence_similarity.py
tests/unit/business_signal/test_risk_echo.py
tests/unit/business_signal/test_sequence_similarity.py
```

## Detector: Risk Echo

Detecta cuando el proyecto actual se parece a una zona historica que termino en incidente, retrabajo, ADR controversial o deuda tecnica.

**Fuentes relevantes en risk_document_hits:**
- memory_type: incident, security, adr, changelog
- tags: scope-change, rework, blocked, migration, performance

**Umbrales:**
- Minimo 3 risk_document_hits del mismo proyecto historico.
- Al menos 2 tipos distintos de documentos de riesgo.

**Severidad:**
- Si hay incidentes: `warning`
- Si hay solo ADRs: `advisory`
- Si hay security: `warning` o `critical` segun cantidad

**Ejemplo de senal:**
```text
Risk Echo: el proyecto actual recupero 6 veces memorias relacionadas con auth-refresh.
En client-portal-v1, ese flujo derivo en un incidente de permisos y una ADR tardia.
Accion: revisar incidentes y ADRs antes de seguir implementando.
```

## Detector: Sequence Similarity

Detecta si el orden de avance del proyecto actual se parece al de un proyecto anterior.

**Algoritmo:**
1. Obtener sequence_fingerprint del proyecto actual.
2. Obtener sequence_fingerprints de proyectos historicos.
3. Comparar usando:
   - Jaccard similarity para sets de tags/dominios por paso.
   - Longest Common Subsequence para secuencia de dominios.
4. Si similitud > 0.6, emitir senal.

**Severidad:** siempre `info` o `advisory`. No emitir warning por similitud de secuencia solamente.

**Valor:** permite anticipar pasos siguientes probables como revision sugerida, no como certeza.

## Checklist

- [ ] `RiskEchoDetector` implementa protocol.
- [ ] Detecta incidentes, ADRs y security en risk_document_hits.
- [ ] Severidad escala con tipo de evidencia.
- [ ] `SequenceSimilarityDetector` implementa protocol.
- [ ] Usa Jaccard + LCS para comparar secuencias.
- [ ] No emite warning solo por similitud de secuencia.
- [ ] Ambos detectores registrados en registry.
- [ ] Tests con trayectorias sinteticas.
- [ ] Tests verifican que no se emite senal con poca evidencia.

## Gate de salida

- `pytest tests/unit/business_signal/test_risk_echo.py` pasa.
- `pytest tests/unit/business_signal/test_sequence_similarity.py` pasa.
- Cortex advierte ecos de riesgo con datos sinteticos.

---
