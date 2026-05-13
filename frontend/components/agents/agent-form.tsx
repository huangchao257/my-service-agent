"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Agent } from "@/lib/api";

interface AgentFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Agent>) => Promise<void>;
  agent?: Agent | null;
}

const BUILTIN_TOOLS = ["calculator", "get_current_time", "web_search", "read_file", "write_file", "execute_code"];

export function AgentForm({ open, onClose, onSave, agent }: AgentFormProps) {
  const [name, setName] = useState(agent?.name || "");
  const [avatar, setAvatar] = useState(agent?.avatar || "🤖");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || "");
  const [model, setModel] = useState(agent?.model || "");
  const [tools, setTools] = useState<string[]>(agent?.tools || []);
  const [temperature, setTemperature] = useState(agent?.temperature ?? 0.7);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (agent) { setName(agent.name); setAvatar(agent.avatar); setSystemPrompt(agent.system_prompt); setModel(agent.model); setTools(agent.tools); setTemperature(agent.temperature); }
  }, [agent]);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ name, avatar, system_prompt: systemPrompt, model, tools, temperature });
    setSaving(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{agent ? "Edit Agent" : "Create Agent"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="w-16"><label className="text-sm font-medium">Avatar</label><Input value={avatar} onChange={(e) => setAvatar(e.target.value)} className="text-center text-xl" maxLength={2} /></div>
            <div className="flex-1"><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name" /></div>
          </div>
          <div><label className="text-sm font-medium">Model</label><Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o or provider/gpt-4o" /></div>
          <div><label className="text-sm font-medium">System Prompt</label><Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} placeholder="You are a helpful assistant..." rows={4} /></div>
          <div><label className="text-sm font-medium">Temperature: {temperature}</label><input type="range" min="0" max="2" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full" /></div>
          <div><label className="text-sm font-medium">Tools</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {BUILTIN_TOOLS.map((tool) => (
                <Button key={tool} variant={tools.includes(tool) ? "default" : "outline"} size="sm" onClick={() => setTools((prev) => prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool])}>{tool}</Button>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !model || saving}>{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}