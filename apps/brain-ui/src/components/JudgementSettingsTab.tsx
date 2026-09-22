import React, { useEffect, useState } from "react";
import { Lang, JudgementSettingsPayload } from "../types";
import { getT } from "../i18n";
import { tauriInvoke } from "../hooks/useTauri";

interface Props {
  projectPath: string | null;
  lang: Lang;
}

export const JudgementSettingsTab: React.FC<Props> = ({ projectPath, lang }) => {
  const t = getT(lang);
  const [data, setData] = useState<JudgementSettingsPayload | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [squeeze, setSqueeze] = useState(false);
  const [promotion, setPromotion] = useState(false);
  const [contextPack, setContextPack] = useState(false);
  const [utterance, setUtterance] = useState(false);
  const [sessionCompact, setSessionCompact] = useState(false);
  const [modelRouting, setModelRouting] = useState(false);

  // Model router roles
  const [designerModel, setDesignerModel] = useState<string>("");
  const [implementerModel, setImplementerModel] = useState<string>("");
  const [documenterModel, setDocumenterModel] = useState<string>("");
  const [auditorModel, setAuditorModel] = useState<string>("");

  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    const payload = await tauriInvoke<JudgementSettingsPayload>("get_judgement_settings", {
      project: projectPath || "",
    });
    setData(payload);
    setEnabled(payload.enabled);
    setSqueeze(payload.search_squeeze);
    setPromotion(payload.promotion);
    setContextPack(payload.context_pack);
    setUtterance(payload.utterance);
    setSessionCompact(payload.session_compact);
    setModelRouting(payload.model_routing);

    setDesignerModel(payload.designer_model || "");
    setImplementerModel(payload.implementer_model || "");
    setDocumenterModel(payload.documenter_model || "");
    setAuditorModel(payload.auditor_model || "");

    setApiKey("");
  };

  useEffect(() => {
    load().catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectPath]);

  const save = async (clearKey = false) => {
    if (!projectPath) {
      setErr(t.settings.judgementNeedProject);
      return;
    }
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const payload = await tauriInvoke<JudgementSettingsPayload>("save_judgement_settings", {
        project: projectPath,
        enabled,
        searchSqueeze: squeeze,
        promotion,
        contextPack,
        utterance,
        sessionCompact,
        modelRouting,
        designerModel: designerModel.trim() ? designerModel : null,
        implementerModel: implementerModel.trim() ? implementerModel : null,
        documenterModel: documenterModel.trim() ? documenterModel : null,
        auditorModel: auditorModel.trim() ? auditorModel : null,
        apiKey: clearKey ? "" : apiKey.trim() ? apiKey : null,
      });
      setData(payload);
      setEnabled(payload.enabled);
      setSqueeze(payload.search_squeeze);
      setPromotion(payload.promotion);
      setContextPack(payload.context_pack);
      setUtterance(payload.utterance);
      setSessionCompact(payload.session_compact);
      setModelRouting(payload.model_routing);

      setDesignerModel(payload.designer_model || "");
      setImplementerModel(payload.implementer_model || "");
      setDocumenterModel(payload.documenter_model || "");
      setAuditorModel(payload.auditor_model || "");

      setApiKey("");
      setMsg(t.settings.judgementSaved);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!projectPath) {
    return (
      <p className="text-xs text-mocha-subtext0 font-sans">{t.settings.judgementNeedProject}</p>
    );
  }

  const availableModels = data?.available_models || [];

  return (
    <div className="space-y-4 font-sans max-h-[460px] overflow-y-auto pr-1">
      <div>
        <div className="flex items-center justify-between">
          <h4 className="font-semibold font-mono text-mocha-mauve text-xs mb-1">
            {t.settings.judgementTitle}
          </h4>
          {data?.detected_host && (
            <span className="rounded bg-mocha-surface px-2 py-0.5 font-mono text-[10px] text-mocha-text border border-mocha-mauve/30">
              {data.detected_host}
            </span>
          )}
        </div>
        <p className="text-[11px] text-mocha-subtext0 mb-2">{t.settings.judgementDesc}</p>

        {data?.host_policy && (
          <div className="rounded border border-mocha-surface bg-mocha-surface/10 px-3 py-1.5 font-mono text-[10px] text-mocha-subtext0 mb-2 flex items-center gap-2">
            <span className="text-mocha-mauve font-bold">🛡️ {t.settings.hostPolicy}</span>
            <span className="text-mocha-text">{data.host_policy}</span>
          </div>
        )}

        <div className="rounded border border-mocha-surface bg-mocha-surface/20 px-3 py-2 font-mono text-[11px] text-mocha-subtext0">
          {t.settings.judgementStatus}:{" "}
          <span className="text-mocha-text font-bold">{data?.status ?? "—"}</span>
          {data?.model ? ` · ${data.model}` : ""}
        </div>
      </div>

      <label className="flex items-center gap-2.5 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4 accent-mocha-mauve"
        />
        <span className="font-semibold text-mocha-text">{t.settings.judgementEnable}</span>
      </label>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={squeeze}
            onChange={(e) => setSqueeze(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px]">{t.settings.judgementSqueeze}</span>
        </label>

        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={promotion}
            onChange={(e) => setPromotion(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px]">{t.settings.judgementPromote}</span>
        </label>

        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={contextPack}
            onChange={(e) => setContextPack(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px]">{t.settings.judgementPack}</span>
        </label>

        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={utterance}
            onChange={(e) => setUtterance(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px]">{t.settings.judgementUtterance}</span>
        </label>

        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={sessionCompact}
            onChange={(e) => setSessionCompact(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px]">{t.settings.judgementSessionCompact}</span>
        </label>

        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={modelRouting}
            onChange={(e) => setModelRouting(e.target.checked)}
            disabled={!enabled}
            className="mt-0.5 h-4 w-4 accent-mocha-mauve"
          />
          <span className="text-mocha-text text-[11px] font-semibold text-mocha-mauve">
            {t.settings.judgementModelRouting}
          </span>
        </label>
      </div>

      {/* Model Router Section */}
      {modelRouting && (
        <div className="rounded-lg border border-mocha-mauve/40 bg-mocha-surface/20 p-3 space-y-3">
          <div>
            <h5 className="font-semibold font-mono text-mocha-text text-xs">
              🧭 {t.settings.routerSectionTitle}
            </h5>
            <p className="text-[10px] text-mocha-subtext0">{t.settings.routerSectionDesc}</p>
          </div>

          <div className="space-y-2.5">
            {/* Architect / Designer */}
            <div>
              <div className="flex justify-between items-center mb-0.5">
                <label className="text-[11px] font-bold text-mocha-text">
                  📐 {t.settings.roleDesigner}
                </label>
              </div>
              <p className="text-[10px] text-mocha-subtext0 mb-1">{t.settings.roleDesignerDesc}</p>
              <select
                value={designerModel}
                onChange={(e) => setDesignerModel(e.target.value)}
                disabled={!enabled}
                className="w-full rounded border border-mocha-surface bg-mocha-surface/70 px-2 py-1 font-mono text-[11px] text-mocha-text focus:border-mocha-mauve focus:outline-none"
              >
                <option value="">{t.settings.defaultModelPlaceholder}</option>
                {availableModels.map((m) => (
                  <option key={m.canonical_id} value={m.canonical_id}>
                    {m.canonical_id} {m.display_name && m.display_name !== m.model_id ? `(${m.display_name})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Implementer */}
            <div>
              <div className="flex justify-between items-center mb-0.5">
                <label className="text-[11px] font-bold text-mocha-text">
                  💻 {t.settings.roleImplementer}
                </label>
              </div>
              <p className="text-[10px] text-mocha-subtext0 mb-1">{t.settings.roleImplementerDesc}</p>
              <select
                value={implementerModel}
                onChange={(e) => setImplementerModel(e.target.value)}
                disabled={!enabled}
                className="w-full rounded border border-mocha-surface bg-mocha-surface/70 px-2 py-1 font-mono text-[11px] text-mocha-text focus:border-mocha-mauve focus:outline-none"
              >
                <option value="">{t.settings.defaultModelPlaceholder}</option>
                {availableModels.map((m) => (
                  <option key={m.canonical_id} value={m.canonical_id}>
                    {m.canonical_id} {m.display_name && m.display_name !== m.model_id ? `(${m.display_name})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Documenter */}
            <div>
              <div className="flex justify-between items-center mb-0.5">
                <label className="text-[11px] font-bold text-mocha-text">
                  📝 {t.settings.roleDocumenter}
                </label>
              </div>
              <p className="text-[10px] text-mocha-subtext0 mb-1">{t.settings.roleDocumenterDesc}</p>
              <select
                value={documenterModel}
                onChange={(e) => setDocumenterModel(e.target.value)}
                disabled={!enabled}
                className="w-full rounded border border-mocha-surface bg-mocha-surface/70 px-2 py-1 font-mono text-[11px] text-mocha-text focus:border-mocha-mauve focus:outline-none"
              >
                <option value="">{t.settings.defaultModelPlaceholder}</option>
                {availableModels.map((m) => (
                  <option key={m.canonical_id} value={m.canonical_id}>
                    {m.canonical_id} {m.display_name && m.display_name !== m.model_id ? `(${m.display_name})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Auditor */}
            <div>
              <div className="flex justify-between items-center mb-0.5">
                <label className="text-[11px] font-bold text-mocha-text">
                  🔍 {t.settings.roleAuditor}
                </label>
              </div>
              <p className="text-[10px] text-mocha-subtext0 mb-1">{t.settings.roleAuditorDesc}</p>
              <select
                value={auditorModel}
                onChange={(e) => setAuditorModel(e.target.value)}
                disabled={!enabled}
                className="w-full rounded border border-mocha-surface bg-mocha-surface/70 px-2 py-1 font-mono text-[11px] text-mocha-text focus:border-mocha-mauve focus:outline-none"
              >
                <option value="">{t.settings.defaultModelPlaceholder}</option>
                {availableModels.map((m) => (
                  <option key={m.canonical_id} value={m.canonical_id}>
                    {m.canonical_id} {m.display_name && m.display_name !== m.model_id ? `(${m.display_name})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      <div>
        <label className="block font-semibold text-mocha-text mb-1">{t.settings.judgementKey}</label>
        {data?.key_configured && (
          <p className="text-[11px] text-cortex-mint font-mono mb-1">{t.settings.judgementKeySet}</p>
        )}
        <input
          type="password"
          autoComplete="off"
          placeholder={t.settings.judgementKeyPh}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="w-full rounded border border-mocha-surface bg-mocha-surface/60 px-3 py-1.5 font-mono text-xs text-mocha-text focus:border-mocha-mauve focus:outline-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => save(false)}
          disabled={busy}
          className="rounded bg-mocha-mauve px-3 py-1.5 font-mono text-xs font-bold text-mocha-base hover:opacity-90 disabled:opacity-40"
        >
          {t.settings.judgementSave}
        </button>
        {data?.key_configured && (
          <button
            onClick={() => save(true)}
            disabled={busy}
            className="rounded bg-mocha-surface px-3 py-1.5 font-mono text-xs text-mocha-text hover:bg-mocha-surface2 disabled:opacity-40"
          >
            {t.settings.judgementKeyClear}
          </button>
        )}
      </div>

      {msg && <p className="text-[11px] text-cortex-mint font-mono">{msg}</p>}
      {err && <p className="text-[11px] text-red-300 font-mono">{err}</p>}
    </div>
  );
};
