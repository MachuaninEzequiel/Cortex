//! Purposes: search squeeze + promotion + context pack. Independientes, default off.

/// Palanca de juicio. Cada purpose se enciende por YAML, no por estar en este enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Purpose {
    SearchSqueeze,
    Promotion,
    ContextPack,
    Utterance,
    SessionCompact,
    ModelRouting,
}

impl Purpose {
    pub fn as_str(self) -> &'static str {
        match self {
            Purpose::SearchSqueeze => "search_squeeze",
            Purpose::Promotion => "promotion",
            Purpose::ContextPack => "context_pack",
            Purpose::Utterance => "utterance",
            Purpose::SessionCompact => "session_compact",
            Purpose::ModelRouting => "model_routing",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_pack_label() {
        assert_eq!(Purpose::ContextPack.as_str(), "context_pack");
    }

    #[test]
    fn utterance_label() {
        assert_eq!(Purpose::Utterance.as_str(), "utterance");
    }

    #[test]
    fn session_compact_label() {
        assert_eq!(Purpose::SessionCompact.as_str(), "session_compact");
    }

    #[test]
    fn model_routing_label() {
        assert_eq!(Purpose::ModelRouting.as_str(), "model_routing");
    }
}
