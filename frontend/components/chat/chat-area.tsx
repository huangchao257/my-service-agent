"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Agent, Conversation, api } from "@/lib/api";
import { useSSE } from "@/hooks/use-sse";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { ToolCallCard } from "./tool-call-card";

interface ChatAreaProps {
  agent: Agent | null;
  conversation: Conversation | null;
}

interface DisplayMessage { role: "user" | "assistant"; content: string }
interface ToolCallEvent { name: string; args: string; output?: string; isExecuting: boolean }

export function ChatArea({ agent, conversation }: ChatAreaProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const { isStreaming, startStream } = useSSE();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversation) {
      api.getMessages(conversation.id).then((msgs) => {
        setMessages(msgs.filter((m) => m.role !== "tool").map((m) => ({
          role: m.role as "user" | "assistant", content: m.content,
        })));
      });
    } else { setMessages([]); }
    setStreamingContent("");
    setToolCalls([]);
  }, [conversation?.id]);

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent]);

  const handleSend = (content: string) => {
    if (!agent || !conversation) return;
    setMessages((prev) => [...prev, { role: "user", content }]);
    setStreamingContent("");
    setToolCalls([]);
    let assistantContent = "";
    startStream(
      conversation.id, agent.id, content,
      (delta) => { assistantContent += delta; setStreamingContent(assistantContent); },
      (name, args) => { setToolCalls((prev) => [...prev, { name, args, isExecuting: true }]); },
      (tool, output) => { setToolCalls((prev) => prev.map((tc) => tc.name === tool && tc.isExecuting ? { ...tc, output, isExecuting: false } : tc)); },
      () => { if (assistantContent) setMessages((prev) => [...prev, { role: "assistant", content: assistantContent }]); setStreamingContent(""); },
      (error) => { console.error("Stream error:", error); },
    );
  };

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Select an agent to start chatting
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="border-b px-6 py-3 flex items-center gap-3">
        <span className="text-xl">{agent.avatar}</span>
        <div>
          <h2 className="font-semibold text-sm">{agent.name}</h2>
          <p className="text-xs text-muted-foreground">{agent.model}</p>
        </div>
      </div>
      <ScrollArea className="flex-1 px-6">
        <div className="max-w-3xl mx-auto">
          {messages.map((msg, i) => <MessageBubble key={i} role={msg.role} content={msg.content} />)}
          {toolCalls.map((tc, i) => <ToolCallCard key={i} {...tc} />)}
          {streamingContent && <MessageBubble role="assistant" content={streamingContent} isStreaming />}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
      <MessageInput onSend={handleSend} isStreaming={isStreaming} />
    </div>
  );
}