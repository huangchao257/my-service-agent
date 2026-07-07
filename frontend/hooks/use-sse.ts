"use client";

/**
 * SSE Hook — 管理与后端流式聊天的连接
 *
 * 解析 SSE (Server-Sent Events) 协议的事件流：
 *   delta → 文本增量
 *   tool_call → 工具调用
 *   tool_result → 工具结果
 *   confirmation_required → 高风险工具需用户确认
 *   title_updated → 会话标题更新
 *   done → 对话完成（可携带 token_usage）
 *   error → 错误
 *
 * 提供 startStream（发送新消息）、regenerate（重生最后一轮）、stopStream 方法。
 */

import { useCallback, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StreamCallbacks {
  onDelta: (content: string) => void;
  onToolCall: (name: string, args: string) => void;
  onToolResult: (tool: string, output: string) => void;
  onDone: (tokenUsage?: unknown) => void;
  onError: (msg: string) => void;
  onTitleUpdated?: (title: string) => void;
  onConfirmationRequired?: (tool: string, args: string) => void;
}

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runStream = useCallback(
    async (url: string, body: unknown, convId: string, cb: StreamCallbacks) => {
      setIsStreaming(true);
      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: abort.signal,
        });

        if (!res.ok || !res.body) {
          cb.onError(`HTTP ${res.status}`);
          setIsStreaming(false);
          return;
        }

        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";

        // SSE 协议解析循环
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";  // 保留未完成的行

          let eventType = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = line.slice(6);
              // 根据事件类型分发到不同的回调
              if (eventType === "delta") {
                const parsed = JSON.parse(data);
                cb.onDelta(parsed.content);
              } else if (eventType === "tool_call") {
                const parsed = JSON.parse(data);
                cb.onToolCall(parsed.name, parsed.arguments);
              } else if (eventType === "tool_result") {
                const parsed = JSON.parse(data);
                cb.onToolResult(parsed.tool, parsed.output);
              } else if (eventType === "confirmation_required") {
                const parsed = JSON.parse(data);
                cb.onConfirmationRequired?.(parsed.tool, parsed.arguments);
              } else if (eventType === "done") {
                const parsed = JSON.parse(data);
                cb.onDone(parsed.token_usage);
              } else if (eventType === "title_updated") {
                const parsed = JSON.parse(data);
                cb.onTitleUpdated?.(parsed.title);
              } else if (eventType === "error") {
                const parsed = JSON.parse(data);
                cb.onError(parsed.message);
              }
            }
          }
        }
      } catch (err: unknown) {
        // AbortError 是用户主动取消，不需要报错
        if (err instanceof Error && err.name !== "AbortError") {
          cb.onError(err.message);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [],
  );

  const startStream = useCallback(
    async (
      conversationId: string,
      agentId: string,
      message: string,
      onDelta: (content: string) => void,
      onToolCall: (name: string, args: string) => void,
      onToolResult: (tool: string, output: string) => void,
      onDone: () => void,
      onError: (msg: string) => void,
      onTitleUpdated?: (title: string) => void,
      onConfirmationRequired?: (tool: string, args: string) => void,
    ) => {
      const convId = conversationId;
      await runStream(
        `${API_URL}/api/chat/${conversationId}`,
        { message, agent_id: agentId },
        convId,
        {
          onDelta, onToolCall, onToolResult,
          onDone: () => onDone(),
          onError, onTitleUpdated, onConfirmationRequired,
        },
      );
    },
    [runStream],
  );

  const regenerate = useCallback(
    async (
      conversationId: string,
      agentId: string,
      cb: StreamCallbacks,
    ) => {
      await runStream(
        `${API_URL}/api/chat/${conversationId}/regenerate`,
        { agent_id: agentId },
        conversationId,
        cb,
      );
    },
    [runStream],
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    readerRef.current?.cancel();
    setIsStreaming(false);
  }, []);

  return { isStreaming, startStream, regenerate, stopStream };
}
