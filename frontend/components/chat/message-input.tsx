"use client";

import { useState, useRef, KeyboardEvent, useCallback } from "react";
import { Send, Loader2, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface MessageInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  onStop?: () => void;
}

export function MessageInput({ onSend, isStreaming, onStop }: MessageInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput("");
    textareaRef.current?.focus();
  }, [input, isStreaming, onSend]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);

  return (
    <div className="border-t bg-background/80 backdrop-blur-sm p-4 shrink-0">
      <div className="flex gap-3 max-w-3xl mx-auto items-end">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? "Waiting for response..." : "Send a message..."}
          rows={1}
          className="min-h-[44px] max-h-[200px] resize-none rounded-xl"
          disabled={isStreaming}
          autoFocus
        />
        {isStreaming ? (
          <Button onClick={onStop} size="icon" className="h-11 w-11 shrink-0 rounded-xl" variant="destructive">
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSend} disabled={!input.trim()} size="icon" className="h-11 w-11 shrink-0 rounded-xl">
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}