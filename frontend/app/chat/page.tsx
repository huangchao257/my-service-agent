"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Sidebar } from "@/components/chat/sidebar";
import { ChatArea } from "@/components/chat/chat-area";
import { Agent, Conversation, api } from "@/lib/api";

function ChatContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const convParam = searchParams.get("conv");

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [convRefreshKey, setConvRefreshKey] = useState(0);
  const [loadingConv, setLoadingConv] = useState(!!convParam);

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
          router.replace("/chat");
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

  const handleSelectConversation = useCallback((conv: Conversation) => {
    setActiveConversation(conv);
    router.replace(`/chat?conv=${conv.id}`, { scroll: false });
  }, [router]);

  const handleSelectAgent = useCallback((agent: Agent) => {
    setSelectedAgent(agent);
    setActiveConversation(null);
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
          setConvRefreshKey((k) => k + 1);
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