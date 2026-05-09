# BusinessSignal Detectors

## Filosofia De Detectores

Cada detector debe ser una pieza pequena, aislada y testeable.

Agregar un detector nuevo deberia implicar:

1. Crear un archivo en `cortex/business_signal/detectors/`.
2. Implementar el contrato base.
3. Registrarlo en el registry.
4. Agregar tests y documentacion.

No debe requerir modificar el motor principal.

## Contrato Conceptual

```text
BusinessSignalDetector
  name: str
  version: str
  evaluate(input: DetectorInput) -> list[BusinessSignal]
```

## Detector 1: Project Concentration

### Objetivo

Detectar cuando una parte significativa del contexto enriquecido del proyecto actual viene de un mismo proyecto historico.

### Ejemplo

```text
En las ultimas 20 HU, 14 tuvieron hits relevantes de project-Y.
El 68% del score historico ponderado proviene de project-Y.
```

### Senal

```text
Historical Project Analogy
```

### Valor

Este detector es el MVP ideal porque usa datos que Cortex ya produce.

### Umbrales Iniciales

- Minimo 8 eventos de enrichment.
- Minimo 5 work items distintos.
- Un proyecto historico concentra mas del 45% del score ponderado.
- Al menos 3 estrategias distintas encontraron hits relacionados.

## Detector 2: Sequence Similarity

### Objetivo

Detectar si el orden de avance del proyecto actual se parece al orden de un proyecto anterior.

### Ejemplo

```text
Proyecto actual:
auth -> roles -> dashboard -> reporting -> exports

Proyecto historico:
auth -> permissions -> dashboard -> reporting -> exports
```

### Senal

```text
Historical Sequence Match
```

### Valor

Permite anticipar pasos siguientes probables. No como certeza, sino como revision sugerida.

### Implementacion Inicial

Usar fingerprints de dominio/tag/modulo por HU y una similitud simple:

- Jaccard para sets de tags.
- Longest Common Subsequence para secuencia de dominios.
- Peso adicional si coinciden memory types criticos.

## Detector 3: Priority Pattern

### Objetivo

Detectar si la priorizacion actual del product owner o equipo se parece a la priorizacion de otro proyecto.

### Evidencia

- Labels.
- Orden de HU.
- Epicas.
- Tipos de documentos recuperados.
- Cambios de foco entre dominios.

### Senal

```text
Priority Pattern Echo
```

### Valor

Ayuda a producto y delivery a anticipar que tipo de solicitudes podrian aparecer.

## Detector 4: Risk Echo

### Objetivo

Detectar cuando un proyecto actual se parece a una zona historica que termino en incidente, retrabajo, ADR controversial o deuda tecnica.

### Fuentes Relevantes

- `incident`
- `security`
- `ADR`
- `changelog`
- sesiones con tags como `scope-change`, `rework`, `blocked`, `migration`, `performance`

### Senal

```text
Risk Echo
```

### Ejemplo

```text
El proyecto actual recupero 6 veces memorias relacionadas con auth-refresh.
En el proyecto historico, ese flujo derivo en un incidente de permisos y una decision arquitectonica tardia.
```

### Accion Recomendada

Revisar incidentes y ADRs antes de seguir implementando.

## Detector 5: Scope Drift

### Objetivo

Advertir que el proyecto actual se parece a proyectos donde hubo cambios de alcance tardios.

### Senal

```text
Scope Drift Warning
```

### Evidencia

- Hits historicos con tags `scope-change`, `late-request`, `product-change`.
- Crecimiento de dominios tocados.
- Aumento de documentos similares fuera del dominio inicial.

### Cuidado

Este detector debe ser conservador. Un falso positivo puede generar ruido politico. Debe usar severidad `advisory` hasta tener feedback historico.

## Detector 6: Client Behavior Analogy

### Objetivo

Detectar patrones repetidos asociados a un cliente o tipo de cliente.

### Ejemplo

```text
Clientes de retail con integraciones legacy suelen pedir reporting avanzado despues de cerrar autenticacion y dashboard.
```

### Senal

```text
Client Behavior Analogy
```

### Requisito

Necesita metadata confiable de cliente, industria o vertical. No debe inferir cliente desde texto libre sin confirmacion.

## Detector 7: Architecture Decision Recurrence

### Objetivo

Detectar que el proyecto actual se acerca a una decision arquitectonica ya tomada antes.

### Senal

```text
Recurring Architecture Decision
```

### Valor

Evita repetir debates y facilita traer ADRs pasados al presente.

## Detector 8: Knowledge Gap

### Objetivo

Detectar cuando Cortex encuentra similitudes fuertes pero no hay suficiente documentacion explicativa.

### Senal

```text
Knowledge Gap
```

### Ejemplo

```text
Hay 12 hits del proyecto historico, pero ninguno es ADR, runbook o decision formal.
```

### Valor

Ayuda a mejorar el vault y la memoria corporativa.

## Detector 9: Delivery Friction Pattern

### Objetivo

Detectar similitudes con proyectos que tuvieron bloqueos, esperas externas, dependencias o aprobaciones lentas.

### Senal

```text
Delivery Friction Pattern
```

### Uso

Muy util para leads, PMs y delivery managers.

## Detector 10: Compliance And Security Echo

### Objetivo

Detectar si el proyecto actual entra en una zona donde antes aparecieron requisitos de seguridad, compliance, auditoria o privacidad.

### Senal

```text
Compliance Echo
```

### Accion Recomendada

Involucrar seguridad o compliance antes de que el requisito aparezca tarde.

