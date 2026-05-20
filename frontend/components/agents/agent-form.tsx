"use client";

/**
 * AgentForm — Agent 创建/编辑弹窗表单
 *
 * 包含：头像、名称、Provider/Model 选择、System Prompt、
 * Temperature 滑块、内置工具多选、MCP Server 多选、Skills 多选。
 *
 * Provider 和 Model 是级联选择：先选 Provider，再选该 Provider 下的模型。
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Agent, ModelOption, MCPServer, Skill, api } from "@/lib/api";

interface AgentFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Agent>) => Promise<void>;
  agent?: Agent | null;
}

// 内置工具列表
const BUILTIN_TOOLS = ["calculator", "get_current_time", "web_search", "read_file", "write_file", "execute_code"];

export function AgentForm({ open, onClose, onSave, agent }: AgentFormProps) {
  const [name, setName] = useState(agent?.name || "");
  const [avatar, setAvatar] = useState(agent?.avatar || "🤖");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || "");
  const [model, setModel] = useState(agent?.model || "");
  const [tools, setTools] = useState<string[]>(agent?.tools || []);
  const [mcpServers, setMcpServers] = useState<string[]>(agent?.mcp_servers || []);
  const [skills, setSkills] = useState<string[]>(agent?.skills || []);
  const [temperature, setTemperature] = useState(agent?.temperature ?? 0.7);
  const [saving, setSaving] = useState(false);

  const [models, setModels] = useState<ModelOption[]>([]);
  const [allMcpServers, setAllMcpServers] = useState<MCPServer[]>([]);
  const [allSkills, setAllSkills] = useState<Skill[]>([]);

  useEffect(() => {
    api.listModels().then(setModels).catch(console.error);
    api.listMCPServers().then(setAllMcpServers).catch(console.error);
    api.listSkills().then(setAllSkills).catch(console.error);
  }, [open]);

  // 编辑时回填表单
  useEffect(() => {
    if (agent) {
      setName(agent.name); setAvatar(agent.avatar); setSystemPrompt(agent.system_prompt);
      setModel(agent.model); setTools(agent.tools);
      setMcpServers(agent.mcp_servers || []); setSkills(agent.skills || []);
      setTemperature(agent.temperature);
    }
  }, [agent]);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ name, avatar, system_prompt: systemPrompt, model, tools, mcp_servers: mcpServers, skills, temperature });
    setSaving(false);
    onClose();
  };

  // Provider/Model 级联选择逻辑
  const providers = [...new Set(models.map((m) => m.provider_name))];
  const selectedProvider = model.split("/")[0] || "";
  const filteredModels = models.filter((m) => m.provider_name === selectedProvider);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{agent ? "Edit Agent" : "Create Agent"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {/* 头像 + 名称 */}
          <div className="flex gap-3">
            <div className="w-16"><label className="text-sm font-medium">Avatar</label><Input value={avatar} onChange={(e) => setAvatar(e.target.value)} className="text-center text-xl" maxLength={2} /></div>
            <div className="flex-1"><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name" /></div>
          </div>

          {/* Provider 选择 */}
          <div>
            <label className="text-sm font-medium">Provider</label>
            <select className="w-full mt-1 rounded-md border px-3 py-2 text-sm" value={selectedProvider}
              onChange={(e) => { const suffix = model.includes("/") ? model.split("/").slice(1).join("/") : ""; setModel(e.target.value ? `${e.target.value}/${suffix}` : suffix); }}>
              <option value="">Select provider...</option>
              {providers.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Model 选择（级联） */}
          <div>
            <label className="text-sm font-medium">Model</label>
            <select className="w-full mt-1 rounded-md border px-3 py-2 text-sm" value={model}
              onChange={(e) => setModel(e.target.value)} disabled={!selectedProvider}>
              <option value="">Select model...</option>
              {filteredModels.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>

          <div><label className="text-sm font-medium">System Prompt</label><Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} placeholder="You are a helpful assistant..." rows={4} /></div>

          {/* Temperature 滑块 */}
          <div><label className="text-sm font-medium">Temperature: {temperature}</label><input type="range" min="0" max="2" step="0.1" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="w-full" /></div>

          {/* 内置工具多选 */}
          <div>
            <label className="text-sm font-medium">Tools</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {BUILTIN_TOOLS.map((tool) => (
                <Button key={tool} variant={tools.includes(tool) ? "default" : "outline"} size="sm"
                  onClick={() => setTools((prev) => prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool])}>
                  {tool}
                </Button>
              ))}
            </div>
          </div>

          {/* MCP Server 多选 */}
          {allMcpServers.length > 0 && (
            <div>
              <label className="text-sm font-medium">MCP Servers</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {allMcpServers.map((srv) => (
                  <Button key={srv.id} variant={mcpServers.includes(srv.id) ? "default" : "outline"} size="sm"
                    onClick={() => setMcpServers((prev) => prev.includes(srv.id) ? prev.filter((id) => id !== srv.id) : [...prev, srv.id])}>
                    {srv.name}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Skills 多选 */}
          {allSkills.length > 0 && (
            <div>
              <label className="text-sm font-medium">Skills</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {allSkills.map((sk) => (
                  <Button key={sk.id} variant={skills.includes(sk.id) ? "default" : "outline"} size="sm"
                    onClick={() => setSkills((prev) => prev.includes(sk.id) ? prev.filter((id) => id !== sk.id) : [...prev, sk.id])}>
                    {sk.name}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !model || saving}>{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}