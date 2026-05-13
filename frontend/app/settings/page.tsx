"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ProviderCard } from "@/components/providers/provider-card";
import { ProviderForm } from "@/components/providers/provider-form";
import { api, Provider } from "@/lib/api";

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);

  const loadProviders = () => { api.listProviders().then(setProviders).catch(console.error); };
  useEffect(() => { loadProviders(); }, []);

  const handleSave = async (data: Partial<Provider>) => {
    if (editingProvider) await api.updateProvider(editingProvider.id, data);
    else await api.createProvider(data);
    setEditingProvider(null);
    loadProviders();
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-6">
          <Link href="/chat"><Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button></Link>
          <h1 className="text-2xl font-bold flex-1">Settings</h1>
        </div>
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">LLM Providers</h2>
            <Button size="sm" onClick={() => { setEditingProvider(null); setFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Add Provider</Button>
          </div>
          <div className="space-y-3">
            {providers.map((p) => <ProviderCard key={p.id} provider={p} onEdit={(provider) => { setEditingProvider(provider); setFormOpen(true); }} onDelete={async (id) => { await api.deleteProvider(id); loadProviders(); }} />)}
            {providers.length === 0 && <p className="text-muted-foreground text-center py-8">No providers configured. Add an LLM provider to start.</p>}
          </div>
        </div>
        <ProviderForm open={formOpen} onClose={() => { setFormOpen(false); setEditingProvider(null); }} onSave={handleSave} provider={editingProvider} />
      </div>
    </div>
  );
}