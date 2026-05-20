"use client";

/**
 * ProviderCard — LLM Provider 卡片组件
 *
 * 显示 Provider 的名称、激活状态、API 地址、脱敏后的 Key 和模型列表。
 */

import { Pencil, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Provider } from "@/lib/api";

interface ProviderCardProps { provider: Provider; onEdit: (provider: Provider) => void; onDelete: (id: string) => void }

export function ProviderCard({ provider, onEdit, onDelete }: ProviderCardProps) {
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
      </CardContent>
    </Card>
  );
}