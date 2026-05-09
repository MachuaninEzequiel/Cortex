# Fase 8 - Integracion Autopilot

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Hace que Autopilot consuma senales de forma prudente segun budget profile. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- No modificar la logica core de Autopilot.
- La inyeccion debe ser configurable y deshabiliteable.
- Respetar los budget profiles existentes de Autopilot.

## Archivos a crear

```text
cortex/business_signal/surfaces/autopilot_advisory.py
tests/unit/business_signal/test_autopilot_advisory.py
```

## Archivos a revisar (no tocar si Autopilot no esta implementado aun)

```text
cortex/autopilot/context.py
cortex/autopilot/budget_profiles.py
```

## Reglas de inyeccion por budget profile

| Profile | Maximo senales | Condicion |
|---|---|---|
| `question_only` | 0 | No inyectar nunca |
| `docs_only` | 1 | Solo si type=knowledge_gap |
| `fast_code` | 1 | Solo si confidence=high |
| `deep_code` | 3 | Senales compactas |
| `finish_only` | 0 | Solo registrar confirmacion/contradiccion |

## Formato de inyeccion compacta

```text
BusinessSignal: el proyecto actual se parece a client-portal-v1.
Evidencia: 14/20 HU recientes recuperaron contexto de ese proyecto.
Revisar: ADR-004, incident-auth-refresh, session-scope-change.
No asumas que el patron se repetira; usalo como referencia historica.
```

Maximo 300 chars por senal inyectada.

## Detalle: autopilot_advisory.py

```python
class AutopilotAdvisory:
    """Formats BusinessSignal for Autopilot injection."""

    def get_advisories(
        self, signals: list[BusinessSignal],
        budget_profile: str,
    ) -> list[str]:
        """Return formatted advisories for the given budget profile."""
        ...

    def format_compact(self, signal: BusinessSignal) -> str:
        """Format a signal as compact text (<300 chars)."""
        ...

    def record_session_outcome(
        self, signal_id: str, session_confirmed: bool,
    ) -> None:
        """Record if the session confirmed or contradicted a signal."""
        ...
```

## Checklist

- [ ] `get_advisories()` respeta limites por budget profile.
- [ ] `format_compact()` produce texto <300 chars.
- [ ] En `question_only` no se inyecta nada.
- [ ] En `fast_code` maximo 1 senal high confidence.
- [ ] `record_session_outcome()` registra confirmacion/contradiccion.
- [ ] Si Autopilot no esta disponible, el modulo no falla.

## Gate de salida

- `pytest tests/unit/business_signal/test_autopilot_advisory.py` pasa.
- La inyeccion respeta budget profiles.

---
