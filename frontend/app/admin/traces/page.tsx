"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  GitFork,
  Clock,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Search,
  RefreshCw,
  Cpu,
  ShieldCheck,
  Wrench,
  Database,
  Volume2,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
  ArrowLeft,
  Layers,
} from "lucide-react";
import { TraceSummary, TraceJourneyResponse, TraceSpan } from "@/lib/types";
import { getTraces, getTraceJourney } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

function TraceExplorerContent() {
  const searchParams = useSearchParams();
  const initialTraceId = searchParams.get("trace_id");

  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(initialTraceId);
  const [selectedJourney, setSelectedJourney] = useState<TraceJourneyResponse | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingJourney, setLoadingJourney] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [expandedSpanId, setExpandedSpanId] = useState<string | null>(null);

  const fetchTracesList = useCallback(async () => {
    try {
      setLoadingList(true);
      const list = await getTraces(40);
      setTraces(list);
      if (!selectedTraceId && list.length > 0) {
        setSelectedTraceId(list[0].trace_id);
      }
    } catch (err) {
      console.error("Failed to load traces:", err);
    } finally {
      setLoadingList(false);
    }
  }, [selectedTraceId]);

  const loadJourney = useCallback(async (traceId: string) => {
    try {
      setLoadingJourney(true);
      const journey = await getTraceJourney(traceId);
      setSelectedJourney(journey);
    } catch (err) {
      console.error("Failed to load trace journey:", err);
      setSelectedJourney(null);
    } finally {
      setLoadingJourney(false);
    }
  }, []);

  useEffect(() => {
    fetchTracesList();
  }, [fetchTracesList]);

  useEffect(() => {
    if (selectedTraceId) {
      loadJourney(selectedTraceId);
    }
  }, [selectedTraceId, loadJourney]);

  const handleCopyTraceId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStageIcon = (name: string) => {
    switch (name) {
      case "request_received":
        return Layers;
      case "ai_inference":
        return Cpu;
      case "policy_evaluation":
        return ShieldCheck;
      case "tool_execution":
        return Wrench;
      case "audit_persistence":
        return Database;
      case "avatar_response":
        return Volume2;
      default:
        return GitFork;
    }
  };

  const getStageLabel = (name: string, index: number) => {
    switch (name) {
      case "request_received":
        return "1. Request Received & Normalization";
      case "ai_inference":
        return "2. AI Inference & Tool Extraction";
      case "policy_evaluation":
        return "3. Governance Policy Evaluation";
      case "tool_execution":
        return "4. Commerce Tool Execution";
      case "audit_persistence":
        return "5. Audit Persistence (SHA-256 Chain)";
      case "avatar_response":
        return "6. Avatar Neural Audio Response";
      case "agent.chat_turn":
        return "End-to-End Chat Turn";
      default:
        return `${index + 1}. ${name}`;
    }
  };

  const filteredTraces = traces.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.trace_id.toLowerCase().includes(q) ||
      (t.user_message && t.user_message.toLowerCase().includes(q)) ||
      t.root_action.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">OpenTelemetry Trace Explorer</h2>
            <span className="px-2 py-0.5 rounded bg-blue-950/80 border border-blue-800 text-[10px] text-blue-300 font-mono">
              Distributed Spans
            </span>
          </div>
          <p className="text-xs text-kon-muted mt-0.5">
            Stage-by-stage request timelines, parent/child span hierarchy, and execution latencies across LLM, policy, and database layers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchTracesList();
              if (selectedTraceId) loadJourney(selectedTraceId);
            }}
            className="p-1.5 rounded-lg bg-kon-surface hover:bg-kon-blue text-slate-300 border border-kon-border transition-colors"
            title="Refresh traces"
          >
            <RefreshCw className="w-4 h-4 text-kon-red" />
          </button>
        </div>
      </div>

      {/* Main Two-Panel Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Panel: Recent Traces Sidebar (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-kon-muted" />
            <input
              type="text"
              placeholder="Filter by Trace ID or message..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-kon-dark border border-kon-border/70 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-kon-blue"
            />
          </div>

          <div className="flex-1 bg-kon-dark/90 border border-kon-border/70 rounded-2xl overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-kon-border/60 bg-kon-surface/40 flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>Recent Request Traces</span>
              <span className="text-[11px] text-kon-muted">{filteredTraces.length} recorded</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-kon-border/40 max-h-[620px]">
              {loadingList ? (
                <div className="p-8 text-center">
                  <LoadingSpinner size="md" label="Loading traces..." />
                </div>
              ) : filteredTraces.length === 0 ? (
                <div className="p-8 text-center text-xs text-kon-muted">
                  No request traces recorded yet. Send a message in the shopping store to generate live spans.
                </div>
              ) : (
                filteredTraces.map((t) => {
                  const isSelected = selectedTraceId === t.trace_id;
                  const isSuccess = t.status === "ok";

                  return (
                    <button
                      key={t.trace_id}
                      onClick={() => setSelectedTraceId(t.trace_id)}
                      className={`w-full text-left p-3.5 transition-all flex flex-col gap-1.5 ${
                        isSelected
                          ? "bg-kon-surface/80 border-l-4 border-l-kon-blue"
                          : "hover:bg-kon-surface/30 border-l-4 border-l-transparent"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-white truncate max-w-[170px]">
                          {t.trace_id.slice(0, 8)}...
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[11px] text-slate-300 font-semibold">
                            {t.total_duration_ms.toFixed(0)} ms
                          </span>
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isSuccess ? "bg-emerald-400" : "bg-rose-500"
                            }`}
                          />
                        </div>
                      </div>

                      <div className="text-[11px] text-kon-muted truncate">
                        {t.user_message ? `"${t.user_message}"` : t.root_action}
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
                        <span>{new Date(t.start_time).toLocaleTimeString()}</span>
                        <span className="font-mono">{t.spans_count} stages</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Panel: Selected Trace Waterfall Timeline (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          {loadingJourney ? (
            <div className="h-full min-h-[450px] bg-kon-dark/90 border border-kon-border/70 rounded-2xl flex items-center justify-center p-8">
              <LoadingSpinner size="lg" label="Hydrating OpenTelemetry waterfall timeline..." />
            </div>
          ) : !selectedJourney ? (
            <div className="h-full min-h-[450px] bg-kon-dark/90 border border-kon-border/70 rounded-2xl flex flex-col items-center justify-center p-8 text-center">
              <GitFork className="w-12 h-12 text-slate-600 mb-3" />
              <h3 className="text-sm font-bold text-slate-300">Select a trace to inspect its journey</h3>
              <p className="text-xs text-kon-muted max-w-sm mt-1">
                Click any request on the left to see its millisecond latency breakdown across AI inference, policy checks, tool execution, and avatar synthesis.
              </p>
            </div>
          ) : (
            <div className="bg-kon-dark/90 border border-kon-border/70 rounded-2xl overflow-hidden flex flex-col">
              {/* Journey Top Header */}
              <div className="p-5 border-b border-kon-border/60 bg-kon-surface/30 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-kon-muted">Trace ID:</span>
                    <span className="font-mono text-sm font-bold text-white bg-slate-900 px-2.5 py-1 rounded-lg border border-kon-border">
                      {selectedJourney.trace_id}
                    </span>
                    <button
                      onClick={() => handleCopyTraceId(selectedJourney.trace_id)}
                      className="p-1 rounded hover:bg-kon-surface text-slate-400 hover:text-white transition-colors"
                      title="Copy full trace ID"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-kon-border text-xs">
                      <Clock className="w-3.5 h-3.5 text-kon-blue" />
                      <span className="font-mono font-bold text-white">
                        {selectedJourney.total_duration_ms.toFixed(0)} ms
                      </span>
                    </div>

                    <Badge variant={selectedJourney.status === "ok" ? "success" : "danger"}>
                      {selectedJourney.status === "ok" ? "Completed" : "Error Occurred"}
                    </Badge>

                    {selectedJourney.jaeger_url && (
                      <a
                        href={selectedJourney.jaeger_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-950/70 hover:bg-blue-900 border border-blue-700/80 text-xs font-medium text-blue-300 transition-colors"
                        title="View trace in external Jaeger container"
                      >
                        <span>Jaeger</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>

                {selectedJourney.user_message && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-kon-border/50 text-xs">
                    <span className="text-kon-muted block font-semibold mb-0.5">Customer Input Prompt:</span>
                    <span className="text-slate-200 italic font-serif">"{selectedJourney.user_message}"</span>
                  </div>
                )}
              </div>

              {/* Waterfall Timeline Visualization */}
              <div className="p-5 space-y-4">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300 pb-1">
                  <span>Execution Stages & Span Waterfall</span>
                  <span className="text-[11px] text-kon-muted">Total Time: {selectedJourney.total_duration_ms.toFixed(0)} ms</span>
                </div>

                <div className="space-y-3">
                  {selectedJourney.spans
                    .filter((s) => s.name !== "agent.chat_turn")
                    .map((span, idx) => {
                      const Icon = getStageIcon(span.name);
                      const isExpanded = expandedSpanId === span.span_id;
                      const maxDuration = Math.max(selectedJourney.total_duration_ms, 1.0);
                      const widthPercent = Math.min(
                        100,
                        Math.max(4, Math.round((span.duration_ms / maxDuration) * 100))
                      );
                      const isOk = span.status === "ok";

                      return (
                        <div
                          key={span.span_id}
                          className="p-3.5 rounded-xl bg-kon-surface/40 hover:bg-kon-surface/70 border border-kon-border/60 transition-all space-y-2.5"
                        >
                          {/* Row Header */}
                          <div className="flex items-center justify-between gap-3 text-xs">
                            <div className="flex items-center gap-2.5">
                              <div
                                className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                                  isOk
                                    ? "bg-slate-800 text-blue-300 border border-slate-700"
                                    : "bg-rose-950/80 text-rose-300 border border-rose-800"
                                }`}
                              >
                                <Icon className="w-4 h-4" />
                              </div>
                              <div>
                                <span className="font-bold text-slate-200 block text-xs">
                                  {getStageLabel(span.name, idx)}
                                </span>
                                <span className="font-mono text-[10px] text-kon-muted">
                                  span_id: {span.span_id.slice(0, 12)}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className="font-mono font-bold text-white text-xs">
                                {span.duration_ms.toFixed(1)} ms
                              </span>

                              <Badge variant={isOk ? "success" : "danger"}>
                                {isOk ? "OK" : "ERROR"}
                              </Badge>

                              <button
                                onClick={() => setExpandedSpanId(isExpanded ? null : span.span_id)}
                                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
                                title="Toggle Span Details"
                              >
                                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              </button>
                            </div>
                          </div>

                          {/* Horizontal Waterfall Gantt Bar */}
                          <div className="h-2 w-full rounded-full bg-slate-900 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                isOk
                                  ? "bg-gradient-to-r from-kon-blue to-emerald-400"
                                  : "bg-gradient-to-r from-amber-500 to-rose-600"
                              }`}
                              style={{ width: `${widthPercent}%` }}
                            />
                          </div>

                          {/* Expandable Attributes Drawer */}
                          {isExpanded && (
                            <div className="pt-2 mt-2 border-t border-kon-border/40 text-[11px] font-mono space-y-2 animate-fade-in">
                              <div className="grid grid-cols-2 gap-2 text-kon-muted">
                                <div>
                                  <span className="text-slate-400 block font-semibold">Start Time:</span>
                                  <span>{span.start_time}</span>
                                </div>
                                <div>
                                  <span className="text-slate-400 block font-semibold">End Time:</span>
                                  <span>{span.end_time}</span>
                                </div>
                              </div>

                              {span.attributes && Object.keys(span.attributes).length > 0 && (
                                <div className="mt-2">
                                  <span className="text-slate-400 block font-semibold mb-1">Span Attributes:</span>
                                  <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                                    {JSON.stringify(span.attributes, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TraceExplorerPage() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" label="Loading Trace Explorer..." />}>
      <TraceExplorerContent />
    </Suspense>
  );
}

