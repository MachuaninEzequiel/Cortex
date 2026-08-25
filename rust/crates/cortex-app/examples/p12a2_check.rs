//! Verificador de paridad P12A-2 — WorkItemService nativo vs oráculo Python.
//!
//! Uso: p12a2_check <fixtures_dir> <golden_dir>
//!
//! Reproduce los escenarios S01–S09 de bench/parity/p12a2_golden.py sobre el
//! porte cortex_app::workitems y compara el reporte normalizado byte-a-byte
//! contra golden_p12a2.txt.
//!
//! Los errores del servicio son Result<String> con el mensaje de Python; acá
//! se les antepone el nombre de la excepción original para igualar el formato
//! del oráculo (KeyError/RuntimeError/FileNotFoundError/DuplicateDocumentError).

use std::collections::{BTreeMap, HashMap};
use std::path::Path;
use std::process::exit;
use std::time::{SystemTime, UNIX_EPOCH};

use chrono::TimeZone;
use cortex_app::workitems::{
    EpisodicMemoryRequest, EpisodicSink, SemanticIndexer, TrackedItem, WorkItemKind,
    WorkItemProvider, WorkItemService, WorkItemSource,
};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    exit(1);
}

// ── fakes espejo de tests/unit/workitems ────────────────────────────────────

struct FakeProvider {
    configurado: bool,
}

const SYNC_FIJA: &str = "2026-08-22T14:03:00.000000Z";

impl WorkItemProvider for FakeProvider {
    fn source_name(&self) -> &str {
        "fake"
    }
    fn is_configured(&self) -> bool {
        self.configurado
    }
    fn get_item(&self, external_id: &str) -> Result<TrackedItem, String> {
        let mut it = TrackedItem::new(
            external_id,
            WorkItemSource::Jira,
            format!("HU {external_id} búsqueda semántica"),
        );
        it.kind = WorkItemKind::Story;
        it.description = "Como usuario quiero buscar en mi bóveda semánticamente.".into();
        it.acceptance_criteria = vec!["búsqueda híbrida responde <1s".into()];
        it.labels = vec!["rag".into()];
        it.assignee = Some("chucho".into());
        it.external_url = Some(format!(
            "https://empresa.atlassian.net/browse/{external_id}"
        ));
        it.sync_timestamp = Some(SYNC_FIJA.into());
        Ok(it)
    }
}

#[derive(Default)]
struct CaptorEpisodic {
    llamadas: Vec<EpisodicMemoryRequest>,
}

impl EpisodicSink for CaptorEpisodic {
    fn add_memory(
        &mut self,
        req: EpisodicMemoryRequest,
    ) -> Result<cortex_app::episodic::MemoryEntry, String> {
        self.llamadas.push(req);
        Ok(cortex_app::episodic::MemoryEntry {
            id: "mem_check000".into(),
            content: String::new(),
            memory_type: String::new(),
            tags: vec![],
            files: vec![],
            timestamp: String::new(),
            metadata: BTreeMap::new(),
        })
    }
}

struct CaptorSemantic {
    llamadas: Vec<String>,
}

impl SemanticIndexer for CaptorSemantic {
    fn index_file(&mut self, rel_path: &str) -> bool {
        self.llamadas.push(rel_path.to_string());
        false
    }
}

// ── mini-JSON estilo json.dumps(indent=1, sort_keys=True) ───────────────────

enum Jv {
    Obj(Vec<(String, Jv)>),
    Arr(Vec<Jv>),
    Str(String),
}

