---
title: cortex (Dashboard TUI Interactivo)
description: Interfaz visual de terminal interactiva construida en Rust con Ratatui.
---

Al ejecutar `cortex` sin ningún argumento en una terminal interactiva, se despliega de forma instantánea el **Dashboard TUI** de Cortex, desarrollado sobre la librería de renderizado [`ratatui`](file:///home/chucho/Cortex/rust/crates/cortex-tui).

```bash
cortex
```

---

## Pantallas Disponibles en la TUI

La TUI ofrece una navegación fluida entre diferentes paneles de control:

1. **`Home` (Pantalla Principal):**
   * Estado de la sesión activa y duración.
   * Resumen de salud del vault y memoria episódica.
   * Acciones recomendadas por el ActionEngine en tiempo real.
   * Atajos rápidos para tareas comunes.
2. **`Search` (Búsqueda Interactiva):**
   * Barra de búsqueda reactiva en vivo con scoring híbrido RRF.
   * Previsualización instantánea de notas del Vault y eventos episódicos.
   * Filtros dinámicos por tags y tipo de documento.
3. **`Sessions` (Historial de Sesiones):**
   * Lista tabular de todas las sesiones (`open`, `closed`, `handoff`, `abandoned`).
   * Inspección detallada de checkpoints, tareas, duración y reclamos.
4. **`Actions` (Aprobación de Decisiones):**
   * Visualización del pipeline de sugerencias de `cortex next`.
   * Posibilidad de aceptar o descartar propuestas interactivamente con teclas de acceso rápido.
5. **`Doctor` (Diagnóstico Visual):**
   * Panel con el estado de salud de todos los prerrequisitos del sistema en tiempo real.
6. **`WebGraph` (Monitor de Grafo):**
   * Exploración de nodos de conocimiento y clusters conceptuales.

---

## Atajos de Teclado Globales

| Tecla | Acción |
| :--- | :--- |
| <kbd>Tab</kbd> / <kbd>Shift+Tab</kbd> | Alternar entre paneles y vistas. |
| <kbd>1</kbd> .. <kbd>6</kbd> | Salto directo a pantallas (Home, Search, Sessions, Actions, Doctor, WebGraph). |
| <kbd>↑</kbd> / <kbd>↓</kbd> o <kbd>j</kbd> / <kbd>k</kbd> | Navegación vertical en listas y tablas. |
| <kbd>Enter</kbd> | Abrir detalle / Aceptar acción. |
| <kbd>Esc</kbd> | Volver a la pantalla previa. |
| <kbd>q</kbd> | Salir de la TUI. |

---

## Comportamiento en Entornos No Interactivos

Si se invoca `cortex` en un entorno donde `stdout` no es un terminal interactivo (por ejemplo, en un script de bash o un pipeline de CI pipado con `| cat`), Cortex emite automáticamente un snapshot formateado del dashboard y finaliza limpiamente con código de salida `rc=0`.
