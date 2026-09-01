import React from "react";
import { ProjectEntry } from "../types";
import { getT } from "../i18n";

interface SidebarProps {
  projects: ProjectEntry[];
  selectedProject: string | null;
  onSelectProject: (path: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  lang: "es" | "en";
}

export const Sidebar: React.FC<SidebarProps> = ({
  projects,
  selectedProject,
  onSelectProject,
  onRefresh,
  isRefreshing,
  lang,
}) => {
  const t = getT(lang);

  // Helper para extraer nombre del directorio del path
  const getProjectName = (path: string) => {
    const parts = path.split("/").filter(Boolean);
    return parts[parts.length - 1] || path;
  };

  return (
    <aside className="flex h-full w-64 flex-shrink-0 flex-col border-r border-mocha-surface bg-mocha-base select-none">
      {/* Sidebar Header */}
      <div className="flex h-11 items-center justify-between border-b border-mocha-surface/60 px-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-wider text-mocha-subtext0 font-mono">
            {t.sidebar.title}
          </span>
          <span className="rounded-full bg-mocha-surface px-1.5 py-0.2 text-[10px] font-mono text-mocha-text">
            {projects.length}
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1 rounded px-2 py-0.5 text-xs font-mono text-mocha-subtext0 transition hover:bg-mocha-surface hover:text-mocha-mauve disabled:opacity-50"
          title={t.sidebar.refresh}
        >
          <svg
            className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-mocha-mauve" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span className="text-[11px]">{isRefreshing ? t.sidebar.refreshing : t.sidebar.refresh}</span>
        </button>
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center p-4 text-center">
            <p className="text-xs text-mocha-surface2 font-mono">
              {isRefreshing ? t.sidebar.refreshing : t.sidebar.noProjects}
            </p>
          </div>
        ) : (
          projects.map((proj) => {
            const isSelected = selectedProject === proj.path;
            const name = getProjectName(proj.path);

            return (
              <button
                key={proj.path}
                onClick={() => onSelectProject(proj.path)}
                className={`group flex w-full flex-col rounded-md p-2 text-left transition ${
                  isSelected
                    ? "bg-mocha-surface text-mocha-text shadow-sm ring-1 ring-mocha-mauve/40"
                    : "text-mocha-subtext0 hover:bg-mocha-surface/40 hover:text-mocha-text"
                }`}
              >
                <div className="flex items-center justify-between gap-1 w-full">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className={`text-xs ${
                        isSelected ? "text-mocha-mauve" : "text-mocha-surface2 group-hover:text-mocha-mauve"
                      }`}
                    >
                      ▸
                    </span>
                    <span className="truncate text-xs font-semibold font-mono tracking-tight text-mocha-text">
                      {name}
                    </span>
                  </div>

                  {/* Badges */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {proj.has_session && (
                      <span
                        className="flex h-2 w-2 rounded-full bg-cortex-mint"
                        title={t.sidebar.activeSession}
                      />
                    )}
                    {!proj.valid_config && (
                      <span
                        className="rounded bg-red-900/40 px-1 py-0.2 text-[9px] font-mono text-red-300"
                        title={t.sidebar.invalidConfig}
                      >
                        !config
                      </span>
                    )}
                  </div>
                </div>

                {/* Subtitle with branch & path */}
                <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-mocha-surface2">
                  <span className="truncate max-w-[130px]" title={proj.path}>
                    {proj.path.replace(/^.*\/([^/]+\/[^/]+)$/, "$1")}
                  </span>
                  {proj.branch ? (
                    <span className="truncate max-w-[80px] text-mocha-lavender/80" title={proj.branch}>
                      {proj.branch}
                    </span>
                  ) : (
                    <span className="text-mocha-surface2/60">{t.sidebar.noBranch}</span>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
};
