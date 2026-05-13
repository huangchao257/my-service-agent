"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Provider } from "@/lib/api";

interface ProviderFormProps {
  open: boolean; onClose: () => void; onSave: (data: Partial<Provider>) => Promise<void>; provider?: Provider | null;
}

export function ProviderForm({ open, onClose, onSave, provider }: ProviderFormProps) {
  const [name, setName] = useState(provider?.name || "");
  const [apiBase, setApiBase] = useState(provider?.api_base || "");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState(provider?.models.join(", ") || "");

  useEffect(() => {
    if (provider) { setName(provider.name); setApiBase(provider.api_base); setModels(provider.models.join(", ")); }
  }, [provider]);

  const handleSave = async () => {
    const modelList = models.split(",").map((m) => m.trim()).filter(Boolean);
    const data: Partial<Provider> = { name, api_base: apiBase, models: modelList };
    if (apiKey) data.api_key = apiKey;
    await onSave(data);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader><DialogTitle>{provider ? "Edit Provider" : "Add Provider"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="OpenAI" /></div>
          <div><label className="text-sm font-medium">API Base URL</label><Input value={apiBase} onChange={(e) => setApiBase(e.target.value)} placeholder="https://api.openai.com/v1" /></div>
          <div><label className="text-sm font-medium">API Key {provider && "(leave blank to keep current)"}</label><Input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="sk-..." /></div>
          <div><label className="text-sm font-medium">Models (comma-separated)</label><Input value={models} onChange={(e) => setModels(e.target.value)} placeholder="gpt-4o, gpt-4o-mini" /></div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !apiBase}>Save</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}