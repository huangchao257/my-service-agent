"use client";

/**
 * ProviderCard — LLM Provider 卡片组件
 *
 * 显示 Provider 的名称、激活状态、API 地址、脱敏后的 Key 和模型列表。
 * 提供连通性测试与模型列表刷新按钮。
 */

import { useState } from "react";
import { Pencil, Trash2, CheckCircle, XCircle, Zap, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Provider, api } from "@/lib/api";

interface ProviderCardProps { provider: Provider; onEdit: (provider: Provider) => void; onDelete: (id: string) => void; onChanged?: () => void }

export function ProviderCard({ provider, onEdit, onDelete, onChanged }: ProviderCardProps) {
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.testProvider(provider.id);
      setTestResult(r);
    } catch (e) {
      setTestResult({ ok: false, detail: String(e) });
    } finally {
      setTesting(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshProviderModels(provider.id);
      onChanged?.();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{provider.name}</h3>
            {/* 激活状态指示 */}
            {provider.is_active ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" title="Test connection" onClick={handleTest} disabled={testing}>
              <Zap className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" title="Refresh models" onClick={handleRefresh} disabled={refreshing}>
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => onEdit(provider)}><Pencil className="h-4 w-4" /></Button>
            <Button variant="ghost" size="icon" onClick={() => onDelete(provider.id)}><Trash2 className="h-4 w-4" /></Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{provider.api_base}</p>
        <p className="text-xs font-mono mt-1">{provider.api_key}</p>  {/* 已脱敏的 API Key */}
        <div className="flex flex-wrap gap-1 mt-2">
          {provider.models.map((m) => <span key={m} className="text-xs bg-secondary px-2 py-0.5 rounded-full">{m}</span>)}
        </div>
        {testResult && (
          <p className={`text-xs mt-2 ${testResult.ok ? "text-green-600" : "text-red-600"}`}>
            {testResult.ok ? "✓ " : "✗ "}{testResult.detail}
          </p>
        )}
      </CardContent>
    </Card>
  );
}