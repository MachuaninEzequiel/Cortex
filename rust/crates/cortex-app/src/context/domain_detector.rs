//! Detector de dominios temáticos — réplica de
//! `cortex/context_enricher/domain_detector.py` (P12A-7).
//!
//! Scoring ponderado por reglas: patrones de archivo (0.6) + keywords de
//! contenido (0.4). Fallback por similitud coseno contra centroides
//! pre-computados del modelo ONNX all-MiniLM-L6-v2 cuando las reglas no
//! alcanzan el umbral. Réplica del pipeline chroma ONNXMiniLM_L6_V2 que usa
//! el Embedder Python, con la MISMA tabla de descripciones.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use cortex_embed::onnx::OnnxEmbedder;

/// Resultado de detección de dominio.
#[derive(Debug, Clone, PartialEq)]
pub struct DomainMatch {
    /// "auth", "database", … o None.
    pub domain: Option<String>,
    pub confidence: f64,
    pub matched_files: Vec<String>,
    pub matched_keywords: Vec<String>,
    /// "rules" | "embedding" | "none"
    pub method_used: String,
}

pub struct DomainRules {
    pub file_patterns: &'static [&'static str],
    pub keywords: &'static [&'static str],
}

/// Tabla canónica DOMAIN_RULES (acceso por dominio; el orden de iteración
/// canónico es RULE_ORDER).
static DOMAIN_RULES: std::sync::LazyLock<std::collections::BTreeMap<&'static str, DomainRules>> =
    std::sync::LazyLock::new(build_rules);

fn build_rules() -> std::collections::BTreeMap<&'static str, DomainRules> {
    // BTreeMap da orden alfabético; los empates en scoring se resuelven por
    // estricto `>` en Python (primer dominio del SET con score mayor). Los
    // gates evitan empates exactos; para replicar el orden de DECLARACIÓN
    // de Python se itera sobre RULE_ORDER.
    let mut m = BTreeMap::new();
    macro_rules! rule {
        ($k:expr, $files:expr, $kws:expr) => {
            m.insert(
                $k,
                DomainRules {
                    file_patterns: $files,
                    keywords: $kws,
                },
            );
        };
    }
    rule!(
        "auth",
        &[
            "auth",
            "login",
            "logout",
            "session",
            "token",
            "jwt",
            "oauth",
            "password",
            "credential",
            "sso",
            "mfa",
            "2fa",
        ],
        &[
            "authenticate",
            "authentication",
            "authorization",
            "login",
            "logout",
            "token",
            "session",
            "credentiv2",
            "jwt",
            "oauth",
            "refresh_token",
            "access_token",
            "password_hash",
            "bcrypt",
            "secret",
        ]
    );
    rule!(
        "database",
        &[
            "migration",
            "schema",
            "model",
            "repository",
            "db",
            "sql",
            "alembic",
            "sequelize",
            "prisma",
            "orm",
        ],
        &[
            "migration",
            "schema",
            "query",
            "transaction",
            "connection",
            "pool",
            "database",
            "table",
            "column",
            "index",
            "foreign_key",
            "constraint",
            "rollback",
        ]
    );
    rule!(
        "api",
        &[
            "route",
            "endpoint",
            "controller",
            "handler",
            "api",
            "rest",
            "graphql",
            "grpc",
            "middleware",
            "router",
        ],
        &[
            "endpoint",
            "route",
            "handler",
            "request",
            "response",
            "status_code",
            "middleware",
            "json",
            "payload",
            "get",
            "post",
            "put",
            "delete",
            "patch",
        ]
    );
    rule!(
        "security",
        &[
            "security",
            "vulnerability",
            "sanitize",
            "validation",
            "encrypt",
            "hash",
            "cors",
            "csrf",
            "xss",
        ],
        &[
            "sanitize",
            "validate",
            "encrypt",
            "hash",
            "vulnerability",
            "injection",
            "xss",
            "csrf",
            "cors",
            "csp",
            "rate_limit",
            "throttle",
        ]
    );
    rule!(
        "payments",
        &[
            "payment",
            "billing",
            "invoice",
            "stripe",
            "checkout",
            "subscription",
            "pricing",
            "plan",
        ],
        &[
            "payment",
            "charge",
            "invoice",
            "subscription",
            "stripe",
            "billing",
            "refund",
            "currency",
            "plan",
            "pricing",
        ]
    );
    rule!(
        "ui",
        &[
            "component",
            "view",
            "template",
            "html",
            "css",
            "jsx",
            "tsx",
            "svelte",
            "vue",
            "angular",
            "react",
        ],
        &[
            "render",
            "component",
            "props",
            "state",
            "stylesheet",
            "css",
            "scss",
            "styled",
            "ui",
            "ux",
            "interface",
        ]
    );
    rule!(
        "testing",
        &["test", "spec", "fixture", "mock", "stub"],
        &[
            "test",
            "expect",
            "assert",
            "describe",
            "it",
            "jest",
            "mocha",
            "chai",
            "vitest",
            "playwright",
            "cypress",
            "selenium",
            "pytest",
            "unittest",
        ]
    );
    rule!(
        "infrastructure",
        &[
            "docker",
            "k8s",
            "kubernetes",
            "terraform",
            "ansible",
            "deploy",
            "helm",
            "pulumi",
            "cloudformation",
        ],
        &[
            "deploy",
            "infrastructure",
            "cloud",
            "aws",
            "azure",
            "gcp",
            "container",
            "orchestration",
            "kubernetes",
            "terraform",
            "helm",
            "ansible",
            "pulumi",
        ]
    );
    rule!(
        "data",
        &[
            "etl",
            "pipeline",
            "analytics",
            "report",
            "dashboard",
            "chart",
            "graph",
            "visualization",
            "powerbi",
            "tableau",
        ],
        &[
            "etl",
            "pipeline",
            "data",
            "analytics",
            "report",
            "dashboard",
            "visualization",
            "chart",
            "graph",
            "bi",
            "business intelligence",
            "sql",
            "nosql",
        ]
    );
    rule!(
        "i18n",
        &["locale", "translation", "i18n", "l10n"],
        &[
            "i18n",
            "l10n",
            "translate",
            "locale",
            "language",
            "internationalization",
            "localization",
            "gettext",
            "polyglot",
            "format",
            "message",
        ]
    );
    rule!(
        "logging",
        &["logger", "log", "monitor", "alert", "metric"],
        &[
            "log",
            "logging",
            "logger",
            "monitor",
            "metric",
            "alert",
            "trace",
            "debug",
            "info",
            "warn",
            "error",
            "fatal",
            "observability",
            "telemetry",
            "tracing",
        ]
    );
    rule!(
        "configuration",
        &["config", "env", "settings", "constants"],
        &[
            "config",
            "configuration",
            "setting",
            "constant",
            "env",
            "environment",
            "variable",
            "yaml",
            "json",
            "ini",
            "toml",
            "properties",
            "dotenv",
        ]
    );
    m
}

