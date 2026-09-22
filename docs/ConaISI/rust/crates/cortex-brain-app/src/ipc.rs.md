# rust/crates/cortex-brain-app/src/ipc.rs

## Qué tiene adentro

IPC JSON-lines (NDJSON):

- `QueryRequest { kind, project, text, request_id }` (serde rename `type`)
- `QueryResponse { kind, text, request_id, tool_calls? }` — kinds: `done`/`error`/`chunk`/`focus_ack`
- `socket_path()`: Linux `$XDG_RUNTIME_DIR/cortex-brain.sock` o `/tmp/cortex-brain-<uid>.sock`; macOS `$TMPDIR`; Windows `None` (named pipe no implementado)
- `BindError` / `ConnectError`
- Unix: `try_bind` (stale socket se borra; permisos 0600), `try_connect`, `IpcServer` (Drop borra el archivo), `IpcClient`, `IpcConnection` + split read/write
- `read_json_line` / `write_json_line`

## Para qué sirve

Single-instance y `--query` contra la GUI viva. Un request por conexión; chunks en la misma conexión.

## Relaciones

### Recibe de

- clientes (`main.rs` QueryClient / focus); `handle_connection` en `lib.rs`

### Envía a

- stream Unix; path del socket

### Notas de implementación observadas en el código

Windows: `socket_path_impl` retorna None. Comentarios G-A2 hablan de echo; el código de `lib.rs` ya responde con el engine (chunks+done).
