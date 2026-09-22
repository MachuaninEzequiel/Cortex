# rust/crates/cortex-doctor — estructura interna

Chequeos de salud del workspace.

```
cortex-doctor/
├── Cargo.toml
├── examples/doctor_check.rs
├── src/
│   ├── lib.rs          # mods checks, doctor, native
│   ├── checks.rs       # DoctorCheck, DoctorReport, severidad
│   ├── doctor.rs       # DoctorScope, run_doctor
│   └── native.rs       # NativeDoctorBackend
└── tests/doctor_core.rs
```

## Relaciones

- **Recibe de:** `cortex-app`, `cortex-config`, `cortex-autopilot`, `cortex-enterprise`, `cortex-workspace`.
- **Envía a:** `cortex-cli doctor`; brain tool `cortex.health` (vía CLI); reporting enterprise (`DoctorBackend`).
