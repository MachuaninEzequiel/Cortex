<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="420">
    </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>Memoria cognitiva híbrida, gobernanza y un brain de IA local — para tus agentes y tu equipo.</strong>
  </p>

  <p>
    <a href="README.md">🇬🇧 English</a> · <a href="README.es.md">🇪🇸 Español</a>
  </p>

  <p>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Rust-capa%20nativa%20(opt--in)-orange.svg" alt="Capa nativa Rust" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/tests-2400%2B%20verdes-brightgreen.svg" alt="tests" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>
</div>

---

Cortex le da a tus agentes de IA **memoria persistente** (episódica +
semántica), un **ciclo de vida disciplinado** (specs → trabajo verificado →
sesiones documentadas) y — algo único — un **asistente local con LLM real**
que consulta tu proyecto sin mutarlo jamás. Todo corre en tu máquina: sin API
keys para la experiencia central.

## 🧠 Conocé `cortex-brain`

Un asistente nativo (Rust + llama.cpp) que conoce **este** proyecto. Responde
preguntas, ejecuta tools de solo lectura y — si quiere ejecutar algo — te lo
tiene que pedir:

```text
🧠 cortex-brain — backend: llama.cpp (GGUF)

Vos: ¿cuántas notas hay en el vault?
🔧 sugerencia del modelo [read]: vault.stats
¿Ejecutás 'vault.stats' ? [s/N]: s
Vault: 128 notas .md

Vos: borrá los archivos temporales
El brain NUNCA ejecuta mutaciones: propone el comando exacto.
  → cortex vault.reindex --dry-run   (revisalo y corrélo vos)
```

| | |
|---|---|
| **100% local** | GGUF vía llama.cpp (`LFM2.5-1.2B-Instruct`, ~730 MB). Sin nube, sin keys. |
| **Propone, nunca muta** | Las mutaciones son imposibles por diseño: el registro de tools no tiene tools destructivas; las acciones vuelven como comandos exactos para que los corras **vos**. |
| **Fallback determinista** | Sin modelo, el router sigue funcionando (`cortex-brain`, cero tokens). |
| **Bilingüe** | UI en español o inglés (`ui.language`). |
| **Ventana dedicada** | `cortex-brain --window` abre su propia terminal. |

## Por qué Cortex

- **La amnesia de sesión es cara.** Los agentes olvidan decisiones, incidentes
  y contexto entre tareas. Cortex los persiste como memoria consultable.
- **La calidad de retrieval en español importa.** Embeddings por idioma,
  medidos con nuestra propia suite: MRR@10 en español **0.88 → 0.96** vs el
  default english-only; en inglés queda **1.0** sobre nuestro dataset.
- **La confianza necesita verificación.** El trabajo se cierra con checkpoints
  y verification hooks ejecutables — "listo" significa *probado*, no *dicho*.
