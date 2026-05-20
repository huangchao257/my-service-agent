"use client";

/**
 * MCPForm — MCP Server 配置创建/编辑弹窗
 *
 * 根据 transport 类型动态显示不同的配置字段：
 * - stdio: Command + Args (JSON) + Env (JSON)
 * - sse: URL + Env (JSON)
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { MCPServer } from "@/lib/api";

interface MCPFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<MCPServer>) => Promise<void>;
  server?: MCPServer | null;
}

export function MCPForm({ open, onClose, onSave, server }: MCPFormProps) {
  const [name, setName] = useState(server?.name || "");
  const [transport, setTransport] = useState(server?.transport || "stdio");
  const [command, setCommand] = useState(server?.command || "");
  const [argsJson, setArgsJson] = useState(server?.args_json || "[]");
  const [url, setUrl] = useState(server?.url || "");
  const [envJson, setEnvJson] = useState(server?.env_json || "{}");
  const [isActive, setIsActive] = useState(server?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (server) {
      setName(server.name); setTransport(server.transport); setCommand(server.command || "");
      setArgsJson(server.args_json); setUrl(server.url || ""); setEnvJson(server.env_json);
      setIsActive(server.is_active);
    }
  }, [server]);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ name, transport, command: command || null, args_json: argsJson, url: url || null, env_json: envJson, is_active: isActive });
    setSaving(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{server ? "Edit MCP Server" : "Add MCP Server"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My MCP Server" /></div>

          {/* 传输方式选择 */}
          <div>
            <label className="text-sm font-medium">Transport</label>
            <select className="w-full mt-1 rounded-md border px-3 py-2 text-sm" value={transport} onChange={(e) => setTransport(e.target.value)}>
              <option value="stdio">stdio</option>
              <option value="sse">sse</option>
            </select>
          </div>

          {/* stdio 模式：命令 + 参数 */}
          {transport === "stdio" && (
            <>
              <div><label className="text-sm font-medium">Command</label><Input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="npx or python or uvx" /></div>
              <div><label className="text-sm font-medium">Args (JSON array)</label><Input value={argsJson} onChange={(e) => setArgsJson(e.target.value)} placeholder='["-m", "my_mcp_server"]' /></div>
            </>
          )}

          {/* sse 模式：URL */}
          {transport === "sse" && (
            <div><label className="text-sm font-medium">URL</label><Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://localhost:3001/sse" /></div>
          )}

          <div><label className="text-sm font-medium">Env (JSON)</label><Textarea value={envJson} onChange={(e) => setEnvJson(e.target.value)} placeholder='{"KEY": "value"}' rows={3} /></div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || saving}>{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}