/// Orden de DECLARACIÓN (Python dict es insertion-ordered; los sets de
/// empate no son contrato pero este orden da resultados estables).
pub static RULE_ORDER: &[&str] = &[
    "auth",
    "database",
    "api",
    "security",
    "payments",
    "ui",
    "testing",
    "infrastructure",
    "data",
    "i18n",
    "logging",
    "configuration",
];

/// Descripciones de centroides (idénticas a domain_detector.py).
static DOMAIN_DESCRIPTIONS: &[(&str, &str)] = &[
    (
        "auth",
        "authentication token jwt login session oauth password credential",
    ),
    (
        "database",
        "migration schema query sql database table model repository",
    ),
    (
        "api",
        "endpoint route handler controller request response status middleware",
    ),
    (
        "security",
        "sanitize validate encrypt hash vulnerability injection xss csrf",
    ),
    (
        "payments",
        "payment charge invoice subscription stripe billing refund currency",
    ),
    (
        "ui",
        "component view template render css jsx tsx angular react svelte vue",
    ),
    (
        "testing",
        "test expect assert describe it jest mocha chai vitest playwright cypress",
    ),
    (
        "infrastructure",
        "deploy infrastructure cloud aws azure gcp container orchestration kubernetes terraform",
    ),
    (
        "data",
        "etl pipeline analytics report dashboard chart graph visualization bi",
    ),
    (
        "i18n",
        "translate locale language internationalization localization gettext polyglot",
    ),
    (
        "logging",
        "log logging logger monitor metric alert trace debug info warn error",
    ),
    (
        "configuration",
        "config configuration setting constant env environment variable yaml json",
    ),
];

const FILE_WEIGHT: f64 = 0.6;
const KEYWORD_WEIGHT: f64 = 0.4;

/// Detector con reglas + fallback embeddings (si hay modelo).
pub struct DomainDetector {
    pub min_confidence: f64,
    embedder: Option<OnnxEmbedder>,
    domain_centroids: Vec<(String, Vec<f64>)>,
}

impl Default for DomainDetector {
    fn default() -> Self {
        Self::new(0.5, None)
    }
}

impl DomainDetector {
    /// `model_dir`: layout chroma (`tokenizer.json` + `model.onnx`). Si es
    /// None u falla la carga ⇒ sólo reglas (paridad del `except Exception`).
    pub fn new(min_confidence: f64, model_dir: Option<&Path>) -> Self {
        let mut detector = Self {
            min_confidence,
            embedder: None,
            domain_centroids: vec![],
        };
        if let Some(dir) = model_dir {
            detector.init_embedding_fallback(dir);
        }
        detector
    }

