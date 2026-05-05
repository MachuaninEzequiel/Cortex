# Roadmap de ejecucion - Cortex

Este directorio contiene el desglose operativo del plan activo definido en [docs/vision/PLAN_CORTEX_MAXIMO_IMPACTO.md](../vision/PLAN_CORTEX_MAXIMO_IMPACTO.md).

## Regla de uso

- Marcar cada tarea completada directamente en el archivo de su epica.
- No dejar tareas hechas sin check.
- Al cerrar una epica, completar su archivo `-REALIZACION.md` asociado de forma concisa.
- Si una tarea cambia de alcance, actualizar primero la epica y despues ejecutar.

## Estructura

- `epics/EPIC-01-...md` = plan ejecutable de la epica.
- `epics/EPIC-01-...-REALIZACION.md` = documento de cierre de la epica.

## Epicas activas

1. [EPIC-01 - Versionado y narrativa publica](./epics/EPIC-01-versionado-y-narrativa-publica.md)
   Documento de realizacion: [EPIC-01 - Realizacion](./epics/EPIC-01-versionado-y-narrativa-publica-REALIZACION.md)
2. [EPIC-02 - Estabilizacion de la suite roja](./epics/EPIC-02-estabilizacion-de-la-suite-roja.md)
   Documento de realizacion: [EPIC-02 - Realizacion](./epics/EPIC-02-estabilizacion-de-la-suite-roja-REALIZACION.md)
3. [EPIC-03 - Promotion enterprise y contrato de layout](./epics/EPIC-03-promotion-enterprise-y-contrato-de-layout.md)
   Documento de realizacion: [EPIC-03 - Realizacion](./epics/EPIC-03-promotion-enterprise-y-contrato-de-layout-REALIZACION.md)
   Guia de ejecucion autonoma: [EPIC-03 - Ejecucion](./epics/EPIC-03-promotion-enterprise-y-contrato-de-layout-EJECUCION.md)
4. [EPIC-04 - Hardening de paths y seguridad operativa](./epics/EPIC-04-hardening-de-paths-y-seguridad-operativa.md)
   Documento de realizacion: [EPIC-04 - Realizacion](./epics/EPIC-04-hardening-de-paths-y-seguridad-operativa-REALIZACION.md)
5. [EPIC-05 - Alineacion documental operativa](./epics/EPIC-05-alineacion-documental-operativa.md)
   Documento de realizacion: [EPIC-05 - Realizacion](./epics/EPIC-05-alineacion-documental-operativa-REALIZACION.md)

## Regla de cierre

Una epica solo puede marcarse como terminada cuando:

- todas sus tareas tienen check;
- las validaciones listadas en la epica fueron ejecutadas;
- su archivo `-REALIZACION.md` fue completado;
- cualquier desviacion respecto del plan original quedo registrada en ese archivo de realizacion.
