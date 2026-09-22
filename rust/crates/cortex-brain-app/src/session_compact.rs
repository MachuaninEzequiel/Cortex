//! Adaptador de compactación de historial (P3: session_compact).
//! Recorta/trunca tool results antiguos verbatim (sin resumir con LLM).
//! Protege los últimos N turnos intactos (pin). Fail-open en 429/timeout.

use std::collections::HashMap;

use cortex_judgement::{
    evaluate_session_compact, CompactCandidate, CompactDecision, JudgementHandle, Purpose,
    TRUNCATED_RESULT_MARKER,
};

use crate::chat::ChatMessagePayload;

/// Compacta mensajes del historial conversacional si `session_compact` está activado.
/// Si está desactivado o hay error (429, timeout), devuelve los mensajes intactos (fail-open).
pub fn compact_chat_messages(
    handle: &JudgementHandle,
    messages: Vec<ChatMessagePayload>,
    pin_last_n: usize,
) -> Vec<ChatMessagePayload> {
    if !handle.client.enabled(Purpose::SessionCompact) {
        return messages;
    }
    if messages.len() <= pin_last_n {
        return messages;
    }

    let split_point = messages.len().saturating_sub(pin_last_n);
    let (to_evaluate, pinned) = messages.split_at(split_point);

    let mut candidates: Vec<CompactCandidate> = Vec::new();
    let mut candidate_to_index: Vec<usize> = Vec::new();

    for (idx, msg) in to_evaluate.iter().enumerate() {
        if msg.text.contains(TRUNCATED_RESULT_MARKER) {
            // Ya compactado anteriormente
            continue;
        }

        if let Some((tool, args, output)) = parse_tool_from_text(&msg.text) {
            candidates.push(CompactCandidate {
                id: msg.id.clone(),
                tool,
                args,
                output,
            });
            candidate_to_index.push(idx);
        } else if let Some(ref calls) = msg.tool_calls {
            if let Some(first) = calls.first() {
                candidates.push(CompactCandidate {
                    id: msg.id.clone(),
                    tool: first.tool.clone(),
                    args: first.args.clone(),
                    output: msg.text.clone(),
                });
                candidate_to_index.push(idx);
            }
        }
    }

    if candidates.is_empty() {
        return messages;
    }

    let decisions = match evaluate_session_compact(&*handle.client, &handle.catalog, &candidates) {
        Some(d) => d,
        None => return messages, // Fail-open: transcript intacto
    };

    let decision_map: HashMap<&str, &CompactDecision> =
        decisions.iter().map(|d| (d.id.as_str(), d)).collect();

    let mut result_evaluated = to_evaluate.to_vec();

    for (candidate, &msg_idx) in candidates.iter().zip(candidate_to_index.iter()) {
        if let Some(decision) = decision_map.get(candidate.id.as_str()) {
            let msg = &mut result_evaluated[msg_idx];

            if !decision.should_keep_result() {
                msg.text = replace_tool_result_in_text(&msg.text, TRUNCATED_RESULT_MARKER);
            }

            if !decision.should_keep_call() {
                msg.tool_calls = None;
            }
        }
    }

    let mut out = result_evaluated;
    out.extend_from_slice(pinned);
    out
}

/// Extrae (tool, args, output) si el mensaje es un reporte de ejecución de tool.
fn parse_tool_from_text(text: &str) -> Option<(String, String, String)> {
    if let Some(pos) = text.find("Resultado de `cortex ") {
        let rest = &text[pos + "Resultado de `cortex ".len()..];
        let end_tick = rest.find('`')?;
        let cmd = rest[..end_tick].trim();
        let mut parts = cmd.split_whitespace();
        let tool = parts.next()?.to_string();
        let args = parts.collect::<Vec<_>>().join(" ");

        let output = extract_code_block_content(text);
        return Some((tool, args, output));
    }
    if let Some(pos) = text.find("Error al ejecutar `cortex ") {
        let rest = &text[pos + "Error al ejecutar `cortex ".len()..];
        let end_tick = rest.find('`')?;
        let cmd = rest[..end_tick].trim();
        let mut parts = cmd.split_whitespace();
        let tool = parts.next()?.to_string();
        let args = parts.collect::<Vec<_>>().join(" ");

        let output = extract_code_block_content(text);
        return Some((tool, args, output));
    }
    None
}

