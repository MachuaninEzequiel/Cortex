import React, { useEffect } from "react";
import { ToolCall, Lang } from "../types";
import { getT } from "../i18n";

interface ToolApprovalModalProps {
  isOpen: boolean;
  toolCall: ToolCall | null;
  onConfirm: () => void;
  onCancel: () => void;
  lang: Lang;
}

export const ToolApprovalModal: React.FC<ToolApprovalModalProps> = ({
  isOpen,
  toolCall,
  onConfirm,
  onCancel,
  lang,
}) => {
  const t = getT(lang);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen || !toolCall) return null;

  const cliCommand = `cortex ${toolCall.tool} ${toolCall.args}`.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="flex w-[480px] flex-col rounded-xl border border-mocha-mauve/40 bg-mocha-base shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-mocha-surface px-4 py-3 bg-mocha-base">
          <span className="text-mocha-mauve text-lg">⚡</span>
          <h3 className="font-mono text-sm font-bold text-mocha-text">
            {t.toolModal.title}
          </h3>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3 text-xs text-mocha-text">
          <p className="text-mocha-subtext0">
            {t.toolModal.desc}
          </p>

          <div className="rounded-lg border border-mocha-surface bg-mocha-surface/30 p-3 space-y-2 font-mono">
            <div className="flex justify-between">
              <span className="text-mocha-surface2">{t.toolModal.tool}</span>
              <span className="text-cortex-mint font-bold">{toolCall.tool}</span>
            </div>
            {toolCall.args && (
              <div className="flex justify-between">
                <span className="text-mocha-surface2">{t.toolModal.args}</span>
                <span className="text-mocha-text max-w-[280px] truncate text-right">{toolCall.args}</span>
              </div>
            )}
          </div>

          <div>
            <span className="block font-mono text-[11px] text-mocha-surface2 mb-1">
              {t.toolModal.cliEquivalent}
            </span>
            <pre className="rounded bg-mocha-base border border-mocha-surface p-2 font-mono text-[11px] text-mocha-lavender select-all overflow-x-auto">
              $ {cliCommand}
            </pre>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 border-t border-mocha-surface bg-mocha-base px-4 py-3">
          <button
            onClick={onCancel}
            className="rounded bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-subtext0 hover:bg-mocha-surface2 hover:text-mocha-text transition"
          >
            {t.toolModal.cancel}
          </button>
          <button
            onClick={onConfirm}
            className="rounded bg-cortex-forest px-3.5 py-1.5 font-mono text-xs font-semibold text-cortex-mint shadow hover:bg-cortex-forest/80 transition active:scale-95"
          >
            {t.toolModal.confirm}
          </button>
        </div>
      </div>
    </div>
  );
};
