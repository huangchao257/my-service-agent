/**
 * API 客户端 — 封装所有后端接口调用
 *
 * 提供统一的 fetchJson 方法和按资源分组的 API 方法。
 * 所有接口类型定义也集中在此文件中，方便前端各组件引用。
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── 类型定义 ──

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  system_prompt: string;
  model: string;
  tools: string[];
  mcp_servers: string[];
  skills: string[];
  high_risk_tools_enabled: string[];
  temperature: number;
  max_tokens: number;
  history_limit: number;
  memory_top_k: number | null;
}

export interface Conversation {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  created_at: string;
}

export interface Provider {
  id: string;
  name: string;
  provider: string;
  api_base: string;
  api_key: string;        // 列表接口中已脱敏
  models: string[];
  is_active: boolean;
}

export interface MCPServer {
  id: string;
  name: string;
  transport: string;       // "stdio" 或 "http"
  command: string | null;
  args_json: string;
  url: string | null;
  env_json: string;
  is_active: boolean;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  prompt_template: string;  // 实际的 prompt 指令内容
  category: string;          // 分类：general / coding / writing 等
  is_active: boolean;
}

export interface ModelOption {
  value: string;           // "provider名称/model名称" 格式
  label: string;           // 显示用标签
  provider_name: string;
  provider_id: string;
}

export interface Memory {
  id: string;
  agent_id: string;
  conversation_id: string | null;  // 关联的会话 ID
  content: string;                  // 记忆文本
  created_at: string;
}

export interface LLMInteraction {
  id: string;
  agent_id: string;
  conversation_id: string | null;
  model: string;                   // 实际使用的模型名
  messages_json: string;           // 发送给模型的完整消息 JSON
  response_json: string | null;    // 模型响应 JSON
  token_usage_json: string | null; // token 用量
  duration_ms: number | null;      // 调用耗时（毫秒）
  created_at: string;
}

export interface LLMInteractionList {
  items: LLMInteraction[];
  total: number;
}

// ── 通用请求方法 ──

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;  // 204 No Content
  return res.json();
}

// ── API 方法（按资源分组） ──

export const api = {
  // Agent CRUD
  listAgents: () => fetchJson<Agent[]>("/api/agents"),
  createAgent: (data: Partial<Agent>) =>
    fetchJson<Agent>("/api/agents", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: string, data: Partial<Agent>) =>
    fetchJson<Agent>(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAgent: (id: string) =>
    fetchJson<void>(`/api/agents/${id}`, { method: "DELETE" }),
  duplicateAgent: (id: string) =>
    fetchJson<Agent>(`/api/agents/${id}/duplicate`, { method: "POST" }),

  // 会话管理
  listConversations: (agentId?: string, search?: string) => {
    const qs = new URLSearchParams();
    if (agentId) qs.set("agent_id", agentId);
    if (search) qs.set("search", search);
    const q = qs.toString();
    return fetchJson<Conversation[]>(`/api/conversations${q ? `?${q}` : ""}`);
  },
  createConversation: (agentId: string, title?: string) =>
    fetchJson<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId, title: title || "New Chat" }),
    }),
  getConversation: (id: string) =>
    fetchJson<Conversation>(`/api/conversations/${id}`),
  deleteConversation: (id: string) =>
    fetchJson<void>(`/api/conversations/${id}`, { method: "DELETE" }),
  getMessages: (conversationId: string) =>
    fetchJson<Message[]>(`/api/conversations/${conversationId}/messages`),
  exportConversation: (id: string, format: "markdown" | "json") =>
    fetch(`${API_URL}/api/conversations/${id}/export?format=${format}`).then((r) => r.blob()),

  // 聊天（SSE 流式端点直接由 use-sse.ts 调用，这里只放重生 URL 构造）
  regenerateUrl: (conversationId: string) =>
    `${API_URL}/api/chat/${conversationId}/regenerate`,

  // LLM Provider 管理
  listProviders: () => fetchJson<Provider[]>("/api/providers"),
  createProvider: (data: Partial<Provider>) =>
    fetchJson<Provider>("/api/providers", { method: "POST", body: JSON.stringify(data) }),
  updateProvider: (id: string, data: Partial<Provider>) =>
    fetchJson<Provider>(`/api/providers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProvider: (id: string) =>
    fetchJson<void>(`/api/providers/${id}`, { method: "DELETE" }),
  listModels: () => fetchJson<ModelOption[]>("/api/providers/models"),
  testProvider: (id: string) =>
    fetchJson<{ ok: boolean; detail: string }>(`/api/providers/${id}/test`, { method: "POST" }),
  refreshProviderModels: (id: string) =>
    fetchJson<Provider>(`/api/providers/${id}/refresh-models`, { method: "POST" }),

  // MCP Server 管理
  listMCPServers: () => fetchJson<MCPServer[]>("/api/mcp-servers"),
  createMCPServer: (data: Partial<MCPServer>) =>
    fetchJson<MCPServer>("/api/mcp-servers", { method: "POST", body: JSON.stringify(data) }),
  updateMCPServer: (id: string, data: Partial<MCPServer>) =>
    fetchJson<MCPServer>(`/api/mcp-servers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteMCPServer: (id: string) =>
    fetchJson<void>(`/api/mcp-servers/${id}`, { method: "DELETE" }),

  // 技能管理
  listSkills: () => fetchJson<Skill[]>("/api/skills"),
  createSkill: (data: Partial<Skill>) =>
    fetchJson<Skill>("/api/skills", { method: "POST", body: JSON.stringify(data) }),
  updateSkill: (id: string, data: Partial<Skill>) =>
    fetchJson<Skill>(`/api/skills/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSkill: (id: string) =>
    fetchJson<void>(`/api/skills/${id}`, { method: "DELETE" }),

  // 记忆管理
  listMemories: (params?: { agent_id?: string; conversation_id?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.agent_id) qs.set("agent_id", params.agent_id);
    if (params?.conversation_id) qs.set("conversation_id", params.conversation_id);
    if (params?.search) qs.set("search", params.search);
    const q = qs.toString();
    return fetchJson<Memory[]>(`/api/memories${q ? `?${q}` : ""}`);
  },
  deleteMemory: (id: string) =>
    fetchJson<void>(`/api/memories/${id}`, { method: "DELETE" }),

  // LLM 交互记录
  listLLMInteractions: (params?: { agent_id?: string; conversation_id?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.agent_id) qs.set("agent_id", params.agent_id);
    if (params?.conversation_id) qs.set("conversation_id", params.conversation_id);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    return fetchJson<LLMInteractionList>(`/api/llm-interactions?${qs.toString()}`);
  },
  getLLMInteraction: (id: string) =>
    fetchJson<LLMInteraction>(`/api/llm-interactions/${id}`),
};