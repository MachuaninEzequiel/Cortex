//! Registro de topics — espejo de `topics/__init__.py::get_all_topics`.
//! Los cuerpos renderizados viven en `content/topic_<slug>.txt` (captura
//! byte-exacto de rich export_text a width=100).

/// Metadatos de un topic (contrato TutorTopic).
#[derive(Debug, Clone)]
pub struct TopicMeta {
    pub title: &'static str,
    pub icon: &'static str,
    pub slug: &'static str,
    pub one_liner: &'static str,
    pub guide_path: Option<&'static str>,
    pub body: &'static str,
}

macro_rules! topic {
    ($title:literal, $icon:literal, $slug:literal, $one:literal, $guide:expr) => {
        TopicMeta {
            title: $title,
            icon: $icon,
            slug: $slug,
            one_liner: $one,
            guide_path: $guide,
            body: include_str!(concat!("../content/topic_", $slug, ".txt")),
        }
    };
}

/// `get_all_topics()` — orden de display canónico.
pub fn get_all_topics() -> Vec<TopicMeta> {
    vec![
        topic!(
            "Primeros Pasos",
            "🚀",
            "start",
            "Cómo instalar y empezar a usar Cortex",
            Some("docs/guides/getting-started.md")
        ),
        topic!(
            "Comandos Esenciales",
            "📋",
            "commands",
            "Cheatsheet rápido de los comandos más usados",
            None
        ),
        topic!(
            "Flujo de Trabajo",
            "🔄",
            "workflow",
            "El modelo tripartito: sync → SDDwork → documenter",
            Some("docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md")
        ),
        topic!(
            "Pipeline CI/CD",
            "⚙️",
            "pipeline",
            "Cómo funciona el pipeline y cómo cambiar módulos",
            Some("docs/guides/pipeline-setup.md")
        ),
        topic!(
            "Vault y Documentación",
            "📁",
            "vault",
            "Estructura del vault y qué va a Git",
            Some("docs/guides/vault-structure.md")
        ),
        topic!(
            "Enterprise Memory",
            "🏢",
            "enterprise",
            "Memoria corporativa, promoción y topologías",
            Some("docs/guides/enterprise-vault.md")
        ),
        topic!(
            "Integración IDE",
            "🔌",
            "ide",
            "Cómo conectar Cortex con tu IDE via MCP",
            None
        ),
    ]
}
