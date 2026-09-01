# Guia de Coexistencia, Compilacion y Migracion: Cortex Python a Cortex Rust

> **Para desarrolladores y beta testers (Windows, macOS y Linux):** Esta guia explica como compilar, probar y utilizar la nueva version de Cortex en Rust (**Cortex CLI** y **Cortex Brain Desktop App**) en paralelo con tu instalacion actual de Cortex en Python, **sin romper tus proyectos, sin colisiones de comandos y sin alterar tu configuracion previa**.

---

## 1. Principios de Coexistencia (Zero-Breakage)

Cortex Rust fue disenado bajo el principio de **paridad estricta y coexistencia pacifica**:

1. **Tu entorno de Python sigue intacto:** El comando global `cortex` (instalado mediante `pipx` o `pip`) sigue respondiendo exactamente igual en tu terminal.
2. **Archivos de proyecto compartidos:** Ambas versiones leen y escriben en la misma estructura estandar (`vault/` para notas y `.cortex/` para sesiones y configuracion). Ninguna version corrompe los archivos de la otra.
3. **Embeddings y Cache Aislados:** El nuevo motor de embeddings valida la identidad y dimension del modelo; si cambias entre modelos, el indice se actualiza automaticamente sin mezclar vectores obsoletos.

---

## 2. Estrategia Recomendada: Sandbox / Repositorio de Pruebas

Para evaluar la nueva version con total tranquilidad y realizar pruebas comparativas A/B:

```bash
# 1. Clonar tu repositorio en una carpeta de pruebas aislada
git clone <url-de-tu-repo> ~/pruebas/mi-proyecto-cortex-rust

# 2. Posicionarte en la carpeta de pruebas
cd ~/pruebas/mi-proyecto-cortex-rust
```

*(Si no deseas clonar todo el repositorio, simplemente realiza un respaldo rapido de tu carpeta de metadatos: `cp -r .cortex .cortex.backup` en macOS/Linux o `Copy-Item -Recurse .cortex .cortex.backup` en Windows PowerShell).*

---

## 3. Requisitos Previos para Compilar Localmente

Para compilar Cortex Rust y la aplicacion Cortex Brain en tu maquina, necesitas:

| Herramienta | Version Minima | Windows | macOS | Linux |
| :--- | :--- | :--- | :--- | :--- |
| **Rust & Cargo** | 1.75+ | `winget install Rustlang.Rustup` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| **Node.js & npm** | Node 18+ / 20+ | `winget install OpenJS.NodeJS` | `brew install node` | `sudo apt install nodejs npm` |
| **CMake** | 3.20+ | `winget install Kitware.CMake` | `brew install cmake` | `sudo apt install cmake build-essential` |
| **C++ Compiler** | MSVC / Clang / GCC | Visual Studio Build Tools (C++) | Xcode Command Line Tools | `gcc` / `g++` (`build-essential`) |

---

## 4. Guia Paso a Paso por Sistema Operativo

### Opcion A: En Windows (PowerShell)

Abre **PowerShell** como usuario normal (o Administrador si necesitas instalar herramientas base):

```powershell
# 1. Clonar el codigo fuente de Cortex
git clone https://github.com/MachuaninEzequiel/Cortex.git cortex-rust-source
cd cortex-rust-source

# 2. Instalar dependencias y compilar el Frontend React de Cortex Brain
npm --prefix apps/brain-ui install
npm --prefix apps/brain-ui run build

# 3. Compilar los binarios nativos en modo Release (con motor LLM local llama.cpp)
cd rust
cargo build --release -p cortex-cli -p cortex-brain-app --features llama

# 4. Crear carpeta local para binarios (si no existe) y copiar ejecutables con alias
New-Item -ItemType Directory -Force -Path "$HOME\.local\bin"
Copy-Item target\release\cortex-cli.exe "$HOME\.local\bin\cortex-rs.exe"
Copy-Item target\release\cortex-brain.exe "$HOME\.local\bin\cortex-brain.exe"

# 5. Agregar $HOME\.local\bin al PATH de tu usuario (solo si aun no lo tenes)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$HOME\.local\bin", "User")
```

