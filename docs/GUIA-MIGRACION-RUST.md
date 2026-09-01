# Guia de Coexistencia y Migracion: Cortex Python a Cortex Rust

> **Para desarrolladores y beta testers:** Esta guia explica como probar y utilizar la nueva version de Cortex en Rust (**Cortex CLI** y **Cortex Brain Desktop**) en paralelo con tu instalacion actual de Cortex en Python, **sin romper tus proyectos, sin colisiones de comandos y sin alterar tu configuracion previa**.

---

## 1. Principios de Coexistencia (Zero-Breakage)

Cortex Rust fue disenado bajo el principio de **paridad estricta y coexistencia pacifica**:

1. **Tu entorno de Python sigue intacto:** El comando global `cortex` (instalado mediante `pipx`) sigue respondiendo exactamente igual en tu terminal.
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

*(Si no deseas clonar todo el repositorio, simplemente realiza un respaldo rapido de tu carpeta de metadatos: `cp -r .cortex .cortex.backup`).*

---

## 3. Instalacion de Cortex Rust

Tienes dos componentes disponibles: la **Aplicacion de Escritorio (Cortex Brain)** y el **CLI Nativo (`cortex-rs`)**.

### Opcion A: Cortex Brain Desktop (App Grafica con LLM Local)
Ideal para explorar el **WebGraph visual**, auditar la salud con **Doctor** y chatear con el modelo local **Liquid LFM2.5**.

* **En Windows:** Descarga `Cortex Brain_<version>_x64-setup.exe` desde la seccion [Releases de GitHub](https://github.com/MachuaninEzequiel/Cortex/releases), ejecuta el instalador y abrelo desde el Menu Inicio.
* **En macOS:** Descarga `Cortex Brain_<version>_universal.dmg` (compatible con Apple Silicon M1/M2/M3/M4 e Intel), arrastra la app a tu carpeta `Applications` y ejecutala.
* **En Linux:** Descarga el paquete `.deb` (`sudo dpkg -i cortex-brain_amd64.deb`) o ejecuta el binario portable `/ruta/target/release/cortex-brain`.

---

### Opcion B: CLI Nativo de Rust (`cortex-rs`)
Si deseas compilar e instalar el CLI nativo en tu sistema sin sobreescribir el comando `cortex` de Python:

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

> **Verificacion de comandos en tu terminal:**
> * `cortex --version` -> Ejecuta la version de **Python** (`~/.local/bin/cortex`).
> * `cortex-rs --version` -> Ejecuta la version de **Rust** (`~/.local/bin/cortex-rs`).
> * `cortex-brain` -> Lanza la **App de Escritorio**.

---

## 4. Desplegar los Nuevos Agentes y Skills

En tu repositorio de prueba, despliega la nueva arquitectura de **Skills Composed** (inspirada en los estandares abiertos de Matt Pocock) y la triada reestructurada de agentes:

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
2. **Familia de Skills Composed:** 8 skills abiertas (`grill/`, `to-spec/`, `to-tickets/`, `implement/`, `tdd/`, `diagnose/`, `review/`, `glossary/`) con ciclo de vida por fases (`CheckpointPhase`).

---

## 5. Configurar el Servidor MCP en tu IDE / Agente

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
      "args": ["mcp-server", "--stdio", "--project-root", "."]
    }
  }
}
```

> **Compatibilidad garantizada:** Ambas versiones exponen exactamente el mismo catalogo de **32 tools canonicas** (`cortex_sync_ticket`, `cortex_create_spec`, `cortex_session_checkpoint`, `cortex_search_semantic`, etc.). Tus prompts y agentes funcionaran de forma identica, pero con latencias de respuesta en sub-milisegundos en Rust.

---

## 6. Embeddings ONNX y Modelos por Idioma

Es importante distinguir los dos tipos de modelos que utiliza Cortex:

1. **LLM Conversacional de Chat (GGUF):** Utilizado exclusivamente dentro de la app Cortex Brain (*Liquid LFM2.5 1.2B*).
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

## 7. Rollback Inmediato (Como volver atras)

Si en algun momento deseas regresar 100% al flujo previo de Python:

1. **En tu IDE:** Ejecuta `cortex ide setup <tu-ide>` para restaurar el comando `"cortex"`.
2. **En tu terminal:** Sigue usando `cortex` (que apunta a tu instalacion de pipx).
3. **En Git:** Todas las versiones estables anteriores permanecen intactas en los tags de Git (`v0.5.0-baseline-seal`, `v1.0.0`, `v2.0.0`). Puedes volver a cualquier commit previo con `git checkout <tag>`.
