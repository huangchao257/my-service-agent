"use client";

import { useState } from "react";
import { Sidebar } from "@/components/chat/sidebar";
import { ChatArea } from "@/components/chat/chat-area";
import { Agent, Conversation, api } from "@/lib/api";

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);

  return (
    <div className="flex h-screen">
      <Sidebar
        selectedAgent={selectedAgent}
        activeConversationId={activeConversation?.id ?? null}
        onSelectAgent={(agent) => { setSelectedAgent(agent); setActiveConversation(null); }}
        onSelectConversation={setActiveConversation}
        onNewConversation={async () => {
          if (!selectedAgent) return;
          const conv = await api.createConversation(selectedAgent.id);
          setActiveConversation(conv);
        }}
      />
      <ChatArea agent={selectedAgent} conversation={activeConversation} />
    </div>
  );
}