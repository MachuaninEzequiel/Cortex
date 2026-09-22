# cortex_core/__init__.py

## Qué tiene adentro

Paquete Python fino. `__version__ = "0.1.0"`. `__all__ = ["__version__", "native_available"]`.

`native_available()`: intenta `from cortex_core import _native`; `ImportError` → False.

El docstring indica que las rutas calientes Python usan el nativo SOLO si `CORTEX_NATIVE=1` y el módulo está presente; default = Python puro.

## Para qué sirve

Detectar si el extension module está compilado, sin fallar el import del paquete.

## Relaciones

### Recibe de

- Extensión `_native` compilada por maturin (opcional).

### Envía a

- Callers Python que consultan disponibilidad.

### Notas de implementación observaciones en el código

Este archivo no implementa scoring/store; solo el flag de disponibilidad.
