# 📦 Guía de Instalación de Cortex — Manual Maestro

> **Documento de referencia único para instalar Cortex desde cero.**
> Cubre: clonar el repositorio → compilar el binario nativo → configurar el
> shell → crear el primer proyecto → instalar integraciones (IDE, MCP, brain
> local) → verificar que todo funciona → y los primeros pasos para el uso
> diario.
>
> Si venís del README: este documento es la **versión completa y profunda**
> de la sección de instalación. La guía de uso diario vive en
> [`GUIA-USO.md`](GUIA-USO.md).
>
> Versión del documento: **2026-08-27** · Compatible con Cortex **0.7.0**
> (línea de comandos verificada contra el binario real).

---

## 1. Antes de empezar: qué vas a instalar

Cortex es una **capa de memoria y gobernanza para agentes de IA**. Todo el
núcleo es un **único binario nativo de Rust** (se llama `cortex-cli`) que
vive **en tu máquina, no en un servidor**. No requiere cuentas, API keys ni
telemetría para la experiencia central.

El modelo de instalación es deliberado:

| Componente | Qué es | ¿Obligatorio? |
|---|---|---|
| **`cortex-cli`** (binario nativo) | El CLI completo: sesiones, memoria, docs, CI, setup, MCP server, TUI | ✅ Sí — es Cortex |
| **`cortex-brain`** (binario opcional) | El asistente local de IA con LLM (llama.cpp + GGUF) | ⭕ Solo si querés el chat con modelo |
| **Configuración por proyecto** | `config.yaml`, `vault/`, sesiones, skills — **dentro de cada repo** | ✅ Se crea con `cortex setup` |
| **Integraciones** | Hooks y perfiles para tu IDE/agente + servidor MCP | ⭕ Por IDE, opt-in |
| **Paquete Python `cortex-memory`** | Legado congelado, solo oráculo de CI | ❌ **No** es canal de instalación |

> ⚠️ **Importante:** el paquete Python (`pip install cortex-memory`) ya **no**
> es una vía de distribución desde la baja definitiva (2026-08). Si lo ves
> mencionado en algún documento viejo, ignoralo: se mantiene únicamente
> como oráculo de verificación del CI. La instalación real es **por
> binario Rust**, como describe esta guía.

---

## 2. Requisitos del sistema

### 2.1 Hardware

| Operación | Pico de RAM medido |
|---|---|
| CLI completo (search, sessions, etc.) | ~106 MB |
| Embedder semántico MiniLM (ONNX, batch) | ~465 MB |
| Embedder multilingual e5-large (español) | ~2.2 GB |
| `cortex-brain --model` (LFM2.5, ctx 4096) | ~1.3 GB |

- **Mínimo cómodo:** 8 GB de RAM (todo corre si no mantenés el LLM y el
  embedder grande cargados a la vez).
- **Disco:** el repositorio + `target/` de Rust ocupan ~3-4 GB durante el
  build; los modelos se descargan a `~/.cache/cortex/` (el GGUF del brain
  son ~730 MB; los embedders ONNX ~100-400 MB).
- **CPU:** cualquier CPU moderna de 4+ núcleos. No se necesita GPU (el
  camino GPU es un roadmap, no un requisito).

### 2.2 Software

