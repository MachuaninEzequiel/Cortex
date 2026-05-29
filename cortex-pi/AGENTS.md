# Cortex Agent — Governance Rules (Release 2.5 + cortex-net)

## Mandatory Pre-flight

Use `cortex-sync` first. **Sync stays outside cortex-net by design** —
its work is sequential and pre-net (B′ design). The network turns on
when sync hands off to SDDwork.

1. **⚠️ Mandatory Ticket Sync**: Run `cortex_sync_ticket` BEFORE any analysis. Skip this and the MCP server will block your Spec creation.
2. Run `git fetch` silently.
3. If remote has commits not in the local branch, stop and ask:
   > "Encontre actualizaciones en el repo de las memorias, hago pull?"
4. Use Cortex tools only to gather context:
   - `cortex_sync_ticket`
   - `cortex_search`
   - `cortex_context`
   - `cortex_create_spec`

## Ecosystem Isolation

External memory tools are strictly forbidden. Use of any of the following is a governance violation:

- `engram_*`
- `mem_*`
- `save_memory`
- `session_summary`

Rule: **If it doesn't start with `cortex_`, it doesn't belong here.**
(This now includes `cortex_net_*` for peer-to-peer coordination.)

## Release 2.5+net Execution Model

```
/cortex-sync         (anchor INICIO, fuera de la red, secuencial)
   ↓ abre Session + persiste Spec
[ red cortex-net se enciende ]
   ↓
cortex-SDDwork  ⇄  cortex-code-*  ⇄  security  ⇄  test-verifier  ⇄  documenter (observer)
   ↓ trabajan en paralelo, intercambian SEÑALES (no payloads)
   ↓ emiten checkpoints persistentes
[ usuario corre `cortex finish-session` o `/cortex-documenter` ]
   ↓
/cortex-documenter   (anchor FIN, cierra la red y persiste)
```

### Roles en la red

| Rol | Cuándo entra | Mensajes permitidos | Salir |
|---|---|---|---|
| `sddwork` | después de sync | `question`, `proposal`, `blocker`, `handoff`, `observe` | turn_end natural |
| `designer` | invocado por SDDwork (Deep Track) | `question`, `proposal` (raro), `blocker` | después del checkpoint |
| `explorer` | invocado por SDDwork (Deep Track) | `question`, `blocker` | después del checkpoint |
| `implementer` | invocado por SDDwork (Deep Track) | `question`, `blocker` | después del checkpoint |
| `security` | después de SDDwork | `question` (al implementer), `blocker` (al sddwork) | después del checkpoint |
| `test-verifier` | después de security | `question` (al implementer), `blocker` (al sddwork) | después del checkpoint |
| `documenter` | desde temprano, en modo observer | `question`, `observe` SOLAMENTE | al cierre formal |

### Lo que NO va por cortex-net

- **Código, specs, designs** → filesystem.
- **Estado de progreso oficial** → `cortex_session_checkpoint`.
- **Invocación de subagentes** → tool nativa del IDE.

## Definition of Done

Una tarea NO está completa hasta que:
- [ ] Code passes security audit.
- [ ] Code passes test verification (>85% coverage).
- [ ] Documentation has been written and synced to the Vault.
- [ ] **NUEVO**: cortex-net se cerró limpiamente (`cortex_close_session` apaga la red para todos los roles).

## Reglas críticas que NO se pueden saltar

- ⛔ Sync nunca entra a cortex-net.
- ⛔ Nadie responde inbounds con `cortex_net_send` manual (auto-reply lo hace).
- ⛔ Los mensajes en la red son **señales**, no **payloads**.
- ⛔ El cierre lo dispara el usuario (`cortex finish-session` o `/cortex-documenter`), no el medio.
- ⛔ Los YAML AgentHandoff están deprecados. El contrato es Cortex Session + checkpoints.
