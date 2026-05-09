# Fase 10 - Reportes y Vault Notes

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Genera reportes Markdown accionables y notas opcionales en vault. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- Los reportes son read-only: no modifican senales ni estado.
- Las vault notes son opcionales y solo se crean bajo comando explicito.
- No escribir vault notes automaticamente.

## Archivos a crear

```text
cortex/business_signal/reporting.py
cortex/business_signal/surfaces/vault_writer.py
tests/unit/business_signal/test_reporting.py
```

## Detalle: reporting.py

```python
class SignalReportRenderer:
    """Generates Markdown reports from active signals."""

    def render_summary(self, signals: list[BusinessSignal],
                       project_id: str) -> str:
        """Full summary report in Markdown."""
        ...

    def render_signal_detail(self, signal: BusinessSignal) -> str:
        """Detailed report for a single signal."""
        ...
```

## Comandos CLI (agregar a cli.py existente)

```bash
cortex signals report                       # Reporte completo del proyecto
cortex signals report --window 30d          # Reporte con ventana temporal
cortex signals report --include-archived    # Incluir senales archivadas
cortex signals report --save                # Guardar como vault note
```

## Vault Notes

Si `--save`, guardar en:
```text
vault/signals/2026-05-09-client-mobile-redesign-historical-analogy.md
```

La nota debe tener frontmatter compatible con el vault semantico.

## Checklist

- [ ] `render_summary()` produce Markdown valido.
- [ ] Reporte incluye top analogias, riesgos y documentos recomendados.
- [ ] `--window` filtra por periodo.
- [ ] `--save` escribe vault note con frontmatter.
- [ ] Vault notes son opcionales, nunca automaticas.
- [ ] Sin senales, el reporte dice "No active signals".

## Gate de salida

- `pytest tests/unit/business_signal/test_reporting.py` pasa.
- `cortex signals report` genera reporte legible.

---
