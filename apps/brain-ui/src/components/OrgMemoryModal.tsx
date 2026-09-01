import React, { useState, useMemo, useEffect } from "react";
import { OrgKnowledgeItem, OrgMemoryPayload, Lang, PinnedContextNode } from "../types";

interface OrgMemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  memoryData: OrgMemoryPayload | null;
  isLoading: boolean;
  onApprove: (relPath: string, reviewer: string, reason: string) => Promise<void>;
  onReject: (relPath: string, reviewer: string, reason: string) => Promise<void>;
  onPinNode: (node: PinnedContextNode) => void;
  lang: Lang;
}

export const OrgMemoryModal: React.FC<OrgMemoryModalProps> = ({
  isOpen,
  onClose,
  memoryData,
  isLoading,
  onApprove,
  onReject,
  onPinNode,
  lang: _lang,
}) => {
  const [activeTab, setActiveTab] = useState<"candidates" | "promoted">("candidates");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Estado para acción de revisión en progreso
  const [selectedItem, setSelectedItem] = useState<OrgKnowledgeItem | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | null>(null);
  const [reviewerName, setReviewerName] = useState<string>("tech-lead");
  const [decisionReason, setDecisionReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        if (selectedItem) {
          setSelectedItem(null);
          setActionType(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedItem, onClose]);

  const items = useMemo(() => memoryData?.items || [], [memoryData]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchesTab = activeTab === "candidates" ? !item.is_promoted : item.is_promoted;
      const matchesType = filterType === "all" || item.doc_type === filterType;
      const matchesPriority = filterPriority === "all" || item.priority === filterPriority;
      const matchesSearch =
        searchTerm.trim() === "" ||
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.rel_path.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesTab && matchesType && matchesPriority && matchesSearch;
    });
  }, [items, activeTab, filterType, filterPriority, searchTerm]);

  const candidatesCount = useMemo(() => items.filter((i) => !i.is_promoted && i.status !== "rejected").length, [items]);
  const promotedCount = useMemo(() => items.filter((i) => i.is_promoted).length, [items]);

  const handleConfirmAction = async () => {
    if (!selectedItem || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === "approve") {
        await onApprove(
          selectedItem.rel_path,
          reviewerName.trim() || "tech-lead",
          decisionReason.trim() || "Aprobado para adopción organizacional"
        );
      } else {
        await onReject(
          selectedItem.rel_path,
          reviewerName.trim() || "tech-lead",
          decisionReason.trim() || "Rechazado en revisión"
        );
      }
      setSelectedItem(null);
      setActionType(null);
      setDecisionReason("");
    } catch (e) {
      console.error("Error al procesar decisión de memoria organizacional:", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDocTypeBadgeColor = (type: string) => {
    switch (type) {
      case "adr":
        return "bg-[#fab387]/20 text-[#fab387] border-[#fab387]/40";
      case "spec":
        return "bg-[#a6e3a1]/20 text-[#a6e3a1] border-[#a6e3a1]/40";
      case "guide":
        return "bg-[#89b4fa]/20 text-[#89b4fa] border-[#89b4fa]/40";
      case "rfc":
        return "bg-[#cba6f7]/20 text-[#cba6f7] border-[#cba6f7]/40";
      default:
        return "bg-[#bac2de]/20 text-[#bac2de] border-[#bac2de]/40";
    }
  };

  const getPriorityBadgeColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-[#f38ba8]/20 text-[#f38ba8] border-[#f38ba8]/40";
      case "medium":
        return "bg-[#f9e2af]/20 text-[#f9e2af] border-[#f9e2af]/40";
      default:
        return "bg-[#89dceb]/20 text-[#89dceb] border-[#89dceb]/40";
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center select-none"
      style={{ backgroundColor: "rgba(0, 0, 0, 0.75)" }}
    >
      <div
        className="flex flex-col rounded-xl border border-[#313244] shadow-2xl overflow-hidden font-sans"
        style={{
          width: "980px",
          maxWidth: "95vw",
          height: "640px",
          maxHeight: "92vh",
          backgroundColor: "#1e1e2e",
          color: "#cdd6f4",
        }}
      >
        {/* Header */}
        <div className="h-12 border-b border-[#313244] bg-[#181825] px-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">🏛️</span>
            <div>
              <h3 className="font-bold text-[#cdd6f4] font-mono text-sm">
                Memoria Organizacional (Enterprise Knowledge Vault)
              </h3>
              <p className="text-[10px] text-[#a6adc8] font-mono">
                {memoryData?.enterprise_vault_path || "Vault Corporativo Compartido"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[#a6adc8] hover:bg-[#313244] hover:text-[#cdd6f4] transition"
          >
            ✕
          </button>
        </div>

        {/* Tabs & Filters Bar */}
        <div className="h-11 border-b border-[#313244] bg-[#11111b] px-4 flex items-center justify-between font-mono text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("candidates")}
              className={`px-3 py-1 rounded-md font-semibold transition ${
                activeTab === "candidates"
                  ? "bg-[#cba6f7] text-[#11111b]"
                  : "text-[#a6adc8] hover:bg-[#313244] hover:text-[#cdd6f4]"
              }`}
            >
              Candidatos Pendientes ({candidatesCount})
            </button>
            <button
              onClick={() => setActiveTab("promoted")}
              className={`px-3 py-1 rounded-md font-semibold transition ${
                activeTab === "promoted"
                  ? "bg-[#a6e3a1] text-[#11111b]"
                  : "text-[#a6adc8] hover:bg-[#313244] hover:text-[#cdd6f4]"
              }`}
            >
              Vault Promulgado ({promotedCount})
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Filter Doc Type */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-[#181825] border border-[#313244] rounded px-2 py-1 text-[11px] text-[#cdd6f4] outline-none"
            >
              <option value="all">Todos los tipos</option>
              <option value="adr">ADRs de Arquitectura</option>
              <option value="spec">Specs de Requerimientos</option>
              <option value="guide">Guías y Manuales</option>
              <option value="rfc">RFCs</option>
            </select>

            {/* Filter Priority */}
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="bg-[#181825] border border-[#313244] rounded px-2 py-1 text-[11px] text-[#cdd6f4] outline-none"
            >
              <option value="all">Toda prioridad</option>
              <option value="high">Prioridad Alta</option>
              <option value="medium">Prioridad Media</option>
              <option value="low">Prioridad Baja</option>
            </select>

            {/* Search Input */}
            <input
              type="text"
              placeholder="Buscar título o ruta..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-[#181825] border border-[#313244] rounded px-2.5 py-1 text-[11px] text-[#cdd6f4] outline-none w-44"
            />
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="flex h-48 items-center justify-center text-[#cba6f7] font-mono text-xs animate-pulse">
              Escaneando y auditando memoria organizacional...
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col h-48 items-center justify-center text-[#585b70] font-mono text-xs gap-2">
              <span>No se encontraron documentos en esta vista.</span>
              <span className="text-[10px]">
                {activeTab === "candidates"
                  ? "Creá ADRs en vault/decisions/ o specs en vault/specs/ para descubrirlos como candidatos."
                  : "Aprobá y promulgá candidatos para que formen parte del Vault Organizacional."}
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {filteredItems.map((item) => (
                <div
                  key={item.origin_id}
                  className="bg-[#181825] border border-[#313244] hover:border-[#45475a] rounded-xl p-3.5 flex flex-col gap-2 transition"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${getDocTypeBadgeColor(
                            item.doc_type
                          )}`}
                        >
                          {item.doc_type}
                        </span>
                        <span
                          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${getPriorityBadgeColor(
                            item.priority
                          )}`}
                        >
                          Prioridad {item.priority}
                        </span>
                        <span className="text-[10px] text-[#585b70] font-mono">
                          {item.rel_path}
                        </span>
                      </div>
                      <h4 className="font-semibold text-sm text-[#cdd6f4] font-sans">
                        {item.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() =>
                          onPinNode({
                            id: item.origin_id,
                            label: item.title,
                            kind: item.doc_type === "adr" ? "adr" : "spec",
                            path: item.rel_path,
                          })
                        }
                        className="px-2.5 py-1 rounded bg-[#313244] hover:bg-[#45475a] text-[#bac2de] text-xs font-mono transition"
                        title="Fijar en el chat para consultar al Brain"
                      >
                        📌 Chat
                      </button>

                      {!item.is_promoted && item.status !== "rejected" && (
                        <>
                          <button
                            onClick={() => {
                              setSelectedItem(item);
                              setActionType("approve");
                              setDecisionReason("Aprobado para adopción transversal");
                            }}
                            className="px-3 py-1 rounded bg-[#a6e3a1]/20 hover:bg-[#a6e3a1]/30 text-[#a6e3a1] border border-[#a6e3a1]/40 text-xs font-mono font-bold transition"
                          >
                            ✨ Promulgar
                          </button>
                          <button
                            onClick={() => {
                              setSelectedItem(item);
                              setActionType("reject");
                              setDecisionReason("No cumple con los requisitos organizacionales");
                            }}
                            className="px-2.5 py-1 rounded bg-[#f38ba8]/15 hover:bg-[#f38ba8]/25 text-[#f38ba8] border border-[#f38ba8]/30 text-xs font-mono transition"
                          >
                            ✕ Rechazar
                          </button>
                        </>
                      )}

                      {item.is_promoted && (
                        <span className="text-[11px] font-mono text-[#a6e3a1] bg-[#a6e3a1]/15 px-2.5 py-1 rounded border border-[#a6e3a1]/30">
                          ✓ Promulgado {item.reviewer ? `por ${item.reviewer}` : ""}
                        </span>
                      )}

                      {item.status === "rejected" && (
                        <span className="text-[11px] font-mono text-[#f38ba8] bg-[#f38ba8]/15 px-2.5 py-1 rounded border border-[#f38ba8]/30">
                          ✕ Rechazado
                        </span>
                      )}
                    </div>
                  </div>

                  {item.reason && (
                    <div className="text-[11px] font-mono text-[#a6adc8] bg-[#11111b] p-2 rounded border border-[#313244]">
                      <span className="text-[#cba6f7] font-semibold">Dictamen: </span>
                      {item.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal de Decisión / Justificación */}
        {selectedItem && actionType && (
          <div
            className="absolute inset-0 bg-black/70 flex items-center justify-center p-4"
            style={{ zIndex: 60 }}
          >
            <div className="w-full max-w-md bg-[#181825] border border-[#45475a] rounded-xl p-5 shadow-2xl font-mono text-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#313244] pb-3">
                <h4 className="font-bold text-sm text-[#cdd6f4]">
                  {actionType === "approve"
                    ? "✨ Promulgar a la Memoria Organizacional"
                    : "✕ Rechazar Candidato"}
                </h4>
                <button
                  onClick={() => {
                    setSelectedItem(null);
                    setActionType(null);
                  }}
                  className="text-[#a6adc8] hover:text-[#cdd6f4]"
                >
                  ✕
                </button>
              </div>

              <div>
                <span className="text-[#6c7086]">Documento:</span>
                <div className="text-[#cdd6f4] font-semibold mt-0.5">
                  {selectedItem.title}
                </div>
                <div className="text-[10px] text-[#a6adc8]">{selectedItem.rel_path}</div>
              </div>

              <div>
                <label className="block text-[#bac2de] mb-1">Nombre o Rol del Revisor:</label>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  placeholder="Ej: tech-lead / architecture-committee"
                  className="w-full bg-[#11111b] border border-[#313244] rounded px-3 py-1.5 text-[#cdd6f4] outline-none"
                />
              </div>

              <div>
                <label className="block text-[#bac2de] mb-1">Motivo o Dictamen:</label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Describí la justificación técnica..."
                  className="w-full bg-[#11111b] border border-[#313244] rounded px-3 py-1.5 text-[#cdd6f4] outline-none h-20 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => {
                    setSelectedItem(null);
                    setActionType(null);
                  }}
                  className="px-3 py-1.5 rounded bg-[#313244] hover:bg-[#45475a] text-[#cdd6f4]"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleConfirmAction}
                  disabled={isSubmitting}
                  className={`px-4 py-1.5 rounded font-bold transition ${
                    actionType === "approve"
                      ? "bg-[#a6e3a1] text-[#11111b] hover:bg-[#94e2d5]"
                      : "bg-[#f38ba8] text-[#11111b] hover:bg-[#eba0ac]"
                  }`}
                >
                  {isSubmitting
                    ? "Registrando..."
                    : actionType === "approve"
                    ? "Confirmar Promulgación"
                    : "Confirmar Rechazo"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
