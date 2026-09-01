# 11 — COMPANION ENGINE (modo remoto Cortex, P13)

> Estado: ESPECIFICACIÓN DETALLADA v2, cerrada con el dueño (2026-08-24).
> Addon/plugin OPCIONAL: cortex funciona exactamente igual sin él.
> Consume piezas de Obra 07/P12 (§12); NO modifica ninguna decisión vigente.
> Regla rectora: **agregar, casi nunca cambiar** (§1.1).
> Incluye: análisis y DECISIÓN FIRMADA por el dueño sobre HANDOFF §4.8
> (wire-format MCP) en Anexo A.

## 0. Por qué y para qué

Hoy todo cortex corre en la máquina del dev y compite por CPU/RAM con IDE +
compilador + agente (el brain pica ~1.3 GB RAM). Companion Engine separa
cortex en dos roles sobre dos máquinas conectadas por LAN:

| Rol | Máquina | Responsabilidad |
|---|---|---|
| **Dev Host** | PC de escritorio | IDE, agente, git. Fuente de verdad de TODO el estado: `vault/`, `.memory/`, `.cortex/`, `config.yaml`. |
| **Compute Node** | mini-PC/laptop vieja x86_64 Linux (target oficial) · Pi 5 tier-2 | Daemon `cortexd`: motores completos sobre réplica + brain GGUF residente opcional. |

Principio operativo:

> **El dev nunca espera a cortex; cortex trabaja mientras el dev codea.**

Valor honesto: no es raw speed (los motores ya son imperceptibles). Es
(1) descarga de recursos, (2) pre-cálculo continuo (índices tibios al
volver al proyecto), (3) cualitativo en PCs de 4 GB donde e5-large + LLM
no caben cómodos.

## 1. Principios de diseño

### 1.1 Agregar, casi nunca cambiar

Todo lo existente queda intacto salvo las extensiones quirúrgicas de §12.
Ningún gate vigente (P1–P11) requiere recaptura por este addon.

### 1.2 Residencia de datos (regla central)

El Compute Node **nunca es dueño de nada**:

```text
Estado canónico (solo Dev Host escribe como dueño):
  vault/**/*.md           — notas semánticas
  .memory/*.jsonl         — store episódico (formato export neutro P3)
  .cortex/sessions/*.yaml — sesiones (P4)
  .cortex/specs|notes     — specs/notas (P12A services)
  config.yaml             — configuración

Réplica en Node (read-only para sus motores):
  copia byte-a-byte bajo /var/lib/cortexd/<workspace>/

Único flujo Node→Dev Host: OP-LOG de escrituras (§6), jamás edición directa.
```

### 1.3 Fallo explícito siempre (patrón P6/P9)

Node caído ⇒ aviso claro + fallback local (§9.4). Outbox lleno ⇒ rechazo
explícito de escrituras remotas. Nunca se finge disponibilidad ni paridad.

### 1.4 Paridad-como-contrato extendida

Toda salida remota debe ser byte-idéntica a la local sobre el mismo
snapshot de estado (gate G-R1). Scoring f64 IEEE-754 escalar ⇒ bit-exacto
cross-machine. Única excepción tolerada: últimos bits de embeddings f32
(ADR-COMPANION-1, §14). Los payloads JSON de tools (strings TextContent)
ya son byte-parity por construcción (goldens P9/P12); el ENVELOPE de
transporte se rige por la decisión del Anexo A.

## 2. Topología y procesos

```text
┌─────────────────── DEV HOST ───────────────────┐   ┌──────────── COMPUTE NODE ────────────┐
│                                                │   │                                       │
│ procesos:                                      │   │ procesos:                             │
│  · IDE/agente (MCP client → Node :7421/mcp)    │   │  · cortexd  (daemon, :7421)           │
│  · cortex (CLI nativo, hooks §9)               │   │  · cortex-brain (opcional, SSH §10)   │
│  · companion-agent (residente, ~5 MB RSS)      │   │                                       │
│                                                │   │ estado:                               │
│ estado: FUENTE DE VERDAD                       │   │  /var/lib/cortexd/<ws>/…  (réplica)   │
│  <repo>/vault .memory .cortex                  │   │  outbox.jsonl (op-log saliente)       │
│                                                │   │  modelos GGUF/ONNX ~/.cache/cortex    │
└────────────────────────────────────────────────┘   └───────────────────────────────────────┘
        │  1. push deltas (manifest+blobs+deletes) ───▶ │
        │  2. pull op-log + ack            ◀──────────  │
        │  3. reads CLI/MCP por HTTP       ◀──(datos)── │
```

