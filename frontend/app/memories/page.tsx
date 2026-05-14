"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Trash2, Brain, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Agent, Conversation, Memory, api } from "@/lib/api";

export default function MemoriesPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedConvId, setSelectedConvId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listAgents().then(setAgents).catch(console.error);
    api.listConversations().then(setConversations).catch(console.error);
  }, []);

  const loadMemories = useCallback(() => {
    setLoading(true);
    setError("");
    api.listMemories({
      agent_id: selectedAgentId || undefined,
      conversation_id: selectedConvId || undefined,
    })
      .then(setMemories)
      .catch((err) => { console.error(err); setError(err.message || "加载失败"); })
      .finally(() => setLoading(false));
  }, [selectedAgentId, selectedConvId]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这条记忆吗？")) return;
    await api.deleteMemory(id);
    setMemories((prev) => prev.filter((m) => m.id !== id));
  };

  const getAgentName = (agentId: string) => agents.find((a) => a.id === agentId)?.name || agentId;
  const getConvTitle = (convId: string) => conversations.find((c) => c.id === convId)?.title || convId;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-xl font-semibold">记忆管理</h1>
        </div>

        <div className="flex gap-3 mb-6">
          <select
            className="flex-1 h-10 rounded-lg border bg-background px-3 text-sm"
            value={selectedAgentId}
            onChange={(e) => { setSelectedAgentId(e.target.value); setSelectedConvId(""); }}
          >
            <option value="">全部 Agent</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <select
            className="flex-1 h-10 rounded-lg border bg-background px-3 text-sm"
            value={selectedConvId}
            onChange={(e) => setSelectedConvId(e.target.value)}
          >
            <option value="">全部会话</option>
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse"><CardContent className="p-4 h-16 bg-muted rounded-xl" /></Card>
            ))}
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Brain className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>暂无记忆数据</p>
            <p className="text-sm mt-1">与 Agent 对话后，系统会自动提取记忆</p>
          </div>
        ) : (
          <div className="space-y-3">
            {memories.map((m) => (
              <Card key={m.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                      <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                        <span>Agent: {getAgentName(m.agent_id)}</span>
                        {m.conversation_id && <span>会话: {getConvTitle(m.conversation_id)}</span>}
                        <span>{new Date(m.created_at).toLocaleString("zh-CN")}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost" size="icon-xs"
                      onClick={() => handleDelete(m.id)}
                      className="text-muted-foreground hover:text-destructive shrink-0"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}