fn extract_code_block_content(text: &str) -> String {
    let Some(code_start) = text.find("```\n").or_else(|| text.find("```")) else {
        return text.to_string();
    };
    let after_fence = &text[code_start + 3..];
    let inner_start = if after_fence.starts_with('\n') { 1 } else { 0 };
    let after_inner = &after_fence[inner_start..];
    let code_end = after_inner.rfind("```").unwrap_or(after_inner.len());
    after_inner[..code_end].trim().to_string()
}

fn replace_tool_result_in_text(text: &str, replacement: &str) -> String {
    if let Some(pos) = text.find("Resultado de `cortex ") {
        let rest = &text[pos + "Resultado de `cortex ".len()..];
        if let Some(end_tick) = rest.find('`') {
            let cmd = rest[..end_tick].trim();
            return format!("⚡ **Resultado de `cortex {cmd}`:**\n\n```\n{replacement}\n```");
        }
    }
    if let Some(pos) = text.find("Error al ejecutar `cortex ") {
        let rest = &text[pos + "Error al ejecutar `cortex ".len()..];
        if let Some(end_tick) = rest.find('`') {
            let cmd = rest[..end_tick].trim();
            return format!("❌ **Error al ejecutar `cortex {cmd}`:**\n\n```\n{replacement}\n```");
        }
    }
    replacement.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::chat::ToolCall;
    use cortex_judgement::{Catalog, JudgementClient, JudgementError, JudgementRequest, JudgementResponse};
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    struct TestClient {
        enabled: bool,
        eval_fn: Box<dyn Fn(&JudgementRequest) -> Result<JudgementResponse, JudgementError> + Send + Sync>,
        calls: AtomicUsize,
    }

    impl JudgementClient for TestClient {
        fn enabled(&self, purpose: Purpose) -> bool {
            self.enabled && matches!(purpose, Purpose::SessionCompact)
        }

        fn evaluate(&self, req: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
            self.calls.fetch_add(1, Ordering::SeqCst);
            (self.eval_fn)(req)
        }
    }

    fn make_handle(
        enabled: bool,
        eval_fn: impl Fn(&JudgementRequest) -> Result<JudgementResponse, JudgementError> + Send + Sync + 'static,
    ) -> (JudgementHandle, Arc<TestClient>) {
        let client = Arc::new(TestClient {
            enabled,
            eval_fn: Box::new(eval_fn),
            calls: AtomicUsize::new(0),
        });
        let catalog = Catalog::embedded().unwrap();
        (
            JudgementHandle {
                client: client.clone(),
                catalog,
            },
            client,
        )
    }

    fn sample_history() -> Vec<ChatMessagePayload> {
        vec![
            ChatMessagePayload {
                id: "msg-0".into(),
                sender: "user".into(),
                text: "¿Cómo funciona la búsqueda?".into(),
                timestamp: 1000,
                tool_calls: None,
                backend: None,
            },
            ChatMessagePayload {
                id: "msg-1".into(),
                sender: "brain".into(),
                text: "⚡ **Resultado de `cortex memory.search jwt`:**\n\n```\n1. auth/jwt.rs\n2. auth/token.rs\n[200 lines of output]\n```".into(),
                timestamp: 1001,
                tool_calls: Some(vec![ToolCall {
                    tool: "memory.search".into(),
                    args: "jwt".into(),
                }]),
                backend: Some("LFM2.5".into()),
            },
            ChatMessagePayload {
                id: "msg-2".into(),
                sender: "user".into(),
                text: "Entendido, ahora mostrame el grafo.".into(),
                timestamp: 1002,
                tool_calls: None,
                backend: None,
            },
            ChatMessagePayload {
                id: "msg-3".into(),
                sender: "brain".into(),
                text: "⚡ **Resultado de `cortex webgraph.serve`:**\n\n```\nServidor activo en http://localhost:8080\n```".into(),
                timestamp: 1003,
                tool_calls: Some(vec![ToolCall {
                    tool: "webgraph.serve".into(),
                    args: "".into(),
                }]),
                backend: Some("LFM2.5".into()),
            },
            ChatMessagePayload {
                id: "msg-4".into(),
                sender: "user".into(),
                text: "¿Está corriendo en el puerto 8080?".into(),
                timestamp: 1004,
                tool_calls: None,
                backend: None,
            },
            ChatMessagePayload {
                id: "msg-5".into(),
                sender: "brain".into(),
                text: "Sí, el servidor está escuchando en el puerto 8080.".into(),
                timestamp: 1005,
                tool_calls: None,
                backend: Some("LFM2.5".into()),
            },
        ]
    }

    #[test]
    fn when_disabled_returns_original_messages_zero_calls() {
        let (handle, client) = make_handle(false, |_| unreachable!());
        let msgs = sample_history();
        let compacted = compact_chat_messages(&handle, msgs.clone(), 4);
        assert_eq!(compacted, msgs);
        assert_eq!(client.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn when_within_pin_limit_returns_original_messages_zero_calls() {
        let (handle, client) = make_handle(true, |_| unreachable!());
        let msgs = sample_history()[..4].to_vec();
        let compacted = compact_chat_messages(&handle, msgs.clone(), 4);
        assert_eq!(compacted, msgs);
        assert_eq!(client.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn on_429_fails_open_returns_original_messages() {
        let (handle, client) = make_handle(true, |_| Err(JudgementError::Http(429)));
        let msgs = sample_history();
        let compacted = compact_chat_messages(&handle, msgs.clone(), 4);
        assert_eq!(compacted, msgs);
        assert_eq!(client.calls.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn compacts_old_tool_result_and_preserves_pinned_messages() {
        let (handle, client) = make_handle(true, |_req| {
            let mut answers = serde_json::Map::new();
            // msg-1: keep_call 0.90, keep_result 0.10 (drop result!)
            answers.insert("keep_call_msg-1".into(), serde_json::json!({ "noul": 0.90 }));
            answers.insert("keep_result_msg-1".into(), serde_json::json!({ "noul": 0.10 }));

            Ok(JudgementResponse {
                model: "jev-1.13.0".into(),
                answers,
                usage: Default::default(),
                backend: "typesafe".into(),
            })
        });

        let msgs = sample_history();
        let pin_n = 4;
        let compacted = compact_chat_messages(&handle, msgs.clone(), pin_n);

        assert_eq!(client.calls.load(Ordering::SeqCst), 1);
        assert_eq!(compacted.len(), msgs.len());

        // msg-0: user message intact
        assert_eq!(compacted[0], msgs[0]);

        // msg-1: tool result truncated verbatim!
        assert!(compacted[1].text.contains(TRUNCATED_RESULT_MARKER));
        assert!(compacted[1].text.contains("Resultado de `cortex memory.search jwt`"));
        assert!(!compacted[1].text.contains("200 lines of output"));
        // keep_call was 0.90 >= 0.25, so tool_calls is preserved
        assert_eq!(compacted[1].tool_calls, msgs[1].tool_calls);

        // pinned messages (msg-2, msg-3, msg-4, msg-5) must be 100% byte-identical
        assert_eq!(compacted[2], msgs[2]);
        assert_eq!(compacted[3], msgs[3]);
        assert_eq!(compacted[4], msgs[4]);
        assert_eq!(compacted[5], msgs[5]);
    }

    #[test]
    fn drops_tool_call_when_keep_call_low() {
        let (handle, _) = make_handle(true, |_| {
            let mut answers = serde_json::Map::new();
            // keep_call 0.05 (< 0.25), keep_result 0.85 (keep result)
            answers.insert("keep_call_msg-1".into(), serde_json::json!({ "noul": 0.05 }));
            answers.insert("keep_result_msg-1".into(), serde_json::json!({ "noul": 0.85 }));

            Ok(JudgementResponse {
                model: "jev-1.13.0".into(),
                answers,
                usage: Default::default(),
                backend: "typesafe".into(),
            })
        });

        let msgs = sample_history();
        let compacted = compact_chat_messages(&handle, msgs.clone(), 4);

        // Result kept
        assert!(compacted[1].text.contains("200 lines of output"));
        // Call dropped
        assert_eq!(compacted[1].tool_calls, None);
    }
}
