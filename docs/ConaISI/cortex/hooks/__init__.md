# cortex/hooks/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/hooks/__init__.py` (4 líneas).
- **Módulo Python:** `cortex.hooks`.
- **Constantes / símbolos de módulo:** `__all__`
- Archivo sin clases/funciones de módulo ni docstring (típicamente reexportes o marcador de paquete).

## Para qué sirve

Marcador de paquete o reexportes. Ver lista de imports y de quién lo importa.

## Relaciones

### Recibe de

- `cortex.hooks.agent_hooks` (CortexHook, CortexLangChainCallback)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 4.
Reexportes observados:
- cortex.hooks.agent_hooks: CortexHook, CortexLangChainCallback

---
Fuente: código de `cortex/hooks/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
