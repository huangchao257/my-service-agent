"use client";

/**
 * ToolCallCard — 工具调用卡片组件
 *
 * 显示 Agent 调用工具的过程：
 * - 执行中：旋转加载图标 + "Calling {name}..."
 * - 执行完成：扳手图标 + 可展开的参数和结果
 *
 * 使用 memo 优化渲染性能。
 */

import { memo, useState } from "react";
import { Wrench, ChevronDown, Loader2 } from "lucide-react";

interface ToolCallCardProps {
  name: string;       // 工具名称
  args: string;       // 调用参数（JSON 字符串）
  output?: string;    // 工具返回结果
  isExecuting?: boolean;  // 是否正在执行中
}

export const ToolCallCard = memo(function ToolCallCard({ name, args, output, isExecuting }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(isExecuting || false);  // 执行时自动展开

  return (
    <div className="flex justify-start py-1.5 animate-fade-in">
      <div className="max-w-[75%] rounded-xl border border-primary/20 bg-primary/5 px-3 py-2">
        <button
          className="flex items-center gap-2 text-sm font-medium text-primary w-full"
          onClick={() => setExpanded(!expanded)}
        >
          {isExecuting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Wrench className="h-3.5 w-3.5" />
          )}
          <span>{isExecuting ? `Calling ${name}...` : `Called ${name}`}</span>
          <ChevronDown className={`h-4 w-4 ml-auto transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>
        {/* 展开区域：参数和结果 */}
        {expanded && (
          <div className="mt-2 text-xs space-y-1.5 animate-fade-in">
            {args && (
              <div>
                <span className="font-medium text-muted-foreground">Args: </span>
                <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{args}</code>
              </div>
            )}
            {output && (
              <div>
                <span className="font-medium text-muted-foreground">Result: </span>
                <pre className="mt-1 bg-muted p-2 rounded-md text-xs whitespace-pre-wrap max-h-40 overflow-y-auto custom-scrollbar">{output}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});