import React from "react";
import { MarkRamState } from "../types";
import { MarkRam } from "./MarkRam";
import { getT } from "../i18n";

interface StatusBarProps {
  totalProjects: number;
  activeSessions: number;
  loadedProjectsCount: number;
  markRamState: MarkRamState;
  activeModelSize?: number;
  lang: "es" | "en";
}

export const StatusBar: React.FC<StatusBarProps> = ({
  totalProjects,
  activeSessions,
  loadedProjectsCount,
  markRamState,
  activeModelSize,
  lang,
}) => {
  const t = getT(lang);

  // Estimación de RAM
  const getRamUsageText = () => {
    if (markRamState === "idle" || loadedProjectsCount === 0) {
      return "0 MB";
    }
    if (activeModelSize) {
      const mb = Math.round(activeModelSize / (1024 * 1024));
      return `~${mb} MB`;
    }
    return "~730 MB";
  };

  const getMarkRamLabel = () => {
    switch (markRamState) {
      case "idle":
        return t.statusBar.idle;
      case "weak_awake":
        return t.statusBar.weakAwake;
      case "awake":
        return t.statusBar.awake;
    }
  };

  return (
    <footer className="flex h-7 w-full select-none items-center justify-between border-t border-mocha-surface bg-mocha-base px-3 text-[11px] font-mono text-mocha-subtext0">
      {/* Left counters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="text-mocha-surface2">{t.statusBar.ramUsage}</span>
          <span
            className={`font-semibold ${
              markRamState !== "idle" ? "text-cortex-mint" : "text-mocha-text"
            }`}
          >
            {getRamUsageText()}
          </span>
        </div>

        <span className="text-mocha-surface/80">|</span>

        <div className="flex items-center gap-1">
          <span className="text-mocha-surface2">{t.statusBar.projectsCount}</span>
          <span className="text-mocha-text">{totalProjects}</span>
        </div>

        <span className="text-mocha-surface/80">|</span>

        <div className="flex items-center gap-1">
          <span className="text-mocha-surface2">{t.statusBar.activeSessions}</span>
          <span className={activeSessions > 0 ? "text-cortex-mint font-semibold" : "text-mocha-text"}>
            {activeSessions}
          </span>
        </div>

        <span className="text-mocha-surface/80 hidden sm:inline">|</span>

        <div className="hidden sm:flex items-center gap-1">
          <span className="text-mocha-surface2">{t.statusBar.loadedBackends}</span>
          <span className={loadedProjectsCount > 0 ? "text-mocha-mauve font-semibold" : "text-mocha-text"}>
            {loadedProjectsCount}
          </span>
        </div>
      </div>

      {/* Right live state indicator */}
      <div className="flex items-center gap-2">
        <MarkRam state={markRamState} size="sm" />
        <span
          className={`font-medium ${
            markRamState === "awake"
              ? "text-cortex-mint font-semibold animate-pulse"
              : markRamState === "weak_awake"
              ? "text-mocha-lavender"
              : "text-mocha-surface2"
          }`}
        >
          {getMarkRamLabel()}
        </span>
      </div>
    </footer>
  );
};