- **Solo el Node escucha** (TCP 7421 default). El Dev Host inicia toda
  conexión: firewall de la PC cerrado, NAT traversal innecesario.
- `companion-agent` es proceso residente Rust (unit `systemd --user`
  provista por `cortex pair install-agent`). RSS objetivo <10 MB.
- Un agent por workspace; N workspaces soportados por Node
  (`data_dir/<dirname-del-repo>/`).

## 3. Plano de datos: MCP streamable-http

El catálogo/ruteo de cortex-mcp están CONGELADOS (P9: 32 tools,
`server_version "2.2"`). El companion reusa ese servidor tal cual y le
agrega un segundo transporte:

- Workspace: `rmcp = { features += ["transport-streamable-http-server"] }`
  (rmcp 0.8 aprobado; tokio multi-thread presente).
- cortex-mcp gana `pub fn serve_http_blocking(server, addr)` junto al
  `serve_stdio_blocking` existente (~90 LOC, patrón idéntico).
- Endpoints MCP: `POST/GET/DELETE /mcp` (streamable-http del SDK).

Consumidores:

1. **Agentes IDE**: apuntan su config MCP a `http://node:7421/mcp`.
   Cero código nuevo en la PC: el IDE ya es cliente MCP.
2. **CLI humano**: cliente MCP interno embebido (§9).

Los handlers de lectura corren sobre la réplica del Node. Los de escritura
usan write-through (§6). Herramientas sin backend remoto válido devuelven
el fallo explícito documentado existente. El wire-format del ENVELOPE:
decisión del Anexo A (recomendación: omisión rmcp + gate de equivalencia
estructural).

## 4. Plano de control HTTP `/control/*`

Servido por el mismo listener (router axum del SDK + rutas propias en
cortex-companion). Formato: JSON UTF-8. Auth: `Authorization: Bearer
<token>` en TODAS las rutas salvo `/control/hello`.

| Método+ruta | Request | Response |
|---|---|---|
| GET `/control/hello` | – | `{service:"cortexd", version, arch, schema:{store:1,sessions:1}, catalog_sha256, features:{brain:bool}}` |
| GET `/control/health` | – | `{status:"ok"\|"degraded", uptime_s, index_lag_ms, replica_age_ms, outbox_depth, outbox_cap, brain_loaded}` |
| POST `/control/sync/manifest` | `{base, manifest:[{path,sha256,size,mtime_ms}]}` | `{want:["relpath"], delete:["relpath"], pull_cursor:N}` |
| PUT `/control/sync/blob` | headers `X-Cortex-Path`, `X-Cortex-Sha256`; body crudo | `{applied:true, changed:bool, reindex_queued:bool}` |
| GET `/control/sync/pull?cursor=N&max=M` | – | `{ops:[OP…], next_cursor:N}` |
| POST `/control/sync/ack` | `{acked_cursor:N}` | `{ok:true}` |
| POST `/control/admin/drain` | – | flush outbox + fsync, sigue sirviendo reads |

Reglas duras del plano de control:

- **Handshake estricto**: `version` exacta + `schema` compatible +
  `catalog_sha256` (SHA-256 del `tests/unit/mcp/golden/list_tools.json`
  empaquetado) iguales. Mismatch ⇒ cliente falla explícito
  `COMPANION_VERSION_MISMATCH` y cae a local.
- **Validación anti-path-traversal** en `X-Cortex-Path` y en cada
  `manifest.path`: relativo POSIX, sin `..`, sin raíz absoluta, prefijo
  obligatorio ∈ {`vault/`, `.memory/`, `.cortex/`} — rechazo `400
  COMPANION_PATH_FORBIDDEN` + log WARN. Test dedicado en gate R2.
- **Comparación de réplicas por sha256 SOLAMENTE** (mtime es informativo,
  no confiable cross-machine).
- **Límite de blob**: 64 MB default (`max_blob_bytes`). Excedido ⇒
  `413 COMPANION_BLOB_TOO_LARGE` (store episódico típico ≪ 64 MB;
  sin chunking en v1).
- `status:"degraded"` si `index_lag_ms > 5000` u `outbox_depth > 80% cap`.
- Deletes: `delete[]` lista relpaths que el Node tiene y el manifest ya no
  trae ⇒ el Node borra de la réplica y marca dirty el índice (evita hits
  fantasma tras borrar notas en la PC).

