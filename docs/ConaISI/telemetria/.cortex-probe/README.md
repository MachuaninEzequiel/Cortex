# 📦 Cortex BlackBox Probe — Telemetría Pasiva

Este paquete es un observador pasivo, transparente y de latencia cero diseñado para medir el rendimiento, uso de contexto y métricas arquitectónicas de Cortex en tu proyecto durante 1 semana.

**Garantía de Funcionamiento (100% Fail-Safe):**
> El proxy retransmite directamente la entrada y salida estándar (*stdio*) entre tu IDE y el servidor de Cortex. La captura de telemetría ocurre en un hilo secundario aislado. **Bajo ninguna circunstancia romperá, bloqueará ni desconectará tu servidor MCP**. Si el disco se llena o falla algún cálculo, el proxy continuará funcionando sin alterar un solo byte de tus respuestas.

---

## ⚡ Paso 1: Agregar a `.gitignore`

Agrega esta línea al archivo `.gitignore` de tu repositorio:

```gitignore
.cortex-probe/
```

*(Opcional)* Si deseas que los commits de git también se auditen automáticamente:
```bash
python .cortex-probe/install_hook.py
```

---

## 🔌 Paso 2: Cambiar la ruta del servidor MCP en tu IDE

Actualmente tu cliente de IA ejecuta Cortex directamente (por ejemplo: `python3 -m cortex.mcp.server`).
Para activar la medición, simplemente cambia el comando para que apunte a `proxy.py`.

A continuación tienes las instrucciones según el entorno que estés utilizando:

### Opción A: Cursor IDE (`.cursor/mcp.json` o Settings -> MCP)
Edita o crea el archivo `.cursor/mcp.json` en la raíz de tu proyecto:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python3",
      "args": [".cortex-probe/proxy.py"]
    }
  }
}
```

---

### Opción B: Claude Code CLI
Si utilizas Claude Code por terminal, puedes actualizar el servidor con un solo comando:

```bash
claude mcp add cortex python3 $(pwd)/.cortex-probe/proxy.py
```

O editando tu archivo de configuración de Claude (`~/.claude.json`):
```json
{
  "mcpServers": {
    "cortex": {
      "command": "python3",
      "args": [".cortex-probe/proxy.py"]
    }
  }
}
```

---

### Opción OpenCode (`~/.config/opencode/opencode.json`)
OpenCode guarda su configuración central en `~/.config/opencode/opencode.json`.
Dentro de la clave `"mcp"` ➔ `"cortex"`, cambia la propiedad `"command"`:

```json
{
  "mcp": {
    "cortex": {
      "type": "local",
      "command": [
        "python3",
        "/RUTA/ABSOLUTA/A/TU/PROYECTO/.cortex-probe/proxy.py"
      ],
      "enabled": true
    }
  }
}
```

---

### Opción C: Claude Desktop App (`claude_desktop_config.json`)
En Linux: `~/.config/Claude/claude_desktop_config.json`  
En macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
En Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python3",
      "args": ["/RUTA/ABSOLUTA/A/TU/PROYECTO/.cortex-probe/proxy.py"]
    }
  }
}
```

---

### Opción D: Pi Coding Agent (`pi.dev`)
En `.pi/agent/settings.json` o en tu configuración de MCP de Pi:

```json
{
  "mcp": {
    "servers": {
      "cortex": {
        "command": "python3",
        "args": [".cortex-probe/proxy.py"]
      }
    }
  }
}
```

---

### Opción E: Google Antigravity
En la configuración de servidores MCP de Antigravity (`~/.gemini/antigravity-cli/mcp/cortex` o configuración de herramientas):
Cambia el ejecutable para que invoque `python3` con el argumento `[RUTA]/.cortex-probe/proxy.py`.

---

## 🔍 Paso 3: ¿Cómo verificar que está funcionando? (En 5 segundos)

1. Abre tu IDE o terminal con tu asistente de IA.
2. Pídele al asistente que use Cortex, o simplemente ejecuta una consulta de prueba (ej: *"¿Qué specs hay en Cortex?"*).
3. Verifica que se haya creado el archivo de telemetría:
   ```bash
   cat .cortex-probe/data/mcp_events.jsonl
   ```
   Verás una línea JSON con la herramienta invocada, milisegundos y tokens estimados.
4. **¡Listo!** A partir de ahora sigue trabajando exactamente como siempre durante toda la semana.

---

## 📤 Paso 4: Al finalizar la semana (Exportar datos)

Cuando termine la semana de trabajo, simplemente ejecuta:

```bash
python .cortex-probe/export.py
```

Esto generará en pantalla un resumen de métricas y creará un archivo comprimido:
`cortex_telemetry_YYYYMMDD_HHMMSS.zip`

**Entrega ese archivo ZIP al líder técnico o investigador.**

---

## 🔄 Paso 5: Semana 2 (Cuando migren a Rust + JEV/SystemOne)

En la segunda semana, cuando el equipo comience a usar Cortex en Rust:
1. Abre `.cortex-probe/config.json`.
2. Cambia `"active_mode": "python_legacy"` por:
   ```json
   "active_mode": "rust_systemone"
   ```
3. ¡No toques nada más! El proxy automáticamente empezará a medir la versión de Rust.
4. Al final de la segunda semana vuelven a correr `python .cortex-probe/export.py` y entregan el segundo archivo ZIP.

---

## 🧹 Cómo desinstalar y borrar todo (Cero huella)

Una vez completado el estudio:
```bash
# 1. Desinstalar el hook de git (si lo habías instalado)
python .cortex-probe/install_hook.py --uninstall

# 2. Restaurar tu configuración de MCP en tu IDE al comando original de Cortex

# 3. Eliminar la carpeta de telemetría
rm -rf .cortex-probe/
```
El repositorio quedará 100% idéntico a su estado original sin rastro alguno.
