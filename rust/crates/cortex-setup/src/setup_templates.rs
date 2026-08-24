//! Renderers de `cortex/setup/templates.py` — config.yaml, workflows de
//! GitHub Actions, docs iniciales del vault, workspace.yaml, org.yaml
//! (topología enterprise) y devsecdocops.sh.
//!
//! Las plantillas embebidas viven en `setup_templates_gen.rs`, derivadas
//! automáticamente del AST de Python: cada interpolación f-string es un
//! sentinela U+E000<n>U+E001 que [`fill`] sustituye por los valores
//! calculados EN EL MISMO ORDEN en que Python los evalúa.

use crate::detector::{Layout, ProjectContext};
use crate::yaml::Yaml;

const OPEN: char = '\u{E000}';
const CLOSE: char = '\u{E001}';

/// Sustituye los sentinelas por `values` en orden.
pub fn fill(tpl: &str, values: &[String]) -> String {
    let mut out = String::with_capacity(tpl.len());
    let mut chars = tpl.chars().peekable();
    while let Some(c) = chars.next() {
        if c == OPEN {
            let mut idx = String::new();
            for c2 in chars.by_ref() {
                if c2 == CLOSE {
                    break;
                }
                idx.push(c2);
            }
            let n: usize = idx.parse().expect("sentinela numérica");
            out.push_str(values.get(n).expect("valor del sentinela"));
        } else {
            out.push(c);
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Helpers project-aware (`_get_*` de templates.py)
// ---------------------------------------------------------------------------

fn get_memory_cache_path(ctx: &ProjectContext) -> String {
    if ctx.is_new_layout == Some(true) {
        ".cortex/memory".into()
    } else {
        ".memory/chroma".into()
    }
}

fn get_test_command(ctx: &ProjectContext) -> String {
    if !ctx.stack.test_command.is_empty() {
        return ctx.stack.test_command.clone();
    }
    match ctx.stack.language.as_str() {
        "python" => "pytest".into(),
        "javascript" | "typescript" => "npm test".into(),
        "go" => "go test ./...".into(),
        "rust" => "cargo test".into(),
        "java" => "mvn test".into(),
        _ => "echo 'no test command detected'".into(),
    }
}

fn get_lint_command(ctx: &ProjectContext) -> String {
    if !ctx.stack.lint_command.is_empty() {
        return ctx.stack.lint_command.clone();
    }
    match ctx.stack.language.as_str() {
        "javascript" | "typescript" => "npm run lint || true".into(),
        "python" => "ruff check . || true".into(),
        "go" => "golangci-lint run || true".into(),
        "rust" => "cargo clippy || true".into(),
        _ => "echo 'no lint command detected'".into(),
    }
}

fn get_audit_command(ctx: &ProjectContext) -> String {
    match ctx.stack.language.as_str() {
        "javascript" | "typescript" => "npm audit --omit=dev --audit-level=high || true".into(),
        "python" => "pip audit || true".into(),
        "go" => "govulncheck ./... || true".into(),
        _ => "echo 'no audit command for this stack'".into(),
    }
}

fn get_install_command(ctx: &ProjectContext) -> String {
    match ctx.stack.package_manager.as_str() {
        "npm" => "npm ci".into(),
        "yarn" => "yarn install --frozen-lockfile".into(),
        "pnpm" => "pnpm install --frozen-lockfile".into(),
        "pip" | "pipenv" | "poetry" => "pip install -r requirements.txt".into(),
        "go" => "go mod download".into(),
        "cargo" => "cargo build".into(),
        _ => "echo 'install dependencies'".into(),
    }
}

#[allow(dead_code)]
fn get_build_command(ctx: &ProjectContext) -> String {
    if !ctx.stack.build_command.is_empty() {
        return ctx.stack.build_command.clone();
    }
    match ctx.stack.language.as_str() {
        "javascript" | "typescript" => "npm run build".into(),
        "python" => "python -m build".into(),
        "go" => "go build ./...".into(),
        "rust" => "cargo build --release".into(),
        _ => "echo 'no build command'".into(),
    }
}

fn get_setup_language(ctx: &ProjectContext) -> String {
    match ctx.stack.language.as_str() {
        "javascript" | "typescript" => r#"      - name: Setup Node.js environment
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
"#
        .into(),
        "python" => r#"      - name: Setup Python environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
"#
        .into(),
        "go" => r#"      - name: Setup Go environment
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
"#
        .into(),
        "java" | "kotlin" => r#"      - name: Setup Java environment
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
"#
        .into(),
        "ruby" => r#"      - name: Setup Ruby environment
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
"#
        .into(),
        _ => String::new(),
    }
}

// ---------------------------------------------------------------------------
// Renderers públicos
// ---------------------------------------------------------------------------

pub fn render_config_yaml(ctx: &ProjectContext) -> String {
    let (persist_dir, vault_path) = if ctx.is_new_layout == Some(true) {
        ("memory", "vault")
    } else {
        (".memory/chroma", "vault")
    };
    let (provider, model) = if ctx.env.has_openai_key {
        ("openai", "text-embedding-3-small")
    } else {
        ("none", "")
    };
    fill(
        crate::setup_templates_gen::RENDERConfigYaml_TPL,
        &[
            ctx.stack.project_name.clone(),
            ctx.stack.language.clone(),
            persist_dir.into(),
            vault_path.into(),
            provider.into(),
            model.into(),
        ],
    )
}

pub fn render_enterprise_vault_readme(ctx: &ProjectContext) -> String {
    let project_name = if ctx.stack.project_name.is_empty() {
        // El caller de Python usa ctx.root.name; el detector ya lo resolvió.
        ctx.stack.project_name.clone()
    } else {
        ctx.stack.project_name.clone()
    };
    fill(
        crate::setup_templates_gen::RENDEREnterpriseVaultReadme_TPL,
        &[project_name],
    )
}

pub fn render_ci_pull_request(ctx: &ProjectContext) -> String {
    fill(
        crate::setup_templates_gen::RENDERCiPullRequest_TPL,
        &[
            get_setup_language(ctx),
            get_install_command(ctx),
            get_memory_cache_path(ctx),
            get_lint_command(ctx),
            get_audit_command(ctx),
            get_test_command(ctx),
            get_memory_cache_path(ctx),
        ],
    )
}

pub fn render_ci_enterprise_governance(ctx: &ProjectContext) -> String {
    fill(
        crate::setup_templates_gen::RENDERCiEnterpriseGovernance_TPL,
        &[get_setup_language(ctx), get_install_command(ctx)],
    )
}

pub fn render_ci_feature(ctx: &ProjectContext) -> String {
    fill(
        crate::setup_templates_gen::RENDERCiFeature_TPL,
        &[
            get_setup_language(ctx),
            get_install_command(ctx),
            get_memory_cache_path(ctx),
            get_lint_command(ctx),
            get_test_command(ctx),
            get_memory_cache_path(ctx),
        ],
    )
}

pub fn render_cd_deploy(ctx: &ProjectContext) -> String {
    fill(
        crate::setup_templates_gen::RENDERCdDeploy_TPL,
        &[
            get_setup_language(ctx),
            get_install_command(ctx),
            get_memory_cache_path(ctx),
            get_memory_cache_path(ctx),
        ],
    )
}

pub fn render_architecture_md(ctx: &ProjectContext) -> String {
    let frameworks = if ctx.stack.frameworks.is_empty() {
        "None detected".to_string()
    } else {
        ctx.stack.frameworks.join(", ")
    };
    fill(
        crate::setup_templates_gen::RENDERArchitectureMd_TPL,
        &[
            ctx.stack.project_name.clone(),
            ctx.stack.language.clone(),
            ctx.stack.package_manager.clone(),
            frameworks,
        ],
    )
}

pub fn render_decisions_md() -> String {
    fill(crate::setup_templates_gen::RENDERDecisionsMd_TPL, &[])
}

pub fn render_context_md(ctx: &ProjectContext) -> String {
    let project = if ctx.stack.project_name.is_empty() {
        "your-project".to_string()
    } else {
        ctx.stack.project_name.clone()
    };
    fill(
        crate::setup_templates_gen::RENDERContextMd_TPL,
        &[project.clone(), project],
    )
}

pub fn render_runbooks_md(ctx: &ProjectContext) -> String {
    let test_cmd = get_test_command(ctx);
    let lint_cmd = get_lint_command(ctx);
    fill(
        crate::setup_templates_gen::RENDERRunbooksMd_TPL,
        &[
            get_install_command(ctx),
            test_cmd.clone(),
            lint_cmd.clone(),
            get_build_command(ctx),
            test_cmd,
            lint_cmd.clone(),
            lint_cmd,
        ],
    )
}

pub fn render_enterprise_runbook_md(ctx: &ProjectContext) -> String {
    fill(
        crate::setup_templates_gen::RENDEREnterpriseRunbookMd_TPL,
        &[
            ctx.stack.project_name.clone(),
            ctx.stack.language.clone(),
            ctx.stack.package_manager.clone(),
        ],
    )
}

/// `recommended_gitignore_snippet` de cortex/git_policy.py.
pub fn recommended_gitignore_snippet(layout: Option<Layout>) -> String {
    if layout == Some(Layout::New) {
        [
            "# Cortex local state (new layout)",
            ".cortex/memory/",
            "*.chroma/",
            "",
            "# Cortex vault policy",
            "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
            "# Ignore session churn by default unless your team explicitly audits sessions in Git",
            ".cortex/vault/sessions/",
        ]
        .join("\n")
    } else {
        [
            "# Cortex local state",
            ".memory/",
            "*.chroma/",
            "",
            "# Cortex vault policy",
            "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
            "# Ignore session churn by default unless your team explicitly audits sessions in Git",
            "vault/sessions/",
        ]
        .join("\n")
    }
}

/// En Python, `render_git_vault_policy_md` invoca
/// `recommended_gitignore_snippet()` SIN argumentos ⇒ snippet conservador.
pub fn render_git_vault_policy_md() -> String {
    fill(
        crate::setup_templates_gen::RENDERGitVaultPolicyMd_TPL,
        &[recommended_gitignore_snippet(None)],
    )
}

/// `render_workspace_yaml` (concatenación literal).
pub fn render_workspace_yaml() -> String {
    concat!(
        "# Cortex workspace — auto-generated by `cortex setup`\n",
        "# This file declares the layout version and project mapping.\n",
        "\n",
        "layout_version: 2\n",
        "projects:\n",
        "  - id: primary\n",
        "    path: .\n",
        "    role: owner\n",
    )
    .to_string()
}

// ---------------------------------------------------------------------------
// org.yaml (enterprise topology)
// ---------------------------------------------------------------------------

/// slugify de cortex/runtime_context.py (con fallback).
fn runtime_slugify(value: &str, fallback: &str) -> String {
    let mut out = String::new();
    let mut prev_dash = false;
    for ch in value.trim().to_lowercase().chars() {
        let keep = ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-');
        let mapped = if keep { ch } else { '-' };
        if mapped == '-' {
            if !prev_dash {
                out.push('-');
            }
            prev_dash = true;
        } else {
            out.push(mapped);
            prev_dash = false;
        }
    }
    let trimmed = out.trim_matches('-').to_string();
    if trimmed.is_empty() {
        fallback.to_string()
    } else {
        trimmed
    }
}

/// `build_enterprise_org_config` + `render_enterprise_config_yaml`.
///
/// El dump replica `yaml.safe_dump(payload, sort_keys=False,
/// allow_unicode=False)` sobre el modelo pydantic EnterpriseOrgConfig:
/// orden de campos = definición del modelo, con todos los defaults.
pub fn render_org_yaml(
    project_name: &str,
    profile: &str,
    github_actions_enabled: bool,
    branch_isolation_enabled: bool,
) -> Result<String, String> {
    let profile = normalize_profile(profile)?;
    let slug = runtime_slugify(project_name, "project");

    // organization / integration (base común).
    let organization = Yaml::Map(vec![
        ("name".into(), Yaml::str(project_name)),
        ("slug".into(), Yaml::str(slug)),
        ("profile".into(), Yaml::str(&profile)),
    ]);
    let integration = Yaml::Map(vec![
        (
            "github_actions_enabled".into(),
            Yaml::Bool(github_actions_enabled),
        ),
        ("webgraph_workspace_enabled".into(), Yaml::Bool(true)),
        ("ide_profiles".into(), Yaml::Seq(vec![])),
    ]);

    // Sección memory/promotion/governance según perfil.
    let (
        retrieval_default_scope,
        retrieval_enterprise_weight,
        branch_isolation,
        git_policy,
        ci_profile,
        version_sessions,
    ) = match profile.as_str() {
        "small-company" => (
            "local",
            "1.0",
            branch_isolation_enabled,
            "balanced",
            "advisory",
            false,
        ),
        "multi-project-team" => (
            "all",
            "1.2",
            branch_isolation_enabled,
            "balanced",
            "advisory",
            false,
        ),
        "regulated-organization" => ("all", "1.3", true, "strict", "enforced", true),
        _ => (
            "local",
            "1.0",
            branch_isolation_enabled,
            "custom",
            "advisory",
            false,
        ),
    };

    let memory = Yaml::Map(vec![
        ("mode".into(), Yaml::str("layered")),
        (
            "enterprise_vault_path".into(),
            Yaml::str("vault-enterprise"),
        ),
        (
            "enterprise_memory_path".into(),
            Yaml::str("memory/enterprise/chroma"),
        ),
        ("enterprise_semantic_enabled".into(), Yaml::Bool(true)),
        ("enterprise_episodic_enabled".into(), Yaml::Bool(false)),
        ("project_memory_mode".into(), Yaml::str("isolated")),
        (
            "branch_isolation_enabled".into(),
            Yaml::Bool(branch_isolation),
        ),
        (
            "retrieval_default_scope".into(),
            Yaml::str(retrieval_default_scope),
        ),
        ("retrieval_local_weight".into(), Yaml::Float(1.0)),
        (
            "retrieval_enterprise_weight".into(),
            Yaml::Float(retrieval_enterprise_weight.parse::<f64>().unwrap_or(1.0)),
        ),
    ]);
    let promotion = Yaml::Map(vec![
        ("enabled".into(), Yaml::Bool(true)),
        (
            "allowed_doc_types".into(),
            Yaml::Seq(
                ["spec", "decision", "runbook", "hu", "incident"]
                    .iter()
                    .map(|s| Yaml::str(*s))
                    .collect(),
            ),
        ),
        ("require_review".into(), Yaml::Bool(true)),
        (
            "default_targets".into(),
            Yaml::Seq(vec![Yaml::str("enterprise_vault")]),
        ),
    ]);
    let governance = Yaml::Map(vec![
        ("git_policy".into(), Yaml::str(git_policy)),
        ("ci_profile".into(), Yaml::str(ci_profile)),
        (
            "version_sessions_in_git".into(),
            Yaml::Bool(version_sessions),
        ),
    ]);

    // Defaults restantes del modelo (teams, classifications, policies,
    // retention_defaults).
    let teams = Yaml::Seq(vec![]);
    let classifications = Yaml::Seq(
        ["public", "internal", "confidential"]
            .iter()
            .map(|s| Yaml::str(*s))
            .collect(),
    );
    let policies = Yaml::Map(vec![("confidential_visible_to".into(), Yaml::Seq(vec![]))]);
    let retention_defaults = Yaml::Map(
        [
            ("session", 365),
            ("handoff", 30),
            ("spec", 1095),
            ("adr", 2555),
            ("decision", 365),
            ("incident", 1825),
            ("postmortem", 2555),
            ("runbook", 730),
            ("architecture", 2555),
            ("changelog", 0),
            ("hu", 90),
            ("glossary", 0),
        ]
        .iter()
        .map(|(k, v)| (k.to_string(), Yaml::Int(*v)))
        .collect(),
    );

    let payload = Yaml::Map(vec![
        ("schema_version".into(), Yaml::Int(1)),
        ("organization".into(), organization),
        ("memory".into(), memory),
        ("promotion".into(), promotion),
        ("governance".into(), governance),
        ("integration".into(), integration),
        ("teams".into(), teams),
        ("classifications".into(), classifications),
        ("policies".into(), policies),
        ("retention_defaults".into(), retention_defaults),
    ]);

    let body = crate::yaml::dump_with(&payload, /*allow_unicode=*/ false);
    Ok(format!(
        "# Cortex enterprise memory topology\n\
         # This file governs organization-level memory, promotion and governance behavior.\n\
         # Local runtime mechanics still live in config.yaml.\n\n{body}"
    ))
}

fn normalize_profile(profile: &str) -> Result<String, String> {
    const VALID: [&str; 4] = [
        "small-company",
        "multi-project-team",
        "regulated-organization",
        "custom",
    ];
    if VALID.contains(&profile) {
        Ok(profile.to_string())
    } else {
        Err(format!("perfil inválido: {profile}"))
    }
}
