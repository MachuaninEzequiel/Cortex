use std::path::PathBuf;

fn main() {
    stage_cli_sidecar();
    tauri_build::build();
}

/// Copia `cortex-cli` al directorio `binaries/` con el triple de target,
/// que es lo que Tauri `externalBin` espera.
fn stage_cli_sidecar() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let workspace = manifest.join("../..");
    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "debug".into());
    let target = std::env::var("TARGET").unwrap_or_default();

    let mut srcs = Vec::new();
    if !target.is_empty() {
        srcs.push(
            workspace
                .join("target")
                .join(&target)
                .join(&profile)
                .join("cortex-cli"),
        );
        srcs.push(
            workspace
                .join("target")
                .join(&target)
                .join(&profile)
                .join("cortex-cli.exe"),
        );
    }
    srcs.push(workspace.join("target").join(&profile).join("cortex-cli"));
    srcs.push(
        workspace
            .join("target")
            .join(&profile)
            .join("cortex-cli.exe"),
    );

    let Some(src) = srcs.into_iter().find(|p| p.is_file()) else {
        println!("cargo:warning=cortex-cli no está compilado aún; el bundle no incluirá sidecar (MCP usará PATH)");
        return;
    };

    let dest_dir = manifest.join("binaries");
    if let Err(e) = std::fs::create_dir_all(&dest_dir) {
        println!("cargo:warning=no pude crear binaries/: {e}");
        return;
    }
    let dest = if target.is_empty() {
        dest_dir.join(src.file_name().unwrap())
    } else if src.extension().is_some_and(|e| e == "exe") {
        dest_dir.join(format!("cortex-cli-{target}.exe"))
    } else {
        dest_dir.join(format!("cortex-cli-{target}"))
    };
    if let Err(e) = std::fs::copy(&src, &dest) {
        println!(
            "cargo:warning=no pude copiar sidecar {}: {e}",
            src.display()
        );
        return;
    }
    println!("cargo:rerun-if-changed={}", src.display());
}