## 5. Motor de sincronización PC→Node (réplica)

**Alcance del manifest**: `vault/**`, `.memory/*.jsonl`, `.cortex/**`,
excluyendo `*.lock`, `*.tmp`, `.git*`. Paths relativos POSIX ordenados
(BTreeMap).

**Trigger**: inotify recursivo vía notify-rs (debounce 500 ms) + reconcile
completo cada 15 min + on-demand `cortex remote sync`. Post-commit hook
opcional (`cortex pair install-hook`).

**Ciclo**:

1. Agent calcula manifest (sha256 streaming; crate sha2 ya en workspace).
2. `POST /sync/manifest` → Node compara contra SU réplica →
   `want[]` + `delete[]`.
3. Agent sube blobs (`PUT /sync/blob`); Node valida sha256, escribe
   `tmp + rename` atómico, marca dirty.
4. Node aplica `delete[]`; drena dirty queue async: reload
   `NativeEpisodicStore` (cold load medido 5 ms),
   `SemanticIndex::index_file` para .md, embeddings batch. Queries durante
   lag sirven índice vigente con `index_lag_ms` visible (stale-ok).
5. `GET /sync/pull?cursor=` → agent integra OP-LOG (§6) en la fuente de
   verdad → `POST /sync/ack`.

**Propiedad clave**: al integrar ops, los archivos de la PC quedan
byte-idénticos a lo que el Node ya generó ⇒ el siguiente delta los ve
iguales por sha256 ⇒ sin eco ni loops. Un mecanismo de convergencia único
para ambas direcciones.

## 6. Write-through determinista Node→PC

### 6.1 Formato OP (JSONL `outbox.jsonl` en Node, cursor monótono persistido)

```json
{"seq":41,"ts":"2026-08-24T12:00:00.123456Z",
 "kind":"episodic.append",
 "payload":{"id":"mem_a1b2c3d4","document":"…","meta":{…flatten…},
            "embedding":[0.018,…]}}
{"seq":42,"ts":"…","kind":"session.save",
 "payload":{"relpath":".cortex/sessions/SES-x.yaml","content_yaml":"…"}}
{"seq":43,"ts":"…","kind":"note.write",
 "payload":{"relpath":".cortex/notes/x.md","content":"…"}}
```

`kind ∈ {episodic.append, session.save, note.write}` (enum cerrado; kind
desconocido ⇒ skip + WARN forward-compatible). `id`/`ts`/contenido/embedding
se generan UNA vez en el Node y viajan fijados ⇒ store de la PC byte-idéntico
al de la réplica (sin drift f32 en datos compartidos).

### 6.2 Integración en Dev Host (idempotente)

- `episodic.append`: si `payload.id` existe en el JSONL fuente ⇒ skip;
  si no ⇒ append de UNA línea O_APPEND single-write (idéntico a
  `append_row`). Colisión mismo-id-contenido-distinto ⇒ id regenerado con
  sufijo `-r2` + WARN (probabilidad despreciable, manejo barato).
- `session.save`/`note.write`: escribir solo si bytes difieren (tmp+rename).
- Integración atómica por batch: procesar ops en orden de `seq`; ack SOLO
  tras fsync del batch.

### 6.3 Extensión mínima requerida en cortex-app (AGREGAR, no cambiar)

- `NativeEpisodicStore::append_row_external(row: EpisodicRow)` (~25 LOC;
  reusa `append_row` interno).
- `session::render_yaml(record) -> String` separado de
  `SessionStorage::save` (P4 ya normaliza con `canonical_json_normalized`;
  exponer el render puro). ~20 LOC.

### 6.4 Backpressure

Outbox cap 10 000 ops default. Lleno ⇒ writes remotas responden
`COMPANION_OUTBOX_FULL`; reads siguen (stale-ok). Reconexión ⇒ drain
automático del pull loop. `cortex remote status` muestra lag/depth.

### 6.5 Compaction

Compactación del JSONL episódico = operación OFFLINE exclusiva del Dev Host
con drain: pausar agent → compactar → full resync (hash cambió ⇒ Node
re-descarga). El append-only hace innecesario cualquier merge complejo.

## 7. Crate nuevo: `cortex-companion`

Alta append-only en rust/Cargo.toml (validar `cargo metadata -q`):

