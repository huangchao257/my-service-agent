"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AgentCard } from "@/components/agents/agent-card";
import { AgentForm } from "@/components/agents/agent-form";
import { api, Agent } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

  const loadAgents = () => { api.listAgents().then(setAgents).catch(console.error); };
  useEffect(() => { loadAgents(); }, []);

  const handleSave = async (data: Partial<Agent>) => {
    if (editingAgent) await api.updateAgent(editingAgent.id, data);
    else await api.createAgent(data);
    setEditingAgent(null);
    loadAgents();
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/chat"><Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button></Link>
          <h1 className="text-2xl font-bold flex-1">Agent Management</h1>
          <Button onClick={() => { setEditingAgent(null); setFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Create Agent</Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onEdit={(a) => { setEditingAgent(a); setFormOpen(true); }} onDelete={async (id) => { await api.deleteAgent(id); loadAgents(); }} />
          ))}
          {agents.length === 0 && <p className="text-muted-foreground col-span-2 text-center py-12">No agents yet. Create your first agent to get started.</p>}
        </div>
        <AgentForm open={formOpen} onClose={() => { setFormOpen(false); setEditingAgent(null); }} onSave={handleSave} agent={editingAgent} />
      </div>
    </div>
  );
}