fn escape(s: &str) -> String {
    let mut out = String::new();
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn emit(v: &Jv, nivel: usize, out: &mut String) {
    let pad = " ".repeat(nivel);
    let pad_inner = " ".repeat(nivel + 1);
    match v {
        Jv::Obj(campos) => {
            if campos.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (i, (k, val)) in campos.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                out.push_str(&escape(k));
                out.push_str(": ");
                emit(val, nivel + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push('}');
        }
        Jv::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                emit(item, nivel + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push(']');
        }
        Jv::Str(s) => out.push_str(&escape(s)),
    }
}

// ── runner de escenarios ─────────────────────────────────────────────────────

/// Copia RECURSIVA: el fixture pristine tiene vault/hu/cor-999.md.
fn copia_recursiva(src: &Path, dst: &Path) {
    std::fs::create_dir_all(dst).expect("create_dir");
    for entry in std::fs::read_dir(src).expect("read_dir").flatten() {
        let destino = dst.join(entry.file_name());
        if entry.path().is_dir() {
            copia_recursiva(&entry.path(), &destino);
        } else {
            std::fs::copy(entry.path(), &destino).expect("copy");
        }
    }
}

fn tipo_de_error(msg: &str) -> &'static str {
    if msg.starts_with("Tracked item not found") {
        "FileNotFoundError"
    } else if msg.starts_with("Document already exists") {
        "DuplicateDocumentError"
    } else if msg.starts_with("Unknown work item provider") {
        "KeyError"
    } else if msg.starts_with("Provider '") {
        "RuntimeError"
    } else {
        "Exception"
    }
}

fn fixed_now() -> chrono::DateTime<chrono::Utc> {
    chrono::Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
}

/// `True`/`False` de Python en los reportes.
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

fn providers(configurado: bool) -> HashMap<String, Box<dyn WorkItemProvider>> {
    HashMap::from([(
        "fake".to_string(),
        Box::new(FakeProvider { configurado }) as Box<dyn WorkItemProvider>,
    )])
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: p12a2_check <fixtures_dir> <golden_dir>");
    }
    let fixtures = std::fs::canonicalize(&args[1]).expect("fixtures_dir");
    let gdir = std::fs::canonicalize(&args[2]).expect("golden_dir");

    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let work = std::env::temp_dir().join(format!("p12a2_work_{nanos}"));
    std::fs::create_dir_all(&work).expect("work");
    copia_recursiva(&fixtures.join("vault"), &work.join("vault"));

    let mut bloques: Vec<String> = Vec::new();

    macro_rules! emitir {
        ($titulo:expr, $body:expr) => {{
            let resultado: Result<String, String> = $body();
            bloques.push(match resultado {
                Ok(salida) => format!("### {}\nrc=0\n{salida}", $titulo),
                Err(e) => {
                    let tipo = tipo_de_error(&e);
                    // str(KeyError) imprime el repr del argumento (comillas).
                    let msg = if tipo == "KeyError" {
                        format!("'{e}'")
                    } else {
                        e
                    };
                    format!("### {}\nrc=1\n{}: {}", $titulo, tipo, msg)
                }
            });
        }};
    }

    // Helper: vault fresco desde pristine antes de cada escenario.
    macro_rules! vault_fresco {
        () => {{
            std::fs::remove_dir_all(work.join("vault")).unwrap();
            copia_recursiva(&fixtures.join("vault"), &work.join("vault"));
        }};
    }

    // S01 import+get canonical
    emitir!("S01 import+get canonical", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let mut svc =
            WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        let path = svc.import_item("COR-482", "fake", false, fixed_now())?;
        let encontrado = svc.get_item_note("COR-482")?;
        let rel = |p: &Path| p.strip_prefix(&work).unwrap().to_string_lossy().to_string();
        Ok(format!(
            "path={}\nencontrado={}",
            rel(&path),
            rel(&encontrado)
        ))
    });

    // S02 contenido nota
    emitir!(
        "S02 contenido nota ({{TS}}/{{ROOT}})",
        || -> Result<String, String> {
            vault_fresco!();
            let mut sem = CaptorSemantic { llamadas: vec![] };
            let mut svc =
                WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
            svc.import_item("COR-482", "fake", false, fixed_now())?;
            let nota = svc.get_item_note("COR-482")?;
            std::fs::read_to_string(nota).map_err(|e| e.to_string())
        }
    );

    // S03 legacy slug
    emitir!("S03 legacy slug", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let svc = WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        let legacy = svc.get_item_note("COR-999")?;
        Ok(legacy
            .strip_prefix(&work)
            .unwrap()
            .to_string_lossy()
            .to_string())
    });

    // S04 no existente
    emitir!("S04 no existente", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let svc = WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        let nota = svc.get_item_note("NOPE-1")?;
        let _ = nota;
        Ok("no debería llegar".into())
    });

    // S05 providers
    emitir!("S05 providers", || -> Result<String, String> {
        vault_fresco!();
        let mut out: Vec<String> = Vec::new();
        {
            let mut sem = CaptorSemantic { llamadas: vec![] };
            let svc =
                WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
            out.push(format!("desconocido={}", py_bool(svc.has_provider("nope"))));
            out.push(format!("fake_ok={}", py_bool(svc.has_provider("fake"))));
            out.push(format!(
                "FAKE_normaliza={}",
                py_bool(svc.has_provider("FAKE"))
            ));
        }
        {
            let mut sem = CaptorSemantic { llamadas: vec![] };
            let mut svc =
                WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
            if let Err(e) = svc.import_item("X-1", "nope", false, fixed_now()) {
                // KeyError imprime repr del argumento (comillas simples).
                out.push(format!("nope={}: '{e}'", tipo_de_error(&e)));
            }
        }
        {
            let mut sem = CaptorSemantic { llamadas: vec![] };
            let mut svc =
                WorkItemService::new(work.join("vault"), providers(false), Some(&mut sem), None);
            if let Err(e) = svc.import_item("X-1", "fake", false, fixed_now()) {
                out.push(format!("sin_conf={}: {e}", tipo_de_error(&e)));
            }
        }
        Ok(out.join("\n"))
    });

    // S06 re-import noop
    emitir!("S06 re-import noop", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let mut svc =
            WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        svc.import_item("A-1", "fake", false, fixed_now())?;
        let f = work.join("vault/hu/HU-A-1.md");
        let antes = std::fs::read_to_string(&f).map_err(|e| e.to_string())?;
        svc.import_item("A-1", "fake", false, fixed_now())?;
        let despues = std::fs::read_to_string(&f).map_err(|e| e.to_string())?;
        let mut archivos: Vec<String> = std::fs::read_dir(work.join("vault/hu"))
            .unwrap()
            .flatten()
            .filter(|e| e.path().extension().and_then(|x| x.to_str()) == Some("md"))
            .map(|e| e.file_name().to_string_lossy().to_string())
            .collect();
        archivos.sort();
        let noop_igual = antes == despues;
        // repr Python de lista de strings: ['a.md', 'b.md'] (comillas simples).
        let lista = format!(
            "[{}]",
            archivos
                .iter()
                .map(|a| format!("'{a}'"))
                .collect::<Vec<_>>()
                .join(", ")
        );
        Ok(format!(
            "noop_igual={}\narchivos={lista}",
            py_bool(noop_igual)
        ))
    });

    // S07 duplicado distinto
    emitir!("S07 duplicado distinto", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let mut svc =
            WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        let path = svc.import_item("DUP-7", "fake", false, fixed_now())?;
        std::fs::write(
            &path,
            "---\ntitle: otra cosa\nfingerprint: deadbeefdeadbeef\n---\ncuerpo distinto\n",
        )
        .map_err(|e| e.to_string())?;
        svc.import_item("DUP-7", "fake", false, fixed_now())?;
        Ok("no debería llegar".into())
    });

    // S08 remember episódico+semantic
    emitir!(
        "S08 remember episódico+semantic",
        || -> Result<String, String> {
            vault_fresco!();
            let mut sem = CaptorSemantic { llamadas: vec![] };
            let mut ep = CaptorEpisodic::default();
            {
                let ctx: BTreeMap<String, serde_json::Value> = BTreeMap::from([(
                    "workspace".to_string(),
                    serde_json::Value::String("obra07".into()),
                )]);
                let mut svc = WorkItemService::new(
                    work.join("vault"),
                    providers(true),
                    Some(&mut sem),
                    Some(&mut ep),
                )
                .with_context_metadata(ctx);
                svc.import_item("EP-3", "fake", true, fixed_now())?;
            }
            // json.dumps(..., indent=1, sort_keys=True) del payload.
            let episodico: Vec<Jv> = ep
                .llamadas
                .iter()
                .map(|r| {
                    Jv::Obj(vec![
                        ("content".into(), Jv::Str(r.content.clone())),
                        (
                            "extra_metadata".into(),
                            Jv::Obj(vec![("workspace".into(), Jv::Str("obra07".into()))]),
                        ),
                        (
                            "files".into(),
                            Jv::Arr(r.files.iter().cloned().map(Jv::Str).collect()),
                        ),
                        ("memory_type".into(), Jv::Str(r.memory_type.clone())),
                        (
                            "tags".into(),
                            Jv::Arr(r.tags.iter().cloned().map(Jv::Str).collect()),
                        ),
                    ])
                })
                .collect();
            let semantic_arr: Vec<Jv> = sem.llamadas.iter().cloned().map(Jv::Str).collect();
            let payload = Jv::Obj(vec![
                ("episodico".into(), Jv::Arr(episodico)),
                ("semantic".into(), Jv::Arr(semantic_arr)),
            ]);
            let mut s = String::new();
            emit(&payload, 0, &mut s);
            Ok(s)
        }
    );

    // S09 list ordenado
    emitir!("S09 list ordenado", || -> Result<String, String> {
        vault_fresco!();
        let mut sem = CaptorSemantic { llamadas: vec![] };
        let mut svc =
            WorkItemService::new(work.join("vault"), providers(true), Some(&mut sem), None);
        for eid in ["B-2", "A-1", "C-3"] {
            svc.import_item(eid, "fake", false, fixed_now())?;
        }
        let rels: Vec<String> = svc
            .list_item_notes()
            .iter()
            .map(|p| p.strip_prefix(&work).unwrap().to_string_lossy().to_string())
            .collect();
        Ok(rels.join("\n"))
    });

    // Normalización idéntica al oráculo.
    let crudo = bloques.join("");
    let ruta = work.to_string_lossy().to_string();
    let mut normalizado = crudo.replace(ruta.as_str(), "{{ROOT}}");
    // created_at/updated_at con comillas simples (yaml_dump_safe).
    let mut limpio = String::with_capacity(normalizado.len());
    for line in normalizado.split_inclusive('\n') {
        let t = line.trim_end_matches('\n');
        if let Some(rest) = t.strip_prefix("created_at: '") {
            if rest.ends_with('\'') && !rest.is_empty() {
                limpio.push_str("created_at: '{{TS}}'\n");
                continue;
            }
        }
        if let Some(rest) = t.strip_prefix("updated_at: '") {
            if rest.ends_with('\'') && !rest.is_empty() {
                limpio.push_str("updated_at: '{{TS}}'\n");
                continue;
            }
        }
        limpio.push_str(line);
    }
    normalizado = limpio;
    if !normalizado.ends_with('\n') {
        normalizado.push('\n');
    }

    let esperado = std::fs::read_to_string(gdir.join("golden_p12a2.txt"))
        .unwrap_or_else(|e| fail(&format!("falta golden: {e}")));
    if normalizado == esperado {
        println!("[PASS] golden_p12a2.txt");
        println!("\nPARIDAD P12A-2 COMPLETA ✅ (WorkItemService byte-a-byte)");
    } else {
        println!("[FAIL] golden_p12a2.txt difiere");
        let mut n = 0usize;
        for (l1, l2) in esperado.lines().zip(normalizado.lines()) {
            if l1 != l2 {
                println!("  py:   {l1}\n  rust: {l2}");
                n += 1;
                if n > 20 {
                    break;
                }
            }
        }
        fail("diferencias de paridad");
    }
    std::fs::remove_dir_all(&work).ok();
}