```text
rust/crates/cortex-companion/
  src/
    lib.rs          — tipos compartidos (Op, ManifestEntry, Health, errores)
    daemon.rs       — cortexd: router (/mcp + /control/*), estado, dirty queue
    agent.rs        — companion-agent: watcher + sync loop + integrador
    client.rs       — cliente MCP/control para CLI y tests
    sync.rs         — manifest/blob/op-log engine
    auth.rs         — token file, constant-time compare
    bin/cortexd.rs
    bin/companion-agent.rs
```

Deps nuevas: `notify` (watcher recursivo) + axum que rmcp-http ya trae.
Ambas aprobadas vía ADR-COMPANION-2. Resto ya presente: sha2, uuid, chrono,
tokio, serde, rmcp. Tipos exactos: Anexo B.

## 8. Config

### 8.1 Dev Host — `[companion]` en config.yaml

```yaml
companion:
  enabled: false                    # default: comportamiento actual exacto
  node_url: http://cortex-node.lan:7421
  token_file: ~/.config/cortex/companion-token
  auto_sync: true
  debounce_ms: 500
  full_reconcile_min: 15
  fallback_timeout_ms: 800
```

### 8.2 Node — `/etc/cortexd/config.yaml` (o env CORTEXD_*)

```yaml
bind: 0.0.0.0:7421
token_file: /etc/cortexd/token
data_dir: /var/lib/cortexd
outbox_max_ops: 10000
max_blob_bytes: 67108864
brain: true
workspaces: ["proyecto-a"]     # allowlist por dirname del repo
```

### 8.3 Impacto en golden P1: CERO

`load_and_dump` serializa el `serde_yaml::Value` CRUDO normalizado, no el
struct: sección ausente ⇒ nunca aparece en dumps. Además
`CompanionConfig` lleva `#[serde(default, skip_serializing_if)]`.
Gate R0 verifica: dumps config PASS SIN recaptura.

## 9. Integración con el CLI nativo (post-P12-B)

### 9.1 Delegación de reads

Env `CORTEX_REMOTE=1` (o `[companion].enabled=true`) + operación soportada
⇒ CLI consulta vía `client.rs` en vez de cortex-app local. Ops v1: search,
search vector, context, next, memory-report, stats, session list/status.
Salida `--json`: el content del tool result se emite TAL CUAL ⇒ byte-parity
por construcción (G-R1). Salida humana: presenter local sobre el JSON.
Matriz completa: Anexo D.

### 9.2 Subcomandos nuevos (agregados)

```text
cortex pair init                 # token + [companion] + prueba hello
cortex pair init --node          # setup del Compute Node (ver Anexo E)
cortex pair install-agent        # systemd --user unit + enable
cortex pair install-hook         # post-commit hook opcional
cortex remote status             # health/lag/outbox/versión Node
cortex remote sync               # ciclo manual
cortex remote drain              # admin drain
```

### 9.3 Fallback local

Connect/read timeout 800 ms ⇒ stderr
`WARN: companion unreachable — local fallback` + ejecución local normal.
Exit code idéntico. Nunca bloquea al dev.

## 10. Brain en el Node

- Instalación cortex COMPLETA en el Node (binarios + GGUF en
  `~/.cache/cortex/models`). El brain corre allí: router/subprocess usan la
  réplica local ⇒ mismas respuestas que en la PC.
- Acceso v1: `ssh <node> cortex-brain` (interactivo; ventana dedicada
  existente sirve). `cortex pair init` sugiere alias `cortex-brain-node`.
- Fase 2 (fuera de alcance): endpoint `/brain/chat` SSE sobre `LlmBackend`.

## 11. Doctor (checks nuevos pm_companion_*)

| Check | OK | WARN/FAIL |
|---|---|---|
| companion_reachable | hello < timeout | FAIL si enabled e inalcanzable |
| companion_version_match | version+schema+catalog_sha iguales | FAIL mismatch |
| companion_replica_lag | replica_age_ms < 60_000 | WARN arriba |
| companion_outbox | depth < 80% cap | WARN cerca, FAIL llena |

`enabled=false` ⇒ checks reportan `skipped` (addon opcional).

## 12. Cambios quirúrgicos por crate existente (TODO agregar)

| Crate | Extensión | LOC aprox |
|---|---|---|
| cortex-app | `append_row_external` + `render_yaml` sesión | ~50 |
| cortex-mcp | `serve_http_blocking` + features rmcp | ~90 |
| cortex-config | `CompanionConfig` (serde default/skip) | ~45 |
| cortex-cli | subcomandos pair/remote + hooks delegación reads | ~130 |
| cortex-doctor | 4 checks pm_companion_* | ~150 |
| rust/Cargo.toml | member nuevo + deps (append-only + cargo metadata) | ~10 |
| **NUEVO** cortex-companion | daemon+agent+client+sync | ~3000 |

