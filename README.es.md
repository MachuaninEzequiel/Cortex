<div align="center">
  <br />
  <a href="https://github.com/MachuaninEzequiel/Cortex">
    <img src="assets/cortex-prime.png" alt="Cortex" width="380" />
  </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>El harness organizacional de memoria corporativa.</strong><br />
    El sistema nervioso de la empresa cuando el trabajo lo hacen agentes.
  </p>

  <p>
    <a href="README.md">English</a>
    ·
    <a href="README.es.md">Español</a>
    ·
    <a href="docs/GUIA-MIGRACION-RUST.md">Guía de coexistencia Python / Rust</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Rust-nativo-orange?logo=rust&style=flat-square" alt="Rust" />
    <img src="https://img.shields.io/badge/Tauri-v2-blue?logo=tauri&style=flat-square" alt="Tauri 2" />
    <img src="https://img.shields.io/badge/LLM-Liquid_LFM2.5-purple?style=flat-square" alt="Liquid LFM" />
    <img src="https://img.shields.io/badge/Embeddings-ONNX-green?style=flat-square" alt="ONNX" />
    <img src="https://img.shields.io/badge/System_One-JEV_1.13-cyan?style=flat-square" alt="System One JEV" />
    <img src="https://img.shields.io/badge/MCP-32_tools-blueviolet?style=flat-square" alt="MCP" />
    <img src="https://img.shields.io/badge/Brain-0.2.7-informational?style=flat-square" alt="Brain 0.2.7" />
  </p>

  <br />
  
</div>

---

<div align="center">

## Qué es

</div>

Cortex es el **harness organizacional de memoria corporativa**: el sistema nervioso de la empresa cuando el trabajo lo hacen agentes.

Cada IDE, cada modelo y cada sesión beben de la misma memoria institucional. Specs, decisiones, evidencia y contexto no viven en un chat que se evapora: viven en el repositorio, gobernados, auditables, reutilizables. Es la capa de inteligencia operativa que convierte agentes sueltos en un organismo — misma verdad, mismo ritual de cierre, misma memoria.

La unidad de trabajo es una **sesión**: se abre desde una spec, registra checkpoints y solo se cierra cuando la verificación pasa. «Listo» significa comprobado, no declarado. Todo corre **en tu máquina**.

---

<div align="center">

## Por qué usarlo

</div>

Los agentes son potentes y amnésicos. Cada conversación arranca de cero, las decisiones se pierden entre herramientas y casi nunca queda rastro verificable.

| Problema | Qué aporta Cortex |
| :--- | :--- |
| **Amnesia entre sesiones** | Memoria híbrida (episódica + semántica) sobre el vault del proyecto. |
| **Trabajo sin disciplina** | Sesiones con checkpoints, quality gates y cierre con evidencia. |
| **Contexto distinto en cada IDE** | Un solo vault y un solo MCP por proyecto, compartido por todos los agentes. |
| **Código que sale de la máquina** | Inferencia y búsqueda locales. Sin API keys ni telemetría en la experiencia central. |

Cortex **solo se activa en los proyectos donde lo instalaste**. Un repositorio sin Setup no expone tools ni servidor MCP.

---

<div align="center">

## Cómo está compuesto

</div>

Cuatro órganos, un cuerpo:

1. **Cortex Brain** — el puente de mando. App de escritorio: setup, chat local, WebGraph, Doctor, memoria organizacional. El instalador trae el CLI nativo (`cortex-cli`).
2. **CLI y MCP nativos (Rust)** — el sistema nervioso periférico. Sesiones, búsqueda, docs, doctor, inyección en IDEs. El agente no «adivina» el proyecto: lo consulta.
3. **Vault y `.cortex/`** — el archivo institucional. Markdown gobernado. Rust y Python leen y escriben la misma estructura.
4. **Agentes en el IDE** — las manos. Skills, subagentes y MCP, vivos **solo** en la carpeta donde Cortex está instalado.

El `cortex` de la terminal (pip / pipx) sigue siendo Python hasta que migres el IDE. Conviven.

### Memoria tripartita — y la cuarta, la corporativa

Tres memorias, como un cerebro que no se rinde al olvido. Una cuarta, cuando la organización exige doctrina.

