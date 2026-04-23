import os
import shutil
import time
from pathlib import Path

# Configuramos el entorno para que Cortex no intente buscar en otras carpetas parent.
os.environ["CORTEX_ENV"] = "sandbox"

try:
    from cortex.core import AgentMemory
    from cortex.models import MemoryType
except ImportError:
    print("❌ Error: Cortex no está instalado o no se puede importar.")
    print("Asegúrate de correr esto desde el entorno virtual de Cortex.")
    exit(1)

def create_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"📄 Creado: {path.relative_to(Path.cwd())}")

def build_matrix(sandbox_dir: str):
    target = Path(sandbox_dir).resolve()
    
    print(f"🚀 Inicializando Cortex Matrix Sandbox en: {target}")
    
    # 1. Limpiar o crear carpeta
    if target.exists():
        print("🧹 Limpiando sandbox anterior...")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    
    # Cambiamos el directorio de trabajo para que Cortex opere acá
    os.chdir(target)
    
    # 2. Inicializar carpetas de Cortex manualmente para evitar prompts interactivos
    Path(".cortex").mkdir()
    Path("vault/architecture").mkdir(parents=True)
    Path("vault/sessions").mkdir(parents=True)
    Path("vault/frontend").mkdir(parents=True)

    # 3. Inyectar Memoria Semántica (Archivos del Vault)
    print("\n🧠 Inyectando Memoria Semántica (Vault)...")
    
    # Escenario A: Autenticación (Core)
    create_file(Path("vault/architecture/auth_patterns.md"), """---
tags: [security, auth, jwt]
timestamp: "2026-01-10T10:00:00"
---
# Patrones de Autenticación
Hemos decidido utilizar JWT (JSON Web Tokens) para la autenticación sin estado en todos los microservicios.
**Regla Estricta:** Los tokens deben expirar en 15 minutos y firmarse con RS256. Nunca usar almacenamiento local (localStorage) en el cliente, usar cookies HttpOnly.
""")

    # Escenario B: Base de datos (Ligeramente relacionado a Auth)
    create_file(Path("vault/architecture/database_schema.md"), """---
tags: [database, postgres, users]
timestamp: "2026-02-15T10:00:00"
---
# Esquema V2
La tabla de `users` ahora tiene una relación directa con `sessions` para permitir revocación de tokens JWT en tiempo real. 
""")

    # Escenario C: Frontend y UI (Nada que ver con Backend)
    create_file(Path("vault/frontend/neo_brutalism.md"), """---
tags: [ui, css, design]
timestamp: "2026-03-01T10:00:00"
---
# Guía de Estilos Neo-Brutalista
El proyecto usará bordes gruesos (2px solid black), colores de alto contraste (Amarillo #FFE600, Rosa #FF00FF) y sombras rígidas sin blur (`box-shadow: 8px 8px 0px black`).
""")

    # Escenario D: Trampa Semántica (Palabras clave ambiguas)
    create_file(Path("vault/frontend/design_tokens.md"), """---
tags: [ui, css, tokens]
timestamp: "2026-03-05T10:00:00"
---
# Design Tokens
Aquí definimos los "tokens" de diseño. 
- Token primario: #FFE600
- Token de espaciado: 16px
**Nota:** Estos tokens no tienen nada que ver con seguridad o JWT, son variables de CSS.
""")

    # 4. Inicializar Cortex Memory
    print("\n⚡ Arrancando motor de Cortex (AgentMemory)...")
    # Al instanciar, leerá el vault que acabamos de crear
    memory = AgentMemory()
    print("✅ Motor inicializado. Sincronizando vault local...")
    indexed = memory.sync_vault()
    print(f"✅ {indexed} documentos indexados en ChromaDB.")

    # 5. Inyectar Memoria Episódica (ChromaDB)
    print("\n🎞️ Inyectando Memoria Episódica (Eventos pasados)...")
    
    eventos = [
        # Escenario A: El desastre del JWT
        {
            "id": "PR-101",
            "content": "Merge pull request #101. Implementación inicial de JWT Auth. Se agregaron las librerías de PyJWT y se configuraron las rutas. Todo funciona en local.",
            "type": MemoryType.PR_SUMMARY
        },
        {
            "id": "CI-101-FAIL",
            "content": "GitHub Actions Error en pipeline de seguridad. Detectada vulnerabilidad crítica: El token JWT se estaba guardando en localStorage en el cliente, violando la arquitectura descrita en auth_patterns.md.",
            "type": MemoryType.CI_FAILURE
        },
        {
            "id": "PR-102",
            "content": "Merge pull request #102. Hotfix: Migrados los tokens JWT de localStorage a cookies HttpOnly. Pipeline CI/CD en verde.",
            "type": MemoryType.PR_SUMMARY
        },
        # Escenario C: Frontend
        {
            "id": "PR-201",
            "content": "Merge pull request #201. Aplicados tokens de diseño CSS al microsite. Sombras sólidas agregadas a los botones.",
            "type": MemoryType.PR_SUMMARY
        },
        # Escenario D: Trampa (Una mención ambigua a tokens)
        {
            "id": "ISSUE-55",
            "content": "Discusión técnica: Necesitamos actualizar los tokens urgentes porque el color de fondo no contrasta con el texto. Actualicen el archivo design_tokens.md por favor.",
            "type": MemoryType.SESSION
        }
    ]

    for evento in eventos:
        memory.store_memory(
            memory_id=evento["id"],
            content=evento["content"],
            memory_type=evento["type"]
        )
        # Pequeña pausa para simular timeline
        time.sleep(0.1)
    
    print("\n🎉 ¡CORTEX MATRIX SANDBOX CREADO EXITOSAMENTE! 🎉")
    print("-" * 50)
    print("Entorno de prueba listo en:", target)
    print("Puedes abrir una terminal en esa carpeta y probar comandos como:")
    print('  cortex search "cómo manejar los tokens"')
    print('  cortex webgraph serve')
    print("-" * 50)

if __name__ == "__main__":
    print("=== Cortex Matrix Simulator ===")
    print("Este script creará un entorno aislado con historias de prueba.")
    print("No contaminará tu repositorio actual.")
    
    default_dir = Path.cwd().parent / "PruebaCortex_Sandbox"
    user_input = input(f"¿Dónde quieres crear el Sandbox? [Enter para '{default_dir}']: ")
    
    target_dir = user_input.strip() if user_input.strip() else str(default_dir)
    build_matrix(target_dir)
