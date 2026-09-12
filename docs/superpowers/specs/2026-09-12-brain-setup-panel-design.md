# Cortex Brain: wizard + panel de instalación (in-process)

Fecha: 2026-09-12
Rama: `feature/brain-setup-panel`
Estado: aprobado (wizard + panel en sidebar, núcleo+extra, preview→confirmar)

## Objetivo

La app de escritorio es la puerta de entrada a Cortex. Quien instala Brain
puede inicializar un proyecto, IDEs, pipeline, enterprise y skills composed
desde la UI, eligiendo carpeta, sin CLI y sin `Command` armado con strings.

## Superficie

- **Sidebar:** ítem fijo debajo de la lista de proyectos: “Instalar Cortex en una carpeta”.
- **Cero proyectos / primer arranque:** el centro es el wizard (mismo panel), no el chat vacío.
- **Con proyectos:** el ítem abre el panel en el centro (reemplaza el chat). Carpeta por defecto = proyecto seleccionado, con “Cambiar…”.
- Escape o click en un proyecto vuelve al chat.

## Acciones v1

Sobre la carpeta elegida:

- Init / setup **agent** (`.cortex`, config, `org.yaml`, vault, memoria)
- Setup **full** (agent + pipeline CI + webgraph)
- Setup **pipeline**
- Setup **enterprise** (`org.yaml` con preset)
- Skills **composed**
- **IDEs:** listar, estado, instalar, quitar
- **Doctor** resumido en el inspect
- **Abrir como proyecto** en Brain al terminar

## Contrato Tauri

Módulo: `rust/crates/cortex-brain-app/src/onboard.rs`.
Llama `cortex-setup` + doctor nativo. **No** llama `cortex-cli` (hace `process::exit`).

| Comando | Rol |
|---|---|
| `pick_project_folder` | Diálogo nativo; `Option<String>` (null = cancelar) |
| `inspect_setup_target { path }` | Snapshot: existe, `.cortex`, `org.yaml`, doctor, IDEs |
| `preview_setup { path, action, ide?, preset? }` | Dry-run: `{ path, op: create\|update, note }[]`. Cero I/O de escritura |
| `apply_setup { path, action, ide?, preset? }` | Escribe in-process. `{ ok, files[], log[] }` |
| `list_ides` | Catálogo (name, display, tier, uninstall) |
| `open_as_project { path }` | Reusa scan de proyectos y deja seleccionable esa carpeta |

`action`: `agent` | `full` | `pipeline` | `enterprise` | `composed` | `ide`.

Preview y apply comparten el plan. Apply es idempotente.

Errores: `Result<_, String>` accionable. Cancelar el picker no es error.

## Arquitectura

```
brain-ui (Sidebar + SetupPanel)
        │ invoke
        ▼
cortex-brain-app::onboard
        │
        ├── cortex-setup (templates, detector, IDE adapters, composed bundle)
        ├── graph::inspect_doctor_health
        └── tauri-plugin-dialog (folder picker)
```

## UX de una acción

1. Elegir carpeta.
2. Inspect (estado).
3. Elegir acción → Preview (lista de archivos).
4. Aplicar → log.
5. “Abrir esta carpeta en Brain”.

Si apply falla a mitad, se reporta lo escrito + el error. Sin rollback (re-aplicar completa).

## Tests (seam: `onboard`, tempdir)

1. Preview `agent` lista `config.yaml`/`org.yaml` y no crea archivos.
2. Apply `agent` los crea; segundo apply no explota.
3. `full` incluye workflows + webgraph.
4. `ide` preview nombra paths del adapter; apply escribe.
5. `enterprise` escribe `org.yaml` con preset.
6. `composed` deja skills bajo `.cortex/skills`.
7. `inspect` distingue carpeta vacía vs proyecto inicializado.
8. Acción o IDE desconocido → error, cero I/O.

## Fuera de v1

Instalar el binario `cortex` en PATH, TUI interactiva, mutaciones git, streaming `setup-log` (v1 devuelve `log[]` al final).
