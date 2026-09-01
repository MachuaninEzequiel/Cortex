import React from "react";
import { ModelEntry, MarkRamState } from "../types";
import { MarkRam } from "./MarkRam";
import { getT } from "../i18n";

interface TopBarProps {
  models: ModelEntry[];
  selectedModel: string;
  onSelectModel: (filename: string) => void;
  markRamState: MarkRamState;
  onOpenSettings: () => void;
  onOpenWebGraph?: () => void;
  lang: "es" | "en";
}

export const TopBar: React.FC<TopBarProps> = ({
  models,
  selectedModel,
  onSelectModel,
  markRamState,
  onOpenSettings,
  onOpenWebGraph,
  lang,
}) => {
  const t = getT(lang);

  return (
    <header className="flex h-12 w-full select-none items-center justify-between border-b border-mocha-surface bg-mocha-base px-4">
      {/* Brand / Logo */}
      <div className="flex items-center gap-3">
        <MarkRam state={markRamState} size="md" />
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-sm font-bold tracking-wider text-mocha-text">
            CORTEX <span className="text-mocha-mauve">BRAIN</span>
          </span>
          <span className="rounded bg-mocha-surface px-1.5 py-0.5 text-[10px] font-mono text-cortex-mint">
            v1.0
          </span>
        </div>
      </div>

      {/* Model Selector & Actions */}
      <div className="flex items-center gap-3">
        {/* Quick WebGraph trigger */}
        {onOpenWebGraph && (
          <button
            onClick={onOpenWebGraph}
            className="flex items-center gap-1.5 rounded border border-mocha-surface bg-mocha-surface/60 px-2.5 py-1 text-xs font-mono text-mocha-text transition hover:border-mocha-mauve hover:text-mocha-mauve active:scale-95"
            title="Abrir Grafo de Conocimiento (WebGraph)"
          >
            <span>🕸️</span>
            <span className="hidden sm:inline font-semibold">WebGraph</span>
          </button>
        )}

        <div className="flex items-center gap-2">
          <label
            htmlFor="model-select"
            className="text-xs font-mono text-mocha-subtext0 hidden sm:inline"
          >
            {t.topBar.model}
          </label>
          <div className="relative">
            <select
              id="model-select"
              value={selectedModel}
              onChange={(e) => onSelectModel(e.target.value)}
              className="h-7 rounded border border-mocha-surface bg-mocha-surface/80 px-2.5 pr-7 text-xs font-mono text-mocha-text shadow-sm transition hover:border-mocha-surface2 focus:border-mocha-mauve focus:outline-none"
            >
              {models.length === 0 ? (
                <option value="LFM2.5-1.2B-Instruct-Q4_K_M.gguf">
                  LFM2.5-1.2B-Instruct-Q4_K_M.gguf
                </option>
              ) : (
                models.map((m) => (
                  <option key={m.filename} value={m.filename}>
                    {m.name} {!m.exists ? " (no descargado)" : ""}
                  </option>
                ))
              )}
            </select>
            <div className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-mocha-subtext0">
              ▼
            </div>
          </div>
        </div>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="flex h-7 w-7 items-center justify-center rounded border border-mocha-surface bg-mocha-surface/60 text-mocha-subtext0 transition hover:border-mocha-mauve hover:bg-mocha-surface hover:text-mocha-text active:scale-95"
          title={t.topBar.settings}
          aria-label={t.topBar.settings}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.8}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>
    </header>
  );
};
