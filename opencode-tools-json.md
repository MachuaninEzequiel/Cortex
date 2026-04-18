{
"$schema": "https://opencode.ai/schemas/tools-config.json",
"profiles": {
"cortex-sync": {
"allowed*tools": [
"read_file",
"write_file",
"cortex_search",
"cortex_context",
"cortex_sync_vault",
"cortex_create_spec"
],
"disallowed_tools": [
"engram*_",
"mem\__",
"execute*command",
"cortex_save_session",
"cortex_delegate_task"
],
"description": "Perfil Pre-flight: Diseñado para análisis y especificación. No implementa ni guarda sesiones."
},
"cortex-SDDwork": {
"allowed_tools": [
"cortex_delegate_task",
"cortex_get_task_result",
"read_file",
"cortex_search",
"cortex_context"
],
"disallowed_tools": [
"write_file",
"edit_file",
"execute_command",
"engram*_",
"mem\__",
"cortex*save_session"
],
"description": "Orquestador SDD: Gestiona la implementación mediante delegación. Tiene prohibido escribir código directamente."
},
"cortex-documenter": {
"allowed_tools": [
"read_file",
"write_file",
"cortex_save_session",
"cortex_sync_vault"
],
"disallowed_tools": [
"execute_command",
"edit_file",
"engram*\*"
],
"description": "Documentador: Guardián de la memoria. Solo escribe en el vault e indexa sesiones."
}
},
"default_profile": "cortex-sync",
"require_profile_selection": true
}
