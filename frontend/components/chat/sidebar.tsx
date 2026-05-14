"use client";

import { Bot, Settings, PanelLeft, Brain, Cpu } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AgentSelector } from "./agent-selector";
import { ConversationList } from "./conversation-list";
import { Agent, Conversation } from "@/lib/api";

interface SidebarProps {
  selectedAgent: Agent | null;
  activeConversationId: string | null;
  onSelectAgent: (agent: Agent) => void;
  onSelectConversation: (conv: Conversation) => void;
  onNewConversation: () => void;
  convRefreshKey: number;
}

export function Sidebar({
  selectedAgent, activeConversationId, onSelectAgent, onSelectConversation, onNewConversation, convRefreshKey,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full w-[280px] border-r bg-sidebar">
      <div className="p-3">
        <AgentSelector selectedId={selectedAgent?.id ?? null} onSelect={onSelectAgent} />
      </div>
      <Separator />
      <div className="flex-1 overflow-hidden min-h-0">
        <ConversationList
          agentId={selectedAgent?.id ?? null}
          activeId={activeConversationId}
          onSelect={onSelectConversation} onNew={onNewConversation}
          refreshKey={convRefreshKey}
        />
      </div>
      <Separator />
      <div className="p-3 flex flex-col gap-1 shrink-0">
        <Link href="/agents">
          <Button variant="ghost" className="w-full justify-start text-sm text-muted-foreground hover:text-foreground">
            <Bot className="mr-2 h-4 w-4" />Manage Agents
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start text-sm text-muted-foreground hover:text-foreground">
            <Settings className="mr-2 h-4 w-4" />Settings
          </Button>
        </Link>
        <Link href="/llm-interactions">
          <Button variant="ghost" className="w-full justify-start text-sm text-muted-foreground hover:text-foreground">
            <Cpu className="mr-2 h-4 w-4" />LLM 交互
          </Button>
        </Link>
        <Link href="/memories">
          <Button variant="ghost" className="w-full justify-start text-sm text-muted-foreground hover:text-foreground">
            <Brain className="mr-2 h-4 w-4" />记忆管理
          </Button>
        </Link>
      </div>
    </div>
  );
}