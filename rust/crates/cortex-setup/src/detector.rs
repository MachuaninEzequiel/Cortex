//! Detector de proyecto — porteo de `cortex/setup/detector.py`.

use std::path::Path;

#[derive(Debug, Clone, Default)]
pub struct StackInfo {
    pub language: String,
    pub package_manager: String,
    pub project_name: String,
    pub frameworks: Vec<String>,
    #[allow(dead_code)]
    pub has_tests: bool,
    pub test_command: String,
    pub lint_command: String,
    pub build_command: String,
    #[allow(dead_code)]
    pub dev_dependencies: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct CIInfo {
    #[allow(dead_code)]
    pub has_github_actions: bool,
    #[allow(dead_code)]
    pub workflows: Vec<String>,
    #[allow(dead_code)]
    pub has_other_ci: bool,
    #[allow(dead_code)]
    pub ci_type: String,
}

#[derive(Debug, Clone, Default)]
pub struct EnvInfo {
    pub has_openai_key: bool,
    #[allow(dead_code)]
    pub has_anthropic_key: bool,
    #[allow(dead_code)]
    pub has_ollama: bool,
    #[allow(dead_code)]
    pub ollama_base_url: Option<String>,
}

/// Layout mínimo consumido por los renderers (`layout.is_new_layout`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Layout {
    New,
    Legacy,
}

#[derive(Debug, Clone, Default)]
pub struct ProjectContext {
    pub stack: StackInfo,
    #[allow(dead_code)]
    pub ci: CIInfo,
    pub env: EnvInfo,
    /// None = layout no descubierto (equivalente a `layout=None` en Python).
    pub is_new_layout: Option<bool>,
}

impl ProjectContext {
    /// Detecta el stack/CI/env sobre `root` y el layout por presencia de
    /// `.cortex/workspace.yaml` con `layout_version >= 2` (sufijo fiel para
    /// los campos que consumen los templates; el descubrimiento completo
    /// vive en cortex-app).
    pub fn detect(root: &Path) -> ProjectContext {
        let env = EnvInfo {
            has_openai_key: std::env::var_os("OPENAI_API_KEY").is_some_and(|v| !v.is_empty()),
            has_anthropic_key: std::env::var_os("ANTHROPIC_API_KEY").is_some_and(|v| !v.is_empty()),
            has_ollama: std::env::var_os("OLLAMA_BASE_URL").is_some_and(|v| !v.is_empty()),
            ollama_base_url: std::env::var("OLLAMA_BASE_URL").ok(),
        };
        Self::detect_with(root, &env)
    }

    /// Variante testeable con env explícito (paridad con `_detect_env`).
    pub fn detect_with(root: &Path, env: &EnvInfo) -> ProjectContext {
        let mut ctx = ProjectContext {
            stack: detect_stack(root),
            ci: detect_ci(root),
            env: env.clone(),
            is_new_layout: Some(detect_layout_new(root)),
        };
        if ctx.stack.project_name.is_empty() {
            let name = root
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_default();
            ctx.stack.project_name = name;
        }
        ctx
    }
}

fn detect_layout_new(root: &Path) -> bool {
    // Espejo del Case 1 de WorkspaceLayout.discover para la raíz dada.
    let ws = root.join(".cortex").join("workspace.yaml");
    if ws.is_file() {
        if let Ok(content) = std::fs::read_to_string(&ws) {
            // parse mínimo de "layout_version:" (fixture controlado)
            for line in content.lines() {
                let line = line.trim();
                if let Some(rest) = line.strip_prefix("layout_version:") {
                    if rest.trim().parse::<i64>().map(|v| v >= 2).unwrap_or(false) {
                        return true;
                    }
                }
            }
        }
    }
    false
}

