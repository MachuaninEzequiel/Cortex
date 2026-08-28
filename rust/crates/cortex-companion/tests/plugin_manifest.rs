//! B9 — validación estructural del manifest del plugin herdr (G-B5, CI).
//!
//! `toml` NO está en Cargo.lock (Ruling R3: cero paquetes nuevos), así que
//! el test parsea el manifest línea por línea con un mini-parser acotado al
//! subconjunto TOML que usamos: claves `clave = valor` en el bloque raíz y
//! bloques `[[seccion]]` con sus claves. Los valores se guardan crudos
//! (incluidos arrays inline) para comparar contra el contrato de la spec 14
//! §4 byte-a-byte. No es un parser TOML completo: si el manifest ganara
//! sintaxis fuera de ese subconjunto, el propio assert de claves lo detecta.

use std::collections::HashMap;

/// Bloques `[[section]]` con sus claves, más las claves del bloque raíz.
struct Manifest {
    root: HashMap<String, String>,
    /// (nombre de sección, claves) en orden de aparición — preserva los
    /// duplicados de `[[actions]]`.
    sections: Vec<(String, HashMap<String, String>)>,
}

fn unquote(v: &str) -> String {
    let t = v.trim();
    t.strip_prefix('"')
        .and_then(|s| s.strip_suffix('"'))
        .unwrap_or(t)
        .to_string()
}

/// Quita el comentario `#` que quede FUERA de comillas dobles (TOML real:
/// dentro de un string, `#` es literal). El manifest usa comentarios
/// inline (p. ej. `placement = "overlay"  # sticky`), así que el parser
/// debe normalizar la línea antes de partir por `=`.
fn strip_comment(line: &str) -> String {
    let mut out = String::new();
    let mut in_str = false;
    let mut prev_backslash = false;
    for c in line.chars() {
        if in_str {
            out.push(c);
            if c == '"' && !prev_backslash {
                in_str = false;
            }
            prev_backslash = c == '\\' && !prev_backslash;
        } else if c == '"' {
            in_str = true;
            out.push(c);
            prev_backslash = false;
        } else if c == '#' {
            break;
        } else {
            out.push(c);
            prev_backslash = false;
        }
    }
    out
}

fn parse_manifest(src: &str) -> Manifest {
    let mut root = HashMap::new();
    let mut sections: Vec<(String, HashMap<String, String>)> = Vec::new();
    for raw in src.lines() {
        let t = strip_comment(raw).trim().to_string();
        if t.is_empty() {
            continue;
        }
        if let Some(rest) = t.strip_prefix("[[") {
            let name = rest.trim_end_matches("]]").trim().to_string();
            sections.push((name, HashMap::new()));
            continue;
        }
        let Some((k, v)) = t.split_once('=') else {
            panic!("línea fuera del subconjunto TOML soportado: {t:?}");
        };
        let k = k.trim().to_string();
        let v = v.trim();
        let val = if v.starts_with('"') {
            unquote(v)
        } else {
            // arrays inline, tables, etc.: crudo normalizado de espacios
            v.split_whitespace().collect::<Vec<_>>().join(" ")
        };
        match sections.last_mut() {
            Some((_, keys)) => {
                keys.insert(k, val);
            }
            None => {
                root.insert(k, val);
            }
        }
    }
    Manifest { root, sections }
}

fn src() -> &'static str {
    include_str!("../../../../integrations/herdr/herdr-plugin.toml")
}

#[test]
fn manifest_has_required_top_level_fields_verbatim() {
    let m = parse_manifest(src());
    // id/name/version/min_herdr_version son obligatorios según docs 0.7.0
    // (API de plugins estable desde 0.7.0; R16 — la máquina del dueño es
    // 0.7.3 y [[panes]] placement=overlay está documentada desde 0.7.0);
    // description y platforms completan el contrato de la spec 14 §4.
    assert_eq!(
        m.root.get("id").map(String::as_str),
        Some("cortex.companion")
    );
    assert_eq!(
        m.root.get("name").map(String::as_str),
        Some("Cortex Companion")
    );
    assert_eq!(m.root.get("version").map(String::as_str), Some("0.1.0"));
    assert_eq!(
        m.root.get("min_herdr_version").map(String::as_str),
        Some("0.7.0")
    );
    assert_eq!(
        m.root.get("description").map(String::as_str),
        Some("Companion de Cortex: sesiones, acciones, búsqueda y brain en un pane")
    );
    assert_eq!(
        m.root.get("platforms").map(String::as_str),
        Some("[\"linux\", \"macos\"]"),
        "platforms debe declarar linux+macos (herdr en Windows es GA pero el \
         companion usa sockets Unix; spec 14 §4)"
    );
}

