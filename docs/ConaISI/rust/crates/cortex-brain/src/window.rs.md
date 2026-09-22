# rust/crates/cortex-brain/src/window.rs

## Qué tiene adentro

`launch_window(cmd: &[String])` abre una terminal nueva ejecutando el argv:

- Linux: prueba `gnome-terminal --`, `konsole -e`, `alacritty -e`, `kitty -e`, `xterm -e` si el binario está en PATH
- macOS: `osascript` → Terminal `do script`
- Windows: `cmd /C start cortex-brain <cmd>`

`which` recorre PATH. Si no hay terminal: error accionable.

## Para qué sirve

Flag `--window` del binario (BRAIN-3): brain en ventana dedicada.

## Relaciones

### Recibe de

- argv construido en `main.rs` (exe + flags)

### Envía a

- proceso de terminal del OS

### Notas de implementación observadas en el código

Best-effort; stdout/stderr del spawn se anulan. En Linux, `PATH` se parte con `MAIN_SEPARATOR` (en Unix es `:` — el split usa el separador de path del OS, no el de PATH).
