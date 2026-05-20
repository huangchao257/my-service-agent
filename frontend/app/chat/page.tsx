"use client";

/**
 * 聊天页面 — 应用主界面
 *
 * 布局：左侧 Sidebar（Agent 选择 + 会话列表） + 右侧 ChatArea（消息显示 + 输入框）
 *
 * URL 路由：
 * - /chat → 默认页面（选择 Agent 后可新建会话）
 * - /chat?conv=<id> → 通过 URL 直接跳转到指定会话（支持分享和书签）
 *
 * 使用 Suspense 包裹 useSearchParams 的子组件（Next.js 15 要求）。
 */

import { useCallback, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Sidebar } from "@/components/chat/sidebar";
import { ChatArea } from "@/components/chat/chat-area";
import { Agent, Conversation, api } from "@/lib/api";

function ChatContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const convParam = searchParams.get("conv");  // URL 中的会话 ID

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [convRefreshKey, setConvRefreshKey] = useState(0);  // 用于触发会话列表刷新
  const [loadingConv, setLoadingConv] = useState(!!convParam);  // URL 加载中状态

  // 初始化：加载 Agent 列表，如果有 conv 参数则直接加载对应会话
  useEffect(() => {
    api.listAgents().then((agents) => {
      if (convParam && agents.length > 0) {
        api.getConversation(convParam).then((conv) => {
          const agent = agents.find((a) => a.id === conv.agent_id);
          if (agent) {
            setSelectedAgent(agent);
            setActiveConversation(conv);
          }
        }).catch(() => {
          router.replace("/chat");  // 会话不存在则回退到默认页
        }).finally(() => setLoadingConv(false));
      } else {
        if (agents.length > 0 && !selectedAgent) {
          setSelectedAgent(agents[0]);
        }
        setLoadingConv(false);
      }
    }).catch(() => {
      console.error("Failed to load agents");
      setLoadingConv(false);
    });
  }, []);

  // 选择会话时更新 URL，支持分享和书签
  const handleSelectConversation = useCallback((conv: Conversation) => {
    setActiveConversation(conv);
    router.replace(`/chat?conv=${conv.id}`, { scroll: false });
  }, [router]);

  const handleSelectAgent = useCallback((agent: Agent) => {
    setSelectedAgent(agent);
    setActiveConversation(null);  // 切换 Agent 时清空当前会话
    router.replace("/chat", { scroll: false });
  }, [router]);

  const handleNewConversation = useCallback(async () => {
    if (!selectedAgent) return;
    const conv = await api.createConversation(selectedAgent.id);
    setActiveConversation(conv);
    setConvRefreshKey((k) => k + 1);
    router.replace(`/chat?conv=${conv.id}`, { scroll: false });
  }, [selectedAgent, router]);

  if (loadingConv) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground text-sm">Loading conversation...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        selectedAgent={selectedAgent}
        activeConversationId={activeConversation?.id ?? null}
        onSelectAgent={handleSelectAgent}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        convRefreshKey={convRefreshKey}
      />
      <ChatArea
        agent={selectedAgent}
        conversation={activeConversation}
        onTitleUpdated={(title) => {
          setActiveConversation((prev) => prev ? { ...prev, title } : null);
          setConvRefreshKey((k) => k + 1);  // 标题更新后刷新侧边栏列表
        }}
      />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground text-sm">Loading...</div>
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}