> **Verificacion en Windows:**
> * `cortex --version` -> Ejecuta la version previa de Python.
> * `cortex-rs --version` -> Ejecuta la version nativa de Rust.
> * `cortex-brain` o `target\release\cortex-brain.exe` -> Abre la app de escritorio Cortex Brain.

---

### Opcion B: En macOS (Terminal / zsh - Apple Silicon e Intel)

Abre tu **Terminal**:

```bash
# 1. Instalar herramientas de desarrollo base (si no las tienes)
xcode-select --install
brew install cmake node

# 2. Clonar el repositorio
git clone https://github.com/MachuaninEzequiel/Cortex.git cortex-rust-source
cd cortex-rust-source

# 3. Compilar el Frontend React de Cortex Brain
npm --prefix apps/brain-ui install
npm --prefix apps/brain-ui run build

# 4. Compilar los binarios nativos en modo Release
cd rust
cargo build --release -p cortex-cli -p cortex-brain-app --features llama

# 5. Instalar en ~/.local/bin con alias seguro
mkdir -p ~/.local/bin
cp target/release/cortex-cli ~/.local/bin/cortex-rs
cp target/release/cortex-brain ~/.local/bin/cortex-brain

# 6. Asegurar que ~/.local/bin este en tu PATH (en ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

> **Verificacion en macOS:**
> * `cortex --version` -> Ejecuta la version de Python.
> * `cortex-rs --version` -> Ejecuta la version de Rust.
> * `cortex-brain` -> Lanza la interfaz de Cortex Brain.

---

### Opcion C: En Linux (Debian / Ubuntu / Mint / Fedora / Arch)

Abre tu terminal favorita:

```bash
# 1. Instalar dependencias de compilacion del sistema
# En Ubuntu / Debian / Mint:
sudo apt update && sudo apt install -y \
  build-essential cmake pkg-config libssl-dev \
  libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev

# En Fedora:
# sudo dnf install gcc-c++ cmake openssl-devel webkit2gtk4.1-devel libappindicator-gtk3-devel

# En Arch Linux:
# sudo pacman -S base-devel cmake openssl webkit2gtk-4.1 libappindicator-gtk3

# 2. Clonar y compilar
git clone https://github.com/MachuaninEzequiel/Cortex.git cortex-rust-source
cd cortex-rust-source

# 3. Compilar Frontend y Binarios
npm --prefix apps/brain-ui install
npm --prefix apps/brain-ui run build
cd rust
cargo build --release -p cortex-cli -p cortex-brain-app --features llama

# 4. Copiar a ~/.local/bin
mkdir -p ~/.local/bin
cp target/release/cortex-cli ~/.local/bin/cortex-rs
cp target/release/cortex-brain ~/.local/bin/cortex-brain
```

---

## 5. Como Generar los Instaladores Oficiales (Bundles de Tauri)

Si deseas generar el instalador distribuible nativo (`.exe` NSIS en Windows, `.dmg` en macOS, `.deb` en Linux):

```bash
# 1. Instalar la herramienta Tauri CLI de Cargo (solo una vez)
cargo install tauri-cli --version "^2.0.0" --locked

# 2. Posicionarte en la carpeta de la app de Cortex Brain
cd cortex-rust-source/rust/crates/cortex-brain-app

# 3. Compilar el bundle instalador
cargo tauri build --features llama
```

Los instaladores empaquetados quedaran listos en:
* **Windows:** `rust/target/release/bundle/nsis/Cortex Brain_0.1.0_x64-setup.exe`
* **macOS:** `rust/target/release/bundle/dmg/Cortex Brain_0.1.0_universal.dmg` (o `.app`)
* **Linux:** `rust/target/release/bundle/deb/cortex-brain_0.1.0_amd64.deb`

---

## 6. Desplegar los Nuevos Agentes y Skills Composed

En la carpeta de tu repositorio o sandbox de pruebas:

```bash
cd ~/pruebas/mi-proyecto-cortex-rust

