# Estructura — `cortex/autopilot/detectors`

## Para qué existe esta carpeta

cortex.autopilot — Policy + hooks layer over the cortex.session primitive.

## Árbol interno (código, sin `__pycache__`)

```
detectors/
├── ambiguous.py
├── base.py
└── default.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/autopilot/detectors/ambiguous.py` | 63 | cortex.autopilot.detectors.ambiguous — Ambiguous-request detector. |
| `cortex/autopilot/detectors/base.py` | 78 | cortex.autopilot.detectors.base — Detector protocol and resolution logic. |
| `cortex/autopilot/detectors/default.py` | 298 | cortex.autopilot.detectors.default — Built-in detectors. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.autopilot.models`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.autopilot.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