| Software | Requerido para | Nota |
|---|---|---|
| **Rust toolchain** (rustc + cargo) | Compilar el binario | Ubuntu/Debian: `apt install cargo` o [rustup.rs](https://rustup.rs). Windows: rustup + MSVC build tools. macOS: `xcode-select --install` + rustup |
| **Git** | Clonar y usar sesiones git-aware | `git --version` → ≥ 2.30 |
| **POSIX `tar`** | Backups del reindex y `docs restore` | Ya viene en Linux/macOS; en Windows usá Git Bash |
| **Python 3.11+** (opcional) | Solo si vas a correr la suite de tests del oráculo | No es necesario para usar Cortex |
| **build-essential / clang** | Build de algunos crates nativos (onnxruntime) | Ubuntu: `apt install build-essential clang` |

---

## 3. Paso a paso: instalación completa

### 3.1 Clonar el repositorio

```bash
git clone https://github.com/MachuaninEzequiel/Cortex.git
cd Cortex
```

Opcional pero recomendado, creá la rama de tu trabajo:

```bash
git checkout -b tu-rama-de-trabajo
```

> El repositorio contiene todo: el código Rust (`rust/`), el código Python
> del oráculo (`cortex/`, `tests/` — no lo toques), los docs de
> transformación (`docs/transformacion/`) y las guías.

### 3.2 Compilar el binario nativo

**Opción A — `cargo install` (un solo binario, recomendado para usuarios):**

```bash
cargo install --path rust/crates/cortex-cli
# → instala ~/.cargo/bin/cortex-cli
```

**Opción B — build release manual (si querés el binario en otro lugar):**

```bash
cargo build --release --manifest-path rust/Cargo.toml -p cortex-cli
# → rust/target/release/cortex-cli
cp rust/target/release/cortex-cli ~/.local/bin/   # o donde prefieras
```

**Verificá la instalación:**

```bash
cortex-cli --cli-version
# → cortex-cli 0.1.0
```

> ⚠️ El build del workspace completo puede tardar varios minutos la primera
> vez (compila todos los crates). Usá `cargo build -p cortex-cli` si solo
> querés el CLI rápido.

### 3.3 Configurar el shell (alias)

El binario se llama `cortex-cli`, pero el nombre corto `cortex` es más
cómodo y es el que usan los docs y las skills.

**Bash** (`~/.bashrc`):

```bash
alias cortex=cortex-cli
```

**Zsh** (`~/.zshrc`):

```zsh
alias cortex=cortex-cli
```

**PowerShell** (Windows, `$PROFILE`):

```powershell
Set-Alias cortex cortex-cli
```

Recargá el shell (`source ~/.bashrc` o abrí una terminal nueva) y
verificá:

```bash
cortex --help
```

Deberías ver la lista de familias de comandos.

### 3.4 Primer proyecto: bootstrap completo

Cortex se configura **por proyecto** — cada repo tiene su propia instancia.
No hay un daemon global ni un servidor central.

Creá (o entrá a) el proyecto donde vas a trabajar:

```bash
mkdir ~/mi-proyecto && cd ~/mi-proyecto
git init   # opcional pero recomendado (habilita sesiones git-aware)
```

Ejecutá el bootstrap:

```bash
cortex init --non-interactive
```

Este comando es un alias de `cortex setup agent` en modo no interactivo y
crea en el proyecto:

```text
.cortex/
├── config.yaml        # configuración (episodic, embedding, semantic, llm…)
├── org.yaml           # configuración enterprise (org)
├── workspace.yaml     # layout v2 + proyecto primary
├── memory/            # store episódico
├── sessions/          # sesiones (YAML por sesión + active.txt)
├── vault/             # tu vault markdown (arquitectura, context, decisions, runbooks)
├── skills/            # skills de agente instaladas
├── AGENT.md           # guidelines para agentes
└── .gitignore         # entradas de runtime (.cortex/session.lock, .memory/)
```

> 💡 **sin `--non-interactive`** `cortex init` intenta un modo interactivo;
> el binario nativo no trae TUI de prompts, así que en la práctica usá
> siempre `--non-interactive` (o pasá flags explícitos).

### 3.5 Validar la instalación: `cortex doctor`

El médico de Cortex verifica prerequisitos y gobernanza:

```bash
cortex doctor
```

Salida esperada (fragmento):

```text
[OK] project_root: /home/tu/mi-proyecto
[OK] layout_mode: new (workspace_root=…/.cortex)
[OK] config_yaml: …/.cortex/config.yaml
[OK] config_validation: config.yaml is valid
[OK] vault_dir: …/.cortex/vault
[OK] cortex_workspace: …/.cortex
...
```

Interpretación de marcas:

| Marca | Significado |
|---|---|
| `[OK]` | Check superado |
| `[WARN]` | Aviso (no bloquea; p. ej. "no es repo git") |
| `[FAIL]` | Algo roto que hay que arreglar (p. ej. store episódico inexistente hasta el primer reindex) |

> Un `[FAIL] episodic_store` en un proyecto recién creado es **normal**: el
> store de Chroma se materializa en el primer reindex/search real. El resto
> de los `[FAIL]`/`[WARN]` de git (no-repo, no-git-branch) desaparecen si
> hacés `git init` y un commit inicial.

### 3.6 Instalar las integraciones de IDE/agente

Cortex soporta **11 IDEs/agentes** (verificados contra el binario real):
`claude_code`, `claude_desktop`, `codex`, `cursor`, `opencode`, `pi`,
`vscode`, `windsurf`, `hermes`, `antigravity` y `zed`.

**Ver la lista y estado:**

```bash
cortex ide list
cortex ide status            # estado detallado de cada uno (--json para machine)
```

**Instalar tu IDE:**

```bash
cortex ide setup --ide claude-code    # o: cursor, codex, opencode, pi, vscode…
```

Lo que instala por IDE (según capacidades del adapter):
- Perfiles/prompts de agente en el directorio del IDE (con marcadores
  `BEGIN/END CORTEX` donde el formato lo permite — patrón codex).
- Configuración MCP (`.mcp.json` del proyecto o config del IDE según
  adapter).
- **Hook de sesión** (modo Observed): artefacto que emite checkpoints
  automáticos cuando trabajás con ese IDE.

**Opciones útiles:**

```bash
cortex ide setup --ide codex --dry-run      # qué haría sin tocar nada
cortex ide setup --ide pi --no-sync-canonical   # no re-sincronizar bundle canónico
cortex ide remove --ide pi                  # desinstalar SOLO lo de Cortex
```

> 🔒 **Garantía de desinstalación:** `cortex ide remove` borra solo lo que
> Cortex creó (bloques marcados, claves JSON inventariadas o archivos
> propios). Nunca toca tu contenido preexistente.

**Módulo Observed a mano (si preferís hooks solos):**

```bash
cortex session hooks list
cortex session hooks install --ide claude-code
cortex session hooks uninstall --ide claude-code
cortex session hooks status --ide claude-code
```

### 3.7 Conectar agentes via MCP (opcional)

Cualquier agente con soporte MCP (Claude Code, Cursor, Codex, Pi,
OpenCode…) puede hablar con Cortex por el servidor MCP nativo:

```bash
cortex mcp-serve                 # arranca el server stdio (bloqueante)
cortex mcp-server --project-root /ruta/proyecto
```

Para integraciones con archivos de config (`.mcp.json` de Claude Code, por
ejemplo) normalmente **no hace falta** hacer nada: `cortex ide setup`
escribe la entrada MCP por vos. Verificá tu archivo:

```json
{
  "mcpServers": {
    "cortex": { "command": "cortex-cli", "args": ["mcp-serve"] }
  }
}
```

> ℹ️ El servidor expone 30+ tools canónicas agrupadas por familia
> (search, context, specs, write_doc, sessions, review, autopilot…). La
> lista completa se ve con cualquier cliente MCP en `tools/list`, o en la
> Guía de Uso §9.

### 3.8 Activar el brain local con LLM (opcional pero recomendado)

El asistente local de IA (`cortex-brain`) corre **en tu máquina** con
llama.cpp y un modelo GGUF. Es opcional: sin modelo, el brain funciona en
modo determinista (router sin LLM, cero tokens).

**Compilar:**

```bash
cd rust
cargo build --release -p cortex-brain --features llama
# → rust/target/release/cortex-brain
```

**Descargar un modelo GGUF** (~730 MB, una sola vez):

```bash
mkdir -p ~/.cache/cortex/models
# Poner allí LFM2.5-1.2B-Instruct-Q4_K_M.gguf
# (cualquier GGUF compatible con llama.cpp sirve; la ruta default la
#  muestra el propio binario con --help)
```

**Usar:**

```bash
cortex-brain --model                 # chat con LLM real (bilingüe ES/EN)
cortex-brain                         # modo determinista, sin modelo
cortex-brain --window                # abre su propia ventana de terminal
```

> El brain es **read-only por diseño**: nunca ejecuta mutaciones. Cuando
> quiere algo, te propone el comando exacto y lo corrés vos. Con
> `actions.propose` te muestra además las sugerencias del Action Engine
> (ver Guía de Uso §10).

### 3.9 Compilar todo el workspace (para desarrollo)

Si vas a desarrollar sobre Cortex o correr sus tests:

```bash
cd rust
cargo build --workspace
cargo test --workspace       # 83+ tests
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all --check
```

La suite Python del oráculo (solo si querés validar compatibilidad):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .             # instala el paquete legado (oráculo)
pytest tests/unit tests/integration -q --no-cov  # 2455+ tests
```

---

## 4. Verificación completa (checklist post-instalación)

```bash
# 1. Binario
cortex-cli --cli-version                     # → cortex-cli 0.1.0

# 2. Alias
cortex --help                                # lista de familias

# 3. Proyecto
cortex doctor                                # todo OK / solo WARN de git

# 4. Memoria funcionando
cortex stats                                 # JSON con counts y topology
cortex search "algo de tu proyecto"          # retrieval híbrido (0 resultados es válido al inicio)
cortex reindex --dry-run                     # plan de reindex (sin aplicar)

# 5. Sesiones
cortex session list                          # "(no sessions on disk)" al inicio
cortex session current                       # error claro si no hay activa

# 6. Action Engine
cortex next                                  # sugiere primeras acciones (validar docs, reindex…)

# 7. TUI
cortex session watch                         # pantalla ratatui (con datos) o snapshot no-TTY

# 8. IDE
cortex ide list                              # 11 adapters

# 9. Brain (si lo compilaste)
cortex-brain                                 # modo determinista → "no model" y router activo
```

Si todo lo anterior corre sin errores de ejecución, **Cortex está
instalado y operativo**.

---

## 5. Estructura de directorios y dónde vive cada cosa

| Ruta | Contenido | Creado por |
|---|---|---|
| `~/.cargo/bin/cortex-cli` | Binario nativo (cargo install) | instalación |
| `<proyecto>/.cortex/config.yaml` | Configuración del proyecto | `cortex setup agent` / `init` |
| `<proyecto>/.cortex/sessions/*.yaml` | Sesiones, una por archivo | flujo cortex-sync / `cortex session checkpoint` |
| `<proyecto>/.cortex/sessions/active.txt` | Id de la sesión activa | al abrir/switch |
| `<proyecto>/.cortex/vault/` | Vault markdown (context, architecture, decisions, runbooks, specs, notas) | setup |
| `<proyecto>/.cortex/memory/` | Store episódico (Chroma) | primer uso de memoria |
| `<proyecto>/.cortex/skills/` | Skills de agente canónicas | `setup agent` |
| `<proyecto>/.cortex/ide-manifest.json` | Inventario de instalación de IDEs | `cortex ide setup` |
| `<proyecto>/.cortex/org.yaml` | Configuración enterprise | `setup enterprise` |
| `<proyecto>/.cortex/actions.yaml` | Preferencias del Action Engine | `cortex next` (learning) |
| `~/.cache/cortex/models/` | GGUF del brain | manual |
| `~/.cache/cortex/fastembed/` | Embedders ONNX | primer embed |
| `~/.codex/`, `~/.cursor/`, `~/.claude/`… | Perfiles/MCP user-level según IDE | `cortex ide setup` |

---

## 6. Configuración (referencia completa de `config.yaml`)

El archivo vive en `<proyecto>/.cortex/config.yaml`. Se genera con setup y
se edita a mano. Bloque por bloque:

```yaml
# ── Memoria episódica ────────────────────────────────────────────────
episodic:
  persist_dir: .memory/chroma        # carpeta del store
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2  # modelo legacy (si no hay per_language)
  embedding_backend: onnx            # onnx | local | openai | fastembed
  namespace_mode: project            # project | branch | custom
  namespace_value: ""

# ── Embeddings por idioma (Obra 04) ──────────────────────────────────
embedding:
  backend: fastembed                 # backend default
  language_detection: heuristic      # heuristic | off
  per_language:                      # quitar este bloque = mono-modelo
    es:
      model: intfloat/multilingual-e5-large
      backend: fastembed

# ── Vault semántico ──────────────────────────────────────────────────
semantic:
  vault_path: vault                  # relativo al proyecto

# ── Retrieval híbrido (RRF) ──────────────────────────────────────────
retrieval:
  top_k: 5                           # resultados por defecto
  episodic_weight: 1.0               # peso de la capa episódica
  semantic_weight: 1.0               # peso de la capa semántica

# ── LLM externo (opcional) ───────────────────────────────────────────
llm:
  provider: none                     # none | openai | anthropic | ollama…
  model: ""

# ── Integraciones ────────────────────────────────────────────────────
integrations:
  jira:
    enabled: false
    base_url: ""
    email_env: JIRA_EMAIL            # variables de entorno para credenciales
    token_env: JIRA_API_TOKEN

# ── Idioma de UI (TUI + brain) ───────────────────────────────────────
ui:
  language: es                       # es | en
```

> 🧪 **Cómo probar un cambio de config:** después de editar, corré
> `cortex doctor` — valida la config y te dice si algo está mal. Cambiar el
> modelo de embeddings invalida la caché automáticamente (firma del modelo);
> para forzar reindex: `cortex reindex` (ver §7 Troubleshooting).

---

## 7. Troubleshooting de instalación

| Síntoma | Causa probable | Solución |
|---|---|---|
| `cortex-cli: command not found` | no está en PATH | `export PATH="$HOME/.cargo/bin:$PATH"` (o usá la ruta absoluta al binario) |
| `cortex: No such command …` al usar el binario viejo | binario desactualizado (con passthrough viejo) | recompilá y reinstalá: `cargo install --path rust/crates/cortex-cli` |
| `No Cortex config found` | estás fuera de un proyecto configurado | `cd` a un proyecto con `.cortex/config.yaml` o pasá `--project-root` |
| `[FAIL] episodic_store` en doctor | store no materializado aún | es normal post-setup; corré `cortex search "…"` o `cortex reindex` una vez |
| `reindex real no nativo…` (rc 1) | `reindex` sin `--dry-run` es fallo explícito (sin escritor de vectors persistente nativo) | usá `cortex reindex --dry-run`, o el oráculo Python legacy si estás en desarrollo |
| `mcp-serve: Only stdio transport is supported` | transport HTTP no implementado | usá stdio (es el default de los clientes MCP) |
| el IDE no aparece en `ide list` | no es un adapter soportado | verificá el nombre: `cortex ide list --json` y buscá `"name"` |
| `Unknown IDE '<name>'` | nombre mal escrito | usá uno de `ide list` (acepta alias: claude, claude-code, code…) |
| el brain no arranca con `--model` | falta el GGUF o el feature llama | verificá `~/.cache/cortex/models/` y que compilaste con `--features llama` |
| OOM durante embed español | e5-large es pesado (~2.2 GB) | usá MiniLM (`embedding.backend: onnx`, sin per_language) o no lo cargues junto al LLM |
| descargas de modelos cortadas | red inestable | los blobs se reanudan al reintentar; nada se pierde a mitad |
| `No such command 'open'` en `session open` | el arranque de sesión lo hace el flujo orquestador (cortex-sync/SDDwork) o los hooks del IDE; el CLI maneja las sesiones ya creadas | consultá `GUIA-USO.md` §5 Sesiones |
| conflictos con config vieja | layout legacy vs nuevo | `cortex doctor` te lo marca; `layout_version: 2` es el actual |

---

## 8. Siguiente paso: la Guía de Uso

Con el binario instalado, el proyecto bootstrap y el doctor en verde, ya
podés usar Cortex en tu día a día → **leé [`GUIA-USO.md`](GUIA-USO.md)**:

- Sesiones (abrir, checkpoint, task, cerrar) — §5
- Los modos **Managed / Observed / BYO** — §6
- Memoria y búsqueda híbrida — §7
- Docs, CI, PR Context — §8
- MCP para agentes — §9
- Action Engine y Brain — §10 · TUI — §11 · Config avanzada — §12

---

*Fin de la guía de instalación. Reportá inconsistencias en el repo —
este documento fue verificado contra el binario nativo 0.7.0.*