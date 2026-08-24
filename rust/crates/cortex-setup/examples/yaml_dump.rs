//! Example de paridad YAML: lee un documento JSON por stdin y lo serializa
//! con el dumper réplica de PyYAML (`yaml_dump_safe`).
//!
//! Lo usa bench/parity/p8_yaml_diff.py para el test diferencial contra
//! PyYAML real: mismo input ⇒ salida byte-a-byte idéntica.
//!
//! Uso: cargo run -q -p cortex-setup --example yaml_dump < case.json

fn json_to_yaml(v: serde_json::Value) -> cortex_setup::yaml::Yaml {
    use cortex_setup::yaml::Yaml;
    match v {
        serde_json::Value::Null => Yaml::Null,
        serde_json::Value::Bool(b) => Yaml::Bool(b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Int(i)
            } else {
                // El frontmatter canónico no produce floats; si aparecieran,
                // se rechazan ruidosamente en vez de divergir.
                panic!("float no soportado por el dumper canónico: {n}")
            }
        }
        serde_json::Value::String(s) => Yaml::Str(s),
        serde_json::Value::Array(items) => Yaml::Seq(items.into_iter().map(json_to_yaml).collect()),
        serde_json::Value::Object(map) => {
            Yaml::Map(map.into_iter().map(|(k, v)| (k, json_to_yaml(v))).collect())
        }
    }
}

fn main() {
    let mut input = String::new();
    std::io::Read::read_to_string(&mut std::io::stdin(), &mut input).expect("stdin");
    let doc: serde_json::Value = serde_json::from_str(&input).expect("JSON inválido por stdin");
    print!("{}", cortex_setup::yaml::dump(&json_to_yaml(doc)));
}
