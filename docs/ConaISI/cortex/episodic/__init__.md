# cortex/episodic/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/episodic/__init__.py` (6 líneas).
- **Módulo Python:** `cortex.episodic`.
- **Constantes / símbolos de módulo:** `__all__`
- Archivo sin clases/funciones de módulo ni docstring (típicamente reexportes o marcador de paquete).

## Para qué sirve

Marcador de paquete o reexportes. Ver lista de imports y de quién lo importa.

## Relaciones

### Recibe de

- `cortex.episodic.embedder` (Embedder)
- `cortex.episodic.memory_store` (EpisodicMemoryStore)
- `cortex.episodic.summarizer` (Summarizer)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 6.
Reexportes observados:
- cortex.episodic.embedder: Embedder
- cortex.episodic.memory_store: EpisodicMemoryStore
- cortex.episodic.summarizer: Summarizer

---
Fuente: código de `cortex/episodic/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
