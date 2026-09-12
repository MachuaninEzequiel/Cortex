import React, { useCallback, useEffect, useState } from "react";
import {
  ApplyResult,
  IdeStatus,
  Lang,
  PlannedFile,
  SetupAction,
  SetupTarget,
} from "../types";
import { getT } from "../i18n";
import { tauriInvoke } from "../hooks/useTauri";

interface SetupPanelProps {
  folder: string | null;
  onPickFolder: () => void;
  onOpenAsProject: (path: string) => void;
  lang: Lang;
}

const ACTIONS: SetupAction[] = ["agent", "full", "pipeline", "enterprise", "composed"];

export const SetupPanel: React.FC<SetupPanelProps> = ({
  folder,
  onPickFolder,
  onOpenAsProject,
  lang,
}) => {
  const t = getT(lang).setup;
  const [target, setTarget] = useState<SetupTarget | null>(null);
  const [plan, setPlan] = useState<PlannedFile[] | null>(null);
  const [pending, setPending] = useState<{ action: SetupAction; ide?: string } | null>(null);
  const [preset, setPreset] = useState("small-company");
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [catalog, setCatalog] = useState<IdeStatus[]>([]);

  const inspect = useCallback(async (path: string) => {
    try {
      const snap = await tauriInvoke<SetupTarget>("inspect_setup_target", { path });
      setTarget(snap);
      setError(null);
    } catch (e) {
      setError(String(e));
      setTarget(null);
    }
  }, []);

  useEffect(() => {
    tauriInvoke<IdeStatus[]>("list_ides")
      .then(setCatalog)
      .catch(() => setCatalog([]));
  }, []);

  useEffect(() => {
    if (folder) {
      inspect(folder);
    } else {
      setTarget(null);
    }
    setPlan(null);
    setPending(null);
  }, [folder, inspect]);

  const runPreview = async (action: SetupAction, ide?: string) => {
    if (!folder) return;
    setBusy(true);
    setError(null);
    try {
      const files = await tauriInvoke<PlannedFile[]>("preview_setup", {
        path: folder,
        action,
        ide: ide || null,
        preset: action === "enterprise" ? preset : null,
      });
      setPlan(files);
      setPending({ action, ide });
    } catch (e) {
      setError(String(e));
      setPlan(null);
      setPending(null);
    } finally {
      setBusy(false);
    }
  };

  const runApply = async () => {
    if (!folder || !pending) return;
    setBusy(true);
    setError(null);
    try {
      const result = await tauriInvoke<ApplyResult>("apply_setup", {
        path: folder,
        action: pending.action,
        ide: pending.ide || null,
        preset: pending.action === "enterprise" ? preset : null,
      });
      setLog(result.log.concat(result.files.map((f) => `✓ ${f}`)));
      setPlan(null);
      setPending(null);
      await inspect(folder);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const actionLabel = (a: SetupAction) => {
    switch (a) {
      case "agent":
        return { title: t.agent, desc: t.agentDesc };
      case "full":
        return { title: t.full, desc: t.fullDesc };
      case "pipeline":
        return { title: t.pipeline, desc: t.pipelineDesc };
      case "enterprise":
        return { title: t.enterprise, desc: t.enterpriseDesc };
      case "composed":
        return { title: t.composed, desc: t.composedDesc };
      default:
        return { title: a, desc: "" };
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-mocha-mantle">
      <div className="border-b border-mocha-surface px-5 py-4">
        <h2 className="font-mono text-sm font-bold tracking-wide text-mocha-text">{t.title}</h2>
        <p className="mt-1 max-w-2xl text-xs text-mocha-subtext0">{t.subtitle}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            onClick={onPickFolder}
            className="rounded bg-cortex-forest px-3 py-1.5 font-mono text-xs font-semibold text-cortex-mint hover:bg-cortex-forest/80"
          >
            {folder ? t.changeFolder : t.pickFolder}
          </button>
          <span className="truncate font-mono text-[11px] text-mocha-subtext0">
            {folder || t.noFolder}
          </span>
        </div>
        {target && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Chip ok={target.has_cortex} label={t.hasCortex} />
            <Chip ok={target.has_org_yaml} label={t.hasOrg} />
            <Chip
              ok={target.doctor_healthy === true}
              label={
                target.doctor_healthy === true
                  ? t.doctorOk
                  : target.doctor_healthy === false
                    ? t.doctorWarn
                    : t.doctorNone
              }
            />
            <span className="self-center font-mono text-[10px] text-mocha-surface2">
              {target.has_cortex ? t.statusReady : t.statusEmpty}
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {error && (
          <div className="mb-3 rounded border border-red-900/50 bg-red-950/40 px-3 py-2 font-mono text-xs text-red-300">
            {error}
          </div>
        )}

        {!folder ? (
          <p className="font-mono text-xs text-mocha-surface2">{t.noFolder}</p>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              {ACTIONS.map((action) => {
                const { title, desc } = actionLabel(action);
                return (
                  <div
                    key={action}
                    className="rounded-md border border-mocha-surface bg-mocha-base p-3"
                  >
                    <div className="font-mono text-xs font-semibold text-mocha-text">{title}</div>
                    <p className="mt-1 text-[11px] text-mocha-subtext0">{desc}</p>
                    {action === "enterprise" && (
                      <select
                        value={preset}
                        onChange={(e) => setPreset(e.target.value)}
                        className="mt-2 w-full rounded border border-mocha-surface bg-mocha-mantle px-2 py-1 font-mono text-[11px] text-mocha-text"
                      >
                        <option value="small-company">small-company</option>
                        <option value="multi-project-team">multi-project-team</option>
                        <option value="regulated-organization">regulated-organization</option>
                      </select>
                    )}
                    <button
                      disabled={busy}
                      onClick={() => runPreview(action)}
                      className="mt-2 rounded bg-mocha-surface px-2 py-1 font-mono text-[11px] text-mocha-lavender hover:bg-mocha-surface disabled:opacity-50"
                    >
                      {t.preview}
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="mt-4">
              <h3 className="mb-2 font-mono text-xs font-bold text-mocha-subtext0">{t.ides}</h3>
              <div className="space-y-1">
                {(target?.ides.length ? target.ides : catalog).map((ide) => (
                  <div
                    key={ide.name}
                    className="flex items-center justify-between rounded border border-mocha-surface bg-mocha-base px-3 py-2"
                  >
                    <div>
                      <div className="font-mono text-xs text-mocha-text">{ide.display_name}</div>
                      <div className="font-mono text-[10px] text-mocha-surface2">
                        {ide.name} · {ide.tier}
                        {ide.injected ? " · on" : ""}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        disabled={busy}
                        onClick={() => runPreview("ide", ide.name)}
                        className="rounded bg-mocha-surface px-2 py-1 font-mono text-[11px] text-mocha-lavender hover:bg-mocha-surface2 disabled:opacity-50"
                      >
                        {t.preview}
                      </button>
                      <button
                        disabled={busy}
                        onClick={() => runPreview("ide_remove", ide.name)}
                        className="rounded bg-mocha-surface px-2 py-1 font-mono text-[11px] text-mocha-red hover:bg-mocha-surface2 disabled:opacity-50"
                      >
                        {t.removeIde}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {plan && pending && (
              <div className="mt-4 rounded-md border border-mocha-mauve/40 bg-mocha-base p-3">
                <div className="mb-2 font-mono text-xs font-semibold text-mocha-mauve">
                  {t.preview} · {pending.action}
                  {pending.ide ? ` / ${pending.ide}` : ""}
                </div>
                <ul className="max-h-40 overflow-y-auto font-mono text-[11px] text-mocha-subtext0">
                  {plan.map((f) => (
                    <li key={f.path}>
                      <span className="text-mocha-green">
                        {f.op === "update" ? t.update : t.create}
                      </span>{" "}
                      {f.path}
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex gap-2">
                  <button
                    disabled={busy}
                    onClick={runApply}
                    className="rounded bg-cortex-forest px-3 py-1.5 font-mono text-xs font-bold text-cortex-mint disabled:opacity-50"
                  >
                    {busy ? t.applying : t.apply}
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => {
                      setPlan(null);
                      setPending(null);
                    }}
                    className="rounded bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text"
                  >
                    {t.cancel}
                  </button>
                </div>
              </div>
            )}

            {log.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-1 font-mono text-[10px] uppercase text-mocha-surface2">
                  {t.logTitle}
                </h3>
                <pre className="max-h-32 overflow-auto rounded bg-mocha-crust p-2 font-mono text-[11px] text-mocha-subtext0">
                  {log.join("\n")}
                </pre>
              </div>
            )}

            <button
              onClick={() => folder && onOpenAsProject(folder)}
              className="mt-5 rounded border border-mocha-mauve/40 px-3 py-2 font-mono text-xs text-mocha-mauve hover:bg-mocha-surface"
            >
              {t.openProject}
            </button>
          </>
        )}
      </div>
    </div>
  );
};

const Chip: React.FC<{ ok: boolean; label: string }> = ({ ok, label }) => (
  <span
    className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${
      ok ? "bg-cortex-forest/40 text-cortex-mint" : "bg-mocha-surface text-mocha-surface2"
    }`}
  >
    {label}
  </span>
);
