# Portero — utterance, sesión, memoria, tools

Spec. El LLM codea. Jev clasifica el *acto*. Cortex ejecuta. El humano no elige agentes.

**No implementar hasta el orden del handoff.** Depende de Direct/JevDD ([08](08-direct-y-jevdd.md)).

---

## Dolor

Hoy el dev debe invocar `/cortex-sync` → desarrollar → `/cortex-documenter`.  
Y `remember` no tiene criterio: el episódico se llena de chatter.

---

## Invariantes

| Situación | Qué debe pasar |
|---|---|
| Pregunta / explicación | 0 sesión nueva, 0 remember |
| Trabajo que cambia el sistema | Sesión abierta (oficio sync), aunque el humano no tipeó el slash |
| Trabajo terminado | Oficio documenter / finish |
| “ok”, pregunta, diff trivial | No entra al episódico |

Sync y documenter **no se borran**. Dejan de ser **personas del menú**. Pasan a ser **jobs del runtime**.

---

## Un HTTP al primer mensaje (y al write)

Purpose tentativo: `utterance` (nombre de palanca; un purpose, no once).

Questions en **un** `system_one` (paralelo, barato):

```
Choice work:     question | implement | chore | done
Noul needs_session
Noul worth_remembering
Noul needs_finish
```

Más, si 08 está on, en el mismo call o el siguiente:

```
Noul needs_explore
Noul needs_security
Noul needs_split
```

State: texto del usuario + “¿hay sesión activa?” + files del observer si hay. No el vault entero.

Confianza de Choice &lt; 0.5 → `question` (no abrir sesión por las dudas) o una pregunta al humano si `implement` es plausible.

---

## Qué hace Cortex con las respuestas

```
question  → el LLM responde; pack ligero o vacío; no remember
implement → si no hay sesión activa, Cortex abre una (job sync)
chore     → ni spec ni vault
done      → job documenter / finish (o “¿cierro?” si needs_finish a medias)
```

`worth_remembering` se evalúa **antes** de `AgentMemory.remember`, no en el chatter del LLM.

Fail-open:

- 429 / sin key → Direct: no se inventa sesión; remember como hoy **salvo** chatter de pregunta (recomendación: pregunta nunca persiste, incluso en Direct).
- Nunca dejar al dev sin poder codear porque Jev no contestó.

---

## MCP: write gated, Read libre

Jev **no llama** tools. El harness pregunta y luego corre o no.

| Tools | ¿Jev antes? |
|---|---|
| Read: search, context, doctor, stats | No. Squeeze / pack *después*. |
| Write liviano: remember, checkpoint | Sí. `worth_remembering` / equivalente. |
| Write pesado: create_spec, finish, promote | Sí. Sesión y ACL primero; Jev no salta gobernanza. |
| Guardrail / veto security | Purpose aparte, **default off**, fail-open. |

Cero tool MCP nueva. El golden de 32 tools no se toca. Cambia *cuándo* el runtime dispara writes, no el catálogo.

---

## UX del camino feliz

```
$ pi
> cómo funciona el checkpoint verification
  → question, 0 sesión, pack ligero, 0 remember

> arreglá el gate que deja pasar checkpoints vacíos
  → implement, Cortex abre sesión, el dev codea

> listo
  → needs_finish → documenter
```

Cero `/cortex-sync` en el camino feliz. Skills de sync/documenter pueden quedar para IDEs sin portero; no son el default.

---

## Relación con otras palancas

| Purpose | Job |
|---|---|
| `search_squeeze` | Ranking de `cortex search` (hecho en código) |
| `promotion` | Ordenar candidatos org (hecho en código, noul en UI) |
| `context_pack` | Prompt del enricher (spec 07, no código) |
| `utterance` | Este doc |
| `session_compact` | Borrar/truncar tool results del historial Brain; **no** es el portero ni el pack. Spec futura. No mezclar. |

No hay SDK de terceros. HTTP nuestro. Nombres de terceros no van a UI ni a skills.

---

## Tests cuando se implemente

- Pregunta → 0 llamada a start-session / remember (mock Jev `work=question`).
- Implement sin sesión → 1 start-session (mock).
- 429 en utterance → no start-session; el chat sigue.
- `worth_remembering` 0.1 → remember no escribe.
- YAML sin purpose ≡ Direct (cero HTTP).
