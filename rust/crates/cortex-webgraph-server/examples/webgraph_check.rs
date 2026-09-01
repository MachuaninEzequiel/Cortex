//! Verificador de paridad P12B-2 — servidor webgraph axum vs Flask.
//!
//! Uso: webgraph_check <fixtures_dir> <golden_dir>
//!
//! Levanta el router axum REAL sobre puerto efímero, golpea la MISMA
//! secuencia del oráculo (`bench/parity/webgraph_golden_p12b.py`), normaliza
//! igual ({{ROOT}}/{{TS}}/{{FP}}) y compara byte-a-byte contra
//! `golden_webgraph.txt`.

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::Path;
use std::sync::Arc;

use cortex_webgraph_server::config::WebGraphConfig;
use cortex_webgraph_server::pyjson;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

// ── embedder puro compartido ────────────────────────────────────────────────

fn fake_embed(text: &str) -> Vec<f64> {
    use sha2::{Digest, Sha256};
    // Espejo EXACTO de la semántica de slicing de Python: digest tiene 32
    // bytes y el loop pide hasta el 64 ⇒ slices vacíos ⇒ chunk=0 ⇒ dim=-1.0.
    let digest = Sha256::digest(text.as_bytes());
    let mut vec = Vec::with_capacity(8);
    for i in 0..8 {
        let start = 8 * i;
        let end = (start + 8).min(digest.len());
        let mut chunk_bytes = [0u8; 8];
        if start < digest.len() {
            chunk_bytes[..end - start].copy_from_slice(&digest[start..end]);
        }
        let chunk = u64::from_le_bytes(chunk_bytes);
        vec.push(((chunk >> 11) as f64) / 9_007_199_254_740_992.0 * 2.0 - 1.0);
    }
    vec
}

// ── carga de episódicos desde el export P3 ──────────────────────────────────

fn load_entries(persist_dir: &Path) -> Vec<cortex_app::episodic::MemoryEntry> {
    let jsonl = persist_dir.join("episodic_export.jsonl");
    if !jsonl.exists() {
        return Vec::new();
    }
    match cortex_app::episodic::NativeEpisodicStore::load(&jsonl) {
        Ok(store) => store.entries_sorted_by_id().into_iter().cloned().collect(),
        Err(e) => fail(&format!("export inválido: {e}")),
    }
}

// ── cliente HTTP std ────────────────────────────────────────────────────────

struct Resp {
    status: u16,
    content_type: String,
    body: Vec<u8>,
}

fn http_request(port: u16, method: &str, path: &str, header: bool, body: Option<&[u8]>) -> Resp {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).expect("connect");
    let mut req = format!("{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n");
    if header {
        req.push_str("X-Cortex-WebGraph: 1\r\n");
    }
    match body {
        Some(b) => {
            req.push_str("Content-Type: application/json\r\n");
            req.push_str(&format!("Content-Length: {}\r\n", b.len()));
            req.push_str("\r\n");
            stream.write_all(req.as_bytes()).unwrap();
            stream.write_all(b).unwrap();
        }
        None => {
            req.push_str("\r\n");
            stream.write_all(req.as_bytes()).unwrap();
        }
    }
    let mut raw = Vec::new();
    stream.read_to_end(&mut raw).unwrap();
    parse_response(&raw)
}

fn parse_response(raw: &[u8]) -> Resp {
    let sep = raw
        .windows(4)
        .position(|w| w == b"\r\n\r\n")
        .unwrap_or_else(|| fail("respuesta sin separador de headers"));
    let head = String::from_utf8_lossy(&raw[..sep]).to_string();
    let mut lines = head.split("\r\n");
    let status_line = lines.next().unwrap_or("");
    let status: u16 = status_line
        .split_whitespace()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(0);
    let mut content_type = String::new();
    for line in lines {
        if let Some((k, v)) = line.split_once(':') {
            if k.trim().eq_ignore_ascii_case("content-type") {
                content_type = v.trim().to_string();
            }
        }
    }
    // Body: puede venir chunked (hyper con Connection: close); decodificar.
    let raw_body = &raw[sep + 4..];
    let chunked = head.to_lowercase().contains("transfer-encoding: chunked");
    let body = if chunked {
        dechunk(raw_body)
    } else {
        raw_body.to_vec()
    };
    Resp {
        status,
        content_type,
        body,
    }
}

fn dechunk(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut pos = 0;
    while let Some(line_end) = data[pos..].windows(2).position(|w| w == b"\r\n") {
        let size_str = String::from_utf8_lossy(&data[pos..pos + line_end]).to_string();
        let size = usize::from_str_radix(size_str.trim().split(';').next().unwrap_or("0"), 16)
            .unwrap_or(0);
        pos += line_end + 2;
        if size == 0 {
            break;
        }
        out.extend_from_slice(&data[pos..pos + size]);
        pos += size + 2;
    }
    out
}

// ── normalización y registro ────────────────────────────────────────────────