| Memoria | Pregunta que responde | Dónde vive |
| :--- | :--- | :--- |
| **Episódica** | ¿Qué ocurrió, cuándo, en qué sesión? | Eventos y embeddings locales |
| **Semántica** | ¿Qué es verdad en este sistema? | Vault: ADRs, specs, runbooks, glosario |
| **Procedural** | ¿Qué hay que hacer ahora? | Action Engine, `next`, autopilot |
| **Organizacional** | ¿Qué ya decidió la empresa? | Candidatos, promoción, vault institucional |

No es un dump al prompt. Cada turno **inyecta** un expediente: sesión activa, checkpoints, hits híbridos (BM25 + vectores ONNX, fusionados por RRF), nodos del grafo, doctrina ya promulgada. El modelo no recibe el universo: recibe **la verdad que importa ahora**.

### Modelos locales — inteligencia sin filtrar hacia afuera

Dos motores, cero nube obligatoria:

- **Liquid LFM2.5** (GGUF, in-process vía llama.cpp) es la voz de Brain. Vive en RAM solo mientras preguntás; se descarga solo si nadie lo usa. Lo conmutás en caliente desde la barra.
- **Embeddings ONNX** indexan el vault en tu disco. Inglés en MiniLM, español en e5-large: la memoria habla el idioma del equipo, no el del proveedor.

El agente del IDE y Liquid beben del **mismo** índice. No hay una verdad para el chat y otra para Cursor.

### WebGraph — el mapa que Liquid puede ver y consultar

El conocimiento no es una lista. Es un grafo: módulos, specs, ADRs, archivos, aristas de dependencia. WebGraph lo vuelve **visible, orbital, consultable**.

Liquid no alucina la topología: la **pregunta**. Un nodo se fija al chat; Doctor y Memoria Org cuelgan del mismo mapa. Lo que la memoria recuerda, el grafo lo muestra; lo que el grafo muestra, el modelo lo puede citar.

### System One — Cognición rápida, gating y blindaje de contexto (motorizado por JEV)

Inspirado en la teoría de los dos sistemas cognitivos, Cortex incorpora una arquitectura dual: mientras el agente deliberativo (**System Two**) analiza código y ejecuta tareas complejas, **System One** opera como un portero perceptual ultra-rápido de baja latencia y alta precisión que filtra, destila y compacta el contexto **antes** de alimentar al modelo principal.

Actualmente, esta capa está motorizada en producción por **JEV** (`jev-1.13.0` / TypeSafe System One).

#### ¿Qué hace System One?
- **Utterance Gating (Portería de Intención):** Clasifica en milisegundos la naturaleza de cada prompt. Si el usuario realiza una consulta casual, teórica o trivia (`casual_trap`), System One la responde o aísla directamente **sin abrir sesiones innecesarias** y sin contaminar la memoria del repositorio con ruido.
- **Search Squeeze & Context Pack v2 (Destilación de Contexto):** En lugar de arrojar al modelo fragmentos gigantes de documentación o dejar pasar distractores léxicos irrelevantes, suprime distractores y condensa el expediente a las variables canónicas y restricciones arquitectónicas vigentes.
- **Session Compaction (Compactación de Historial):** Comprime automáticamente salidas masivas de linters, tests o ejecuciones de herramientas (reduciendo volcados ruidosos de más de 1.400 tokens a resúmenes informativos de 15 tokens), impidiendo el crecimiento cuadrático del contexto.
- **Blindaje y Cumplimiento de ADRs:** Asegura que ante prompts escuetos o ambiguos en «terminal fría», el agente no alucine dependencias ni viole decisiones de diseño preexistentes.

#### Impacto en el funcionamiento y resultados empíricos
En una evaluación experimental controlada de **18 turnos continuos** (benchmark ConaISI):
- **Frente a un Agente sin Cortex (RAW):**
  - **-53.2% de tokens acumulados** al cabo de la sesión (14.856 vs 31.756 tokens).
  - **Punto de cruce (Turno 9):** A partir del noveno turno, Cortex + System One se vuelve **más económico que operar sin Cortex**, mientras que el agente sin memoria sufre una tasa de cumplimiento arquitectónico de apenas **61.1%** frente al **100%** alcanzado con System One.
- **Frente a Cortex tradicional / Baseline (sin System One):**
  - **-68.6% de ahorro en tokens acumulados** (14.856 vs 47.368 tokens), evitando la explosión de contexto causada por volcados de herramientas y fragmentos ruidosos.
  - **-52.8% de reducción en tokens de razonamiento (*thinking waste*):** Al no recibir distractores en el prompt, el modelo principal no gasta ciclos dudando o analizando código irrelevante.

