{
  "$schema": "https://opencode.ai/schemas/tools-config.json",
  "agent": {
    "cortex-sync": {
      "mode": "primary",
      "description": "ANALISIS: Pre-flight con inyeccion obligatoria de contexto.",
      "prompt": "{file:/home/chucho/.config/opencode/skills/cortex-sync.md}",
      "tools": {
        "read": true,
        "write": false,
        "edit": false,
        "bash": false,
        "glob": true,
        "grep": true,
        "cortex_sync_ticket": true,
        "cortex_create_spec": true,
        "cortex_context": true,
        "cortex_search": true,
        "cortex_sync_vault": true
      }
    },
    "cortex-SDDwork": {
      "mode": "primary",
      "description": "ORQUESTADOR: Delegacion obligatoria por rondas de subagentes.",
      "prompt": "{file:/home/chucho/.config/opencode/skills/cortex-SDDwork.md}",
      "tools": {
        "read": true,
        "write": false,
        "edit": false,
        "bash": false,
        "cortex_context": true,
        "cortex_search": true,
        "cortex_delegate_task": true,
        "cortex_delegate_batch": true,
        "cortex_get_task_result": true
      }
    },
    "cortex-documenter": {
      "mode": "primary",
      "description": "DOCUMENTACION: Persistencia final en Vault.",
      "prompt": "{file:/home/chucho/.config/opencode/subagents/cortex-documenter.md}",
      "tools": {
        "read": true,
        "write": true,
        "edit": false,
        "bash": false,
        "cortex_save_session": true,
        "cortex_sync_vault": true
      }
    }
  }
}