fn normalizar(texto: &str, base: &Path) -> String {
    let base_str = base.to_string_lossy();
    let mut texto = texto.replace(base_str.as_ref(), "{{ROOT}}");
    let re_ts = regex::Regex::new(r#""generated_at":\s*"[^"]*""#).unwrap();
    texto = re_ts
        .replace_all(&texto, r#""generated_at":"{{TS}}""#)
        .to_string();
    let re_fp = regex::Regex::new(r#""fingerprint":\s*"[0-9a-f]{64}""#).unwrap();
    texto = re_fp
        .replace_all(&texto, r#""fingerprint":"{{FP}}""#)
        .to_string();
    if !texto.ends_with('\n') {
        texto.push('\n');
    }
    texto
}

struct Bloques {
    items: Vec<String>,
}

impl Bloques {
    fn new() -> Self {
        Self { items: Vec::new() }
    }

    fn registrar(&mut self, case_id: &str, resp: &Resp, base: &Path, status_only: bool) {
        if status_only {
            self.items
                .push(format!("### {case_id} rc={} STATUS_ONLY", resp.status));
            return;
        }
        let text = String::from_utf8_lossy(&resp.body).to_string();
        self.items.push(format!(
            "### {case_id} rc={} ct={}\n{}",
            resp.status,
            resp.content_type,
            normalizar(&text, base)
        ));
    }

    fn registrar_texto(&mut self, case_id: &str, ct: &str, texto: &str, base: &Path) {
        self.items.push(format!(
            "### {case_id} rc=200 ct={ct}\n{}",
            normalizar(texto, base)
        ));
    }
}

// ── main ────────────────────────────────────────────────────────────────────

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: webgraph_check <fixtures_dir> <golden_dir>");
    }
    let fixtures = Path::new(&args[1]);
    let golden_dir = Path::new(&args[2]);

    // Stub de apertura de archivos (sin side-effects del SO).
    std::env::set_var("CORTEX_WEBGRAPH_OPEN_DISABLE", "1");

    let work = tempfile::tempdir().unwrap();
    let wb = work.path().join("fixtures");
    copy_dir(&fixtures.join("alpha"), &wb.join("alpha"));
    copy_dir(&fixtures.join("beta"), &wb.join("beta"));
    copy_dir(&fixtures.join("ws"), &wb.join("ws"));
    // El workspace.yaml copiado trae paths ABSOLUTOS del fixture original;
    // reescribirlo contra la copia (el oráculo hace lo propio en su base).
    let ws_path = wb
        .join("ws")
        .join(".cortex")
        .join("webgraph")
        .join("workspace.yaml");
    std::fs::write(
        &ws_path,
        format!(
            "projects:\n- id: alpha\n  root: {}\n- id: beta\n  root: {}\n",
            yaml_str(&wb.join("alpha")),
            yaml_str(&wb.join("beta")),
        ),
    )
    .unwrap();

    let rt = tokio::runtime::Runtime::new().unwrap();

    // Puertos single + federado.
    let router_single = build_single(&wb);
    let router_fed = build_federated(&wb);
    let port_single = rt.block_on(serve_router(router_single));
    let port_fed = rt.block_on(serve_router(router_fed));

    let mut bloques = Bloques::new();

    // CFG: config canónica (puertos/rutas por defecto).
    let cfg_dump = pyjson::dumps(
        &WebGraphConfig::default().model_dump(),
        pyjson::Mode::Compact,
        true,
    );
    bloques.registrar_texto("CFG", "application/json", &cfg_dump, &wb);

    run_single_sequence(port_single, &wb, &mut bloques);
    run_federated_sequence(port_fed, &wb, &mut bloques);

    let salida = format!("{}\n", bloques.items.join("\n"));
    if let Ok(path) = std::env::var("WEBGRAPH_SALIDA") {
        std::fs::write(&path, &salida).unwrap();
    }
    let esperado_path = golden_dir.join("golden_webgraph.txt");
    let esperado = std::fs::read_to_string(&esperado_path)
        .unwrap_or_else(|e| fail(&format!("golden ilegible: {e}")));
    if salida == esperado {
        println!("[PASS] webgraph_check byte-parity vs golden_webgraph.txt");
        println!("\n✅ PARIDAD P12B-2");
    } else {
        diff_print(&esperado, &salida);
        eprintln!("\n❌ diferencias vs golden");
        std::process::exit(1);
    }
}

fn build_single(wb: &Path) -> axum::Router {
    // create_app reconstruye el service con entradas propias: inyectamos el
    // embedder determinista y los episódicos del export P3.
    let entries = load_entries(&wb.join("alpha").join("memory"));
    cortex_webgraph_server::server::create_app(
        &wb.join("alpha"),
        entries,
        Some(Arc::new(|t: &str| fake_embed(t))),
        None,
    )
}

fn build_federated(wb: &Path) -> axum::Router {
    cortex_webgraph_server::server::create_app(
        &wb.join("alpha"),
        Vec::new(),
        Some(Arc::new(|t: &str| fake_embed(t))),
        Some(
            &wb.join("ws")
                .join(".cortex")
                .join("webgraph")
                .join("workspace.yaml"),
        ),
    )
}

async fn serve_router(router: axum::Router) -> u16 {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    port
}

fn wait_ready(port: u16) {
    for _ in 0..200 {
        let r = http_request(port, "GET", "/api/snapshot", false, None);
        if r.status == 200 || r.status == 403 {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(25));
    }
    fail(&format!("server {port} no arrancó"));
}

fn run_single_sequence(port: u16, wb: &Path, bloques: &mut Bloques) {
    wait_ready(port);

    let r = http_request(port, "GET", "/api/snapshot", false, None);
    bloques.registrar("S00_sin_header", &r, wb, r.status == 403);

    let r = http_request(port, "GET", "/api/snapshot", true, None);
    bloques.registrar("S01_snapshot_hybrid_default", &r, wb, false);

    let r = http_request(port, "GET", "/api/snapshot?mode=semantic", true, None);
    bloques.registrar("S02_snapshot_semantic", &r, wb, false);

    let r = http_request(port, "GET", "/api/snapshot?mode=episodic", true, None);
    bloques.registrar("S03_snapshot_episodic", &r, wb, false);

    let r = http_request(port, "GET", "/api/snapshot?mode=bogus", true, None);
    bloques.registrar("S04_mode_invalido", &r, wb, false);

    let node_id = "semantic:specs%2F2026-05-01_auth-spec.md";
    let r = http_request(port, "GET", &format!("/api/node/{node_id}"), true, None);
    bloques.registrar("S05_node_detail_spec", &r, wb, false);

    let r = http_request(port, "GET", "/api/node/missing-node", true, None);
    bloques.registrar("S06_node_missing", &r, wb, false);

    let r = http_request(
        port,
        "GET",
        "/api/subgraph?node_id=semantic%3Aspecs%2F2026-05-01_auth-spec.md&depth=1",
        true,
        None,
    );
    bloques.registrar("S07_subgraph_depth1", &r, wb, false);

    let r = http_request(
        port,
        "GET",
        "/api/subgraph?node_id=semantic%3Anotes%2Fideas.md&depth=2&edge_types=shared_tag,wikilink",
        true,
        None,
    );
    bloques.registrar("S08_subgraph_edge_types", &r, wb, false);

    let r = http_request(
        port,
        "POST",
        "/api/open",
        true,
        Some(br#"{"node_id":"missing"}"#),
    );
    bloques.registrar("S09_open_unknown", &r, wb, false);

    let r = http_request(port, "POST", "/api/open", true, Some(b"{}"));
    bloques.registrar("S10_open_body_invalido", &r, wb, false);

    let r = http_request(
        port,
        "POST",
        "/api/open",
        true,
        Some(br#"{"node_id":"episodic:mem_02"}"#),
    );
    bloques.registrar("S11_open_sin_doc_local", &r, wb, false);

    let r = http_request(
        port,
        "POST",
        "/api/open",
        true,
        Some(br#"{"node_id":"semantic:glossary/rrf.md"}"#),
    );
    bloques.registrar("S12_open_ok", &r, wb, false);

    let r = http_request(port, "GET", "/static/style.css", true, None);
    bloques.registrar("S13_static_css", &r, wb, false);

    let r = http_request(port, "GET", "/static/app.js", true, None);
    bloques.registrar("S14_static_js", &r, wb, false);

    let r = http_request(port, "GET", "/", true, None);
    bloques.registrar("S15_index_html", &r, wb, false);
}

fn run_federated_sequence(port: u16, wb: &Path, bloques: &mut Bloques) {
    wait_ready(port);

    let r = http_request(port, "GET", "/api/snapshot", true, None);
    bloques.registrar("F01_snapshot_federated", &r, wb, false);

    let r = http_request(
        port,
        "GET",
        "/api/node/alpha%3A%3Asemantic%3Aglossary%2Frrf.md",
        true,
        None,
    );
    bloques.registrar("F02_node_prefijado", &r, wb, false);

    let r = http_request(port, "GET", "/api/node/no-existe", true, None);
    bloques.registrar("F03_node_missing_federated", &r, wb, false);
}

fn yaml_str(p: &Path) -> String {
    p.to_string_lossy().replace('\\', "/")
}

fn copy_dir(src: &Path, dst: &Path) {
    std::fs::create_dir_all(dst).unwrap();
    for entry in std::fs::read_dir(src).unwrap() {
        let e = entry.unwrap();
        let ty = e.file_type().unwrap();
        let to = dst.join(e.file_name());
        if ty.is_dir() {
            copy_dir(&e.path(), &to);
        } else {
            std::fs::copy(e.path(), &to).unwrap();
        }
    }
}

fn diff_print(esperado: &str, salida: &str) {
    let el: Vec<&str> = esperado.split('\n').collect();
    let sl: Vec<&str> = salida.split('\n').collect();
    let mut count = 0;
    for i in 0..el.len().max(sl.len()) {
        let ev = el.get(i).copied();
        let sv = sl.get(i).copied();
        if ev != sv {
            println!("@@ línea {}\n- {ev:?}\n+ {sv:?}", i + 1);
            count += 1;
            if count >= 40 {
                println!("… (más diferencias truncadas)");
                break;
            }
        }
    }
}
