@echo off
REM Cortex Autopilot hook wrapper for Windows.
REM Usage: run_hook.cmd <module_name> [args...]
REM Example: run_hook.cmd session_start --project-root C:\repo

python -m cortex.autopilot.hooks.%* 2>&1
if errorlevel 1 (
    echo {"error": "Hook failed or Python not in PATH"}
    exit /b 1
)