fn read_json(path: &Path) -> Option<serde_json::Value> {
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

fn walk_contains(
    root: &Path,
    pred: impl Fn(&std::path::PathBuf) -> bool + Copy,
    depth: usize,
) -> bool {
    let Ok(entries) = std::fs::read_dir(root) else {
        return false;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if pred(&p) {
            return true;
        }
        let descend =
            depth > 0 && p.is_dir() && p.file_name().map(|n| n != ".git").unwrap_or(false);
        if descend && walk_contains(&p, pred, depth - 1) {
            return true;
        }
    }
    false
}

fn detect_stack(root: &Path) -> StackInfo {
    let mut info = StackInfo::default();

    // Orden de prioridad de Python: python, javascript, go, rust, java, ruby.
    let order = ["python", "javascript", "go", "rust", "java", "ruby"];
    for lang in order {
        let result = match lang {
            "python" => detect_python(root),
            "javascript" => detect_node(root),
            "go" => detect_go(root),
            "rust" => detect_rust(root),
            "java" => detect_java(root),
            _ => detect_ruby(root),
        };
        if let Some(result) = result {
            info.language = lang.to_string();
            info.package_manager = result
                .get("package_manager")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .into();
            info.project_name = result
                .get("project_name")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .into();
            info.frameworks = result
                .get("frameworks")
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default();
            info.has_tests = result
                .get("has_tests")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            info.test_command = result
                .get("test_command")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .into();
            info.lint_command = result
                .get("lint_command")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .into();
            info.build_command = result
                .get("build_command")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .into();
            info.dev_dependencies = result
                .get("dev_dependencies")
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default();
            break;
        }
    }
    info
}

fn map_of(
    pairs: Vec<(&str, serde_json::Value)>,
) -> Option<serde_json::Map<String, serde_json::Value>> {
    let mut m = serde_json::Map::new();
    for (k, v) in pairs {
        m.insert(k.to_string(), v);
    }
    Some(m)
}

fn s(v: &str) -> serde_json::Value {
    serde_json::Value::String(v.into())
}

fn root_name(root: &Path) -> String {
    root.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default()
}

fn detect_python(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    let pyproject = root.join("pyproject.toml");
    let setup_py = root.join("setup.py");
    let requirements = root.join("requirements.txt");
    if pyproject.exists() || setup_py.exists() || requirements.exists() {
        let has_tests = walk_contains(
            root,
            |p| {
                p.is_file()
                    && p.file_name()
                        .map(|n| {
                            let n = n.to_string_lossy();
                            n.starts_with("test_") && n.ends_with(".py")
                                || (n.ends_with("_test.py"))
                        })
                        .unwrap_or(false)
            },
            8,
        ) || root.join("tests").is_dir();
        map_of(vec![
            ("package_manager", s("pip")),
            ("project_name", s(&root_name(root))),
            ("has_tests", serde_json::Value::Bool(has_tests)),
            (
                "test_command",
                s(if has_tests {
                    "pytest"
                } else {
                    "python -m unittest"
                }),
            ),
            ("lint_command", s("ruff check .")),
        ])
    } else {
        None
    }
}

fn detect_go(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    let go_mod = root.join("go.mod");
    let content = std::fs::read_to_string(&go_mod).ok()?;
    let name = content
        .lines()
        .find_map(|l| l.strip_prefix("module "))
        .map(|m| m.split_whitespace().next().unwrap_or("").to_string())
        .filter(|m| !m.is_empty())
        .unwrap_or_default();
    let has_tests = root.join("go_test.go").exists()
        || walk_contains(
            root,
            |p| {
                p.is_file()
                    && p.file_name()
                        .map(|n| n.to_string_lossy().ends_with("_test.go"))
                        .unwrap_or(false)
            },
            8,
        );
    map_of(vec![
        ("package_manager", s("go")),
        ("project_name", s(&name)),
        ("has_tests", serde_json::Value::Bool(has_tests)),
        ("test_command", s("go test ./...")),
        ("lint_command", s("golangci-lint run")),
    ])
}

fn detect_rust(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    let cargo_toml = root.join("Cargo.toml");
    let content = std::fs::read_to_string(cargo_toml).ok()?;
    // re.search(r'name\s*=\s*"([^"]+)"')
    let name = find_toml_name(&content).unwrap_or_default();
    map_of(vec![
        ("package_manager", s("cargo")),
        ("project_name", s(&name)),
        ("has_tests", serde_json::Value::Bool(true)),
        ("test_command", s("cargo test")),
        ("lint_command", s("cargo clippy")),
        ("build_command", s("cargo build --release")),
    ])
}

/// Primera aparición de `name = "..."` (semántica de la regex original).
pub(crate) fn find_toml_name(content: &str) -> Option<String> {
    for line in content.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("name") {
            let rest = rest.trim_start();
            if let Some(rest) = rest.strip_prefix('=') {
                let rest = rest.trim_start();
                if let Some(rest) = rest.strip_prefix('"') {
                    if let Some(end) = rest.find('"') {
                        return Some(rest[..end].to_string());
                    }
                }
            }
        }
    }
    None
}

fn detect_java(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    if root.join("build.gradle").exists() || root.join("build.gradle.kts").exists() {
        return map_of(vec![
            ("package_manager", s("gradle")),
            ("project_name", s(&root_name(root))),
            ("has_tests", serde_json::Value::Bool(true)),
            ("test_command", s("./gradlew test")),
            ("lint_command", s("./gradlew check")),
            ("build_command", s("./gradlew build")),
        ]);
    }
    if root.join("pom.xml").exists() {
        return map_of(vec![
            ("package_manager", s("maven")),
            ("project_name", s(&root_name(root))),
            ("has_tests", serde_json::Value::Bool(true)),
            ("test_command", s("mvn test")),
            ("lint_command", s("mvn checkstyle:check")),
            ("build_command", s("mvn package")),
        ]);
    }
    None
}

