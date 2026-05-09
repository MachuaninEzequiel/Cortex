# Fase 11 - Doctor y Observabilidad

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Hace visible el estado de BusinessSignal y detecta problemas. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Doctor no modifica archivos, solo reporta.
- Integrar con `cortex doctor` existente si es posible.

## Archivos a crear

```text
cortex/business_signal/doctor.py
tests/unit/business_signal/test_doctor.py
```

## Doctor debe validar

1. **Config**: BusinessSignal habilitado/deshabilitado, config presente o defaults.
2. **Telemetria**: eventos capturados, ultimo evento, tasa de captura.
3. **Detectores**: cantidad cargados, versiones, errores recientes.
4. **Senales**: activas, archivadas, dismissed, false_positive_rate por detector.
5. **Retencion**: tamano de JSONL, si necesita rotacion.
6. **EnrichedItem**: verificar si tiene origin_project_id (Fase 0 completada).
7. **project_id**: verificar si esta configurado en config.yaml.
8. **Feedback**: cantidad de feedback recibido, tasa de utilidad.

## Ejemplo de salida

```text
cortex signals doctor

✅ BusinessSignal Config
   Enabled: true
   Project ID: client-mobile-redesign

✅ Telemetry
   Events captured: 47
   Last event: 2h ago
   Retention: 47/5000 (0.9%)

✅ Detectors
   Loaded: 3/3 (project_concentration v1, risk_echo v1, sequence_similarity v1)

⚠️ Signals
   Active: 2
   Archived: 1
   False positive rate (project_concentration): 15% (OK)

✅ Feedback
   Total: 8 feedbacks
   Useful: 5 | Not useful: 2 | False positive: 1
```

## Checklist

- [ ] Doctor valida config, telemetria, detectores, senales, retencion.
- [ ] No modifica archivos.
- [ ] Emite warnings claros cuando faltan pre-requisitos.
- [ ] Verifica que EnrichedItem tiene origin metadata.
- [ ] Calcula false_positive_rate por detector.
- [ ] `cortex signals doctor` funciona sin datos previos.

## Gate de salida

- `pytest tests/unit/business_signal/test_doctor.py` pasa.
- Un usuario puede diagnosticar por que BusinessSignal no emite senales.

---
