//! Porteo de `cortex/ide/prompts.py` — SSoT de prompts desde el workspace.

use std::collections::BTreeMap;
use std::fs;

use super::IdeCtx;

/// `split_markdown_frontmatter` → (frontmatter | None, body).
pub fn split_markdown_frontmatter(content: &str) -> (Option<String>, String) {
    let lines: Vec<&str> = content.split('\n').collect();
    if lines.is_empty() || lines[0].trim() != "---" {
        return (None, content.trim().to_string());
    }
    for (index, line) in lines.iter().enumerate().skip(1) {
        if line.trim() == "---" {
            let frontmatter = lines[1..index].join("\n").trim().to_string();
            let body = lines[index + 1..].join("\n").trim().to_string();
            return (Some(frontmatter), body);
        }
    }
    (None, content.trim().to_string())
}

/// `strip_markdown_frontmatter`.
pub fn strip_markdown_frontmatter(content: &str) -> String {
    split_markdown_frontmatter(content).1
}

/// `get_skill_prompt`: lee `.md` del skills dir con fallback mínimo.
pub fn get_skill_prompt(ctx: &IdeCtx, skill_name: &str) -> String {
    let path = ctx.skills_dir().join(format!("{skill_name}.md"));
    if let Ok(text) = fs::read_to_string(&path) {
        return text;
    }
    format!("# {skill_name}\n\nSkill file not found. Run `cortex setup agent` to generate.")
}

/// `get_subagent_prompt`.
pub fn get_subagent_prompt(ctx: &IdeCtx, subagent_name: &str) -> String {
    let path = ctx.subagents_dir().join(format!("{subagent_name}.md"));
    if let Ok(text) = fs::read_to_string(&path) {
        return text;
    }
    format!("# {subagent_name}\n\nYou are {subagent_name}, a Cortex subagent.")
}

/// `build_all_prompts`: los 3 anchors triádicos.
pub fn build_all_prompts(ctx: &IdeCtx) -> BTreeMap<String, String> {
    let mut prompts = BTreeMap::new();
    for skill in ["cortex-sync", "cortex-SDDwork", "cortex-documenter"] {
        prompts.insert(skill.to_string(), get_skill_prompt(ctx, skill));
    }
    prompts
}
