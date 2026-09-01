//! Puerto de `cortex/context_enricher/budget_resolver.py` — Task-aware
//! retrieval budget. Función pura que mapea un ``task_type`` detectado (y
//! opcionalmente ``complexity``) a un sobre de retrieval (``top_k`` y
//! ``max_chars``). Los perfiles son DATA; si un test fija un valor, todo PR
//! futuro debe actualizar data y test juntos.

/// Sobre por perfil: `top_k` (máx items) + `max_chars` (budget del prompt).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BudgetProfile {
    pub top_k: usize,
    pub max_chars: usize,
}

const QUESTION_ONLY: BudgetProfile = BudgetProfile {
    top_k: 0,
    max_chars: 0,
};
const DOCS_ONLY: BudgetProfile = BudgetProfile {
    top_k: 3,
    max_chars: 1200,
};
const FAST_CODE: BudgetProfile = BudgetProfile {
    top_k: 5,
    max_chars: 2000,
};
const DEEP_CODE: BudgetProfile = BudgetProfile {
    top_k: 8,
    max_chars: 3500,
};
const SECURITY: BudgetProfile = BudgetProfile {
    top_k: 8,
    max_chars: 3500,
};
const AMBIGUOUS: BudgetProfile = BudgetProfile {
    top_k: 3,
    max_chars: 1500,
};
const NOOP: BudgetProfile = BudgetProfile {
    top_k: 0,
    max_chars: 0,
};

/// Fallback para task_type desconocido o None — dimensionado como fast-code
/// para nunca dejar sin contexto al caller.
pub const DEFAULT_PROFILE: BudgetProfile = FAST_CODE;

fn profile_of(task_type: &str) -> Option<BudgetProfile> {
    Some(match task_type {
        "question-only" => QUESTION_ONLY,
        "docs-only" => DOCS_ONLY,
        "fast-code" => FAST_CODE,
        "deep-code" => DEEP_CODE,
        "security" => SECURITY,
        "ambiguous" => AMBIGUOUS,
        "noop" => NOOP,
        _ => return None,
    })
}

/// Mapea un ``task_type`` detectado a un sobre de budget.
///
/// Tipos desconocidos / None caen al default fast-code. ``complexity`` se
/// acepta por compatibilidad futura pero hoy no se consulta (perfiles planos).
pub fn resolve_budget_profile(
    task_type: Option<&str>,
    #[allow(unused_variables)] complexity: Option<&str>,
) -> BudgetProfile {
    task_type.and_then(profile_of).unwrap_or(DEFAULT_PROFILE)
}

#[cfg(test)]
mod tests {
    // Espejo de tests/unit/context_enricher/test_budget_resolver.py.
    use super::*;

    #[test]
    fn known_profiles_match_spec() {
        let casos = [
            ("question-only", 0, 0),
            ("docs-only", 3, 1200),
            ("fast-code", 5, 2000),
            ("deep-code", 8, 3500),
            ("security", 8, 3500),
            ("ambiguous", 3, 1500),
            ("noop", 0, 0),
        ];
        for (task, top_k, max_chars) in casos {
            let p = resolve_budget_profile(Some(task), None);
            assert_eq!(p.top_k, top_k, "{task} top_k");
            assert_eq!(p.max_chars, max_chars, "{task} max_chars");
        }
    }

    #[test]
    fn unknown_falls_back_to_default() {
        assert_eq!(
            resolve_budget_profile(Some("some-future-type"), None),
            BudgetProfile {
                top_k: 5,
                max_chars: 2000
            }
        );
    }

    #[test]
    fn none_falls_back_to_default() {
        assert_eq!(resolve_budget_profile(None, None), DEFAULT_PROFILE);
    }

    /// Mutar el resultado no afecta llamadas siguientes (Copy ⇒ trivial acá,
    /// pero el test documenta el contrato del oráculo).
    #[test]
    fn fresh_profile_each_call() {
        let first = resolve_budget_profile(Some("docs-only"), None);
        // BudgetProfile es Copy: una "mutación" del valor recibido no puede
        // afectar llamadas siguientes (contrato fresh-dict del oráculo).
        let mut copia = first;
        copia.top_k = 999;
        assert_eq!(copia.top_k, 999);
        let second = resolve_budget_profile(Some("docs-only"), None);
        assert_eq!(second.top_k, 3);
    }
}
