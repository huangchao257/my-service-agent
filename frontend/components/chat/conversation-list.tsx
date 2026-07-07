"use client";

/**
 * ConversationList — 会话列表组件
 *
 * 按创建日期分组显示（Today / Yesterday / Earlier），
 * 支持新建、选择和删除会话。
 * 使用 refreshKey 在会话创建/标题更新后触发刷新。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { MessageSquare, Trash2, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, Conversation } from "@/lib/api";
import { isToday, isYesterday } from "date-fns";

interface ConversationListProps {
  agentId: string | null;
  activeId: string | null;
  onSelect: (conv: Conversation) => void;
  onNew: () => void;
  refreshKey: number;
}

export function ConversationList({ agentId, activeId, onSelect, onNew, refreshKey }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (agentId) {
      api.listConversations(agentId, search || undefined).then(setConversations).catch(console.error);
    } else {
      setConversations([]);
    }
  }, [agentId, refreshKey, search]);

  const handleDelete = useCallback(async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();  // 防止冒泡触发选中
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }, []);

  // 按日期分组：今天、昨天、更早
  const groups = useMemo(() => {
    const groups: Record<string, Conversation[]> = { Today: [], Yesterday: [], Earlier: [] };
    conversations.forEach((c) => {
      const d = new Date(c.created_at);
      if (isToday(d)) groups["Today"].push(c);
      else if (isYesterday(d)) groups["Yesterday"].push(c);
      else groups["Earlier"].push(c);
    });
    return Object.entries(groups).filter(([, v]) => v.length > 0);
  }, [conversations]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 space-y-2">
        <Button className="w-full rounded-xl" onClick={onNew} disabled={!agentId} size="sm">
          <Plus className="mr-2 h-4 w-4" />New Chat
        </Button>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search chats..."
            className="h-8 pl-7 text-sm rounded-lg"
          />
        </div>
      </div>
      <ScrollArea className="flex-1 px-3 custom-scrollbar">
        {groups.map(([group, convs]) => (
          <div key={group} className="mb-3">
            <p className="text-xs text-muted-foreground px-2 mb-1 font-medium">{group}</p>
            {convs.map((conv) => (
              <div key={conv.id}
                className={`flex items-center group rounded-lg px-2 py-1.5 cursor-pointer text-sm transition-colors animate-slide-in ${activeId === conv.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"}`}
                onClick={() => onSelect(conv)}>
                <MessageSquare className="mr-2 h-4 w-4 shrink-0" />
                <span className="truncate flex-1">{conv.title}</span>
                <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => handleDelete(e, conv.id)}>
                  <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
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