"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skill } from "@/lib/api";

interface SkillFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Partial<Skill>) => Promise<void>;
  skill?: Skill | null;
}

const CATEGORIES = ["general", "coding", "writing", "analysis", "creative"];

export function SkillForm({ open, onClose, onSave, skill }: SkillFormProps) {
  const [name, setName] = useState(skill?.name || "");
  const [description, setDescription] = useState(skill?.description || "");
  const [promptTemplate, setPromptTemplate] = useState(skill?.prompt_template || "");
  const [category, setCategory] = useState(skill?.category || "general");
  const [isActive, setIsActive] = useState(skill?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (skill) {
      setName(skill.name); setDescription(skill.description); setPromptTemplate(skill.prompt_template);
      setCategory(skill.category); setIsActive(skill.is_active);
    }
  }, [skill]);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ name, description, prompt_template: promptTemplate, category, is_active: isActive });
    setSaving(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{skill ? "Edit Skill" : "Create Skill"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div><label className="text-sm font-medium">Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Code Review" /></div>
          <div><label className="text-sm font-medium">Description</label><Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Expert code review skill" /></div>
          <div>
            <label className="text-sm font-medium">Category</label>
            <select className="w-full mt-1 rounded-md border px-3 py-2 text-sm" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div><label className="text-sm font-medium">Prompt Template</label><Textarea value={promptTemplate} onChange={(e) => setPromptTemplate(e.target.value)} placeholder="You are an expert code reviewer..." rows={6} /></div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSave} disabled={!name || !promptTemplate || saving}>{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}