Ninguna firma pública existente cambia. Suite Python oráculo: intacta.

## 13. Gates (un commit cada uno, estilo Obra 07)

| Gate | Contenido | Criterio de pase |
|---|---|---|
| R0 | ADRs + scaffolding + golden P1 intacto | cargo metadata ok · dumps config PASS sin recaptura · clippy/fmt |
| R1 | transporte http cortex-mcp | **equivalencia estructural** vs golden (Anexo A) + `cortex_ping` payload byte-a-byte vía HTTP loopback |
| R2 | cortexd read-only hello/health/manifest | goldens hello/health · mismatch rechaza · path-traversal rechazado (tests dedicados) |
| R3 | sync push + deletes + reindex | round-trip fixture 200 archivos · alta/baja/modificación convergen · index_lag converge |
| R4 | reads remotas paridad | G-R1: search/context/next `--json` byte-a-byte local vs remote (loopback, fixture común) |
| R5 | op-log + append_row_external | merge concurrente determinista: 2 productores × 500 ops ⇒ store final idéntico esperado, 0 pérdidas |
| R6 | write-through sesiones/notas | YAML generado en Node == YAML integrado en PC (bytes) |
| R7 | cliente CLI + fallback | G-R3: fallback <1 s con aviso; `--json` remoto==local |
| R8 | brain en Node + guía SSH | eval manual scriptada (chat + tool suggestion sobre réplica) |
| R9 | doctor checks + docs | suite completa verde · README Companion · fila COMPARE con RAM liberada |

Cross-arch (tier-2 Pi): script manual `scripts/companion-crossarch.sh`
(build aarch64 + misma batería generada EN la Pi). No bloquea gates x86.

## 14. ADRs requeridos

1. **ADR-COMPANION-0 — Wire-format MCP** (Anexo A): FIRMADA por el
   dueño (2026-08-24): omisión rmcp como formato canónico de ENVELOPE +
   gate de equivalencia estructural contra el golden. Resuelve
   HANDOFF §4.8 para P12-A#3 y companion a la vez.
2. **ADR-COMPANION-1 — Drift f32 embeddings cross-machine**: ONNX f32/SIMD
   difiere en últimos bits entre CPUs; scoring f64 bit-exacto. Tolerado
   SOLO en embeddings; datos compartidos viajan con embedding fijado
   (§6.1). Usa la puerta prevista en HANDOFF §4.1.
3. **ADR-COMPANION-2 — Seguridad LAN v1**: Bearer 256-bit (archivo 0600),
   constant-time compare, workspaces allowlist, anti-path-traversal,
   logs sin contenido de notas (relpaths/hashes solamente). SIN TLS v1
   (LAN confiable; rustls fase 2 ⇒ ADR propio). Aprueba deps notify/axum.
4. **ADR-COMPANION-3 — Residencia de datos + write-through determinista**:
   formaliza §1.2/§6: convergencia byte-exacta sin resolución de conflictos.

---

# ANEXO A — Decisión wire-format MCP (HANDOFF §4.8)

## A.1 El dilema exacto

El server Python serializa sus objetos pydantic con **nulls explícitos**.
Evidencia: `tests/unit/mcp/golden/list_tools.json` contiene 224 `null`
(6 campos nulos × 32 tools: `title, outputSchema, icons, annotations,
meta, execution`). El SDK Rust rmcp serializa con serde y OMITE los
`None` (`skip_serializing_if`), por lo que su `list_tools` por el wire
emite menos claves. El gate P9 congeló catálogo+dispatch (no bytes de
transporte) precisamente para no casar esta decisión sin análisis. Hoy
P12-A#3 (handlers MCP) y el companion necesitan la resolución.

## A.2 Alcance real del problema

| Capa | ¿Afecta nulls-vs-omisión? |
|---|---|
| Payload de tools (TextContent, strings JSON `indent=2`) | **NO** — es un string opaco; los goldens p9_ping ya lo prueban byte-a-byte |
| inputSchema dentro de Tool definitions | SÍ (objetos estructurados del envelope) |
| Envelope JSON-RPC (ListToolsResult, CallToolResult…) | SÍ |

