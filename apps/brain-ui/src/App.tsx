import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ProjectEntry,
  ModelEntry,
  ChatMessage,
  MarkRamState,
  ToolCall,
  ChatTurn,
  ChatChunkPayload,
  Lang,
} from "./types";
import { tauriInvoke, tauriListen } from "./hooks/useTauri";
import { TopBar } from "./components/TopBar";
import { Sidebar } from "./components/Sidebar";
import { Chat } from "./components/Chat";
import { StatusBar } from "./components/StatusBar";
import { SettingsModal } from "./components/SettingsModal";
import { ToolApprovalModal } from "./components/ToolApprovalModal";

export function App() {
  // Estado de proyectos
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [selectedProjectPath, setSelectedProjectPath] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Estado de modelos
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("LFM2.5-1.2B-Instruct-Q4_K_M.gguf");

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
    if (isGenerating) return "awake";
    if (loadedProjectsList.length > 0) return "weak_awake";
    return "idle";
  }, [isGenerating, loadedProjectsList]);

  // Manejo de envío de mensajes de chat con streaming en vivo
  const handleSendMessage = async (text: string) => {
    if (!selectedProjectPath || isGenerating) return;

    const projPath = selectedProjectPath;
    const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text,
      timestamp: Date.now(),
    };

    const initialAssistantMessage: ChatMessage = {
      id: assistantMsgId,
      sender: "brain",
      text: "",
      timestamp: Date.now(),
      isStreaming: true,
    };

    // Añadir mensaje del usuario y placeholder de streaming
    setMessagesByProject((prev) => ({
      ...prev,
      [projPath]: [...(prev[projPath] || []), userMessage, initialAssistantMessage],
    }));

    setIsGenerating(true);

    let unlistenChunk: (() => void) | null = null;

    try {
      // Escuchar chunks en vivo para este request_id
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

      // Invocar command de streaming en el backend
      const turn = await tauriInvoke<ChatTurn>("chat_turn_stream", {
        project: projPath,
        text,
        requestId,
      });

      // Reconciliar con el resultado autoritativo final (done)
      setMessagesByProject((prev) => {
        const list = prev[projPath] || [];
        return {
          ...prev,
          [projPath]: list.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: turn.text,
                  tool_calls: turn.tool_calls,
                  backend: turn.backend,
                  isStreaming: false,
                }
              : msg
          ),
        };
      });

      // Actualizar backends cargados
      const loaded = await tauriInvoke<string[]>("loaded_projects");
      setLoadedProjectsList(loaded);
    } catch (err: unknown) {
      const errMsg = typeof err === "string" ? err : (err as Error)?.message || "Error al procesar consulta";
      setMessagesByProject((prev) => {
        const list = prev[projPath] || [];
        return {
          ...prev,
          [projPath]: list.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  text: `⚠️ Error: ${errMsg}`,
                  isStreaming: false,
                }
              : msg
          ),
        };
      });
    } finally {
      if (unlistenChunk) unlistenChunk();
      setIsGenerating(false);
    }
  };

  // Manejo de ejecución de Tool propuesta
  const handleExecuteTool = (tool: ToolCall) => {
    setPendingToolCall(tool);
  };

  const handleConfirmTool = () => {
    if (!pendingToolCall || !selectedProjectPath) return;
    const executedTool = pendingToolCall;
    setPendingToolCall(null);

    // Feedback en el chat
    setMessagesByProject((prev) => ({
      ...prev,
      [selectedProjectPath]: [
        ...(prev[selectedProjectPath] || []),
        {
          id: `tool-exec-${Date.now()}`,
          sender: "brain",
          text: `⚡ Acción aprobada y ejecutada: \`cortex ${executedTool.tool} ${executedTool.args}\`.`,
          timestamp: Date.now(),
        },
      ],
    }));
  };

  // Conteo de sesiones activas
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
        onSelectModel={setSelectedModel}
        markRamState={markRamState}
        onOpenSettings={() => setIsSettingsOpen(true)}
        lang={lang}
      />

      {/* 2. Main Work Area: Sidebar + Chat */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          projects={projects}
          selectedProject={selectedProjectPath}
          onSelectProject={setSelectedProjectPath}
          onRefresh={handleRefreshProjects}
          isRefreshing={isRefreshing}
          lang={lang}
        />

        <Chat
          project={selectedProject}
          messages={currentMessages}
          onSendMessage={handleSendMessage}
          onExecuteTool={handleExecuteTool}
          isGenerating={isGenerating}
          lang={lang}
        />
      </div>

      {/* 3. Status Bar */}
      <StatusBar
        totalProjects={projects.length}
        activeSessions={activeSessionsCount}
        loadedProjectsCount={loadedProjectsList.length}
        markRamState={markRamState}
        activeModelSize={activeModelObj?.size_bytes}
        lang={lang}
      />

      {/* 4. Modals */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        models={models}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        detectedCount={projects.length}
        lastScanTimestamp={lastScanTimestamp}
        onScanNow={handleRefreshProjects}
        isScanning={isRefreshing}
        idleTimeout={idleTimeout}
        onSetIdleTimeout={setIdleTimeout}
        lang={lang}
        onSetLang={setLang}
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