#[test]
fn manifest_declares_companion_pane_overlay() {
    let m = parse_manifest(src());
    let panes: Vec<_> = m.sections.iter().filter(|(n, _)| n == "panes").collect();
    assert_eq!(panes.len(), 1, "exactamente un pane (spec 14 §4)");
    let keys = &panes[0].1;
    assert_eq!(keys.get("id").map(String::as_str), Some("companion"));
    assert_eq!(keys.get("title").map(String::as_str), Some("Cortex"));
    assert_eq!(keys.get("placement").map(String::as_str), Some("overlay"));
    assert_eq!(
        keys.get("command").map(String::as_str),
        Some("[\"cortex-companion\"]"),
        "el pane debe invocar el binario del workspace (no `companion` — el \
         [[bin]] name explícito existe por esto)"
    );
}

#[test]
fn manifest_declares_four_actions_with_canonical_commands() {
    let m = parse_manifest(src());
    let actions: Vec<_> = m.sections.iter().filter(|(n, _)| n == "actions").collect();
    assert!(
        actions.len() >= 4,
        "al menos 4 acciones, hay {}",
        actions.len()
    );
    let find = |id: &str| {
        actions
            .iter()
            .find(|(_, k)| k.get("id").map(String::as_str) == Some(id))
    };

    // open: self-referencial — abre el pane overlay del propio plugin.
    let open = find("open").expect("acción open");
    assert_eq!(
        open.1.get("command").map(String::as_str),
        Some(
            "[\"herdr\", \"plugin\", \"pane\", \"open\", \"--plugin\", \"cortex.companion\", \
             \"--entrypoint\", \"companion\", \"--placement\", \"overlay\"]"
        )
    );
    assert_eq!(
        open.1.get("contexts").map(String::as_str),
        Some("[\"workspace\"]")
    );

    // next / status / doctor: CLI canónico con salida --json donde el brief
    // la fija; doctor SIN --json (el CLI real no lo expone — finding del
    // self-review de planes).
    assert_eq!(
        find("next")
            .expect("acción next")
            .1
            .get("command")
            .map(String::as_str),
        Some("[\"cortex\", \"next\", \"--json\"]")
    );
    assert_eq!(
        find("status")
            .expect("acción status")
            .1
            .get("command")
            .map(String::as_str),
        Some("[\"cortex\", \"session\", \"current\", \"--json\"]")
    );
    assert_eq!(
        find("doctor")
            .expect("acción doctor")
            .1
            .get("command")
            .map(String::as_str),
        Some("[\"cortex\", \"doctor\"]")
    );

    // Búsqueda: SIN acción (herdr invoca acciones sin argumentos y
    // `cortex search` exige query — la búsqueda vive en el panel Search).
    assert!(
        find("search").is_none(),
        "no debe existir acción search en el manifest (spec 14 §4)"
    );

    // Toda acción lleva title + contexts workspace (contrato 0.7.0).
    for (n, (name, k)) in actions.iter().enumerate() {
        assert_eq!(name, "actions", "sección {n} debe ser [[actions]]");
        assert!(k.contains_key("title"), "acción {n} sin title");
        assert_eq!(
            k.get("contexts").map(String::as_str),
            Some("[\"workspace\"]")
        );
    }
}

#[test]
fn manifest_ids_are_legal_for_herdr() {
    // Ids: letras ASCII, dígitos, . : _ - (docs 0.7.0). Pane/action ids no
    // llevan punto (son locales al plugin).
    let m = parse_manifest(src());
    let id = m.root.get("id").expect("id");
    assert!(id
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | ':' | '_' | '-')));
    for (name, keys) in &m.sections {
        let local = keys
            .get("id")
            .unwrap_or_else(|| panic!("[[{name}]] sin id"));
        assert!(
            !local.contains('.'),
            "id local {local:?} de [{name}] no puede contener punto"
        );
        assert!(local
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, ':' | '_' | '-')));
    }
}
