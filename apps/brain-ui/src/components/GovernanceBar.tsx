import React from "react";
import { SessionStatusPayload, DoctorReportPayload, PinnedContextNode, Lang } from "../types";
import { getT } from "../i18n";

interface GovernanceBarProps {
  sessionStatus: SessionStatusPayload | null;
  doctorReport: DoctorReportPayload | null;
  onOpenWebGraph: () => void;
  onOpenDoctor: () => void;
  onOpenOrgMemory: () => void;
  orgCandidatesCount?: number;
  onSaveCheckpoint: () => void;
  pinnedNodes: PinnedContextNode[];
  onRemovePinnedNode: (id: string) => void;
  lang: Lang;
}

export const GovernanceBar: React.FC<GovernanceBarProps> = ({
  sessionStatus,
  doctorReport,
  onOpenWebGraph,
  onOpenDoctor,
  onOpenOrgMemory,
  orgCandidatesCount = 0,
  onSaveCheckpoint,
  pinnedNodes,
  onRemovePinnedNode,
  lang,
}) => {
  const t = getT(lang);

  const isHealthy = doctorReport ? doctorReport.is_healthy : true;

  return (
    <div className="flex flex-col border-b border-mocha-surface/60 bg-mocha-base px-4 py-2 text-xs font-mono select-none">
      <div className="flex items-center justify-between gap-3">
        {/* Left: Session Badge & Checkpoints */}
        <div className="flex items-center gap-2.5">
          {sessionStatus?.active ? (
            <div className="flex items-center gap-2 rounded-lg bg-cortex-forest/40 border border-cortex-forest px-2.5 py-1 text-cortex-mint shadow-sm">
              <span className="inline-block h-2 w-2 rounded-full bg-cortex-mint animate-pulse" />
              <span className="font-bold">
                {sessionStatus.session_id ? `Sesión #${sessionStatus.session_id}` : t.governance.sessionActive}
              </span>
              <span className="text-[10px] text-mocha-subtext0">
                ({sessionStatus.checkpoints_count} {t.governance.checkpoints})
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-lg border border-mocha-surface bg-mocha-surface/20 px-2.5 py-1 text-mocha-surface2">
              <span>○</span>
              <span>{t.governance.noSession}</span>
            </div>
          )}

          {sessionStatus?.active && (
            <button
              onClick={onSaveCheckpoint}
              className="flex items-center gap-1 rounded-lg bg-mocha-surface/50 border border-mocha-surface px-2.5 py-1 text-[11px] text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition active:scale-95"
              title={t.governance.checkpointPrompt}
            >
              <span>📌</span>
              <span>{t.governance.newCheckpoint}</span>
            </button>
          )}
        </div>

        {/* Right: Quick Action Buttons (WebGraph & Doctor) */}
        <div className="flex items-center gap-2">
          {/* Memoria Organizacional Trigger */}
          <button
            onClick={onOpenOrgMemory}
            className="flex items-center gap-1.5 rounded-lg border border-mocha-surface bg-mocha-surface/30 px-3 py-1 text-xs text-mocha-text hover:border-[#cba6f7] hover:text-[#cba6f7] transition active:scale-95"
            title="Abrir Memoria Organizacional y Enterprise Knowledge Vault"
          >
            <span>🏛️</span>
            <span className="font-semibold">Memoria Org</span>
            {orgCandidatesCount > 0 && (
              <span className="rounded-full bg-[#cba6f7]/20 border border-[#cba6f7]/40 px-1.5 py-0.2 text-[10px] text-[#cba6f7] font-bold">
                {orgCandidatesCount}
              </span>
            )}
          </button>

          {/* WebGraph Trigger */}
          <button
            onClick={onOpenWebGraph}
            className="flex items-center gap-1.5 rounded-lg border border-mocha-surface bg-mocha-surface/30 px-3 py-1 text-xs text-mocha-text hover:border-mocha-mauve hover:text-mocha-mauve transition active:scale-95"
          >
            <span>🕸️</span>
            <span className="font-semibold">{t.governance.webgraphBtn}</span>
          </button>

          {/* Doctor Status Badge & Trigger */}
          <button
            onClick={onOpenDoctor}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1 text-xs transition active:scale-95 ${
              isHealthy
                ? "border-mocha-surface bg-mocha-surface/30 text-mocha-subtext0 hover:text-mocha-text hover:border-mocha-mauve"
                : "border-yellow-500/50 bg-yellow-500/10 text-yellow-300 animate-pulse"
            }`}
          >
            <span>🛡️</span>
            <span className="font-semibold">{t.governance.doctorBtn}</span>
            <span
              className={`h-2 w-2 rounded-full ${isHealthy ? "bg-cortex-mint" : "bg-yellow-400"}`}
            />
          </button>
        </div>
      </div>

      {/* Pinned Context Nodes Banner (if any nodes are pinned) */}
      {pinnedNodes.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2 pt-2 border-t border-mocha-surface/30">
          <span className="text-[10px] font-semibold text-mocha-mauve">
            {t.governance.pinnedContext}
          </span>
          {pinnedNodes.map((node) => (
            <div
              key={node.id}
              className="flex items-center gap-1.5 rounded-md bg-mocha-surface/60 border border-mocha-surface px-2 py-0.5 text-[11px] text-mocha-text shadow-sm"
            >
              <span className="text-[10px]">
                {node.kind === "module" ? "📦" : node.kind === "spec" ? "📄" : node.kind === "adr" ? "🏛️" : "📄"}
              </span>
              <span className="font-bold">{node.label}</span>
              <button
                onClick={() => onRemovePinnedNode(node.id)}
                className="ml-1 text-[10px] text-mocha-surface2 hover:text-mocha-text"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
