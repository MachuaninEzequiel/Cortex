import React from "react";
import { ChatMessage as ChatMessageType, ToolCall } from "../types";
import { getT } from "../i18n";

interface ChatMessageProps {
  message: ChatMessageType;
  onExecuteTool?: (tool: ToolCall) => void;
  lang: "es" | "en";
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onExecuteTool,
  lang,
}) => {
  const t = getT(lang);
  const isUser = message.sender === "user";

  // Simple formatter for lines and markdown code blocks
  const renderFormattedText = (content: string) => {
    return (
      <div className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-mocha-text">
        {content}
        {message.isStreaming && (
          <span className="inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-cortex-mint ml-0.5" />
        )}
      </div>
    );
  };

  return (
    <div
      className={`flex w-full gap-3 p-3 transition ${
        isUser
          ? "justify-end bg-transparent"
          : "justify-start bg-mocha-surface/20 rounded-lg border border-mocha-surface/40"
      }`}
    >
      {/* Brain Avatar */}
      {!isUser && (
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-mocha-surface text-base shadow-sm ring-1 ring-mocha-mauve/30 select-none">
          🧠
        </div>
      )}

      {/* Message Content Container */}
      <div className={`flex flex-col max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Header (Sender & Timestamp & Backend) */}
        <div className="mb-1 flex items-center gap-2 text-[11px] font-mono text-mocha-subtext0">
          <span className={isUser ? "font-semibold text-mocha-lavender" : "font-semibold text-mocha-mauve"}>
            {isUser ? "yo" : "Cortex Brain"}
          </span>
          <span className="text-mocha-surface2 text-[10px]">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {message.backend && (
            <span className="rounded bg-mocha-surface px-1.5 py-0.2 text-[9px] font-mono text-cortex-mint">
              {message.backend}
            </span>
          )}
        </div>

        {/* Text Box */}
        <div
          className={`rounded-lg px-3.5 py-2.5 shadow-sm ${
            isUser
              ? "bg-mocha-mauve text-mocha-base font-medium rounded-tr-none"
              : "bg-mocha-surface/50 text-mocha-text rounded-tl-none border border-mocha-surface/60"
          }`}
        >
          {renderFormattedText(message.text)}
        </div>

        {/* Proposed Tool Actions */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2.5 flex w-full flex-col gap-2 rounded border border-mocha-mauve/30 bg-mocha-base/80 p-2.5">
            <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-mocha-mauve">
              <span>⚡</span>
              <span>{t.chat.toolProposal}</span>
            </div>
            {message.tool_calls.map((tc, idx) => (
              <div key={idx} className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                <div className="font-mono text-xs text-mocha-subtext0">
                  <span className="text-cortex-mint font-semibold">{tc.tool}</span>{" "}
                  <span className="text-mocha-text/80">{tc.args}</span>
                </div>
                {onExecuteTool && (
                  <button
                    onClick={() => onExecuteTool(tc)}
                    className="self-start rounded bg-cortex-forest px-2.5 py-1 text-xs font-mono font-medium text-cortex-mint shadow transition hover:bg-cortex-forest/80 active:scale-95 sm:self-auto"
                  >
                    [ {t.chat.execute} ]
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded bg-mocha-mauve text-xs font-bold text-mocha-base select-none">
          yo
        </div>
      )}
    </div>
  );
};