    fn init_embedding_fallback(&mut self, dir: &Path) {
        if let Ok(mut emb) = OnnxEmbedder::open(dir) {
            let texts: Vec<String> = DOMAIN_DESCRIPTIONS
                .iter()
                .map(|(_, d)| d.to_string())
                .collect();
            if let Ok(vecs) = emb.embed_batch(&texts) {
                for ((domain, _), v) in DOMAIN_DESCRIPTIONS.iter().zip(vecs) {
                    self.domain_centroids.push((domain.to_string(), v));
                }
                self.embedder = Some(emb);
            }
        }
    }

    pub fn has_embedder(&self) -> bool {
        self.embedder.is_some()
    }

    fn embedding_fallback(
        &mut self,
        files: &[String],
        keywords: &[String],
    ) -> (Option<String>, f64) {
        let Some(embedder) = self.embedder.as_mut() else {
            return (None, 0.0);
        };
        if self.domain_centroids.is_empty() {
            return (None, 0.0);
        }
        // file_text: basename sin extensión, espacio-join.
        let file_text = files
            .iter()
            .map(|f| {
                f.rsplit('/')
                    .next()
                    .unwrap_or(f)
                    .split('.')
                    .next()
                    .unwrap_or("")
                    .to_string()
            })
            .collect::<Vec<_>>()
            .join(" ");
        let keyword_text = keywords.join(" ");
        let text = format!("{file_text} {keyword_text}").trim().to_string();
        if text.is_empty() {
            return (None, 0.0);
        }
        let query_vec = match embedder.embed_batch(&[text]) {
            Ok(mut v) if v.len() == 1 => v.pop().unwrap(),
            _ => return (None, 0.0),
        };
        // Cosine similarity; mejor estrictamente mayor (> best_sim).
        let qnorm = dot(&query_vec, &query_vec).sqrt();
        let mut best_domain: Option<String> = None;
        let mut best_sim = 0.0f64;
        for (domain, centroid) in &self.domain_centroids {
            let cnorm = dot(centroid, centroid).sqrt();
            let denom = qnorm * cnorm;
            if denom == 0.0 {
                continue;
            }
            let sim = dot(&query_vec, centroid) / denom;
            if sim > best_sim {
                best_sim = sim;
                best_domain = Some(domain.clone());
            }
        }
        (best_domain, best_sim)
    }

    pub fn detect(&mut self, files: &[&str], keywords: &[&str]) -> DomainMatch {
        let files: Vec<String> = files.iter().map(|s| s.to_string()).collect();
        let keywords: Vec<String> = keywords.iter().map(|s| s.to_string()).collect();
        self.detect_owned(files, keywords)
    }

