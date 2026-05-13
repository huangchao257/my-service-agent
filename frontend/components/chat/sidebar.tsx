"use client";

import { Bot, Settings } from "lucide-react";
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
}

export function Sidebar({
  selectedAgent, activeConversationId, onSelectAgent, onSelectConversation, onNewConversation,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full w-[280px] border-r bg-muted/30">
      <div className="p-3">
        <AgentSelector selectedId={selectedAgent?.id ?? null} onSelect={onSelectAgent} />
      </div>
      <Separator />
      <div className="flex-1 overflow-hidden">
        <ConversationList
          agentId={selectedAgent?.id ?? null}
          activeId={activeConversationId}
          onSelect={onSelectConversation} onNew={onNewConversation}
        />
      </div>
      <Separator />
      <div className="p-3 flex flex-col gap-1">
        <Link href="/agents">
          <Button variant="ghost" className="w-full justify-start text-sm">
            <Bot className="mr-2 h-4 w-4" />Manage Agents
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start text-sm">
            <Settings className="mr-2 h-4 w-4" />Settings
          </Button>
        </Link>
      </div>
    </div>
  );
}