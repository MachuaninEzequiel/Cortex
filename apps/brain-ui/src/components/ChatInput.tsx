import React, { useState, useRef, useEffect } from "react";
import { getT } from "../i18n";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  isGenerating: boolean;
  lang: "es" | "en";
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  isGenerating,
  lang,
}) => {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const t = getT(lang);

  useEffect(() => {
    if (!disabled && !isGenerating && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled, isGenerating]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled || isGenerating) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="border-t border-mocha-surface bg-mocha-base/90 p-3">
      <div className="flex items-end gap-2 rounded-lg border border-mocha-surface bg-mocha-surface/40 p-1.5 focus-within:border-mocha-mauve focus-within:ring-1 focus-within:ring-mocha-mauve/50 transition">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isGenerating}
          rows={1}
          placeholder={disabled ? t.chat.noProjectSelected : isGenerating ? t.chat.thinking : t.chat.placeholder}
          className="max-h-32 min-h-[38px] flex-1 resize-none bg-transparent px-3 py-2 text-sm text-mocha-text placeholder-mocha-surface2 focus:outline-none disabled:opacity-50 font-sans"
        />

        <button
          onClick={handleSubmit}
          disabled={disabled || isGenerating || !text.trim()}
          className="flex h-9 w-9 items-center justify-center rounded-md bg-mocha-mauve text-mocha-base font-bold transition hover:opacity-90 active:scale-95 disabled:bg-mocha-surface2 disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          title={t.chat.send}
          aria-label={t.chat.send}
        >
          {isGenerating ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-mocha-base border-t-transparent" />
          ) : (
            <span className="text-base font-mono">↵</span>
          )}
        </button>
      </div>
    </div>
  );
};
