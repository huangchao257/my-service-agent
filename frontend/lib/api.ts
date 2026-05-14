const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  system_prompt: string;
  model: string;
  tools: string[];
  mcp_servers: string[];
  skills: string[];
  temperature: number;
  max_tokens: number;
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
  api_key: string;
  models: string[];
  is_active: boolean;
}

export interface MCPServer {
  id: string;
  name: string;
  transport: string;
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
  prompt_template: string;
  category: string;
  is_active: boolean;
}

export interface ModelOption {
  value: string;
  label: string;
  provider_name: string;
  provider_id: string;
}

export interface Memory {
  id: string;
  agent_id: string;
  conversation_id: string | null;
  content: string;
  created_at: string;
}

export interface LLMInteraction {
  id: string;
  agent_id: string;
  conversation_id: string | null;
  model: string;
  messages_json: string;
  response_json: string | null;
  token_usage_json: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface LLMInteractionList {
  items: LLMInteraction[];
  total: number;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listAgents: () => fetchJson<Agent[]>("/api/agents"),
  createAgent: (data: Partial<Agent>) =>
    fetchJson<Agent>("/api/agents", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: string, data: Partial<Agent>) =>
    fetchJson<Agent>(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAgent: (id: string) =>
    fetchJson<void>(`/api/agents/${id}`, { method: "DELETE" }),

  listConversations: (agentId?: string) =>
    fetchJson<Conversation[]>(`/api/conversations${agentId ? `?agent_id=${agentId}` : ""}`),
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

  listProviders: () => fetchJson<Provider[]>("/api/providers"),
  createProvider: (data: Partial<Provider>) =>
    fetchJson<Provider>("/api/providers", { method: "POST", body: JSON.stringify(data) }),
  updateProvider: (id: string, data: Partial<Provider>) =>
    fetchJson<Provider>(`/api/providers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProvider: (id: string) =>
    fetchJson<void>(`/api/providers/${id}`, { method: "DELETE" }),
  listModels: () => fetchJson<ModelOption[]>("/api/providers/models"),

  listMCPServers: () => fetchJson<MCPServer[]>("/api/mcp-servers"),
  createMCPServer: (data: Partial<MCPServer>) =>
    fetchJson<MCPServer>("/api/mcp-servers", { method: "POST", body: JSON.stringify(data) }),
  updateMCPServer: (id: string, data: Partial<MCPServer>) =>
    fetchJson<MCPServer>(`/api/mcp-servers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteMCPServer: (id: string) =>
    fetchJson<void>(`/api/mcp-servers/${id}`, { method: "DELETE" }),

  listSkills: () => fetchJson<Skill[]>("/api/skills"),
  createSkill: (data: Partial<Skill>) =>
    fetchJson<Skill>("/api/skills", { method: "POST", body: JSON.stringify(data) }),
  updateSkill: (id: string, data: Partial<Skill>) =>
    fetchJson<Skill>(`/api/skills/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSkill: (id: string) =>
    fetchJson<void>(`/api/skills/${id}`, { method: "DELETE" }),

  listMemories: (params?: { agent_id?: string; conversation_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.agent_id) qs.set("agent_id", params.agent_id);
    if (params?.conversation_id) qs.set("conversation_id", params.conversation_id);
    const q = qs.toString();
    return fetchJson<Memory[]>(`/api/memories${q ? `?${q}` : ""}`);
  },
  deleteMemory: (id: string) =>
    fetchJson<void>(`/api/memories/${id}`, { method: "DELETE" }),

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