Es decir: el debate es EXCLUSIVAMENTE sobre el envelope estructurado que
arma el SDK, no sobre datos de cortex.

## A.3 Opciones

**Opción A — Nulls explícitos (clonar pydantic)**: forzar a rmcp a emitir
nulls. Requiere serializers custom o post-proceso del cuerpo JSON-RPC,
acoplados a internals del SDK que cambian entre minors de rmcp 0.x.
Compra compatibilidad con: nadie — ningún cliente MCP real distingue
ausencia de null en campos opcionales (el SDK TS usa propiedades
opcionales; el spec MCP no exige presencia).

**Opción B — Omisión rmcp (formato canónico del transporte)**: el envelope
es infraestructura del SDK; el CONTRATO de cortex sigue siendo el golden
(catálogo, descripciones, schemas, mensajes), verificado estructuralmente.
Precedente interno: P9 ya declaró "el gate es contrato de catálogo +
dispatch, no bytes de transporte"; P12B aplicó "omisión tolerante solo
donde Python la tiene".

## A.4 RECOMENDACIÓN: Opción B, con blindaje

1. **Formato canónico de envelope = omisión rmcp** (stdio y http por
   igual). No se escribe ни una línea de serialización custom.
2. **Gate de equivalencia estructural** (nuevo, R1): parsear la respuesta
   HTTP `tools/list`, normalizar (null ≡ ausente), comparar profundamente
   contra `golden/list_tools.json`: mismo set de names, mismas descriptions
   byte-a-byte, mismos inputSchema profundos. Cualquier drift REAL
   (tool faltante, description editada, schema alterado) sigue siendo
   imposible colarlo como "diferencia de transporte".
3. **Los payloads de tools permanecen byte-a-byte** como hoy (p9_ping y
   goldens P12 lo exigen) — ahí vive la paridad conductual real.
4. Si algún día un cliente estricto exigiera nulls: modo compatibilidad
   OPCIONAL en `serve_http_blocking` (post-proceso acotado), nunca default.

Por qué NO A: fragilidad permanente contra upgrades del SDK oficial, costo
sin beneficiario real, y precedente peligroso (empezar a replicar quirks de
serialización del envelope Python termina replicando el stack completo).
La regla "paridad antes que velocidad" apunta a CONDUCTA observable del
usuario/agentes, no a bytes de infraestructura del SDK.

> Estado: ✅ FIRMADO POR EL DUEÑO (2026-08-24). Registrado en HANDOFF §4.8;
> desbloquea P12-A#3 (handlers MCP) y el gate R1 del companion.

# ANEXO B — Tipos Rust del crate cortex-companion

```rust
// lib.rs — tipos compartidos (todos Serialize+Deserialize, camelCase wire)

pub struct HelloInfo {
    pub service: String,            // "cortexd"
    pub version: String,            // cortex-cli --cli-version exacta
    pub arch: String,               // std::env::consts::ARCH
    pub schema: SchemaInfo,         // {store: u32, sessions: u32}
    pub catalog_sha256: String,     // hex del golden empaquetado
    pub features: FeaturesInfo,     // {brain: bool}
}

pub struct HealthInfo {
    pub status: HealthStatus,       // Ok | Degraded
    pub uptime_s: u64,
    pub index_lag_ms: u64,
    pub replica_age_ms: u64,
    pub outbox_depth: u64,
    pub outbox_cap: u64,
    pub brain_loaded: bool,
}

#[derive(PartialOrd, Ord, PartialEq, Eq)]   // orden canónico BTreeMap
pub struct ManifestEntry {
    pub path: String,      // relativo POSIX, validado (§4)
    pub sha256: String,    // hex, lowercase
    pub size: u64,
    pub mtime_ms: u64,     // informativo; NUNCA se compara
}

pub struct ManifestRequest { pub base: String, pub manifest: Vec<ManifestEntry> }
pub struct ManifestReply   { pub want: Vec<String>, pub delete: Vec<String>, pub pull_cursor: u64 }

#[derive(Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum OpPayload {
    EpisodicAppend { row: EpisodicRowDto },           // export neutro completo
    SessionSave    { relpath: String, content_yaml: String },
    NoteWrite      { relpath: String, content: String },
}

pub struct Op {
    pub seq: u64,          // monótono por Node, persistido junto al outbox
    pub ts: String,        // RFC3339 micros UTC fijado por originador
    #[serde(flatten)]
    pub payload: OpPayload,
}

// errores de dominio (siempre explícitos, patrón P6/P9)
pub enum CompanionError {
    VersionMismatch { expected: String, got: String },
    PathForbidden(String),
    BlobTooLarge(u64),
    OutboxFull,
    Unreachable(String),
    AuthRejected,
}
```

