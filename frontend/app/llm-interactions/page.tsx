"use client";

/**
 * LLM 交互记录页面 — 查看每次 LLM 调用的完整上下文
 *
 * 功能：
 * - 按 Agent 和会话筛选
 * - 分页列表（每页 20 条），显示模型名、消息数、耗时、时间戳
 * - 点击展开完整上下文：Messages（按 role 着色）+ 模型响应
 * - 请求详情和错误状态提示
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronDown, ChevronUp, Clock, MessageSquare, Cpu, AlertCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Agent, Conversation, LLMInteraction, api } from "@/lib/api";

// 消息角色颜色映射 — 展开时用不同背景色区分 system/user/assistant/tool
const ROLE_COLORS: Record<string, string> = {
  system: "bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-600",
  user: "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-700",
  assistant: "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-700",
  tool: "bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-700",
};

export default function LLMInteractionsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [interactions, setInteractions] = useState<LLMInteraction[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedConvId, setSelectedConvId] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<LLMInteraction | null>(null);
  const pageSize = 20;

  useEffect(() => {
    api.listAgents().then(setAgents).catch(console.error);
    api.listConversations().then(setConversations).catch(console.error);
  }, []);

  const loadInteractions = useCallback(() => {
    setLoading(true);
    setError("");
    api.listLLMInteractions({
      agent_id: selectedAgentId || undefined,
      conversation_id: selectedConvId || undefined,
      page,
      page_size: pageSize,
    })
      .then((res) => { setInteractions(res.items); setTotal(res.total); })
      .catch((err) => { console.error(err); setError(err.message || "加载失败"); })
      .finally(() => setLoading(false));
  }, [selectedAgentId, selectedConvId, page]);

  useEffect(() => {
    loadInteractions();
  }, [loadInteractions]);

  // 筛选条件变化时重置到第一页
  useEffect(() => { setPage(1); }, [selectedAgentId, selectedConvId]);

  // 展开/收起：展开时调用详情接口获取完整数据
  const handleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); setExpandedData(null); return; }
    setExpandedId(id);
    const detail = await api.getLLMInteraction(id);
    setExpandedData(detail);
  };

  const totalPages = Math.ceil(total / pageSize);
  const getAgentName = (agentId: string) => agents.find((a) => a.id === agentId)?.name || agentId;
  const getConvTitle = (convId: string) => conversations.find((c) => c.id === convId)?.title || convId;

  // 渲染消息列表，按 role 着色
  const renderMessages = (messagesJson: string) => {
    let messages: { role: string; content: string | null }[];
    try { messages = JSON.parse(messagesJson); } catch { return <p className="text-sm text-red-500">无法解析消息</p>; }
    return (
      <div className="space-y-2 max-h-[500px] overflow-y-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`p-3 rounded-lg border text-sm ${ROLE_COLORS[msg.role] || "bg-muted"}`}>
            <span className="font-semibold text-xs uppercase tracking-wide opacity-60">{msg.role}</span>
            <p className="mt-1 whitespace-pre-wrap">{msg.content || "(tool call)"}</p>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/chat">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-xl font-semibold">LLM 交互记录</h1>
        </div>

        {/* 筛选栏 */}
        <div className="flex gap-3 mb-6">
          <select
            className="flex-1 h-10 rounded-lg border bg-background px-3 text-sm"
            value={selectedAgentId}
            onChange={(e) => { setSelectedAgentId(e.target.value); setSelectedConvId(""); }}
          >
            <option value="">全部 Agent</option>
            {agents.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
          </select>
          <select
            className="flex-1 h-10 rounded-lg border bg-background px-3 text-sm"
            value={selectedConvId}
            onChange={(e) => setSelectedConvId(e.target.value)}
          >
            <option value="">全部会话</option>
            {conversations.map((c) => (<option key={c.id} value={c.id}>{c.title}</option>))}
          </select>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse"><CardContent className="p-4 h-16 bg-muted rounded-xl" /></Card>
            ))}
          </div>
        ) : interactions.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Cpu className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>暂无交互记录</p>
            <p className="text-sm mt-1">与 Agent 对话后，交互记录会自动生成</p>
          </div>
        ) : (
          <div className="space-y-3">
            {interactions.map((item) => (
              <Card key={item.id} className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => handleExpand(item.id)}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Cpu className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{item.model}</p>
                        <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
                          <span>{getAgentName(item.agent_id)}</span>
                          {item.conversation_id && <span>{getConvTitle(item.conversation_id)}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><MessageSquare className="h-3 w-3" />{(() => { try { return JSON.parse(item.messages_json).length; } catch { return "-"; } })()} msgs</span>
                      {item.duration_ms != null && (
                        <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{(item.duration_ms / 1000).toFixed(1)}s</span>
                      )}
                      {item.token_usage_json && (() => {
                        try {
                          const u = JSON.parse(item.token_usage_json);
                          if (u && u.total_tokens != null) {
                            return <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" />{u.total_tokens} tok</span>;
                          }
                        } catch { /* ignore */ }
                        return null;
                      })()}
                      <span>{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                      {expandedId === item.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>
                  {/* 展开的详情区域 */}
                  {expandedId === item.id && expandedData && (
                    <div className="mt-4 pt-4 border-t" onClick={(e) => e.stopPropagation()}>  {/* stopPropagation 防止点击详情区时收起 */}
                      <h4 className="text-sm font-semibold mb-2">完整上下文 (Messages)</h4>
                      {renderMessages(expandedData.messages_json)}
                      {expandedData.response_json && (
                        <>
                          <h4 className="text-sm font-semibold mt-4 mb-2">模型响应</h4>
                          <pre className="p-3 rounded-lg border bg-muted/50 text-xs overflow-x-auto max-h-[300px] overflow-y-auto">
                            {(() => { try { return JSON.stringify(JSON.parse(expandedData.response_json), null, 2); } catch { return expandedData.response_json; } })()}
                          </pre>
                        </>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* 分页控件 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
            <span className="text-sm text-muted-foreground">第 {page} / {totalPages} 页 (共 {total} 条)</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>下一页</Button>
          </div>
        )}
      </div>
    </div>
  );
}