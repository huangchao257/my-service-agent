const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  system_prompt: string;
  model: string;
  tools: string[];
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
};