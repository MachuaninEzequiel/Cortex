# Fase 12 - Enterprise Dashboard

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Crea visibilidad organizacional cross-project. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Respetar scopes enterprise de org.yaml.
- No exponer senales de un proyecto a otro sin permiso.
- Usar `EnterpriseRetrievalService` existente como referencia.

## Archivos a crear

```text
cortex/business_signal/surfaces/enterprise_report.py
tests/unit/business_signal/test_enterprise_report.py
```

## Reportes enterprise

En modo enterprise, BusinessSignal puede responder:

- Que proyectos actuales se parecen a proyectos pasados.
- Que dominios generan mas ecos de riesgo.
- Que clientes o verticales repiten patrones.
- Que conocimiento historico esta siendo reutilizado.
- Que areas tienen memoria insuficiente (knowledge gaps).

## Comando

```bash
cortex enterprise signals-report
cortex enterprise signals-report --by-project
cortex enterprise signals-report --by-client
cortex enterprise signals-report --by-domain
cortex enterprise signals-report --by-detector
```

## Scopes de visibilidad

Definir en org.yaml:

```yaml
business_signal:
  cross_project_visibility: true  # o false
  allowed_scopes: ["local", "enterprise"]
```

Si `cross_project_visibility` es false, cada proyecto solo ve sus propias senales.

## Checklist

- [ ] Reportes enterprise respetan scopes de org.yaml.
- [ ] Reporte por proyecto, cliente, dominio y detector.
- [ ] Si no hay modo enterprise, el comando avisa.
- [ ] No expone senales cross-project sin permiso.

## Gate de salida

- `pytest tests/unit/business_signal/test_enterprise_report.py` pasa.
- La organizacion puede ver como se reutiliza su memoria.

---
