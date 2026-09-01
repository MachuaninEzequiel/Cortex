# 🦀 Guía de Coexistencia y Migración: Cortex Python a Cortex Rust

> **Para desarrolladores y beta testers:** Esta guía explica cómo probar y utilizar la nueva versión de Cortex en Rust (**Cortex CLI** y **Cortex Brain Desktop**) en paralelo con tu instalación actual de Cortex en Python, **sin romper tus proyectos, sin colisiones de comandos y sin alterar tu configuración previa**.

---

## 🧭 1. Principios de Coexistencia (Zero-Breakage)

Cortex Rust fue diseñado bajo el principio de **paridad estricta y coexistencia pacífica**:

1. **Tu entorno de Python sigue intacto:** El comando global `cortex` (instalado mediante `pipx`) sigue respondiendo exactamente igual en tu terminal.
2. **Archivos de proyecto compartidos:** Ambas versiones leen y escriben en la misma estructura estándar (`vault/` para notas y `.cortex/` para sesiones y configuración). Ninguna versión corrompe los archivos de la otra.
3. **Embeddings y Caché Aislados:** El nuevo motor de embeddings valida la identidad y dimensión del modelo; si cambiás entre modelos, el índice se actualiza automáticamente sin mezclar vectores obsoletos.

---

## 🧪 2. Estrategia Recomendada: Sandbox / Repositorio de Pruebas

Para evaluar la nueva versión con total tranquilidad y realizar pruebas comparativas A/B:

```bash
# 1. Clonar tu repositorio en una carpeta de pruebas aislada
git clone <url-de-tu-repo> ~/pruebas/mi-proyecto-cortex-rust

# 2. Posicionarte en la carpeta de pruebas
cd ~/pruebas/mi-proyecto-cortex-rust
```

*(Si no deseás clonar todo el repositorio, simplemente hacé un respaldo rápido de tu carpeta de metadatos: `cp -r .cortex .cortex.backup`).*

---

## 📥 3. Instalación de Cortex Rust

Tenés dos componentes disponibles: la **Aplicación de Escritorio (Cortex Brain)** y el **CLI Nativo (`cortex-rs`)**.

### Opción A: Cortex Brain Desktop (App Gráfica con LLM Local)
Ideal para explorar el **WebGraph visual**, auditar la salud con **Doctor** y chatear con el modelo local **Liquid LFM2.5**.

