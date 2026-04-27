# Avance EPIC 1: Enterprise Foundation

## Documento

- Fecha: 2026-04-26
- Iniciativa: `Enterprise Memory Productization`
- Epic completada: `E1 - Modelo organizacional enterprise`

---

## Resumen

En esta entrega se implemento la base organizacional de memoria enterprise para Cortex.

El objetivo de la EPIC 1 era que Cortex dejara de depender de convenciones implcitas para representar topologias empresariales y pasara a tener:

- una configuracion organizacional formal
- carga nativa en runtime
- exposicion por CLI
- diagnostico especifico desde `doctor`
- integracion basica con `setup`

Ese objetivo quedo completado.

---

## Que se desarrollo

### 1. Nuevo paquete `cortex.enterprise`

Se agrego una nueva capa de codigo en:

- [cortex/enterprise/models.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/enterprise/models.py)
- [cortex/enterprise/config.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/enterprise/config.py)
- [cortex/enterprise/__init__.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/enterprise/__init__.py)

Esto incorpora:

- schema formal de `.cortex/org.yaml`
- validacion tipada con Pydantic
- presets base:
  - `small-company`
  - `multi-project-team`
  - `regulated-organization`
  - `custom`
- reglas cross-section para evitar combinaciones invalidas
- helpers de discovery, load, write y descripcion de topologia

### 2. Nuevo archivo organizacional `.cortex/org.yaml`

Se formalizo el archivo de configuracion enterprise con estas secciones:

- `organization`
- `memory`
- `promotion`
- `governance`
- `integration`

Tambien se introdujo `schema_version` para versionar el formato desde el principio.

### 3. Integracion con runtime

Se integro la carga enterprise en [cortex/core.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/core.py).

Ahora `AgentMemory`:

- descubre `.cortex/org.yaml` si existe
- lo carga sin romper backward compatibility si no existe
- expone `enterprise_config`
- expone `enterprise_topology`
- agrega metadata organizacional a la metadata de runtime que ya viaja a memorias episodicas

### 4. Integracion con CLI

Se agrego soporte en [cortex/cli/main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/cli/main.py) para:

- `cortex doctor --scope enterprise`
- `cortex doctor --scope all`
- `cortex org-config`

Esto permite:

- validar especificamente la topologia enterprise
- detectar ausencia o inconsistencia de `.cortex/org.yaml`
- inspeccionar la configuracion enterprise resuelta desde CLI

### 5. Integracion con `doctor`

Se extendio [cortex/doctor.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/doctor.py) para diagnosticar:

- existencia de `.cortex/org.yaml`
- validez del schema
- topologia efectiva
- directorio de `vault-enterprise`
- directorio de memoria enterprise si estuviera habilitado
- alineacion entre `config.yaml` y `org.yaml` para branch isolation

### 6. Integracion con `setup`

Se extendieron:

- [cortex/setup/templates.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/templates.py)
- [cortex/setup/orchestrator.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/cortex/setup/orchestrator.py)

Ahora `setup` genera automaticamente:

- `.cortex/org.yaml`
- `vault-enterprise/README.md`
- estructura minima de `vault-enterprise/`

Esto deja una base enterprise inicial sin esperar todavia al futuro `cortex setup enterprise`.

---

## Precedencia definida entre `config.yaml` y `org.yaml`

Quedo establecido este criterio:

- `config.yaml` sigue siendo la fuente de verdad para el runtime local del proyecto
- `.cortex/org.yaml` pasa a ser la fuente de verdad para topologia enterprise, promotion y gobernanza organizacional

Esto evita romper setups existentes y mantiene separadas las responsabilidades.

---

## Comportamiento actual despues de esta entrega

### Si el repo no tiene `.cortex/org.yaml`

- Cortex sigue funcionando como antes
- `AgentMemory` no se rompe
- `cortex doctor` normal sigue siendo compatible
- `cortex org-config --required` falla de forma explicita
- `cortex doctor --scope enterprise` falla porque ese scope ahora exige config organizacional

### Si el repo si tiene `.cortex/org.yaml`

- Cortex carga la topologia enterprise
- la CLI la puede mostrar
- `doctor` la puede validar
- la metadata organizacional ya empieza a viajar con la memoria episodica

---

## Tests agregados

Se agregaron tests nuevos en:

- [tests/unit/enterprise/test_config.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/tests/unit/enterprise/test_config.py)
- [tests/unit/enterprise/test_enterprise_setup.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/tests/unit/enterprise/test_enterprise_setup.py)
- [tests/unit/cli/test_main.py](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/tests/unit/cli/test_main.py)

Cobertura funcional validada:

- carga y validacion de `org.yaml`
- presets enterprise
- backward compatibility cuando falta config
- `doctor --scope enterprise`
- `org-config`
- generacion de `.cortex/org.yaml` y `vault-enterprise/` desde setup

---

## Comandos utiles despues de esta entrega

```bash
cortex org-config
cortex org-config --json
cortex doctor --scope enterprise
cortex doctor --scope all
```

---

## Estado en el backlog

Se marco como completada la `EPIC E1 - Modelo organizacional enterprise` en:

- [BACKLOG-Enterprise-Memory-Productization.md](/D:/DevSecDocOps/DevSecDocOps-3erCortex/cortex-repo/cortex/BACKLOG-Enterprise-Memory-Productization.md)

---

## Proximo paso natural

Con esta base ya resuelta, Cortex queda listo para avanzar a la siguiente capa real de producto:

- `E2 - Retrieval multi-nivel`

Ese es el punto donde la topologia enterprise pasa de estar modelada a estar operativa en recuperacion de contexto.
