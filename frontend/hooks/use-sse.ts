"use client";

import { useCallback, useRef, useState } from "react";

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    async (
      conversationId: string,
      agentId: string,
      message: string,
      onDelta: (content: string) => void,
      onToolCall: (name: string, args: string) => void,
      onToolResult: (tool: string, output: string) => void,
      onDone: () => void,
      onError: (msg: string) => void
    ) => {
      setIsStreaming(true);
      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_URL}/api/chat/${conversationId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, agent_id: agentId }),
          signal: abort.signal,
        });

        if (!res.ok || !res.body) {
          onError(`HTTP ${res.status}`);
          setIsStreaming(false);
          return;
        }

        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (eventType === "delta") {
                const parsed = JSON.parse(data);
                onDelta(parsed.content);
              } else if (eventType === "tool_call") {
                const parsed = JSON.parse(data);
                onToolCall(parsed.name, parsed.arguments);
              } else if (eventType === "tool_result") {
                const parsed = JSON.parse(data);
                onToolResult(parsed.tool, parsed.output);
              } else if (eventType === "done") {
                onDone();
              } else if (eventType === "error") {
                const parsed = JSON.parse(data);
                onError(parsed.message);
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          onError(err.message);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    readerRef.current?.cancel();
    setIsStreaming(false);
  }, []);

  return { isStreaming, startStream, stopStream };
}