# 1. Inicializar la estructura base de gobernanza y vault
cortex-rs setup init

# 2. Desplegar la Triada Thin + Craft y la Familia Composed
cortex-rs setup composed
```

### Que instala este comando?
1. **Triada de Agentes Thin + Craft On-Demand:**
   * `/cortex-sync` (`cortex-sync.md`) con proposal mode y pericia en `cortex-sync-spec-craft.md`.
   * `/cortex-SDDwork` (`cortex-SDDwork.md`) con pericia en `cortex-SDDwork-implement-craft.md`.
   * `/cortex-documenter` (`cortex-documenter.md`) con pericia en `cortex-documenter-close-craft.md`.
2. **Familia de Skills Composed (Estandar Matt Pocock):** 8 skills abiertas (`grill/`, `to-spec/`, `to-tickets/`, `implement/`, `tdd/`, `diagnose/`, `review/`, `glossary/`) con ciclo de vida por fases (`CheckpointPhase`).

---

## 7. Configurar el Servidor MCP en tu IDE / Agente

Los clientes de IA (Claude Code, Cursor, Windsurf, Codex, etc.) se conectan a Cortex via **transporte stdio**. Puedes alternar que servidor usar facilmente:

### Metodo 1: Automatico mediante `ide setup`
En tu carpeta de proyecto:
* **Para usar el MCP de Rust:**
  ```bash
  cortex-rs ide setup cursor       # o claude-code, windsurf, vscode, etc.
  ```
* **Para volver al MCP de Python:**
  ```bash
  cortex ide setup cursor
  ```

### Metodo 2: Manual por Proyecto (`.mcp.json`)
En el archivo `.mcp.json` de tu proyecto:
```json
{
  "mcpServers": {
    "cortex": {
      "command": "cortex-rs",
      "args": ["mcp-serve"]
    }
  }
}
```

> **Compatibilidad garantizada:** Ambas versiones exponen exactamente el mismo catalogo de **32 tools canonicas** (`cortex_sync_ticket`, `cortex_create_spec`, `cortex_session_checkpoint`, `cortex_search_semantic`, etc.). Tus prompts y agentes funcionaran de forma identica, pero con latencias de respuesta en sub-milisegundos en Rust.

---

## 8. Embeddings ONNX y Modelos por Idioma

Es importante distinguir los dos tipos de modelos que utiliza Cortex:

1. **LLM Conversacional de Chat (GGUF):** Utilizado exclusivamente dentro de la app Cortex Brain (*Liquid LFM2.5 1.2B Instruct*, ~712 MB en RAM). Corre 100% offline en tu maquina.
2. **Embeddings de Busqueda Semantica (ONNX):** Utilizado por el CLI y MCP para vectorizar notas en `vault/` y la memoria episodica.

### Enrutamiento por Idioma (`config.yaml`)
Cortex detecta automaticamente el idioma de tus consultas y documentos:
* **Ingles (`en`):** Usa `all-MiniLM-L6-v2` (384 dimensiones).
* **Espanol (`es`):** Usa `intfloat/multilingual-e5-large` (1024 dimensiones) para maxima precision de busqueda y retrieval.

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

> **Que pasa con mis documentos anteriores?**
> Gracias a la clave salada con identidad de modelo (`sha256(model_name + schema_version + texto)`), si el sistema detecta un cambio de modelo o dimension, re-indexa los documentos en limpio sin corromper el cache anterior.

---

## 9. Rollback Inmediato (Como volver atras)

Si en algun momento deseas regresar 100% al flujo previo de Python:

1. **En tu IDE:** Ejecuta `cortex ide setup <tu-ide>` para restaurar el comando `"cortex"`.
2. **En tu terminal:** Sigue usando `cortex` (que apunta a tu instalacion de pipx).
3. **En Git:** Todas las versiones estables anteriores permanecen intactas en los tags de Git (`v0.5.0-baseline-seal`, `v1.0.0`, `v2.0.0`). Puedes volver a cualquier commit previo con `git checkout <tag>`.
