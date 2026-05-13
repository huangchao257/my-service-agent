"use client";

import { useState } from "react";
import { Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ToolCallCardProps {
  name: string;
  args: string;
  output?: string;
  isExecuting?: boolean;
}

export function ToolCallCard({ name, args, output, isExecuting }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="flex justify-start py-2">
      <Card className="max-w-[70%] border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
        <CardContent className="p-3">
          <button className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400 w-full"
            onClick={() => setExpanded(!expanded)}>
            <Wrench className="h-4 w-4" />
            {isExecuting ? `Calling ${name}...` : `Called ${name}`}
            {output && (expanded ? <ChevronDown className="h-4 w-4 ml-auto" /> : <ChevronRight className="h-4 w-4 ml-auto" />)}
          </button>
          {expanded && (
            <div className="mt-2 text-xs space-y-1">
              <div><span className="font-medium">Args:</span> <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">{args}</code></div>
              {output && (
                <div><span className="font-medium">Result:</span>
                  <pre className="mt-1 bg-amber-100 dark:bg-amber-900 p-2 rounded text-xs whitespace-pre-wrap">{output}</pre>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}