* **En Windows:** Descargá `Cortex Brain_<version>_x64-setup.exe` desde la sección [Releases de GitHub](https://github.com/MachuaninEzequiel/Cortex/releases), ejecutá el instalador y abrila desde el Menú Inicio.
* **En macOS:** Descargá `Cortex Brain_<version>_universal.dmg` (compatible con Apple Silicon M1/M2/M3/M4 e Intel), arrastrá la app a tu carpeta `Applications` y ejecutala.
* **En Linux:** Descargá el paquete `.deb` (`sudo dpkg -i cortex-brain_amd64.deb`) o ejecutá el binario portable `/ruta/target/release/cortex-brain`.

---

### Opción B: CLI Nativo de Rust (`cortex-rs`)
Si querés compilar e instalar el CLI nativo en tu sistema sin sobreescribir el comando `cortex` de Python:

```bash
# 1. Clonar y compilar Cortex Rust
git clone https://github.com/MachuaninEzequiel/Cortex.git cortex-source
cd cortex-source

# 2. Compilar en modo Release
npm --prefix apps/brain-ui run build
cd rust && cargo build --release -p cortex-cli -p cortex-brain-app --features llama

# 3. Instalar con un alias seguro en ~/.local/bin
mkdir -p ~/.local/bin
cp target/release/cortex-cli ~/.local/bin/cortex-rs
cp target/release/cortex-brain ~/.local/bin/cortex-brain
```

> **Verificación de comandos en tu terminal:**
> * `cortex --version` $\to$ Ejecuta la versión de **Python** (`~/.local/bin/cortex`).
> * `cortex-rs --version` $\to$ Ejecuta la versión de **Rust** (`~/.local/bin/cortex-rs`).
> * `cortex-brain` $\to$ Lanza la **App de Escritorio**.

---

## 🤖 4. Desplegar los Nuevos Agentes y Skills

En tu repositorio de prueba, desplegá la nueva arquitectura de **Skills Composed** (inspirada en los estándares abiertos de Matt Pocock) y la tríada reestructurada de agentes:

```bash
cd ~/pruebas/mi-proyecto-cortex-rust

# 1. Inicializar la estructura base de gobernanza y vault
cortex-rs setup init

# 2. Desplegar la Tríada Thin + Craft y la Familia Composed
cortex-rs setup composed
```

### ¿Qué instala este comando?
1. **Tríada de Agentes Thin + Craft On-Demand:**
   * `/cortex-sync` (`cortex-sync.md`) con proposal mode y pericia en `cortex-sync-spec-craft.md`.
   * `/cortex-SDDwork` (`cortex-SDDwork.md`) con pericia en `cortex-SDDwork-implement-craft.md`.
   * `/cortex-documenter` (`cortex-documenter.md`) con pericia en `cortex-documenter-close-craft.md`.
2. **Familia de Skills Composed:** 8 skills abiertas (`grill/`, `to-spec/`, `to-tickets/`, `implement/`, `tdd/`, `diagnose/`, `review/`, `glossary/`) con ciclo de vida por fases (`CheckpointPhase`).

---

## 🔌 5. Configurar el Servidor MCP en tu IDE / Agente

Los clientes de IA (Claude Code, Cursor, Windsurf, Codex, etc.) se conectan a Cortex vía **transporte stdio**. Podés alternar qué servidor usar fácilmente:

### Método 1: Automático mediante `ide setup`
En tu carpeta de proyecto:
* **Para usar el MCP de Rust:**
  ```bash
  cortex-rs ide setup cursor       # o claude-code, windsurf, vscode, etc.
  ```
* **Para volver al MCP de Python:**
  ```bash
  cortex ide setup cursor
  ```

### Método 2: Manual por Proyecto (`.mcp.json`)
En el archivo `.mcp.json` de tu proyecto:
```json
{
  "mcpServers": {
    "cortex": {
      "command": "cortex-rs",
      "args": ["mcp-server", "--stdio", "--project-root", "."]
    }
  }
}
```

> **Compatibilidad garantizada:** Ambas versiones exponen exactamente el mismo catálogo de **32 tools canónicas** (`cortex_sync_ticket`, `cortex_create_spec`, `cortex_session_checkpoint`, `cortex_search_semantic`, etc.). Tus prompts y agentes funcionarán de forma idéntica, pero con latencias de respuesta en sub-milisegundos en Rust.

---

## 🧬 6. Embeddings ONNX y Modelos por Idioma

Es importante distinguir los dos tipos de modelos que utiliza Cortex:

1. **LLM Conversacional de Chat (GGUF):** Utilizado exclusivamente dentro de la app Cortex Brain (*Liquid LFM2.5 1.2B*).
2. **Embeddings de Búsqueda Semántica (ONNX):** Utilizado por el CLI y MCP para vectorizar notas en `vault/` y la memoria episódica.

### Enrutamiento por Idioma (`config.yaml`)
Cortex detecta automáticamente el idioma de tus consultas y documentos:
* **Inglés (`en`):** Usa `all-MiniLM-L6-v2` (384 dimensiones).
* **Español (`es`):** Usa `intfloat/multilingual-e5-large` (1024 dimensiones) para máxima precisión de búsqueda y retrieval.

```yaml
embedding:
  language_detection: heuristic
  per_language:
    en:
      model: all-MiniLM-L6-v2
      backend: onnx
    es:
      model: intfloat/multilingual-e5-large
      backend: fastembed
```

> **¿Qué pasa con mis documentos anteriores?**
> Gracias a la clave salada con identidad de modelo (`sha256(model_name + schema_version + texto)`), si el sistema detecta un cambio de modelo o dimensión, re-indexa los documentos en limpio sin corromper el caché anterior.

---

## ⏪ 7. Rollback Inmediato (¿Cómo volver atrás?)

Si en algún momento querés regresar 100% al flujo previo de Python:

1. **En tu IDE:** Ejecutá `cortex ide setup <tu-ide>` para restaurar el comando `"cortex"`.
2. **En tu terminal:** Seguí usando `cortex` (que apunta a tu instalación de pipx).
3. **En Git:** Todas las versiones estables anteriores permanecen intactas en los tags de Git (`v0.5.0-baseline-seal`, `v1.0.0`, `v2.0.0`). Podés volver a cualquier commit previo con `git checkout <tag>`.
