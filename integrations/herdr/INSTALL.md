# Cortex Companion — plugin de herdr (G-B6a)

El Companion de Cortex (`cortex-companion`) como **pane overlay sticky**
dentro de [herdr](https://github.com/herdrdev/herdr), el terminal workspace
mouse-first donde vivís mientras codeás. Sin herdr, el binario corre igual
de solo en cualquier terminal (ver **Standalone**).

**Requisitos**: herdr ≥ 0.8.0 (`herdr -V`) y el binario `cortex-companion`
(en PATH). Las acciones del manifest invocan también el CLI `cortex`
(`cargo install --path rust/crates/cortex-cli`).

## Instalar

```bash
# 1) binario del Companion (si no lo tenés):
cargo install --path rust/crates/cortex-companion

# 2) link del plugin desde el repo (usa el manifest de este directorio):
herdr plugin link <ruta-al-repo>/integrations/herdr
```

`herdr plugin install <owner>/<repo>` funcionará cuando exista la release
pública del plugin (misma convención GitHub del marketplace de herdr); por
hoy, `link` es el camino soportado.

## Verificar

```bash
herdr plugin list                                # → cortex.companion 0.1.0
herdr plugin action list --plugin cortex.companion
#   → open, next, status, doctor (4 acciones, contexto workspace)
```

**Paso manual (UI)** — abrir el pane Companion dentro de tu sesión herdr:

```bash
herdr plugin pane open --plugin cortex.companion --entrypoint companion --placement overlay
```

Tenés que ver el Home del Companion (proyecto, rama, sesión, doctor-lite).
Si preferís un acceso por tecla, agregalo en `~/.config/herdr/config.toml`
(sintaxis real de `[[keys.command]]`, verificada contra
`herdr --default-config`; `type = "shell"` corre el CLI destacado y el pane
queda abierto en la sesión):

```toml
[[keys.command]]
key = "prefix+c"
type = "shell"
command = "herdr plugin pane open --plugin cortex.companion --entrypoint companion --placement overlay"
```

## Uso

- **Dentro de un pane de proyecto**: el Companion toma el `cwd` del pane
  como `project_root` — la sesión, el vault y las acciones que ves son las
  de ese proyecto. Si querés fijar otro, lanzá el pane con `--cwd <ruta>`.
- Las acciones `next` / `status` / `doctor` imprimen la salida canónica del
  CLI (`--json` donde existe) en el pane que herdr abre para ellas.
- **Mouse-first**: click en botones/filas, rueda para scroll, `Esc`/`q` para
  volver/salir (`q` tipea en los inputs de Search/Brain; `Ctrl+C` sale). Las
  mutaciones siempre pasan por el modal de aprobación con el efecto exacto.

## Troubleshooting

| Síntoma | Causa / arreglo |
|---|---|
| `plugin not found` tras link | el manifest vive en `integrations/herdr/` — link **esa carpeta**, no la raíz del repo |
| Pane abre y cierra al toque | `cortex-companion` no está en PATH del server de herdr (el server hereda el PATH del shell que lo lanzó): `which cortex-companion`; reabrí el server o instalá con `cargo install` |
| El overlay no recibe clics | terminal sin reporte de mouse o bug de versión: abrí el pane en split — `herdr plugin pane open --plugin cortex.companion --entrypoint companion --placement split` (o cambiá `placement` en una copia local del manifest) |
| `min_herdr_version` rechaza | actualizá herdr (`herdr update`) a ≥ 0.8.0 |
| `No such command` en una acción | el CLI `cortex` no está instalado (ver Install) o el proyecto no es workspace Cortex — el Home lo dice explícito (P6/P9, nunca silencio) |

## Seguridad (modelo de confianza)

Como cualquier plugin de herdr, **el manifest corre código ordinario con tus
permisos de usuario**: el pane ejecuta `cortex-companion` y las acciones
ejecutan el CLI `cortex`. Revisá `herdr-plugin.toml` antes de linkear de un
repo ajeno (`herdr plugin install` muestra preview interactivo de comandos).
El Companion no abre red, no envía telemetría y no escribe fuera de lo que
el propio CLI de Cortex escribiría; ninguna mutación se ejecuta sin tu clic
explícito en el modal, y cada una queda auditada en `.cortex/action_log`.

## Standalone (sin herdr)

```bash
cortex-companion                          # Home del workspace actual
cortex-companion --project-root <ruta>    # otro proyecto
cortex-companion --model <gguf>           # brain con LLM local (feature llama)
```

Corre en cualquier terminal con ratatui; herdr solo aporta el sticky
overlay, la acción rápida y el contexto de workspace.
