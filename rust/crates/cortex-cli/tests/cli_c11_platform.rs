#[test]
fn remember_summarize_sin_llm_trunca_a_300() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".git")).unwrap();
    std::fs::create_dir_all(root.join(".cortex/memory")).unwrap();
    std::fs::write(root.join(".cortex/workspace.yaml"), "layout_version: 2\n").unwrap();
    std::fs::write(
        root.join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\nllm:\n  provider: none\nepisodic:\n  persist_dir: memory\n",
    )
    .unwrap();
    std::fs::create_dir_all(root.join(".cortex/vault")).unwrap();
    std::fs::write(root.join(".cortex/memory/memories.jsonl"), "").unwrap();

    let long_text = "x".repeat(500);
    let bin = env!("CARGO_BIN_EXE_cortex-cli");
    let out = std::process::Command::new(bin)
        .current_dir(root)
        .args(["remember", "--summarize", &long_text])
        .output()
        .expect("cortex remember");
    assert!(
        out.status.success(),
        "stdout: {} | stderr: {}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );

    let mut mem = cortex_cli::memory::NativeMemory::open_without_embeddings(Some(root)).unwrap();
    let store = mem.episodic.store().expect("episodic store");
    let all = store.entries_sorted_by_id();
    assert_eq!(all.len(), 1);
    assert_eq!(all[0].content.chars().count(), 300);
}

#[test]
fn native_memory_lee_vectors_v3_si_existe() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex/workspace")).unwrap();
    std::fs::create_dir_all(root.join(".cortex/vectors")).unwrap();
    std::fs::create_dir_all(root.join("vault")).unwrap();
    std::fs::write(
        root.join("config.yaml"),
        "semantic:\n  vault_path: vault\nllm:\n  provider: none\nepisodic:\n  persist_dir: memory\n",
    )
    .unwrap();
    std::fs::write(
        root.join("vault/sample.md"),
        "---\ntitle: Sample Doc\ntags: [sample]\n---\n\n# Sample Doc\n\nContenido de prueba para vectores.\n",
    )
    .unwrap();

    let model = "all-MiniLM-L6-v2";
    let dim = 4;
    let mut store =
        cortex_core::store::VectorStore::open(&root.join(".cortex/vectors"), model).unwrap();

    let semantic = cortex_app::semantic::SemanticIndex::build(&root.join("vault")).unwrap();
    let infos: Vec<_> = semantic
        .docs
        .iter()
        .map(cortex_app::semantic::chunks_for_doc)
        .collect::<Vec<_>>()
        .concat();
    let fps: Vec<String> = infos
        .iter()
        .map(|c| cortex_app::reindex::cache_fingerprint(model, &c.embedding_text()))
        .collect();
    let ids: Vec<String> = infos.iter().map(|c| c.chunk_id.clone()).collect();
    let fake_vector: Vec<f32> = vec![0.1, 0.2, 0.3, 0.4];

    store.put_many(&fps, &ids, &fake_vector, dim).unwrap();
    store.compact().unwrap();

    let mem = cortex_cli::memory::NativeMemory::open(Some(root)).unwrap();
    assert_eq!(mem.semantic.chunks.len(), 1);
    assert_eq!(mem.semantic.chunks[0].embedding.len(), dim);
    assert!((mem.semantic.chunks[0].embedding[0] - 0.1).abs() < 1e-5);
    // Sin ONNX cargado porque hit-rate fue 100%
    assert!(mem.embedder.is_none());
}