- **Tu notebook alcanza.** La CLI completa corre en ~100 MB de RAM; lo pesado
  es opt-in y está medido (ver [Hardware](#hardware-números-honestos)).

## Instalación

Requisitos: Python **3.11+** · Linux/macOS/Windows.

### Recomendado: pipx (un CLI global, cero contaminación de proyectos)

Cortex es una herramienta de gobernanza transversal: **un** comando global,
mientras que los datos quedan por proyecto (`config.yaml`, `vault/`,
`.memory/` viven dentro de cada repo). `pipx` te da exactamente eso — un
entorno aislado y el comando `cortex` global:

```bash
# Desde un clone de este repositorio:
pipx install .

# Extras: embeddings multilingües + visualizador de grafo
pipx inject cortex-memory fastembed webgraph

cortex doctor    # valida prerequisitos y estado de gobernanza
```

> Cuando haya releases en PyPI esto queda simplemente en
> `pipx install cortex-memory` (los wheels multiplataforma ya se compilan en
> cada tag).

### Para desarrollo (instalación editable)

```bash
git clone https://github.com/MachuaninEzequiel/Cortex && cd Cortex
pip install -e ".[dev]"
pytest tests/unit tests/integration -q --no-cov
```

Bootstrap de un proyecto (crea config, vault, skills, adapters IDE):

```bash
cortex init          # alias de `cortex setup agent` — flujo nuevo usuario
cortex doctor        # valida prerequisitos y estado de gobernanza
cortex tutor         # guía interactiva offline, cero tokens
```

### Activar el brain 🧠 (opcional)

```bash
# Compilar el workspace Rust con la feature llama.cpp (requiere toolchain Rust)
cd rust && cargo build --release -p cortex-brain --features llama

# Una sola vez: ubicar un GGUF (la ruta default la muestra el binario)
mkdir -p ~/.cache/cortex/models
# … dejar ahí LFM2.5-1.2B-Instruct-Q4_K_M.gguf (~730 MB)

./rust/target/release/cortex-brain --model        # chat con LLM real
./rust/target/release/cortex-brain                # modo determinista, sin modelo
```

En hardware, el brain pica a **~1.3 GB de RAM** — tranquilo en una laptop de 8 GB.

## Quickstart — 60 segundos

```bash
cortex init                      # bootstrap del proyecto
cortex start                     # abrir sesión de trabajo (spec-driven)
# … hacé el trabajo con tu agente/IDE …
cortex finish                    # corren los verification hooks y se documenta
cortex next                      # ¿qué sigue? (acciones sugeridas)
cortex search "refactor auth"    # búsqueda híbrida episódica + semántica
cortex context                   # bundle de contexto enriquecido para la tarea
```

## Los 8 comandos de nivel 0

| Comando | Qué hace |
|---|---|
| `brain` | Asistente local experto (solo lectura + safe-actions). |
| `start` | Persiste una spec de implementación en el vault. |
| `finish` | Cierra la Sesión: reconstruye, verifica, persiste. |
| `init` | Bootstrap de Cortex en un proyecto (flujo nuevo usuario). |
| `doctor` | Valida prerequisitos y estado de gobernanza. |
| `context` | Contexto enriquecido para el trabajo actual. |
| `tutor` | Guía interactiva offline (cero tokens). |
| `search` | Consulta ambas capas de memoria y muestra resultados. |

Debajo hay 35+ comandos más (`reindex`, `embedding-status`, `session`, `ci`,
`ide`, `stats`, `next`…) — se descubren progresivamente con `tutor` y `doctor`.

## Memoria híbrida, retrieval bilingüe

Dos capas fusionadas con Reciprocal Rank Fusion:

| Capa | Store | Fortaleza |
|---|---|---|
| **Episódica** | ChromaDB (`.memory/chroma`) | eventos, decisiones, entidades — *qué pasó* |
| **Semántica** | Vault markdown (compatible Obsidian) | conocimiento curado — *qué sabemos* |

Los embeddings se configuran **por idioma**, elegidos por frontmatter
(`lang: es`) o detección heurística:

| Idioma | Modelo | Backend | Calidad medida |
|---|---|---|---|
| 🇪🇸 ES | `intfloat/multilingual-e5-large` | fastembed (ONNX) | MRR@10 **0.9615** |
| 🇬🇧 EN | `all-MiniLM-L6-v2` | ONNX (chromadb) | MRR@10 **1.0** |

Las migraciones de modelo son seguras: los caches firman el modelo activo y
`cortex reindex --prune-old-caches` reconstruye con backup + rollback.

## Integración con IDEs y agentes

```bash
cortex ide list                  # 11 IDEs/agentes soportados
cortex ide setup --ide claude-code   # o cursor, codex, opencode, pi…
cortex ide status
```

Los agentes acceden estructuradamente vía el **MCP server**
(`cortex mcp-server`): tools canónicos de sesiones, specs, notas, design docs
y review gates — con una golden contract test suite que fija la superficie
byte-a-byte.

## Sesiones y modos operativos

Cada unidad de trabajo es una **Sesión** con checkpoints. Tres modos,
inferidos automáticamente:

| Modo | Cómo llegan los checkpoints |
|---|---|
| `managed` | El skill orquestador verifica cada paso antes de avanzar. |
| `observed` | Tu IDE emite checkpoints por hooks (Claude Code, Cursor, Pi, OpenCode…). |
| `byo` | Traé cualquier workflow; el reconstructor sintetiza desde git diff + hooks. |

Los quality gates vienen integrados: indexación transaccional de notas,
review en dos etapas (`accept / redelegate / warn`), self-review de drafts e
inyección de contexto con presupuesto.

## Performance (medida, no prometida)

Una capa nativa escrita en Rust — opt-in por entorno con `CORTEX_NATIVE=1`,
con paridad bit-a-bit verificada gate por gate:

| Ruta caliente | Baseline Python | Nativo | Speed-up |
|---|---|---|---|
| Scoring batch coseno | 51.1 ms | 1.85 ms | **27.6×** |
| Cold load store vectorial (5k) | 31.6 ms | 5.0 ms | **6.4×** |
| Ingesta vectorial (5k) | 50 s | 13.6 ms | **3684×** |
| BM25 p99 | 10.1 ms | 1.85 ms | **5.5×** (gate ≤2 ms cumplido) |
| Webgraph n=1000 | 3.16 s | 345 ms | **9.2×** |
| Primera query tras boot (embedder frío) | 457 ms | 22 ms | **20.8×** |

Metodología completa: `bench/results/COMPARE.md` y los ADRs en
`docs/transformacion/`.

## Hardware: números honestos

Picos medidos en una laptop de gama media (ASUS S5402ZA, 11 GB RAM):

| Operación | Pico de RAM |
|---|---|
| `cortex search` (pipeline CLI completo) | ~106 MB |
| Embedder semántico (MiniLM, batch) | ~465 MB |
| Multilingual e5-large cargado (ES) | ~2.2 GB |
| `cortex-brain --model` (LFM2.5, ctx 4096) | ~1.3 GB |

Regla práctica: **un solo modelo residente por vez**. En 8 GB corre todo
cómodo si no mantenés abiertos juntos el LLM y el embedder grande.
(Cuantizamos MiniLM a int8 para ahorrar RAM y el gate de calidad lo rechazó —
paridad 0.947 < 0.99 — así que no lo shipeamos.)

## Arquitectura

```text
┌──────────────────── Capa de aplicación Python ───────────────────────────┐
│  CLI (Typer, 8 cmds visibles)   MCP server   TUI Home   ActionEngine     │
│  Session primitive · quality gates · documenter · retrieval híbrido (RRF)│
└───────┬────────────────────────┬──────────────────────┬─────────────────┘
        │ pyo3 (_native, opt-in) │ subprocess           │ chromadb / vault
┌───────▼──────────┐   ┌─────────▼─────────┐   ┌────────▼─────────┐
│ cortex-core (RS) │   │ cortex-brain (RS) │   │ storage           │
│ scoring·BM25·    │   │ llama.cpp + GGUF  │   │ .memory/chroma    │
│ store·webgraph   │   │ LFM2.5 local LLM  │   │ vault/*.md        │
└──────────────────┘   └───────────────────┘   └───────────────────┘
```

## Referencia de configuración

Todo vive en `config.yaml` (por proyecto) — validado por Pydantic al arrancar:

| Bloque | Propósito |
|---|---|
| `episodic` | Persistencia ChromaDB, colección, campos legacy de embedding |
| `embedding` | **Modelos por idioma**: `per_language.es/en` + `language_detection: heuristic\|off` |
| `semantic` | Ruta del vault (markdown compatible Obsidian) |
| `retrieval` | `top_k`, pesos RRF por fuente |
| `llm` / `integrations` | Proveedores cloud opcionales |
| `documenter` | `default_mode: auto \| interactive` |
| `ui.language` | `es` \| `en` (TUI + chrome del brain) |

## Solución de problemas

- `cortex doctor` — valida todo y te dice el comando para arreglarlo.
- `cortex embedding-status` — qué embedder activo por idioma y estado de cache.
- Los modelos bajan a `~/.cache/cortex/fastembed` (persistente, jamás `/tmp`).
- ¿Corriendo tools/scripts? Sobreescribí el binario con `CORTEX_BIN=/ruta/cortex`.
- En redes donde las descargas largas se cortan: al reintentar se reanudan los
  blobs parciales; nada se pierde a mitad de modelo.

## Estado del proyecto

El Programa de Transformación 2026-08 está **completo**: poda y estructura
(01), estándar IDE (02), capa nativa Rust (03), embeddings bilingües (04),
UX/ActionEngine/TUI (05), brain local (06) — más una auditoría de realidad
con todos sus hallazgos resueltos. Versión actual: **0.7.0**. Ver
[`CHANGELOG.md`](CHANGELOG.md) y `docs/transformacion/`.

En el roadmap: camino GPU para la última milla de latencia end-to-end,
subcomandos nativos del CLI (cuando migren los servicios en Obra E) y la
ventana de uso `pct_motor`.

## Contribuir y licencia

PRs bienvenidos — mantené commits atómicos y los gates verdes
(`pytest tests/unit tests/integration`, `ruff`, `vulture`,
`cargo clippy && cargo test`).

MIT — ver [LICENSE](LICENSE).
