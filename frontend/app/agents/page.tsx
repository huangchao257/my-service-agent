"use client";

/**
 * Agents 管理页面 — Agent 的列表、创建和编辑
 *
 * 网格布局展示所有 Agent 卡片，支持创建新 Agent 和编辑现有 Agent。
 * 通过 AgentForm 弹窗进行创建/编辑操作。
 */

import { useEffect, useState, useCallback } from "react";
import { ArrowLeft, Plus, Bot } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/agents/agent-card";
import { AgentForm } from "@/components/agents/agent-form";
import { api, Agent } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAgents = useCallback(() => {
    api.listAgents().then(setAgents).catch(console.error).finally(() => setLoading(false));
  }, []);
  useEffect(() => { loadAgents(); }, [loadAgents]);

  const handleSave = useCallback(async (data: Partial<Agent>) => {
    if (editingAgent) await api.updateAgent(editingAgent.id, data);
    else await api.createAgent(data);
    setEditingAgent(null);
    loadAgents();
  }, [editingAgent, loadAgents]);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/chat"><Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button></Link>
          <h1 className="text-2xl font-bold flex-1">Agent Management</h1>
          <Button onClick={() => { setEditingAgent(null); setFormOpen(true); }} className="rounded-xl"><Plus className="mr-2 h-4 w-4" />Create Agent</Button>
        </div>

        {/* 加载骨架屏 */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="h-32 rounded-xl bg-muted animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} onEdit={(a) => { setEditingAgent(a); setFormOpen(true); }} onDelete={async (id) => { await api.deleteAgent(id); loadAgents(); }} />
            ))}
            {agents.length === 0 && (
              <div className="col-span-2 text-center py-16">
                <Bot className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground text-lg">No agents yet</p>
                <p className="text-muted-foreground/70 text-sm mt-1">Create your first agent to get started.</p>
              </div>
            )}
          </div>
        )}
        <AgentForm open={formOpen} onClose={() => { setFormOpen(false); setEditingAgent(null); }} onSave={handleSave} agent={editingAgent} />
      </div>
    </div>
  );
}