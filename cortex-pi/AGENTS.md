# Cortex Agent — Governance Rules

## Mandatory Pre-flight

Use `cortex-sync` first. **Sync stays outside cortex-net by design** —
its work is sequential and pre-net. The network turns on when sync hands
off to SDDwork.

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
(This includes `cortex_net_*` for peer-to-peer coordination.)

## Modelo de ejecución

```
/cortex-sync         (anchor INICIO, fuera de la red, secuencial)
   ↓ abre Session + persiste Spec
[ el humano arma el equipo con /cortex-team → la red cortex-net se enciende ]
   ↓
cortex-SDDwork  ⇄  cortex-code-*  ⇄  security  ⇄  test-verifier  ⇄  documenter (observer)
   ↓ trabajan en paralelo, coordinan por cortex-net (cada envío lo aprueba el humano)
   ↓ emiten checkpoints persistentes
[ el usuario corre `cortex finish-session` o `/cortex-documenter` ]
   ↓
/cortex-documenter   (anchor FIN, cierra la red y persiste)
```

### Cómo se coordinan los roles

La comunicación es **autónoma pero con el humano en el loop**:

- Para hablarle a otro rol, usá `cortex_net_send(to_role, msg_type, body)`.
  **El humano confirma, edita o rechaza cada envío** antes de que salga.
- **Cuando recibís un mensaje, ejecutá su instrucción directamente** (el
  emisor ya lo aprobó). Para responder o seguir coordinando, mandá otro
  `cortex_net_send`. No hay auto-reply y no se arman loops: cada paso
  necesita un humano que diga "sí".
- Los mensajes son **instrucción + contexto, ≤ ~1500 caracteres, nunca
  código ni archivos** (eso vive en el filesystem y en la Cortex Session).

### Roles en la red

| Rol | Cuándo entra | Mensajes permitidos | Sale |
|---|---|---|---|
| `sddwork` | después de sync | `question`, `proposal`, `blocker`, `handoff`, `observe` | turn_end natural |
| `designer` | desplegado en el team (Deep Track) | `question`, `proposal`, `blocker` | después del checkpoint |
| `explorer` | desplegado en el team (Deep Track) | `question`, `blocker` | después del checkpoint |
| `implementer` | desplegado en el team (Deep Track) | `question`, `blocker` | después del checkpoint |
| `security` | después de SDDwork | `question` (al implementer), `blocker` (al sddwork) | después del checkpoint |
| `test-verifier` | después de security | `question` (al implementer), `blocker` (al sddwork) | después del checkpoint |
| `documenter` | desde temprano, en modo observer | `question`, `observe` SOLAMENTE | al cierre formal |

### Lo que NO va por cortex-net

- **Código, specs, designs** → filesystem.
- **Estado de progreso oficial** → `cortex_session_checkpoint`.
- **Armado del equipo** → el humano con `/cortex-team`.

## Definition of Done

Una tarea NO está completa hasta que:
- [ ] Code passes security audit.
- [ ] Code passes test verification (>85% coverage).
- [ ] Documentation has been written and synced to the Vault.
- [ ] cortex-net se cerró limpiamente (`cortex_close_session` apaga la red para todos los roles).

## Reglas críticas que NO se pueden saltar

- ⛔ Sync nunca entra a cortex-net.
- ⛔ Cuando recibís un inbound, ejecutás su instrucción; si querés responder, mandás un `cortex_net_send` explícito (lo aprueba el humano). No hay auto-reply.
- ⛔ Los mensajes en la red son **señales** (instrucción + contexto), no **payloads** (código/archivos).
- ⛔ El cierre lo dispara el usuario (`cortex finish-session` o `/cortex-documenter`), no el medio.
- ⛔ Los YAML AgentHandoff están deprecados. El contrato es Cortex Session + checkpoints.
