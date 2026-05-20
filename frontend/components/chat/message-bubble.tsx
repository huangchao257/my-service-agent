"use client";

/**
 * MessageBubble — 消息气泡组件
 *
 * 用户消息：右侧蓝色气泡（Primary 色）
 * 助手消息：左侧卡片气泡，支持 Markdown 渲染（含 GFM 表格、代码高亮）
 * 流式输出时显示闪烁光标指示器
 *
 * 使用 memo 优化渲染性能。
 */

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

export const MessageBubble = memo(function MessageBubble({ role, content, isStreaming }: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 py-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      {/* 头像 */}
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium ${isUser ? "bg-primary text-primary-foreground" : "bg-gradient-to-br from-primary/20 to-primary/10 text-primary"}`}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      {/* 消息内容 */}
      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${isUser ? "bg-primary text-primary-foreground rounded-tr-md" : "bg-card border shadow-sm rounded-tl-md"}`}>
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-a:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-muted">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {content}
            </ReactMarkdown>
            {/* 流式输出光标 */}
            {isStreaming && <span className="inline-block w-1.5 h-4 bg-primary rounded-full cursor-blink ml-0.5 align-middle" />}
          </div>
        )}
      </div>
    </div>
  );
});