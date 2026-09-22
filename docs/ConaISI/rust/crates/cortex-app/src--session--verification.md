# src/session/verification.rs

## Qué tiene adentro

`VerificationRunner { repo_root, max_output_bytes }`. Ejecuta `sh -c hook.command` en `repo_root`.

Contrato: cada hook produce un `VerificationHookResult`. Timeout → `exit_code=-1`, output `"(timeout after Ns)"`. Spawn fail o wait error → **panic** (infra). Non-zero del hook → `passed=false`, no panic.

Output: stdout + `\n[stderr]\n` + stderr si ambos; truncado con `truncate_output`. `now_iso` RFC3339 micros con `Z` (`SecondsFormat::Micros, true`) — distinto del `now_iso` de `service.rs` (`false` → `+00:00`).

`run_all` mapea secuencial.

## Para qué sirve

Correr verification hooks de la spec/sesión.

## Relaciones

### Recibe de

- `VerificationHook` (command, timeout_seconds, name).

### Envía a

- `CiValidator`, documenter, `SessionService` close.

### Notas de implementación observadas en el código

Polling 25ms. `max_output_bytes` está `allow(dead_code)`; el truncado real es el de `truncate_output` (10_000).
