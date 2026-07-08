"use client";

/**
 * 工具广场 — 用户可直接选择内置工具、填写参数并运行，无需通过 Agent 对话。
 *
 * 左侧：按分类分组的工具列表
 * 右侧：选中工具的参数表单（根据 JSON Schema 自动渲染）+ 运行按钮 + 结果展示
 * 高风险工具需勾选确认框后才能运行。
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Play, Loader2, AlertTriangle, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ToolInfo, api } from "@/lib/api";

type ParamSpec = { type?: string; description?: string; default?: unknown };
type JsonSchema = { type?: string; properties?: Record<string, ParamSpec>; required?: string[] };

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [selected, setSelected] = useState<ToolInfo | null>(null);
  const [args, setArgs] = useState<Record<string, string>>({});
  const [confirmHighRisk, setConfirmHighRisk] = useState(false);
  const [search, setSearch] = useState("");
  const [result, setResult] = useState<{ success: boolean; result: string; duration_ms: number } | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listTools().then(setTools).catch((e) => setError(e.message));
  }, []);

  // 按分类分组，固定分类优先
  const groups = useMemo(() => {
    const order = ["system", "web", "file", "code", "dev", "general"];
    const g: Record<string, ToolInfo[]> = {};
    for (const t of tools) {
      if (search && !t.name.includes(search) && !t.description.toLowerCase().includes(search.toLowerCase())) continue;
      (g[t.category] ||= []).push(t);
    }
    return Object.entries(g).sort(([a], [b]) => {
      const ia = order.indexOf(a), ib = order.indexOf(b);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib) || a.localeCompare(b);
    });
  }, [tools, search]);

  const schema: JsonSchema | null = selected ? (selected.parameters as JsonSchema) : null;
  const props = schema?.properties || {};
  const required = schema?.required || [];

  const selectTool = (t: ToolInfo) => {
    setSelected(t);
    setResult(null);
    setError("");
    setConfirmHighRisk(false);
    // 用默认值初始化参数
    const init: Record<string, string> = {};
    for (const [k, spec] of Object.entries(props)) {
      if (spec.default !== undefined) init[k] = String(spec.default);
    }
    setArgs(init);
  };

  const handleRun = async () => {
    if (!selected) return;
    setRunning(true);
    setError("");
    setResult(null);
    try {
      // 把表单字符串值按 schema 类型转换
      const payload: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(args)) {
        if (v === "") continue;
        const t = props[k]?.type;
        if (t === "integer") payload[k] = parseInt(v, 10);
        else if (t === "number") payload[k] = parseFloat(v);
        else if (t === "boolean") payload[k] = v === "true" || v === "1";
        else payload[k] = v;
      }
      const res = await api.runTool(selected.name, payload, confirmHighRisk);
      setResult(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/chat"><Button variant="ghost" size="icon"><ArrowLeft className="h-5 w-5" /></Button></Link>
          <h1 className="text-xl font-semibold">工具广场</h1>
          <span className="text-xs text-muted-foreground">{tools.length} 个工具，可直接运行</span>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* 左侧工具列表 */}
          <Card className="col-span-5 h-[70vh] flex flex-col">
            <CardHeader className="pb-2">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜索工具..." className="pl-8" />
              </div>
            </CardHeader>
            <ScrollArea className="flex-1 custom-scrollbar">
              <CardContent className="pt-0">
                {groups.map(([group, items]) => (
                  <div key={group} className="mb-3">
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1 px-1">{group}</p>
                    {items.map((t) => (
                      <button
                        key={t.name}
                        onClick={() => selectTool(t)}
                        className={`w-full text-left rounded-lg px-2 py-1.5 text-sm transition-colors ${selected?.name === t.name ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"}`}
                      >
                        <div className="flex items-center gap-1.5">
                          {t.risk === "high" && <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />}
                          <span className="font-mono">{t.name}</span>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{t.description}</p>
                      </button>
                    ))}
                  </div>
                ))}
              </CardContent>
            </ScrollArea>
          </Card>

          {/* 右侧参数表单与结果 */}
          <Card className="col-span-7 h-[70vh] flex flex-col">
            <CardContent className="flex-1 flex flex-col p-4 overflow-hidden">
              {!selected ? (
                <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
                  从左侧选择一个工具开始
                </div>
              ) : (
                <>
                  <div className="mb-3">
                    <div className="flex items-center gap-2">
                      <h2 className="font-mono font-semibold">{selected.name}</h2>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${riskColor(selected.risk)}`}>{selected.risk}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary">{selected.category}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{selected.description}</p>
                  </div>

                  <ScrollArea className="flex-1 custom-scrollbar">
                    <div className="space-y-3 pr-2">
                      {Object.keys(props).length === 0 && (
                        <p className="text-sm text-muted-foreground">该工具无需参数，直接运行即可。</p>
                      )}
                      {Object.entries(props).map(([key, spec]) => (
                        <div key={key}>
                          <label className="text-xs font-medium">
                            {key}
                            {required.includes(key) && <span className="text-destructive ml-0.5">*</span>}
                            <span className="text-muted-foreground ml-1 font-normal">({spec.type || "any"})</span>
                          </label>
                          {spec.description && <p className="text-[11px] text-muted-foreground mb-1">{spec.description}</p>}
                          {renderInput(key, spec, args[key] ?? "", (v) => setArgs((p) => ({ ...p, [key]: v })))}
                        </div>
                      ))}

                      {selected.risk === "high" && (
                        <label className="flex items-start gap-2 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-700 dark:text-amber-400">
                          <input type="checkbox" checked={confirmHighRisk} onChange={(e) => setConfirmHighRisk(e.target.checked)} className="mt-0.5" />
                          <span>这是高风险工具，我已知晓风险并确认执行。</span>
                        </label>
                      )}

                      {error && (
                        <div className="p-2 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive">{error}</div>
                      )}

                      {result && (
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-xs font-medium">结果</p>
                            <span className={`text-[11px] ${result.success ? "text-green-600" : "text-red-600"}`}>
                              {result.success ? "✓ success" : "✗ failed"} · {result.duration_ms}ms
                            </span>
                          </div>
                          <pre className="text-xs font-mono p-3 rounded-lg bg-muted overflow-auto max-h-64 whitespace-pre-wrap break-all">{result.result}</pre>
                        </div>
                      )}
                    </div>
                  </ScrollArea>

                  <div className="flex justify-end gap-2 mt-3 pt-3 border-t">
                    <Button onClick={handleRun} disabled={running || (selected.risk === "high" && !confirmHighRisk)}>
                      {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                      {running ? "Running..." : "Run"}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function riskColor(risk: string) {
  if (risk === "high") return "bg-amber-500/15 text-amber-700 dark:text-amber-400";
  if (risk === "medium") return "bg-blue-500/15 text-blue-700 dark:text-blue-400";
  return "bg-green-500/15 text-green-700 dark:text-green-400";
}

function renderInput(key: string, spec: ParamSpec, value: string, onChange: (v: string) => void) {
  const type = spec.type;
  if (type === "boolean") {
    return (
      <select className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={value || "false"} onChange={(e) => onChange(e.target.value)}>
        <option value="false">false</option>
        <option value="true">true</option>
      </select>
    );
  }
  // 长文本字段（description 含 "code"/"json"/"csv"/"text" 或无 type）用 Textarea
  const desc = (spec.description || "").toLowerCase();
  const multiline = type === undefined || /code|json|csv|yaml|text|content|prompt/.test(desc + key);
  if (multiline) {
    return <Textarea value={value} onChange={(e) => onChange(e.target.value)} rows={4} className="text-sm font-mono" placeholder={spec.description || key} />;
  }
  return <Input value={value} onChange={(e) => onChange(e.target.value)} className="text-sm" placeholder={spec.description || key} />;
}
