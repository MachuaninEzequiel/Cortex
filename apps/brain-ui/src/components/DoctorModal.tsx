import React, { useEffect } from "react";
import { DoctorReportPayload, Lang } from "../types";
import { getT } from "../i18n";

interface DoctorModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: DoctorReportPayload | null;
  isLoading: boolean;
  onRunInspect: () => void;
  onExecuteFix?: (toolName: string) => void;
  lang: Lang;
}

export const DoctorModal: React.FC<DoctorModalProps> = ({
  isOpen,
  onClose,
  report,
  isLoading,
  onRunInspect,
  onExecuteFix,
  lang,
}) => {
  const t = getT(lang);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-mocha-crust/80 backdrop-blur-sm p-4 select-none animate-fade-in">
      <div className="flex h-[480px] w-full max-w-lg flex-col rounded-xl border border-mocha-surface bg-mocha-base shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="flex h-12 items-center justify-between border-b border-mocha-surface bg-mocha-surface/20 px-5">
          <div className="flex items-center gap-2">
            <span className="text-base">🛡️</span>
            <h3 className="font-semibold text-mocha-text font-mono text-sm">
              {t.governance.doctorTitle}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-mocha-subtext0 hover:bg-mocha-surface hover:text-mocha-text transition"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3 font-mono text-xs">
          {isLoading ? (
            <div className="flex h-48 items-center justify-center text-mocha-mauve animate-pulse">
              <span>Auditan do estado de gobernanza y salud del repositorio...</span>
            </div>
          ) : !report ? (
            <div className="flex h-48 flex-col items-center justify-center gap-3 text-mocha-subtext0">
              <span>No se ha ejecutado el diagnóstico todavía.</span>
              <button
                onClick={onRunInspect}
                className="rounded-lg bg-mocha-surface px-4 py-2 font-bold text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
              >
                Ejecutar Diagnóstico
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Overall Status Banner */}
              <div
                className={`flex items-center gap-3 rounded-lg border p-3 ${
                  report.is_healthy
                    ? "border-cortex-forest bg-cortex-forest/20 text-cortex-mint"
                    : "border-yellow-500/40 bg-yellow-500/10 text-yellow-300"
                }`}
              >
                <span className="text-lg">{report.is_healthy ? "✓" : "⚠"}</span>
                <div>
                  <div className="font-bold">
                    {report.is_healthy ? t.governance.doctorHealthy : t.governance.doctorIssues}
                  </div>
                  <div className="text-[11px] opacity-80">
                    {report.checks.length} validaciones ejecutadas en el proyecto
                  </div>
                </div>
              </div>

              {/* List of checks */}
              <div className="space-y-2">
                {report.checks.map((check, idx) => (
                  <div
                    key={idx}
                    className="flex items-start justify-between rounded-lg border border-mocha-surface bg-mocha-surface/20 p-3"
                  >
                    <div className="flex items-start gap-2.5">
                      <span
                        className={
                          check.status === "ok"
                            ? "text-cortex-mint"
                            : check.status === "warn"
                            ? "text-yellow-400"
                            : "text-red-400"
                        }
                      >
                        {check.status === "ok" ? "●" : "▲"}
                      </span>
                      <div>
                        <div className="font-bold text-mocha-text">{check.name}</div>
                        <p className="mt-0.5 text-[11px] text-mocha-subtext0 font-sans">
                          {check.message}
                        </p>
                      </div>
                    </div>

                    {check.auto_fix_tool && onExecuteFix && (
                      <button
                        onClick={() => onExecuteFix(check.auto_fix_tool!)}
                        className="rounded bg-mocha-surface px-2.5 py-1 text-[11px] text-cortex-mint hover:bg-cortex-forest transition"
                      >
                        {t.governance.autoFix}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex h-12 items-center justify-between border-t border-mocha-surface bg-mocha-base px-5">
          <button
            onClick={onRunInspect}
            disabled={isLoading}
            className="rounded bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-surface2 transition disabled:opacity-50"
          >
            Re-inspeccionar
          </button>
          <button
            onClick={onClose}
            className="rounded bg-mocha-surface px-4 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
