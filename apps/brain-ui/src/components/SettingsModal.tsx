import React, { useEffect, useState } from "react";
import { ModelEntry, Lang, DownloadProgressPayload } from "../types";
import { getT } from "../i18n";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: ModelEntry[];
  selectedModel: string;
  onSelectModel: (filename: string) => void;
  onDownloadModel: (url?: string) => void;
  isDownloading: boolean;
  downloadProgress: DownloadProgressPayload | null;
  detectedCount: number;
  lastScanTimestamp: number;
  onScanNow: () => void;
  isScanning: boolean;
  idleTimeout: number;
  onSetIdleTimeout: (sec: number) => void;
  lang: Lang;
  onSetLang: (lang: Lang) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  models,
  selectedModel,
  onSelectModel,
  onDownloadModel,
  isDownloading,
  downloadProgress,
  detectedCount,
  lastScanTimestamp,
  onScanNow,
  isScanning,
  idleTimeout,
  onSetIdleTimeout,
  lang,
  onSetLang,
}) => {
  const [activeTab, setActiveTab] = useState<"model" | "paths" | "general" | "about">("model");
  const t = getT(lang);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const activeModelObj = models.find((m) => m.filename === selectedModel) || models[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="flex h-[520px] w-[640px] flex-col rounded-xl border border-mocha-surface bg-mocha-base shadow-2xl overflow-hidden font-sans">
        {/* Modal Header */}
        <div className="flex h-12 items-center justify-between border-b border-mocha-surface px-5 bg-mocha-base">
          <div className="flex items-center gap-2">
            <span className="text-mocha-mauve font-mono text-base font-bold">⚙</span>
            <h2 className="text-sm font-semibold text-mocha-text font-mono">
              {t.settings.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded text-mocha-subtext0 hover:bg-mocha-surface hover:text-mocha-text transition"
            title={t.settings.close}
          >
            ✕
          </button>
        </div>

        {/* Modal Body: Tabs Sidebar + Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Tabs Navigation */}
          <div className="w-44 border-r border-mocha-surface bg-mocha-base/50 p-2 space-y-1 select-none font-mono text-xs">
            <button
              onClick={() => setActiveTab("model")}
              className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left transition ${
                activeTab === "model"
                  ? "bg-mocha-surface text-mocha-mauve font-semibold"
                  : "text-mocha-subtext0 hover:bg-mocha-surface/50 hover:text-mocha-text"
              }`}
            >
              <span>🧠</span> {t.settings.modelTab}
            </button>

            <button
              onClick={() => setActiveTab("paths")}
              className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left transition ${
                activeTab === "paths"
                  ? "bg-mocha-surface text-mocha-mauve font-semibold"
                  : "text-mocha-subtext0 hover:bg-mocha-surface/50 hover:text-mocha-text"
              }`}
            >
              <span>📁</span> {t.settings.pathsTab}
            </button>

            <button
              onClick={() => setActiveTab("general")}
              className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left transition ${
                activeTab === "general"
                  ? "bg-mocha-surface text-mocha-mauve font-semibold"
                  : "text-mocha-subtext0 hover:bg-mocha-surface/50 hover:text-mocha-text"
              }`}
            >
              <span>⚡</span> {t.settings.generalTab}
            </button>

            <button
              onClick={() => setActiveTab("about")}
              className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left transition ${
                activeTab === "about"
                  ? "bg-mocha-surface text-mocha-mauve font-semibold"
                  : "text-mocha-subtext0 hover:bg-mocha-surface/50 hover:text-mocha-text"
              }`}
            >
              <span>ℹ</span> {t.settings.aboutTab}
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-5 text-xs text-mocha-text">
            {activeTab === "model" && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold font-mono text-mocha-subtext0 mb-1">
                    {t.settings.activeModel}
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => onSelectModel(e.target.value)}
                    disabled={isDownloading}
                    className="w-full rounded border border-mocha-surface bg-mocha-surface/60 p-2 text-xs font-mono text-mocha-text focus:border-mocha-mauve focus:outline-none disabled:opacity-50"
                  >
                    {models.map((m) => (
                      <option key={m.filename} value={m.filename}>
                        {m.name} {!m.exists ? " (no descargado)" : ""}
                      </option>
                    ))}
                  </select>
                </div>

                {activeModelObj && (
                  <div className="rounded-lg border border-mocha-surface bg-mocha-surface/20 p-3 space-y-2 font-mono">
                    <div className="flex justify-between">
                      <span className="text-mocha-surface2">{t.settings.modelFile}</span>
                      <span className="text-mocha-text">{activeModelObj.filename}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-mocha-surface2">{t.settings.modelStatus}</span>
                      <span className={activeModelObj.exists ? "text-cortex-mint font-bold" : "text-mocha-mauve"}>
                        {activeModelObj.exists ? t.settings.installed : t.settings.notInstalled}
                      </span>
                    </div>
                    {activeModelObj.size_bytes && (
                      <div className="flex justify-between">
                        <span className="text-mocha-surface2">Tamaño:</span>
                        <span className="text-mocha-text">
                          {(activeModelObj.size_bytes / (1024 * 1024)).toFixed(1)} MB
                        </span>
                      </div>
                    )}
                    <div className="text-[10px] text-mocha-surface2 truncate pt-1 border-t border-mocha-surface/40" title={activeModelObj.path}>
                      {t.settings.modelPath} {activeModelObj.path}
                    </div>
                  </div>
                )}

                {/* Download / Re-download Section */}
                <div className="pt-2 border-t border-mocha-surface/40">
                  {isDownloading ? (
                    <div className="space-y-2 rounded-lg border border-mocha-mauve/40 bg-mocha-surface/30 p-3">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="flex items-center gap-2 text-mocha-mauve font-semibold">
                          <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-mocha-mauve border-t-transparent" />
                          {t.settings.downloading}
                        </span>
                        <span className="text-mocha-text font-bold">
                          {downloadProgress?.percentage !== undefined
                            ? `${downloadProgress.percentage.toFixed(1)}%`
                            : "0%"}
                        </span>
                      </div>

                      {/* Progress Bar */}
                      <div className="h-2 w-full overflow-hidden rounded-full bg-mocha-base">
                        <div
                          className="h-full bg-cortex-mint transition-all duration-300"
                          style={{
                            width: `${Math.min(100, Math.max(5, downloadProgress?.percentage || 5))}%`,
                          }}
                        />
                      </div>

                      <div className="flex justify-between text-[10px] font-mono text-mocha-subtext0">
                        <span>
                          {downloadProgress
                            ? `${(downloadProgress.bytes_done / (1024 * 1024)).toFixed(1)} MB`
                            : "0 MB"}
                          {downloadProgress?.bytes_total
                            ? ` / ${(downloadProgress.bytes_total / (1024 * 1024)).toFixed(1)} MB`
                            : " / ~730 MB"}
                        </span>
                        <span className="text-mocha-surface2">HuggingFace (LiquidAI/LFM2.5)</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={() => onDownloadModel()}
                        className="flex items-center justify-center gap-2 rounded bg-cortex-forest px-4 py-2 font-mono text-xs font-semibold text-cortex-mint shadow transition hover:bg-cortex-forest/80 active:scale-95"
                      >
                        <span>⬇</span>
                        <span>
                          {activeModelObj?.exists
                            ? t.settings.redownloadModel
                            : t.settings.downloadModel}
                        </span>
                      </button>

                      {downloadProgress?.status === "done" && (
                        <div className="rounded bg-cortex-forest/40 p-2 font-mono text-[11px] text-cortex-mint">
                          ✓ {t.settings.downloadSuccess}
                        </div>
                      )}

                      {downloadProgress?.status === "error" && (
                        <div className="rounded bg-red-900/40 p-2 font-mono text-[11px] text-red-300">
                          ✗ {t.settings.downloadError} {downloadProgress.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "paths" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-mocha-text">{t.settings.detectedProjects}</div>
                    <div className="text-xs text-mocha-subtext0">{detectedCount} encontrados en $HOME</div>
                  </div>
                  <button
                    onClick={onScanNow}
                    disabled={isScanning}
                    className="rounded bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-surface2 hover:text-mocha-mauve transition disabled:opacity-50"
                  >
                    {isScanning ? "..." : t.settings.scanNow}
                  </button>
                </div>

                <div className="rounded-lg border border-mocha-surface bg-mocha-surface/20 p-3 font-mono text-xs space-y-1">
                  <div className="text-mocha-surface2">
                    {t.settings.lastScan} {lastScanTimestamp ? new Date(lastScanTimestamp * 1000).toLocaleString() : "—"}
                  </div>
                  <div className="text-mocha-surface2">
                    Caché: <span className="text-mocha-subtext0">~/.cache/cortex/brain-projects.json</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "general" && (
              <div className="space-y-5">
                <div>
                  <label className="block font-semibold text-mocha-text mb-1">
                    {t.settings.idleTimeout}
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="number"
                      min={10}
                      max={600}
                      step={10}
                      value={idleTimeout}
                      onChange={(e) => onSetIdleTimeout(Number(e.target.value) || 90)}
                      className="w-24 rounded border border-mocha-surface bg-mocha-surface/60 p-2 font-mono text-xs text-mocha-text focus:border-mocha-mauve focus:outline-none"
                    />
                    <span className="text-xs text-mocha-surface2">segundos (default: 90s)</span>
                  </div>
                  <p className="mt-1 text-[11px] text-mocha-subtext0">
                    {t.settings.idleTimeoutDesc}
                  </p>
                </div>

                <div>
                  <label className="block font-semibold text-mocha-text mb-1">
                    {t.settings.language}
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onSetLang("es")}
                      className={`rounded px-3 py-1.5 font-mono text-xs transition ${
                        lang === "es"
                          ? "bg-mocha-mauve text-mocha-base font-bold"
                          : "bg-mocha-surface text-mocha-text hover:bg-mocha-surface2"
                      }`}
                    >
                      Español (ES)
                    </button>
                    <button
                      onClick={() => onSetLang("en")}
                      className={`rounded px-3 py-1.5 font-mono text-xs transition ${
                        lang === "en"
                          ? "bg-mocha-mauve text-mocha-base font-bold"
                          : "bg-mocha-surface text-mocha-text hover:bg-mocha-surface2"
                      }`}
                    >
                      English (EN)
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-mocha-text mb-1">
                    {t.settings.theme}
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="h-4 w-4 rounded-full bg-mocha-base border border-mocha-mauve" />
                    <span className="font-mono text-xs text-mocha-subtext0">{t.settings.themeDesc}</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "about" && (
              <div className="space-y-3 font-sans">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">🧠</div>
                  <div>
                    <h3 className="font-bold text-mocha-text font-mono text-sm">Cortex Brain App</h3>
                    <p className="text-xs text-mocha-subtext0">Obra 20 — Experto local standalone con Liquid LFM2.5</p>
                  </div>
                </div>

                <div className="rounded-lg border border-mocha-surface bg-mocha-surface/20 p-3 space-y-1.5 font-mono text-xs text-mocha-subtext0">
                  <div>{t.settings.version}: 0.1.0 (G-A8)</div>
                  <div>Arquitectura: Tauri 2 + Rust + React + Vite + Tailwind</div>
                  <div>Motor: Liquid LFM2.5 (GGUF Q4_K_M) + Protocolo TOOL + HttpSource</div>
                  <div>Design System: Catppuccin Mocha + Voxel Mint</div>
                </div>

                <div className="pt-2 text-xs text-mocha-surface2">
                  Spec de referencia: <span className="text-mocha-mauve">docs/transformacion/20-CORTEX-BRAIN-APP.md</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex h-11 items-center justify-end border-t border-mocha-surface bg-mocha-base px-4">
          <button
            onClick={onClose}
            className="rounded bg-mocha-surface px-4 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-mauve hover:text-mocha-base transition"
          >
            {t.settings.close}
          </button>
        </div>
      </div>
    </div>
  );
};
