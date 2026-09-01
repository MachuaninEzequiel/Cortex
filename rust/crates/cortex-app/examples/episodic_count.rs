//! Cuenta y valida el JSONL exportado (round-trip de datos reales, P3).
fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        return Err("uso: episodic_count <export.jsonl>".into());
    }
    let store = cortex_app::episodic::NativeEpisodicStore::load(std::path::Path::new(&args[1]))?;
    println!("count={}", store.count());
    Ok(())
}
