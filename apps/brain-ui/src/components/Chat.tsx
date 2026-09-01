import React, { useRef, useEffect } from "react";
import { ChatMessage as ChatMessageType, ProjectEntry, ToolCall } from "../types";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { getT } from "../i18n";

interface ChatProps {
  project: ProjectEntry | null;
  messages: ChatMessageType[];
  onSendMessage: (text: string) => void;
  onExecuteTool: (tool: ToolCall) => void;
  isGenerating: boolean;
  lang: "es" | "en";
}

export const Chat: React.FC<ChatProps> = ({
  project,
  messages,
  onSendMessage,
  onExecuteTool,
  isGenerating,
  lang,
}) => {
  const t = getT(lang);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const getProjectName = (path: string) => {
    const parts = path.split("/").filter(Boolean);
    return parts[parts.length - 1] || path;
  };

  return (
    <div className="flex h-full flex-1 flex-col bg-mocha-base/60 overflow-hidden">
      {/* Project Header in Chat */}
      {project && (
        <div className="flex h-11 items-center justify-between border-b border-mocha-surface/60 bg-mocha-base/80 px-4 select-none">
          <div className="flex items-center gap-2">
            <span className="text-xs text-mocha-mauve font-mono font-bold">
              {getProjectName(project.path)}
            </span>
            {project.branch && (
              <span className="rounded bg-mocha-surface px-1.5 py-0.5 text-[10px] font-mono text-mocha-lavender">
                {project.branch}
              </span>
            )}
            {project.has_session && (
              <span className="flex items-center gap-1 rounded bg-cortex-forest/60 px-1.5 py-0.5 text-[10px] font-mono text-cortex-mint">
                <span className="h-1.5 w-1.5 rounded-full bg-cortex-mint animate-pulse" />
                {t.sidebar.activeSession}
              </span>
            )}
          </div>

          <div className="text-[11px] font-mono text-mocha-surface2 truncate max-w-sm" title={project.path}>
            {project.path}
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!project ? (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center select-none">
            <div className="mb-3 text-4xl">🧠</div>
            <h2 className="text-base font-semibold text-mocha-text font-mono">
              {t.chat.noProjectSelected}
            </h2>
            <p className="mt-1 max-w-sm text-xs text-mocha-subtext0">
              {t.chat.emptyDesc}
            </p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center select-none">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-mocha-surface text-2xl shadow-inner ring-1 ring-mocha-mauve/20">
              🧠
            </div>
            <h2 className="text-sm font-semibold text-mocha-text font-mono">
              {t.chat.emptyTitle} — {getProjectName(project.path)}
            </h2>
            <p className="mt-1 max-w-sm text-xs text-mocha-subtext0 font-sans">
              {t.chat.emptyDesc}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-md">
              {[
                "¿Cómo está la salud del proyecto?",
                "¿Qué sesión está activa?",
                "Buscar archivos de configuración",
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(suggestion)}
                  disabled={isGenerating}
                  className="rounded border border-mocha-surface bg-mocha-surface/40 px-2.5 py-1 text-xs font-mono text-mocha-subtext0 transition hover:border-mocha-mauve hover:text-mocha-text active:scale-95 disabled:opacity-50"
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onExecuteTool={onExecuteTool}
              lang={lang}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <ChatInput
        onSend={onSendMessage}
        disabled={!project}
        isGenerating={isGenerating}
        lang={lang}
      />
    </div>
  );
};
