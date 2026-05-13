"use client";

import { useEffect, useState } from "react";
import { Check, ChevronsUpDown, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api, Agent } from "@/lib/api";

interface AgentSelectorProps {
  selectedId: string | null;
  onSelect: (agent: Agent) => void;
}

export function AgentSelector({ selectedId, onSelect }: AgentSelectorProps) {
  const [open, setOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(console.error);
  }, []);

  const selected = agents.find((a) => a.id === selectedId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger>
        <Button variant="outline" role="combobox" className="w-full justify-between">
          {selected ? (
            <span className="flex items-center gap-2">
              <span>{selected.avatar}</span>
              <span className="truncate">{selected.name}</span>
            </span>
          ) : (
            <span className="flex items-center gap-2 text-muted-foreground">
              <Bot className="h-4 w-4" />Select Agent
            </span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[240px] p-0">
        <Command>
          <CommandInput placeholder="Search agents..." />
          <CommandList>
            <CommandEmpty>No agents found.</CommandEmpty>
            <CommandGroup>
              {agents.map((agent) => (
                <CommandItem key={agent.id} value={agent.name}
                  onSelect={() => { onSelect(agent); setOpen(false); }}>
                  <Check className={cn("mr-2 h-4 w-4", selectedId === agent.id ? "opacity-100" : "opacity-0")} />
                  <span className="mr-2">{agent.avatar}</span>{agent.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}