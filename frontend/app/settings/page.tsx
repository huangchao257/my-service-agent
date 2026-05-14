"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus, Edit3, Trash2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProviderCard } from "@/components/providers/provider-card";
import { ProviderForm } from "@/components/providers/provider-form";
import { MCPForm } from "@/components/providers/mcp-form";
import { SkillForm } from "@/components/providers/skill-form";
import { api, Provider, MCPServer, Skill } from "@/lib/api";

type Tab = "providers" | "mcp" | "skills";

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("providers");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [providerFormOpen, setProviderFormOpen] = useState(false);
  const [mcpFormOpen, setMcpFormOpen] = useState(false);
  const [skillFormOpen, setSkillFormOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [editingMcp, setEditingMcp] = useState<MCPServer | null>(null);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);

  const loadProviders = () => { api.listProviders().then(setProviders).catch(console.error); };
  const loadMcpServers = () => { api.listMCPServers().then(setMcpServers).catch(console.error); };
  const loadSkills = () => { api.listSkills().then(setSkills).catch(console.error); };

  useEffect(() => { loadProviders(); loadMcpServers(); loadSkills(); }, []);

  const handleSaveProvider = async (data: Partial<Provider>) => {
    if (editingProvider) await api.updateProvider(editingProvider.id, data);
    else await api.createProvider(data);
    setEditingProvider(null); loadProviders();
  };

  const handleSaveMcp = async (data: Partial<MCPServer>) => {
    if (editingMcp) await api.updateMCPServer(editingMcp.id, data);
    else await api.createMCPServer(data);
    setEditingMcp(null); loadMcpServers();
  };

  const handleSaveSkill = async (data: Partial<Skill>) => {
    if (editingSkill) await api.updateSkill(editingSkill.id, data);
    else await api.createSkill(data);
    setEditingSkill(null); loadSkills();
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "providers", label: "LLM Providers" },
    { key: "mcp", label: "MCP Servers" },
    { key: "skills", label: "Skills" },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/chat"><Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button></Link>
          <h1 className="text-2xl font-bold flex-1">Settings</h1>
        </div>

        <div className="flex gap-1 mb-6 border-b">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === "providers" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">LLM Providers</h2>
              <Button size="sm" onClick={() => { setEditingProvider(null); setProviderFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Add Provider</Button>
            </div>
            <div className="space-y-3">
              {providers.map((p) => <ProviderCard key={p.id} provider={p} onEdit={(pr) => { setEditingProvider(pr); setProviderFormOpen(true); }} onDelete={async (id) => { await api.deleteProvider(id); loadProviders(); }} />)}
              {providers.length === 0 && <p className="text-muted-foreground text-center py-8">No providers configured.</p>}
            </div>
          </div>
        )}

        {tab === "mcp" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">MCP Servers</h2>
              <Button size="sm" onClick={() => { setEditingMcp(null); setMcpFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Add MCP Server</Button>
            </div>
            <div className="space-y-3">
              {mcpServers.map((srv) => (
                <Card key={srv.id} className={!srv.is_active ? "opacity-50" : ""}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{srv.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {srv.transport === "stdio" ? `$ ${srv.command}` : srv.url} &middot; {srv.is_active ? "Active" : "Inactive"}
                        </p>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => { setEditingMcp(srv); setMcpFormOpen(true); }}><Edit3 className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={async () => { await api.deleteMCPServer(srv.id); loadMcpServers(); }}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {mcpServers.length === 0 && <p className="text-muted-foreground text-center py-8">No MCP servers configured.</p>}
            </div>
          </div>
        )}

        {tab === "skills" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Skills</h2>
              <Button size="sm" onClick={() => { setEditingSkill(null); setSkillFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Create Skill</Button>
            </div>
            <div className="space-y-3">
              {skills.map((sk) => (
                <Card key={sk.id} className={!sk.is_active ? "opacity-50" : ""}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{sk.name}</p>
                          <span className="text-xs bg-muted px-2 py-0.5 rounded">{sk.category}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{sk.description || "No description"}</p>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => { setEditingSkill(sk); setSkillFormOpen(true); }}><Edit3 className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={async () => { await api.deleteSkill(sk.id); loadSkills(); }}><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {skills.length === 0 && <p className="text-muted-foreground text-center py-8">No skills defined.</p>}
            </div>
          </div>
        )}

        <ProviderForm open={providerFormOpen} onClose={() => { setProviderFormOpen(false); setEditingProvider(null); }} onSave={handleSaveProvider} provider={editingProvider} />
        <MCPForm open={mcpFormOpen} onClose={() => { setMcpFormOpen(false); setEditingMcp(null); }} onSave={handleSaveMcp} server={editingMcp} />
        <SkillForm open={skillFormOpen} onClose={() => { setSkillFormOpen(false); setEditingSkill(null); }} onSave={handleSaveSkill} skill={editingSkill} />
      </div>
    </div>
  );
}