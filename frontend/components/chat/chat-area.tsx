"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Agent, Conversation, api } from "@/lib/api";
import { useSSE } from "@/hooks/use-sse";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { ToolCallCard } from "./tool-call-card";
import { Bot, Sparkles, Loader2 } from "lucide-react";

interface ChatAreaProps {
  agent: Agent | null;
  conversation: Conversation | null;
  onTitleUpdated?: (title: string) => void;
}

interface DisplayMessage { id: string; role: "user" | "assistant"; content: string }
interface ToolCallEvent { id: string; name: string; args: string; output?: string; isExecuting: boolean }

let msgCounter = 0;

export function ChatArea({ agent, conversation, onTitleUpdated }: ChatAreaProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState("");
  const { isStreaming, startStream, stopStream } = useSSE();
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeConvRef = useRef<string | null>(null);

  useEffect(() => {
    if (isStreaming) stopStream();
    if (conversation) {
      activeConvRef.current = conversation.id;
      api.getMessages(conversation.id).then((msgs) => {
        setMessages(msgs.filter((m) => m.role !== "tool").map((m) => ({
          id: m.id, role: m.role as "user" | "assistant", content: m.content,
        })));
      }).catch(() => setMessages([]));
    } else {
      activeConvRef.current = null;
      setMessages([]);
    }
    setStreamingContent("");
    setToolCalls([]);
    setError("");
  }, [conversation?.id]);

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent, error, toolCalls]);

  const handleSend = useCallback((content: string) => {
    if (!agent || !conversation) return;
    const convId = conversation.id;
    activeConvRef.current = convId;
    const userMsg: DisplayMessage = { id: `u${++msgCounter}`, role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setStreamingContent("");
    setToolCalls([]);
    setError("");

    let assistantContent = "";
    startStream(
      conversation.id, agent.id, content,
      (delta) => {
        if (activeConvRef.current !== convId) return;
        assistantContent += delta; setStreamingContent(assistantContent);
      },
      (name, args) => {
        if (activeConvRef.current !== convId) return;
        setToolCalls((prev) => [...prev, { id: `tc${++msgCounter}`, name, args, isExecuting: true }]);
      },
      (tool, output) => {
        if (activeConvRef.current !== convId) return;
        setToolCalls((prev) => prev.map((tc) => tc.name === tool && tc.isExecuting ? { ...tc, output, isExecuting: false } : tc));
      },
      () => {
        if (activeConvRef.current !== convId) return;
        if (assistantContent) setMessages((prev) => [...prev, { id: `a${++msgCounter}`, role: "assistant", content: assistantContent }]);
        setStreamingContent("");
      },
      (errMsg) => {
        if (activeConvRef.current !== convId) return;
        setError(errMsg); setStreamingContent("");
      },
      (title: string) => {
        if (activeConvRef.current !== convId) return;
        onTitleUpdated?.(title);
      },
    );
  }, [agent, conversation, startStream, onTitleUpdated]);

  const messageList = useMemo(() => {
    const items: Array<{ type: "msg"; data: DisplayMessage } | { type: "tool"; data: ToolCallEvent }> = [];
    for (const m of messages) {
      items.push({ type: "msg", data: m });
      for (const tc of toolCalls) {
        if (tc.isExecuting) items.push({ type: "tool", data: tc });
      }
    }
    return items;
  }, [messages, toolCalls]);

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gradient-to-b from-background to-muted/30">
        <div className="text-center space-y-4">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <Bot className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">Welcome to Agent Platform</h2>
            <p className="text-muted-foreground mt-1 max-w-sm">Select an agent from the sidebar to start chatting. You can switch between different AI assistants.</p>
          </div>
          <div className="flex gap-2 justify-center text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" />Multi-agent</span>
            <span>·</span>
            <span>Web search</span>
            <span>·</span>
            <span>Code execution</span>
            <span>·</span>
            <span>Memory</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      <div className="border-b bg-card/50 backdrop-blur-sm px-6 py-3 flex items-center gap-3 shrink-0">
        <span className="text-xl">{agent.avatar}</span>
        <div>
          <h2 className="font-semibold text-sm">{agent.name}</h2>
          <p className="text-xs text-muted-foreground">{agent.model.split("/")[1] || agent.model}</p>
        </div>
      </div>
      <ScrollArea className="flex-1 px-6 custom-scrollbar">
        <div className="max-w-3xl mx-auto py-4">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg">Start a conversation with {agent.name}</p>
              <p className="text-sm mt-1">Ask anything — I can search the web, run code, and more.</p>
            </div>
          )}
          {messages.map((msg) => <MessageBubble key={msg.id} role={msg.role} content={msg.content} />)}
          {toolCalls.map((tc) => <ToolCallCard key={tc.id} name={tc.name} args={tc.args} output={tc.output} isExecuting={tc.isExecuting} />)}
          {isStreaming && !streamingContent && (
            <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm animate-fade-in">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
          {streamingContent && !messages.some((m) => m.role === "assistant" && m.content === streamingContent) && (
            <MessageBubble role="assistant" content={streamingContent} isStreaming />
          )}
          {error && (
            <div className="my-3 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive animate-fade-in">
              {error}
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
      <MessageInput onSend={handleSend} isStreaming={isStreaming} onStop={stopStream} />
    </div>
  );
}