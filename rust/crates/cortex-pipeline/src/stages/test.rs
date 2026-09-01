//! Puerto de `stages/test.py`: ejecuta suite + coverage opcional.
use crate::domain::context::PipelineContext;
use crate::domain::types::{StageResult, StageStatus, StageType};
use crate::stages::run_command;

pub struct TestStage {
    pub command: Option<String>,
    pub min_coverage: i64,
    pub block_on_failure: bool,
    pub timeout_s: u64,
}

impl Default for TestStage {
    fn default() -> Self {
        Self {
            command: None,
            min_coverage: 0,
            block_on_failure: true,
            timeout_s: 300,
        }
    }
}

fn detect_command(ctx: &PipelineContext) -> Option<String> {
    let has = |f: &str| {
        ctx.changed_files.iter().any(|c| c.ends_with(f))
            || ctx.vault_path.exists().then_some(()).is_none()
    };
    let _ = has;
    if std::path::Path::new("pyproject.toml").exists()
        || std::path::Path::new("pytest.ini").exists()
    {
        Some("pytest -q".into())
    } else if std::path::Path::new("Cargo.toml").exists() {
        Some("cargo test".into())
    } else {
        None
    }
}

fn extract_coverage(stdout: &str) -> Option<f64> {
    for line in stdout.lines().rev() {
        if let Some(idx) = line.find("TOTAL") {
            let tail = &line[idx..];
            let pct: String = tail
                .chars()
                .skip_while(|c| !c.is_ascii_digit())
                .take_while(|c| c.is_ascii_digit() || *c == '.')
                .collect();
            if let Ok(v) = pct.parse::<f64>() {
                return Some(v);
            }
        }
    }
    None
}

impl crate::orchestrator::PipelineStage for TestStage {
    fn name(&self) -> &str {
        "Tests"
    }
    fn stage_type(&self) -> StageType {
        StageType::Test
    }
    fn block_on_failure(&self) -> bool {
        self.block_on_failure
    }
    fn execute(&self, ctx: &mut PipelineContext) -> StageResult {
        let started = std::time::Instant::now();
        let cmd = self.command.clone().or_else(|| detect_command(ctx));
        let Some(cmd) = cmd else {
            return StageResult {
                stage_type: self.stage_type(),
                stage_name: "Tests".into(),
                status: StageStatus::Skipped,
                message: "No test command detected for this project type.".into(),
                artifacts: Default::default(),
                duration_ms: 0,
                timestamp: chrono::Utc::now(),
            };
        };
        let (code, stdout) = run_command(&cmd, self.timeout_s);
        let duration_ms = started.elapsed().as_millis() as i64;
        let coverage = extract_coverage(&stdout);

        if code != 0 {
            let fail_count = stdout
                .lines()
                .find_map(|l| {
                    let idx = l.find(" failed")?;
                    let digits: String = l[..idx]
                        .chars()
                        .rev()
                        .take_while(|c| c.is_ascii_digit())
                        .collect::<String>()
                        .chars()
                        .rev()
                        .collect();
                    digits.parse::<i64>().ok()
                })
                .map(|n| n.to_string())
                .unwrap_or_else(|| "unknown".into());
            let mut artifacts = std::collections::BTreeMap::new();
            artifacts.insert("command".to_string(), serde_json::json!(cmd));
            artifacts.insert("coverage_pct".to_string(), serde_json::json!(coverage));
            return StageResult {
                stage_type: self.stage_type(),
                stage_name: "Tests".into(),
                status: StageStatus::Failed,
                message: format!("{fail_count} test(s) failed."),
                artifacts,
                duration_ms,
                timestamp: chrono::Utc::now(),
            };
        }
        if self.min_coverage > 0
            && coverage
                .map(|c| c < self.min_coverage as f64)
                .unwrap_or(false)
        {
            return StageResult {
                stage_type: self.stage_type(),
                stage_name: "Tests".into(),
                status: StageStatus::Failed,
                message: format!(
                    "Coverage {:.1}% is below minimum {}%.",
                    coverage.unwrap_or(0.0),
                    self.min_coverage
                ),
                artifacts: Default::default(),
                duration_ms,
                timestamp: chrono::Utc::now(),
            };
        }
        let pass_count = stdout
            .lines()
            .find_map(|l| {
                let idx = l.find(" passed")?;
                let digits: String = l[..idx]
                    .chars()
                    .rev()
                    .take_while(|c| c.is_ascii_digit())
                    .collect::<String>()
                    .chars()
                    .rev()
                    .collect();
                digits.parse::<i64>().ok().map(|n| n.to_string())
            })
            .unwrap_or_else(|| "all".into());
        StageResult {
            stage_type: self.stage_type(),
            stage_name: "Tests".into(),
            status: StageStatus::Passed,
            message: format!("{pass_count} tests passed."),
            artifacts: Default::default(),
            duration_ms,
            timestamp: chrono::Utc::now(),
        }
    }
}
