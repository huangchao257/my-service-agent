"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, Conversation } from "@/lib/api";
import { isToday, isYesterday } from "date-fns";

interface ConversationListProps {
  agentId: string | null;
  activeId: string | null;
  onSelect: (conv: Conversation) => void;
  onNew: () => void;
}

export function ConversationList({ agentId, activeId, onSelect, onNew }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    if (agentId) {
      api.listConversations(agentId).then(setConversations).catch(console.error);
    } else {
      setConversations([]);
    }
  }, [agentId]);

  const groupByDate = (convs: Conversation[]) => {
    const groups: Record<string, Conversation[]> = { Today: [], Yesterday: [], Earlier: [] };
    convs.forEach((c) => {
      const d = new Date(c.created_at);
      if (isToday(d)) groups["Today"].push(c);
      else if (isYesterday(d)) groups["Yesterday"].push(c);
      else groups["Earlier"].push(c);
    });
    return Object.entries(groups).filter(([, v]) => v.length > 0);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-3">
        <Button className="w-full" onClick={onNew} disabled={!agentId}>
          <Plus className="mr-2 h-4 w-4" />New Chat
        </Button>
      </div>
      <ScrollArea className="flex-1 px-3">
        {groupByDate(conversations).map(([group, convs]) => (
          <div key={group} className="mb-3">
            <p className="text-xs text-muted-foreground px-2 mb-1">{group}</p>
            {convs.map((conv) => (
              <div key={conv.id}
                className={`flex items-center group rounded-md px-2 py-1.5 cursor-pointer text-sm hover:bg-accent ${activeId === conv.id ? "bg-accent" : ""}`}
                onClick={() => onSelect(conv)}>
                <MessageSquare className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="truncate flex-1">{conv.title}</span>
                <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDelete(e, conv.id)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            {agentId ? "No conversations yet" : "Select an agent to start"}
          </p>
        )}
      </ScrollArea>
    </div>
  );
}