Estados internos del daemon: `DirtyQueue(BTreeSet<RelPath>)`,
`ReplicaRoot(PathBuf)`, `OutboxCursor(AtomicU64)` — single-writer por
workspace (el daemon es el ÚNICO proceso que toca la réplica).

# ANEXO C — Ejemplos wire-level

**hello**
```http
GET /control/hello HTTP/1.1

{"service":"cortexd","version":"0.7.0","arch":"x86_64",
 "schema":{"store":1,"sessions":1},
 "catalog_sha256":"9f2a…e1","features":{"brain":true}}
```

**sync/manifest**
```json
→ {"base":"proyecto-a","manifest":[
    {"path":"vault/arquitectura.md","sha256":"aa13…","size":4021,"mtime_ms":1756000000000},
    {"path":".memory/episodic.jsonl","sha256":"bb71…","size":1048576,"mtime_ms":1756000001000}]}

← {"want":[".memory/episodic.jsonl"],
   "delete":["vault/notas-viejas.md"],
   "pull_cursor":41}
```

**sync/blob**
```http
PUT /control/sync/blob HTTP/1.1
X-Cortex-Path: .memory/episodic.jsonl
X-Cortex-Sha256: bb71…
Content-Type: application/octet-stream

<1048576 bytes crudos>
← {"applied":true,"changed":true,"reindex_queued":true}
```

**sync/pull (op real de memoria)**
```json
{"ops":[{"seq":41,"ts":"2026-08-24T12:00:00.123456Z",
  "kind":"episodic.append",
  "payload":{"id":"mem_a1b2c3d4",
             "document":"Decisión: BM25 casero, tantivy descartado",
             "meta":{"id":"mem_a1b2c3d4","memory_type":"decision",
                     "timestamp":"2026-08-24T12:00:00.123456Z",
                     "tags":"[\"bm25\"]","files":"[]"},
             "embedding":[0.0182,-0.0417,…]}}],
 "next_cursor":42}
```

**MCP por HTTP (agente IDE)**
```http
POST /mcp HTTP/1.1
Authorization: Bearer …

{"jsonrpc":"2.0","id":7,"method":"tools/call",
 "params":{"name":"cortex_search",
           "arguments":{"query":"auth refactor","limit":5}}}
← {"jsonrpc":"2.0","id":7,"result":{"content":[{"type":"text","text":"{ …payload byte-a-byte… }"}]}}
```

# ANEXO D — Matriz de residencia de operaciones (v1)

| Operación | Dónde corre | Notas |
|---|---|---|
| search / search vector / context / next / memory-report / stats | **Node** | reads sobre réplica; stale-ok |
| session list / status | **Node** | read |
| MCP tools de agentes IDE (todas) | **Node** | reads directos; writes write-through §6 |
| remember / episodic.append vía MCP | **Node → PC** | op-log, embedding fijado |
| session open/checkpoint/close (CLI humano) | **PC local** | flujo interactivo canónico |
| init / setup / tutor / ci / pipeline / autopilot | **PC local** | tocan fuente de verdad o IDE |
| doctor | **PC local** | + checks remotos §11 |
| vault.reindex / operaciones destructivas | **PC local SIEMPRE** | jamás vía Node |
| webgraph server axum (P12-B) | **Node ideal** | always-on natural; fase 2 del addon |
| brain chat | **Node (SSH)** | §10 |

Criterio general: READ pesado ⇒ Node; WRITE interactivo/destructivo ⇒ PC.

# ANEXO E — Runbook `cortex pair`

**Node (una vez)**
1. Instalar binarios (`cargo install --path rust/crates/cortex-companion`
   o release) + instalación cortex completa + modelos ONNX/GGUF.
2. `cortex pair init --node` crea: `/etc/cortexd/config.yaml`,
   `/etc/cortexd/token` (0600, 256-bit hex),
   `/var/lib/cortexd/<ws>/`, unit systemd `cortexd.service` (Restart=always).
3. Imprime huella del token (primeros 8 hex) para verificar pairing.

**Dev Host (una vez)**
1. `cortex pair init` pregunta URL del Node; valida hello + huella;
   escribe `[companion]` en config.yaml y `~/.config/cortex/companion-token`
   (0600).
