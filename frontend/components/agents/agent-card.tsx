"use client";

import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Agent } from "@/lib/api";

interface AgentCardProps { agent: Agent; onEdit: (agent: Agent) => void; onDelete: (id: string) => void }

export function AgentCard({ agent, onEdit, onDelete }: AgentCardProps) {
  return (
    <Card className="hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 rounded-xl">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{agent.avatar}</span>
            <div>
              <h3 className="font-semibold">{agent.name}</h3>
              <p className="text-xs text-muted-foreground">{agent.model}</p>
            </div>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(agent)}><Pencil className="h-4 w-4" /></Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onDelete(agent.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2 mt-2">{agent.system_prompt}</p>
        {agent.tools.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {agent.tools.map((t) => (
              <span key={t} className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">{t}</span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}