    pub fn detect_owned(&mut self, files: Vec<String>, keywords: Vec<String>) -> DomainMatch {
        if files.is_empty() && keywords.is_empty() {
            // El early-return de Python NO pasa method_used ⇒ default "rules".
            return DomainMatch {
                domain: None,
                confidence: 0.0,
                matched_files: vec![],
                matched_keywords: vec![],
                method_used: "rules".into(),
            };
        }

        // FASE 1: reglas.
        let mut file_scores: BTreeMap<&str, f64> = BTreeMap::new();
        let mut keyword_scores: BTreeMap<&str, f64> = BTreeMap::new();

        for domain in RULE_ORDER {
            let rules = &DOMAIN_RULES[*domain];
            let matched: Vec<&String> = files
                .iter()
                .filter(|f| {
                    rules
                        .file_patterns
                        .iter()
                        .any(|p| f.to_lowercase().contains(p))
                })
                .collect();
            if !matched.is_empty() {
                file_scores.insert(domain, matched.len() as f64 / files.len().max(1) as f64);
            }
        }
        for domain in RULE_ORDER {
            let rules = &DOMAIN_RULES[*domain];
            let matched: Vec<&String> = keywords
                .iter()
                .filter(|kw| {
                    rules
                        .keywords
                        .iter()
                        .any(|dkw| kw.to_lowercase().contains(dkw))
                })
                .collect();
            if !matched.is_empty() {
                keyword_scores.insert(domain, matched.len() as f64 / keywords.len().max(1) as f64);
            }
        }

        // Unión en orden RULE_ORDER (determinista; Python itera un set — los
        // gates evitan empates y el ganador estricto coincide).
        let all_domains: Vec<&str> = RULE_ORDER
            .iter()
            .copied()
            .filter(|d| file_scores.contains_key(d) || keyword_scores.contains_key(d))
            .collect();

        let mut best_domain: Option<String> = None;
        let mut best_score = 0.0f64;
        let mut all_matched_files: Vec<String> = vec![];
        let mut all_matched_keywords: Vec<String> = vec![];

        for domain in all_domains {
            let file_score = file_scores.get(domain).copied().unwrap_or(0.0);
            let kw_score = keyword_scores.get(domain).copied().unwrap_or(0.0);
            let combined = FILE_WEIGHT * file_score + KEYWORD_WEIGHT * kw_score;
            if combined > best_score {
                best_score = combined;
                best_domain = Some(domain.to_string());
                let rules = &DOMAIN_RULES[domain];
                all_matched_files = files
                    .iter()
                    .filter(|f| {
                        rules
                            .file_patterns
                            .iter()
                            .any(|p| f.to_lowercase().contains(p))
                    })
                    .cloned()
                    .collect();
                all_matched_keywords = keywords
                    .iter()
                    .filter(|kw| {
                        rules
                            .keywords
                            .iter()
                            .any(|dkw| kw.to_lowercase().contains(dkw))
                    })
                    .cloned()
                    .collect();
            }
        }

        if best_score >= 0.5 {
            return DomainMatch {
                domain: best_domain,
                confidence: best_score,
                matched_files: all_matched_files,
                matched_keywords: all_matched_keywords,
                method_used: "rules".into(),
            };
        }

        // FASE 2: fallback embeddings.
        if self.embedder.is_some() && !self.domain_centroids.is_empty() {
            let (embed_domain, embed_confidence) = self.embedding_fallback(&files, &keywords);
            if let Some(ed) = embed_domain {
                if embed_confidence > best_score {
                    let (mf, mk) = matched_for(&ed, &files, &keywords);
                    return DomainMatch {
                        domain: Some(ed),
                        confidence: embed_confidence,
                        matched_files: mf,
                        matched_keywords: mk,
                        method_used: "embedding".into(),
                    };
                }
            }
        }

        if best_score < self.min_confidence {
            return DomainMatch {
                domain: None,
                confidence: best_score,
                matched_files: all_matched_files,
                matched_keywords: all_matched_keywords,
                method_used: if best_score > 0.0 { "rules" } else { "none" }.into(),
            };
        }

        DomainMatch {
            domain: best_domain,
            confidence: best_score,
            matched_files: all_matched_files,
            matched_keywords: all_matched_keywords,
            method_used: "rules".into(),
        }
    }
}

fn matched_for(domain: &str, files: &[String], keywords: &[String]) -> (Vec<String>, Vec<String>) {
    let Some(rules) = DOMAIN_RULES.get(domain) else {
        return (vec![], vec![]);
    };
    let mf = files
        .iter()
        .filter(|f| {
            rules
                .file_patterns
                .iter()
                .any(|p| f.to_lowercase().contains(p))
        })
        .cloned()
        .collect();
    let mk = keywords
        .iter()
        .filter(|kw| {
            rules
                .keywords
                .iter()
                .any(|dkw| kw.to_lowercase().contains(dkw))
        })
        .cloned()
        .collect();
    (mf, mk)
}

fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

/// Ruta canónica del modelo ONNX chroma (~/.cache/chroma/onnx_models/…).
pub fn default_model_dir() -> Option<PathBuf> {
    let dir = dirs_home()?.join(".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx");
    if dir.join("model.onnx").exists() {
        Some(dir)
    } else {
        None
    }
}

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reglas_sin_modelo() {
        let mut d = DomainDetector::new(0.5, None);
        assert!(!d.has_embedder());
        let r = d.detect(&["auth.py", "jwt.ts"], &["token", "login"]);
        assert_eq!(r.domain.as_deref(), Some("auth"));
        assert_eq!(r.method_used, "rules");
        // Ambos archivos y ambas keywords matchean ⇒ 0.6*1 + 0.4*1 = 1.0.
        assert_eq!(r.confidence, 1.0);
        assert!(r.matched_files.contains(&"auth.py".to_string()));
    }

    #[test]
    fn vacio_devuelve_default_rules() {
        let mut d = DomainDetector::default();
        let r = d.detect(&[], &[]);
        assert_eq!(r.domain, None);
        assert_eq!(r.confidence, 0.0);
        assert_eq!(r.method_used, "rules");
    }

    #[test]
    fn tabla_reglas_completa_y_orden() {
        assert_eq!(RULE_ORDER.len(), 12);
        for d in RULE_ORDER {
            assert!(DOMAIN_RULES.contains_key(d), "falta {d}");
        }
    }

    #[test]
    fn cosine_helpers() {
        assert!((dot(&[1.0, 0.0], &[1.0, 0.0]) - 1.0).abs() < 1e-12);
    }
}