2. `cortex pair install-agent` instala y habilita la unit `--user`;
   primer full sync visible en `cortex remote status`.
3. Opcional: `cortex pair install-hook` (post-commit) y apuntar el IDE a
   `http://node:7421/mcp`.

**Verificación del pairing**: `cortex remote status` ⇒ status ok,
lag≈0, depth 0; `cortex search --json` remoto == local (fixture).

# ANEXO F — Plan de pruebas (por módulo)

**auth.rs**: token válido/inválido/vacío; constant-time (misma latencia
aprox); archivo 0600 exigido.
**sync.rs**: manifest round-trip idempotente (×2 corridas ⇒ 0 want);
alta/baja/modificación de archivo; delete converge; blob corrupto
(sha mismatch) rechazado; blob > cap rechazado; path traversal
(`../x`, `/abs`, `vault/../../etc`) rechazado ×6 casos.
**op-log/integrador (gate R5)**: 2 productores × 500 ops intercaladas ⇒
JSONL final == esperado byte-a-byte; duplicado id ⇒ skip; colisión
contenido-distinto ⇒ `-r2`; crash mid-batch ⇒ re-pull sin duplicar
(at-least-once + dedup = exactly-once efectivo).
**client.rs/fallback**: timeout ⇒ WARN + resultado local; mismatch
versión ⇒ fallo explícito; outbox_full ⇒ mensaje contracto.
**daemon.rs**: hello/health shapes; degraded thresholds; drain.
**parity (gates R1/R4)**: equivalencia estructural list_tools;
ping byte-a-byte vía HTTP; search/context/next `--json` remoto==local
sobre fixture común commiteado.
**config**: dumps golden P1 PASS sin recaptura; defaults no materializan.

# ANEXO G — Operación y observabilidad

- **Logs daemon**: tracing estructurado a journald: eventos
  `sync.cycle{n_files_changed}`, `reindex.done{lag_ms}`, `op.appended{seq}`,
  `auth.reject{ip}` — JAMÁS contenido de notas (solo relpaths/hashes).
- **Métricas expuestas** en `/control/health` (poll por agent): base de
  `cortex remote status` y checks doctor.
- **Troubleshooting rápido**:
  - `version mismatch` tras upgrade ⇒ correr misma versión en ambos
    (`cortex --cli-version` en los dos lados).
  - lag alto persistente ⇒ revisar tamaño de vault y CPU del Node
    (embeddings); `auto_sync: false` + sync manual como válvula.
  - outbox lleno ⇒ PC offline demasiado tiempo; reconectar y dejar drain;
    writes locales siguen posibles siempre.
  - token roto/regenerado ⇒ repetir `pair init` (30 segundos).

# ANEXO H — FMEA (modos de fallo)

| Fallo | Efecto | Detección | Mitigación |
|---|---|---|---|
| Node caído | reads remotas imposibles | timeout 800 ms | fallback local automático + WARN |
| Red particionada mid-write | op no acked | cursor sin avanzar | at-least-once + dedup por id (§6.2) |
| Disco Node lleno | blobs/ops fallan | errores 5xx + health | fallo explícito; réplica es desechable (full resync tras limpiar) |
| Réplica corrupta (power loss) | resultados erróneos | sha256 en próximo reconcile | tmp+rename + full resync on-demand |
| Token filtrado | acceso LAN al vault | — | rotación = re-run pair init; bind selectivo; TLS fase 2 |
| Upgrade asimétrico PC/Node | handshake rechaza | hello | mensaje claro; sincronizar versiones |
| Reloj Node desfasado | ts cosméticos raros | doctor WARN futuro | ts viaja fijado ⇒ sin impacto de paridad |
| Workspace renombrado | base mismatch | manifest reject | re-run pair init (barato, documentado) |
| Vault gigante (>cap blob) | JSONL rechazado | 413 explícito | compaction PC (§6.5); cap configurable |

# ANEXO I — Fase 2 (explícitamente fuera de v1)

1. TLS rustls + mTLS por dispositivo (dep nueva ⇒ ADR propio).
2. `/brain/chat` SSE (brain accesible sin SSH, desde la PC).
3. Cola always-on de trabajos (pre-cálculo bundles, documenter programático,
   webgraph server residente en Node).
4. Múltiples Nodes por workspace (hash-sharding de consultas — probablemente
   innecesario; documentado por completitud).
5. Modo compatibilidad nulls-explícitos del envelope (solo si aparece un
   cliente que lo exija).
