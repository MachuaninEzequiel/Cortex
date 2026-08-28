# Craft de revision (on-demand)

Referencia de `review/SKILL.md`. Checklists por eje y gramatica de hallazgos.

## Checklist — eje Standards (calidad)

- **Diseno**: modulos con una responsabilidad, interfaces angostas, sin god objects nuevos. El diff metio una funcion que "hace de todo"?
- **Tests**: verifican comportamiento (no mocks), cubren bordes y el camino de error, sin orden ni suenos. Nombre legible como especificacion.
- **Duplicacion**: copy-paste entre archivos o ramas que piden un helper. (La abstraccion prematura tambien es hallazgo: dos usos triviales no piden trait.)
- **Errores**: propagacion explicita; nada de `let _ =` sobre falibles; mensajes consistentes con el resto del crate.
- **Nombres**: terminos de `CONTEXT.md` usados canonicalmente (cruza con el eje Spec).

## Checklist — eje Spec (fidelidad)

- Cada Acceptance criterion ⇒ veredicto SI/NO con evidencia (comando + resultado o artefacto mirado), no con opinion del autor.
- `files_in_scope` respetado? Todo lo demas es drift ⇒ Important o mayor.
- Los verification hooks de la spec: correrlos, no suponerlos.
- `unverified_claims` abiertos de los checkpoints `implement`: alguno es critico para el cierre?

## Gramatica del hallazgo

`[Critical|Important|Minor] file:line — que esta mal. Por que importa. Fix sugerido (si no es obvio).`

Sin file:line es opinion. Sin severidad, el autor no sabe que bloquea. Sin "por que", parece gusto.

## Veredictos

- **approve**: sin Critical ni Important.
- **request-changes**: hay Important ⇒ fix + re-check del MISMO hallazgo (no "confio en que quedo bien").
- **block**: hay Critical, o no hay evidencia que mostrar (corrida, comando, artefacto).

## Anti-racionalizaciones del revisor

| Escusa | Respuesta |
|---|---|
| "Se ve bien, apruebo" | Corriste algo? Si no, leiste, no revisaste. |
| "Es chico, no necesita test" | El volumen de bugs tontos vive en los cambios chicos. |
| "Lo hago Minor para no frenar" | Severidad describe, no negocia. |
| "El autor sabe lo que quiso decir" | Si tuviste que adivinar, falta un nombre claro o una linea de comentario. |
