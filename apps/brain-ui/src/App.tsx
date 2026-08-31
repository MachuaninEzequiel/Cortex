/**
 * App — shell mínimo de Cortex Brain.
 *
 * Estado (G-A1, 2026-08-31): placeholder con el título de la app.
 * Las pantallas reales (sidebar de proyectos, chat, status bar, settings)
 * llegan en G-A7.
 *
 * Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md §2.
 */

export function App() {
  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold text-mocha-mauve">
        Hello, Cortex Brain
      </h1>
      <p className="max-w-md text-center text-sm text-mocha-subtext0">
        G-A1: scaffolding Tauri + React. La ventana abre, el motor llega en
        G-A4.
      </p>
      <p className="text-xs text-mocha-surface2">
        Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md
      </p>
    </main>
  );
}
