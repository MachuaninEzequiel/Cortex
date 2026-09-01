fn main() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    std::fs::create_dir_all(&root).unwrap();
    let layout = cortex_workspace::WorkspaceLayout::discover(&root);
    println!("repo_root={:?} ws={:?}", layout.repo_root, layout.workspace_root);
}