fn detect_ruby(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    let content = std::fs::read_to_string(root.join("Gemfile")).ok()?;
    let mut frameworks: Vec<String> = Vec::new();
    if content.contains("rails") || content.contains("gem 'rails'") {
        frameworks.push("rails".into());
    }
    if content.contains("rspec") || content.contains("gem 'rspec'") {
        frameworks.push("rspec".into());
    }
    let has_tests = root.join("spec").exists();
    let test_command = if frameworks.iter().any(|f| f == "rspec") {
        "bundle exec rspec"
    } else {
        "bundle exec rake test"
    };
    map_of(vec![
        ("package_manager", s("bundler")),
        ("project_name", s(&root_name(root))),
        (
            "frameworks",
            serde_json::Value::Array(frameworks.into_iter().map(|f| s(&f)).collect()),
        ),
        ("has_tests", serde_json::Value::Bool(has_tests)),
        ("test_command", s(test_command)),
        ("lint_command", s("bundle exec rubocop")),
    ])
}

fn detect_node(root: &Path) -> Option<serde_json::Map<String, serde_json::Value>> {
    let pkg_path = root.join("package.json");
    if !pkg_path.exists() {
        return None;
    }
    let pkg = read_json(&pkg_path)?.as_object()?.clone();

    let deps_value = |k: &str| {
        pkg.get(k)
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default()
    };
    let mut deps = deps_value("dependencies");
    for (k, v) in deps_value("devDependencies") {
        deps.insert(k, v);
    }

    let framework_map: &[(&str, &str)] = &[
        ("react", "React"),
        ("next", "Next.js"),
        ("next.js", "Next.js"),
        ("vue", "Vue"),
        ("nuxt", "Nuxt"),
        ("@angular/core", "Angular"),
        ("express", "Express"),
        ("fastify", "Fastify"),
        ("nestjs", "NestJS"),
        ("@nestjs/core", "NestJS"),
        ("svelte", "Svelte"),
        ("remix", "Remix"),
        ("@remix-run/node", "Remix"),
        ("django", "Django"),
        ("flask", "Flask"),
        ("fastapi", "FastAPI"),
        ("bullmq", "BullMQ"),
        ("bull", "Bull"),
        ("prisma", "Prisma"),
        ("sequelize", "Sequelize"),
        ("typeorm", "TypeORM"),
    ];
    let frameworks: Vec<String> = framework_map
        .iter()
        .filter(|(dep, _)| deps.contains_key(*dep))
        .map(|(_, fw)| fw.to_string())
        .collect();

    let scripts = pkg
        .get("scripts")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let get_script = |k: &str| scripts.get(k).and_then(|v| v.as_str()).unwrap_or("");
    let has_tests = !get_script("test").is_empty();

    let package_manager = if root.join("pnpm-lock.yaml").exists() {
        "pnpm"
    } else if root.join("yarn.lock").exists() {
        "yarn"
    } else {
        "npm"
    };

    let project_name = pkg
        .get("name")
        .and_then(|v| v.as_str())
        .map(str::to_string)
        .unwrap_or_default();

    let dev_dependencies: Vec<String> = deps_value("devDependencies").keys().cloned().collect();

    map_of(vec![
        ("package_manager", s(package_manager)),
        ("project_name", s(&project_name)),
        (
            "frameworks",
            serde_json::Value::Array(frameworks.into_iter().map(|f| s(&f)).collect()),
        ),
        ("has_tests", serde_json::Value::Bool(has_tests)),
        (
            "test_command",
            s(if get_script("test").is_empty() {
                "echo 'no test script'"
            } else {
                get_script("test")
            }),
        ),
        ("lint_command", s(get_script("lint"))),
        ("build_command", s(get_script("build"))),
        (
            "dev_dependencies",
            serde_json::Value::Array(dev_dependencies.into_iter().map(|d| s(&d)).collect()),
        ),
    ])
}

fn detect_ci(root: &Path) -> CIInfo {
    let mut info = CIInfo::default();
    let gh_workflows = root.join(".github").join("workflows");
    if gh_workflows.is_dir() {
        info.has_github_actions = true;
        if let Ok(entries) = std::fs::read_dir(&gh_workflows) {
            info.workflows = entries
                .flatten()
                .filter(|e| e.path().is_file())
                .filter(|e| {
                    e.path()
                        .extension()
                        .map(|x| x == "yml" || x == "yaml")
                        .unwrap_or(false)
                })
                .map(|e| e.file_name().to_string_lossy().to_string())
                .collect();
        }
    }
    if root.join(".gitlab-ci.yml").exists() {
        info.has_other_ci = true;
        info.ci_type = "gitlab-ci".into();
    }
    if root.join(".circleci").join("config.yml").exists() {
        info.has_other_ci = true;
        info.ci_type = "circleci".into();
    }
    if root.join("Jenkinsfile").exists() {
        info.has_other_ci = true;
        info.ci_type = "jenkins".into();
    }
    if !info.has_github_actions && !info.has_other_ci {
        info.ci_type = "none".into();
    }
    info
}
