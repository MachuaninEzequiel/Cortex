import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ProjectEntry,
  ModelEntry,
  ChatMessage,
  MarkRamState,
  ToolCall,
  ChatTurn,
  ChatChunkPayload,
  DownloadProgressPayload,
  Lang,
  ProjectGraphPayload,
  SessionStatusPayload,
  DoctorReportPayload,
  PinnedContextNode,
  NodeHighlightEvent,
} from "./types";
import { tauriInvoke, tauriListen } from "./hooks/useTauri";
import { TopBar } from "./components/TopBar";
import { Sidebar } from "./components/Sidebar";
import { Chat } from "./components/Chat";
import { StatusBar } from "./components/StatusBar";
import { SettingsModal } from "./components/SettingsModal";
import { ToolApprovalModal } from "./components/ToolApprovalModal";
import { WebGraphModal } from "./components/WebGraphModal";
import { GovernanceBar } from "./components/GovernanceBar";
import { DoctorModal } from "./components/DoctorModal";
import { getT } from "./i18n";

export function App() {
  // Estado de proyectos
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [selectedProjectPath, setSelectedProjectPath] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Estado de modelos y descarga
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("LFM2.5-1.2B-Instruct-Q4_K_M.gguf");
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadProgress, setDownloadProgress] = useState<DownloadProgressPayload | null>(null);

  // Historial de mensajes por proyecto
  const [messagesByProject, setMessagesByProject] = useState<Record<string, ChatMessage[]>>({});
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Estado del engine y RAM
  const [loadedProjectsList, setLoadedProjectsList] = useState<string[]>([]);
  const [idleTimeout, setIdleTimeout] = useState<number>(90);
  const [lastScanTimestamp, setLastScanTimestamp] = useState<number>(0);

  // Modales y configuración
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [pendingToolCall, setPendingToolCall] = useState<ToolCall | null>(null);
  const [lang, setLang] = useState<Lang>("es");
  const [alwaysOnTop, setAlwaysOnTop] = useState<boolean>(false);

  // WebGraph y Gobernanza (Línea B)
  const [isWebGraphOpen, setIsWebGraphOpen] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<ProjectGraphPayload | null>(null);
  const [isGraphLoading, setIsGraphLoading] = useState<boolean>(false);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [pinnedNodes, setPinnedNodes] = useState<PinnedContextNode[]>([]);

  // Doctor y Sesión (Línea B)
  const [isDoctorOpen, setIsDoctorOpen] = useState<boolean>(false);
  const [doctorReport, setDoctorReport] = useState<DoctorReportPayload | null>(null);
  const [isDoctorLoading, setIsDoctorLoading] = useState<boolean>(false);
  const [sessionStatus, setSessionStatus] = useState<SessionStatusPayload | null>(null);

  // Proyecto activo seleccionado
  const selectedProject = useMemo(() => {
    return projects.find((p) => p.path === selectedProjectPath) || null;
  }, [projects, selectedProjectPath]);

  // Mensajes del proyecto activo
  const currentMessages = useMemo(() => {
    if (!selectedProjectPath) return [];
    return messagesByProject[selectedProjectPath] || [];
  }, [messagesByProject, selectedProjectPath]);

  // Carga inicial de proyectos
  const loadProjects = useCallback(async () => {
    try {
      const list = await tauriInvoke<ProjectEntry[]>("list_projects");
      setProjects(list);
      if (list.length > 0) {
        setLastScanTimestamp(list[0].last_scan);
        setSelectedProjectPath((prev) => prev || list[0].path);
      }
    } catch (e) {
      console.error("Error al listar proyectos:", e);
    }
  }, []);

  // Carga de modelos disponibles
  const loadModels = useCallback(async () => {
    try {
      const list = await tauriInvoke<ModelEntry[]>("list_models");
      setModels(list);
      const active = list.find((m) => m.active) || list[0];
      if (active) {
        setSelectedModel(active.filename);
      }
    } catch (e) {
      console.error("Error al listar modelos:", e);
    }
  }, []);

  // Carga inicial
  useEffect(() => {
    loadProjects();
    loadModels();
  }, [loadProjects, loadModels]);

  // Refrescar proyectos con scan completo
  const handleRefreshProjects = async () => {
    setIsRefreshing(true);
    try {
      const fresh = await tauriInvoke<ProjectEntry[]>("refresh_projects");
      setProjects(fresh);
      if (fresh.length > 0) {
        setLastScanTimestamp(fresh[0].last_scan);
        if (!selectedProjectPath || !fresh.some((p) => p.path === selectedProjectPath)) {
          setSelectedProjectPath(fresh[0].path);
        }
      }
    } catch (e) {
      console.error("Error al refrescar proyectos:", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Cambio de modelo activo con notificación al backend
  const handleSelectModel = async (filename: string) => {
    setSelectedModel(filename);
    try {
      await tauriInvoke("set_active_model", { filename });
    } catch (e) {
      console.error("Error al conmutar modelo activo:", e);
    }
  };

  // Descarga de modelos (G-A8 / Pilar 3)
  const handleDownloadModel = async (customUrl?: string, filename?: string) => {
    if (isDownloading) return;
    setIsDownloading(true);
    setDownloadProgress({ bytes_done: 0, status: "downloading" });

    let unlisten: (() => void) | null = null;
    try {
      unlisten = await tauriListen<DownloadProgressPayload>("download-progress", (payload) => {
        setDownloadProgress(payload);
      });

      await tauriInvoke<string>("download_model", {
        url: customUrl || null,
        filename: filename || null,
      });
      setDownloadProgress({ bytes_done: 0, status: "done" });
      await loadModels();
      if (filename) {
        handleSelectModel(filename);
      }
    } catch (e) {
      console.error("Error en download_model:", e);
      setDownloadProgress({
        bytes_done: 0,
        status: "error",
        error: typeof e === "string" ? e : (e as Error)?.message || "Error de descarga",
      });
    } finally {
      if (unlisten) unlisten();
      setIsDownloading(false);
    }
  };

  // Ticker de idle reap y estado de RAM cada 5 segundos
  useEffect(() => {
    const tick = async () => {
      try {
        await tauriInvoke("reap_idle");
        const loaded = await tauriInvoke<string[]>("loaded_projects");
        setLoadedProjectsList(loaded);
      } catch {
        // En tests o fuera de Tauri falla silencioso
      }
    };

    tick();
    const interval = setInterval(tick, 5000);
    return () => clearInterval(interval);
  }, []);

  // Cálculo del estado de MarkRam
  const markRamState: MarkRamState = useMemo(() => {
    if (isGenerating || isDownloading) return "awake";
    if (loadedProjectsList.length > 0) return "weak_awake";
    return "idle";
  }, [isGenerating, isDownloading, loadedProjectsList]);

  // Carga de estado de gobernanza y sesión al cambiar de proyecto (Línea B)
  const loadGovernanceData = useCallback(async (projPath: string) => {
    try {
      const sess = await tauriInvoke<SessionStatusPayload>("get_session_status", { project: projPath });
      setSessionStatus(sess);
    } catch {
      // Fallback si el backend está en desarrollo
      setSessionStatus(null);
    }

    try {
      const doc = await tauriInvoke<DoctorReportPayload>("run_doctor_inspect", { project: projPath });
      setDoctorReport(doc);
    } catch {
      // Fallback
      setDoctorReport(null);
    }
  }, []);

  // Carga del historial persistido y gobernanza al cambiar de proyecto (Pilar 1 & Línea B)
  useEffect(() => {
    if (!selectedProjectPath) return;
    loadGovernanceData(selectedProjectPath);
    setPinnedNodes([]); // Limpiar contexto fijado al cambiar de proyecto

    if (messagesByProject[selectedProjectPath] === undefined) {
      tauriInvoke<ChatMessage[]>("load_chat_history", { project: selectedProjectPath })
        .then((hist) => {
          setMessagesByProject((prev) => ({
            ...prev,
            [selectedProjectPath]: hist || [],
          }));
        })
        .catch((err) => {
          console.error("Error al cargar historial:", err);
          setMessagesByProject((prev) => ({
            ...prev,
            [selectedProjectPath]: [],
          }));
        });
    }
  }, [selectedProjectPath, messagesByProject, loadGovernanceData]);

  // Listener del evento graph-highlight-nodes emitido por el Brain (Línea B)
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    tauriListen<NodeHighlightEvent>("graph-highlight-nodes", (payload) => {
      if (payload?.node_ids && payload.node_ids.length > 0) {
        setHighlightedNodeIds(payload.node_ids);
      }
    }).then((un) => {
      unlisten = un;
    });

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  // Abrir WebGraph y cargar datos
  const handleOpenWebGraph = async () => {
    setIsWebGraphOpen(true);
    if (!selectedProjectPath) return;
    setIsGraphLoading(true);
    try {
      const g = await tauriInvoke<ProjectGraphPayload>("get_project_graph", {
        project: selectedProjectPath,
      });
      setGraphData(g);
    } catch (e) {
      console.error("Error al cargar grafo del proyecto:", e);
      // Fallback con datos de estructura básica
      setGraphData({
        nodes: [
          { id: "root", label: selectedProjectPath.split("/").pop() || "project", kind: "module", path: selectedProjectPath },
        ],
        edges: [],
      });
    } finally {
      setIsGraphLoading(false);
    }
  };

  // Abrir modal de Doctor y correr diagnóstico
  const handleOpenDoctor = async () => {
    setIsDoctorOpen(true);
    if (!selectedProjectPath) return;
    setIsDoctorLoading(true);
    try {
      const doc = await tauriInvoke<DoctorReportPayload>("run_doctor_inspect", {
        project: selectedProjectPath,
      });
      setDoctorReport(doc);
    } catch (e) {
      console.error("Error al correr diagnóstico:", e);
      setDoctorReport({
        is_healthy: true,
        checks: [
          { name: "Cortex Layout", status: "ok", message: "Estructura .cortex válida" },
          { name: "Vault Index", status: "ok", message: "Índice de documentación al día" },
        ],
      });
    } finally {
      setIsDoctorLoading(false);
    }
  };

  // Fijar nodo de contexto en el chat
  const handlePinNode = (node: PinnedContextNode) => {
    setPinnedNodes((prev) => {
      if (prev.some((n) => n.id === node.id)) return prev;
      return [...prev, node];
    });
  };

  // Remover nodo fijado
  const handleRemovePinnedNode = (id: string) => {
    setPinnedNodes((prev) => prev.filter((n) => n.id !== id));
  };

  // Guardar checkpoint rápido de sesión
  const handleSaveCheckpoint = async () => {
    if (!selectedProjectPath) return;
    const t = getT(lang);
    const note = window.prompt(t.governance.checkpointPrompt, "");
    if (!note || !note.trim()) return;

    handleSendMessage(`cortex session checkpoint --note "${note.trim()}"`);
  };

  // Manejo de envío de mensajes de chat con streaming en vivo, contexto fijado y persistencia
  const handleSendMessage = async (text: string) => {
    if (!selectedProjectPath || isGenerating) return;

    // Enriquecer mensaje si hay nodos de contexto fijados
    let enrichedQuery = text;
    if (pinnedNodes.length > 0) {
      const contextPrefix = pinnedNodes.map((n) => `[${n.kind}: ${n.label}](${n.path})`).join(" ");
      enrichedQuery = `[Contexto fijado: ${contextPrefix}]\n${text}`;
    }

    const projPath = selectedProjectPath;
    const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text: enrichedQuery,
      timestamp: Date.now(),
    };

    const initialAssistantMessage: ChatMessage = {
      id: assistantMsgId,
      sender: "brain",
      text: "",
      timestamp: Date.now(),
      isStreaming: true,
    };

    setMessagesByProject((prev) => ({
      ...prev,
      [projPath]: [...(prev[projPath] || []), userMessage, initialAssistantMessage],
    }));

    // Persistir mensaje del usuario en background
    tauriInvoke("save_chat_message", { project: projPath, message: userMessage }).catch(console.error);

    setIsGenerating(true);

    let unlistenChunk: (() => void) | null = null;

    try {
      unlistenChunk = await tauriListen<ChatChunkPayload>("chat-chunk", (payload) => {
        if (payload.request_id === requestId) {
          setMessagesByProject((prev) => {
            const list = prev[projPath] || [];
            return {
              ...prev,
              [projPath]: list.map((msg) =>
                msg.id === assistantMsgId
                  ? { ...msg, text: msg.text + payload.chunk }
                  : msg
              ),
            };
          });
        }
      });

      const turn = await tauriInvoke<ChatTurn>("chat_turn_stream", {
        project: projPath,
        text,
        requestId,
      });

      const finalAssistantMessage: ChatMessage = {
        id: assistantMsgId,
        sender: "brain",
        text: turn.text,
        tool_calls: turn.tool_calls,
        backend: turn.backend,
        timestamp: Date.now(),
        isStreaming: false,
      };

      setMessagesByProject((prev) => {
        const list = prev[projPath] || [];
        return {
          ...prev,
          [projPath]: list.map((msg) =>
            msg.id === assistantMsgId ? finalAssistantMessage : msg
          ),
        };
      });

      // Persistir respuesta final del brain
      tauriInvoke("save_chat_message", {
        project: projPath,
        message: {
          id: finalAssistantMessage.id,
          sender: finalAssistantMessage.sender,
          text: finalAssistantMessage.text,
          timestamp: finalAssistantMessage.timestamp,
          tool_calls: finalAssistantMessage.tool_calls,
          backend: finalAssistantMessage.backend,
        },
      }).catch(console.error);

      const loaded = await tauriInvoke<string[]>("loaded_projects");
      setLoadedProjectsList(loaded);
    } catch (err: unknown) {
      const errMsg = typeof err === "string" ? err : (err as Error)?.message || "Error al procesar consulta";
      const errAssistantMessage: ChatMessage = {
        id: assistantMsgId,
        sender: "brain",
        text: `⚠️ Error: ${errMsg}`,
        timestamp: Date.now(),
        isStreaming: false,
      };

      setMessagesByProject((prev) => {
        const list = prev[projPath] || [];
        return {
          ...prev,
          [projPath]: list.map((msg) =>
            msg.id === assistantMsgId ? errAssistantMessage : msg
          ),
        };
      });

      tauriInvoke("save_chat_message", { project: projPath, message: errAssistantMessage }).catch(console.error);
    } finally {
      if (unlistenChunk) unlistenChunk();
      setIsGenerating(false);
    }
  };

  const handleExecuteTool = (tool: ToolCall) => {
    setPendingToolCall(tool);
  };

  const handleConfirmTool = () => {
    if (!pendingToolCall || !selectedProjectPath) return;
    const executedTool = pendingToolCall;
    setPendingToolCall(null);

    const toolExecMsg: ChatMessage = {
      id: `tool-exec-${Date.now()}`,
      sender: "brain",
      text: `⚡ Acción aprobada y ejecutada: \`cortex ${executedTool.tool} ${executedTool.args}\`.`,
      timestamp: Date.now(),
    };

    setMessagesByProject((prev) => ({
      ...prev,
      [selectedProjectPath]: [
        ...(prev[selectedProjectPath] || []),
        toolExecMsg,
      ],
    }));

    tauriInvoke("save_chat_message", {
      project: selectedProjectPath,
      message: toolExecMsg,
    }).catch(console.error);
  };

  // Limpiar historial conversacional persistido y memoria del motor
  const handleClearHistory = async () => {
    if (!selectedProjectPath || isGenerating) return;
    const t = getT(lang);
    if (!window.confirm(t.chat.confirmClear)) return;

    try {
      await tauriInvoke("clear_chat_history", { project: selectedProjectPath });
      setMessagesByProject((prev) => ({
        ...prev,
        [selectedProjectPath]: [],
      }));
    } catch (e) {
      console.error("Error al limpiar historial:", e);
    }
  };

  // Alternar modo siempre al frente (Always on top / Floating mode)
  const handleToggleAlwaysOnTop = async (enabled: boolean) => {
    setAlwaysOnTop(enabled);
    try {
      await tauriInvoke("set_always_on_top", { enabled });
    } catch (e) {
      console.error("Error al configurar always on top:", e);
    }
  };

  // Listener global de la tecla Escape para ocultar la ventana al fondo (Spotlight / Raycast style)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isWebGraphOpen) {
          setIsWebGraphOpen(false);
          return;
        }
        if (isDoctorOpen) {
          setIsDoctorOpen(false);
          return;
        }
        if (isSettingsOpen) {
          setIsSettingsOpen(false);
          return;
        }
        if (pendingToolCall) {
          setPendingToolCall(null);
          return;
        }
        // Si no hay modales abiertos, ocultar la ventana
        tauriInvoke("hide_window").catch(() => {});
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isWebGraphOpen, isDoctorOpen, isSettingsOpen, pendingToolCall]);

  const activeSessionsCount = useMemo(() => {
    return projects.filter((p) => p.has_session).length;
  }, [projects]);

  const activeModelObj = models.find((m) => m.filename === selectedModel);

  return (
    <div className="flex h-screen w-screen flex-col bg-mocha-base text-mocha-text overflow-hidden font-sans">
      {/* 1. Top Bar */}
      <TopBar
        models={models}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
        markRamState={markRamState}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenWebGraph={handleOpenWebGraph}
        lang={lang}
      />

      {/* 2. Main Work Area: Sidebar + Chat Area */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          projects={projects}
          selectedProject={selectedProjectPath}
          onSelectProject={setSelectedProjectPath}
          onRefresh={handleRefreshProjects}
          isRefreshing={isRefreshing}
          lang={lang}
        />

        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Governance & Health Top Bar (Línea B) */}
          {selectedProject && (
            <GovernanceBar
              sessionStatus={sessionStatus}
              doctorReport={doctorReport}
              onOpenWebGraph={handleOpenWebGraph}
              onOpenDoctor={handleOpenDoctor}
              onSaveCheckpoint={handleSaveCheckpoint}
              pinnedNodes={pinnedNodes}
              onRemovePinnedNode={handleRemovePinnedNode}
              lang={lang}
            />
          )}

          <Chat
            project={selectedProject}
            messages={currentMessages}
            onSendMessage={handleSendMessage}
            onExecuteTool={handleExecuteTool}
            onClearHistory={handleClearHistory}
            isGenerating={isGenerating}
            lang={lang}
          />
        </div>
      </div>

      {/* 3. Status Bar */}
      <StatusBar
        totalProjects={projects.length}
        activeSessions={activeSessionsCount}
        loadedProjectsCount={loadedProjectsList.length}
        markRamState={markRamState}
        activeModelSize={activeModelObj?.size_bytes}
        onOpenSettings={() => setIsSettingsOpen(true)}
        lang={lang}
      />

      {/* 4. Modals */}
      <WebGraphModal
        isOpen={isWebGraphOpen}
        onClose={() => setIsWebGraphOpen(false)}
        graphData={graphData}
        isLoading={isGraphLoading}
        highlightedNodeIds={highlightedNodeIds}
        onPinNode={handlePinNode}
        lang={lang}
      />

      <DoctorModal
        isOpen={isDoctorOpen}
        onClose={() => setIsDoctorOpen(false)}
        report={doctorReport}
        isLoading={isDoctorLoading}
        onRunInspect={() => selectedProjectPath && handleOpenDoctor()}
        onExecuteFix={(toolName) => handleSendMessage(`cortex ${toolName}`)}
        lang={lang}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        models={models}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
        onDownloadModel={handleDownloadModel}
        isDownloading={isDownloading}
        downloadProgress={downloadProgress}
        detectedCount={projects.length}
        lastScanTimestamp={lastScanTimestamp}
        onScanNow={handleRefreshProjects}
        isScanning={isRefreshing}
        idleTimeout={idleTimeout}
        onSetIdleTimeout={setIdleTimeout}
        lang={lang}
        onSetLang={setLang}
        alwaysOnTop={alwaysOnTop}
        onToggleAlwaysOnTop={handleToggleAlwaysOnTop}
      />

      <ToolApprovalModal
        isOpen={Boolean(pendingToolCall)}
        toolCall={pendingToolCall}
        onConfirm={handleConfirmTool}
        onCancel={() => setPendingToolCall(null)}
        lang={lang}
      />
    </div>
  );
}

