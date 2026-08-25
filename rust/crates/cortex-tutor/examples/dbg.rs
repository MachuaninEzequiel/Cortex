fn main() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("proj");
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let l = cortex_workspace::WorkspaceLayout::discover(&root);
    println!(
        "vault={:?} ws={:?} is_new={}",
        l.vault_path(),
        l.workspace_root.display(),
        l.is_new_layout
    );
}
