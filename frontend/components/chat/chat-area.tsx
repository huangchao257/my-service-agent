"use client";

/**
 * ChatArea — 聊天主区域
 *
 * 功能：
 * - 消息列表（用户/助手对话气泡）
 * - 工具调用卡片（展开查看参数和结果）
 * - 流式回复显示（SSE 实时渲染 Markdown）
 * - "Thinking..." 加载动画
 * - 自动滚动到底部
 *
 * 防串扰机制：通过 activeConvRef 记录当前会话 ID，
 * 所有 SSE 回调检查 activeConvRef.current === convId 后才会更新状态。
 */

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

let msgCounter = 0;  // 前端临时消息 ID 计数器

export function ChatArea({ agent, conversation, onTitleUpdated }: ChatAreaProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEvent[]>([]);
  const [streamingContent, setStreamingContent] = useState("");  // 当前流式文本
  const [error, setError] = useState("");
  const { isStreaming, startStream, stopStream } = useSSE();
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeConvRef = useRef<string | null>(null);  // 当前活跃会话 ID，防止 SSE 串扰

  // 会话切换时：停止旧的 SSE 流，加载新会话的消息历史
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

  // 自动滚动到底部
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingContent, error, toolCalls]);

  // 发送消息并启动 SSE 流
  const handleSend = useCallback((content: string) => {
    if (!agent || !conversation) return;
    const convId = conversation.id;
    activeConvRef.current = convId;

    // 立即显示用户消息
    const userMsg: DisplayMessage = { id: `u${++msgCounter}`, role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setStreamingContent("");
    setToolCalls([]);
    setError("");

    let assistantContent = "";
    startStream(
      conversation.id, agent.id, content,
      // delta 回调：追加流式文本
      (delta) => {
        if (activeConvRef.current !== convId) return;  // 防止串扰
        assistantContent += delta; setStreamingContent(assistantContent);
      },
      // tool_call 回调：显示工具调用卡片
      (name, args) => {
        if (activeConvRef.current !== convId) return;
        setToolCalls((prev) => [...prev, { id: `tc${++msgCounter}`, name, args, isExecuting: true }]);
      },
      // tool_result 回调：更新工具结果
      (tool, output) => {
        if (activeConvRef.current !== convId) return;
        setToolCalls((prev) => prev.map((tc) => tc.name === tool && tc.isExecuting ? { ...tc, output, isExecuting: false } : tc));
      },
      // done 回调：将流式文本固化到消息列表
      () => {
        if (activeConvRef.current !== convId) return;
        if (assistantContent) setMessages((prev) => [...prev, { id: `a${++msgCounter}`, role: "assistant", content: assistantContent }]);
        setStreamingContent("");
      },
      // error 回调
      (errMsg) => {
        if (activeConvRef.current !== convId) return;
        setError(errMsg); setStreamingContent("");
      },
      // title_updated 回调：通知父组件
      (title: string) => {
        if (activeConvRef.current !== convId) return;
        onTitleUpdated?.(title);
      },
    );
  }, [agent, conversation, startStream, onTitleUpdated]);

  // 合并消息和中间工具调用卡片的渲染列表
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

  // 未选择 Agent 时的欢迎页面
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
      {/* 顶部 Agent 信息栏 */}
      <div className="border-b bg-card/50 backdrop-blur-sm px-6 py-3 flex items-center gap-3 shrink-0">
        <span className="text-xl">{agent.avatar}</span>
        <div>
          <h2 className="font-semibold text-sm">{agent.name}</h2>
          <p className="text-xs text-muted-foreground">{agent.model.split("/")[1] || agent.model}</p>
        </div>
      </div>

      {/* 消息区域 — 可滚动 */}
      <ScrollArea className="flex-1 px-6 custom-scrollbar">
        <div className="max-w-3xl mx-auto py-4">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg">Start a conversation with {agent.name}</p>
              <p className="text-sm mt-1">Ask anything — I can search the web, run code, and more.</p>
            </div>
          )}

          {/* 历史消息 */}
          {messages.map((msg) => <MessageBubble key={msg.id} role={msg.role} content={msg.content} />)}

          {/* 工具调用卡片 */}
          {toolCalls.map((tc) => <ToolCallCard key={tc.id} name={tc.name} args={tc.args} output={tc.output} isExecuting={tc.isExecuting} />)}

          {/* "Thinking..." 加载动画 — 流已启动但尚无文本时显示 */}
          {isStreaming && !streamingContent && (
            <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm animate-fade-in">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}

          {/* 流式文本渲染 — 实时 Markdown */}
          {streamingContent && !messages.some((m) => m.role === "assistant" && m.content === streamingContent) && (
            <MessageBubble role="assistant" content={streamingContent} isStreaming />
          )}

          {/* 错误提示 */}
          {error && (
            <div className="my-3 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive animate-fade-in">
              {error}
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* 底部输入框 */}
      <MessageInput onSend={handleSend} isStreaming={isStreaming} onStop={stopStream} />
    </div>
  );
}