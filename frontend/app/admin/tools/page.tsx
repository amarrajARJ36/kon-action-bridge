"use client";

import React, { useEffect, useState } from "react";
import { Wrench, Code2, ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";
import { ToolRegistry } from "@/lib/types";
import { getTools } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function ToolRegistryPage() {
  const [tools, setTools] = useState<ToolRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);

  useEffect(() => {
    async function loadTools() {
      try {
        const data = await getTools();
        setTools(data);
      } catch (err) {
        console.error("Failed to load tool registry:", err);
      } finally {
        setLoading(false);
      }
    }
    loadTools();
  }, []);

  if (loading) {
    return <LoadingSpinner size="lg" label="Loading approved tools catalog..." />;
  }

  const toggleExpand = (toolName: string) => {
    setExpandedTool(expandedTool === toolName ? null : toolName);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Approved Tool Registry</h2>
        <p className="text-xs text-kon-muted mt-0.5">
          Central registry of approved commerce tools with strict JSON input schemas and permission boundaries.
        </p>
      </div>

      <div className="space-y-3">
        {tools.map((tool) => {
          const isExpanded = expandedTool === tool.tool_name;

          return (
            <div
              key={tool.id}
              className="bg-kon-dark border border-kon-border/60 rounded-xl overflow-hidden transition-all shadow-md"
            >
              <div
                onClick={() => toggleExpand(tool.tool_name)}
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-kon-surface/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-kon-surface text-kon-red">
                    <Wrench className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-white">{tool.tool_name}</span>
                      <Badge variant={tool.is_active ? "success" : "neutral"}>
                        {tool.is_active ? "Active" : "Disabled"}
                      </Badge>
                      <Badge variant={tool.permission_level === "public" ? "info" : "warning"}>
                        {tool.permission_level}
                      </Badge>
                    </div>
                    <p className="text-xs text-kon-muted mt-0.5">{tool.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-kon-muted text-xs">
                  <span className="hidden sm:inline">Input Schema</span>
                  {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
              </div>

              {isExpanded && (
                <div className="p-4 bg-kon-navy border-t border-kon-border/40 space-y-2 animate-fade-in">
                  <div className="flex items-center justify-between text-xs text-kon-muted pb-1">
                    <div className="flex items-center gap-1.5">
                      <Code2 className="w-4 h-4 text-emerald-400" />
                      <span className="font-semibold text-slate-300">Pydantic JSON Input Schema</span>
                    </div>
                    <span>Validated server-side prior to execution</span>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950 font-mono text-xs text-emerald-300 overflow-x-auto border border-slate-800">
                    {JSON.stringify(tool.input_schema, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

