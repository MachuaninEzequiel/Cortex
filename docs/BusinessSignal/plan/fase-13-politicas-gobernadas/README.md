# Fase 13 - Politicas Gobernadas

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Permite que organizaciones maduras creen reglas sobre senales. BusinessSignal pasa de advisory a governance opcional. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Las politicas deben ser explicitamente opt-in.
- Nunca bloquear CI por defecto.
- Documentar cada policy con ejemplos claros.

## Archivos a crear

```text
cortex/business_signal/policies/__init__.py
cortex/business_signal/policies/base.py
cortex/business_signal/policies/compliance_gate.py
tests/unit/business_signal/test_policies.py
```

## Modos de CI

| Modo | Comportamiento |
|---|---|
| `advisory` | Reporta senales en CI output, no falla |
| `warning` | Marca riesgo como warning, no falla |
| `enforced` | Falla CI si se cumple condicion especifica |

Default: `advisory`. `enforced` solo para organizaciones que lo configuren explicitamente.

## Ejemplos de politicas

```yaml
# En business-signal.yaml
policies:
  - name: compliance_gate
    rule: "if compliance_echo.severity == critical and no_adr_associated"
    action: "fail_ci"
    message: "Feature de pagos activa Compliance Echo critical sin ADR asociado"

  - name: risk_notification
    rule: "if risk_echo.touches_payments"
    action: "notify_security_team"

  - name: knowledge_gap_task
    rule: "if knowledge_gap.repeated > 3"
    action: "create_documentation_task"
```

## Detalle: policies/base.py

```python
class SignalPolicy(Protocol):
    name: str

    def evaluate(self, signal: BusinessSignal,
                 context: PolicyContext) -> PolicyAction: ...

class PolicyAction(BaseModel):
    action: Literal["pass", "warn", "fail", "notify"]
    message: str
    target: str | None = None  # team, channel, etc.
```

## Checklist

- [ ] Policies son opt-in, nunca default.
- [ ] CI mode `advisory` no falla nunca.
- [ ] CI mode `enforced` solo falla con policy explicita.
- [ ] Policies se cargan desde YAML.
- [ ] Cada policy tiene nombre y mensaje claro.
- [ ] Tests cubren los tres modos de CI.

## Gate de salida

- `pytest tests/unit/business_signal/test_policies.py` pasa.
- BusinessSignal puede ejecutar policies sin romper CI existente.

---
