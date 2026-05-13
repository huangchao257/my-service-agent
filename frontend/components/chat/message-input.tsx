"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface MessageInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function MessageInput({ onSend, isStreaming }: MessageInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="border-t bg-background p-4">
      <div className="flex gap-3 max-w-3xl mx-auto">
        <Textarea ref={textareaRef} value={input}
          onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
          placeholder="Send a message..." rows={1}
          className="min-h-[44px] max-h-[200px] resize-none" disabled={isStreaming} />
        <Button onClick={handleSend} disabled={!input.trim() || isStreaming} size="icon" className="h-11 w-11 shrink-0">
          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}