<img src="assets/cortex-brain.png" alt="Cortex Brain" width="92%" />

---


<div align="center">

## Instalación: Cortex Brain

</div>

Lo primero que se instala es la aplicación. Desde ahí se inicializa un proyecto, se conecta el IDE y se usa Cortex **sin clonar este repositorio y sin `pip` ni `cargo`**.

**Descargas** (0.2.7):
 
[github.com/MachuaninEzequiel/Cortex/releases/tag/brain-v0.2.7](https://github.com/MachuaninEzequiel/Cortex/releases/tag/brain-v0.2.7)

| Sistema | Archivo |
| :--- | :--- |
| Linux | `Cortex.Brain_0.2.7_amd64.deb` |
| Windows | `Cortex.Brain_0.2.7_x64-setup.exe` |
| macOS (Apple Silicon) | `Cortex.Brain_0.2.7_aarch64.dmg` |

Instalá el paquete y abrí **Cortex Brain**.

### Uso

1. En la barra izquierda, abajo: **Instalar Cortex**.
2. **Elegir carpeta** (un repositorio propio, vacío o no).
3. **Preview** y luego **Aplicar**.
   - **Init (agent)** crea `.cortex/`, configuración, vault y `org.yaml`.
   - **Full** agrega CI y WebGraph.
   - **IDEs** inyecta el MCP en Cursor, Claude Code, OpenCode, VS Code y similares, **solo en esa carpeta**.
4. **Abrir esta carpeta en Brain** para chatear contra ese proyecto.

El instalador trae `cortex-cli`. El MCP de los IDEs apunta a ese binario.

### Si el proyecto no aparece a la izquierda

Ninguno de estos casos exige repetir Init si el proyecto **ya** tiene Cortex.

1. **Elegiste la carpeta y no la abriste.** Setup no la agrega solo. Hacé: Instalar Cortex → Elegir carpeta → **Abrir esta carpeta en Brain**. No ejecutes Init.
2. **El repo no está bajo tu usuario** (`D:\…`, `C:\dev\…`). Refrescar solo recorre el perfil (`C:\Users\…`). Misma secuencia: Elegir carpeta → Abrir esta carpeta. Requiere Brain 0.2.7 o posterior.
3. **Hay `.cortex/` pero no hay config.** Brain exige `.cortex/config.yaml`, o `config.yaml` en la raíz, o `.cortex/workspace.yaml`. Si existe `config.yaml` en la raíz, usá el caso 1. Si no hay ninguno de los tres, ahí sí hace falta Init. Si ya hay config y vault, no corras Init: los pisa.

Refrescar solo lista repos **dentro del perfil de usuario** que ya tengan uno de esos yaml. En la práctica: **Elegir carpeta → Abrir esta carpeta**, sin Init.

---

<div align="center">

## Quienes ya usan Cortex en Python

</div>

Antes que nada, hacé un backup por las dudas (`cp -r .cortex .cortex.backup` o una copia del repo). No debería romper el proyecto — en las pruebas no lo hizo — pero conviene.

Rust y Python usan la misma estructura (`.cortex/` y `vault/`).

- El comando `cortex` de la terminal **sigue siendo Python**. No lo desinstales todavía.
- En Brain, elegí **la misma carpeta**. No hace falta Init si el proyecto ya está gobernado. Podés usar el chat, Doctor y memoria, y reinyectar el IDE cuando quieras.
- No desinstales Python hasta estar cómodo. Las dos versiones conviven.

### Pasar el IDE a Rust (sin tocar el vault)

No hace falta reemplazar carpetas. Las notas de `vault/` y `.cortex/` las leen ambos motores.

1. Brain → Instalar Cortex → la carpeta del proyecto (**sin Init**).
2. En **IDEs**, OpenCode (o el que uses) → Preview → Aplicar. Eso reescribe la config del MCP; no pisa el vault.
3. Cerrá y volvé a abrir el IDE en ese repositorio.

Comprobación: en `.mcp.json` el campo `command` debe ser `cortex-cli` o la ruta absoluta de ese ejecutable, **no** `cortex`.

---

<div align="center">

## Compilar desde el código

</div>

Quienes desarrollan Cortex, no quienes solo lo usan, pueden seguir la [guía de coexistencia y compilación](docs/GUIA-MIGRACION-RUST.md).

---

<div align="center">

**MIT License** · Véase `LICENSE`

</div>
