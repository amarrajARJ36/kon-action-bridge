"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Clock,
  RefreshCw,
  ArrowUpRight,
  Shield,
  Layers,
  Radio,
  ExternalLink,
  GitFork,
  Cpu,
  Wrench,
  Bot,
} from "lucide-react";
import { DashboardMetrics, AuditLog } from "@/lib/types";
import { getDashboardMetrics, createAdminEventSource } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function AdminOverviewPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSseActive, setIsSseActive] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");
  const [neonData, setNeonData] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await getDashboardMetrics();
      setMetrics(data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load dashboard metrics:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();

    fetch("/api/neon")
      .then((r) => r.json())
      .then((data) => setNeonData(data))
      .catch((e) => console.error("Failed to load Neon status", e));

    // Real-Time Server-Sent Events (SSE) stream subscription
    const unsubscribe = createAdminEventSource(
      (type, data) => {
        setIsSseActive(true);
        // Refresh metrics instantly upon receiving real-time audit or trace events
        loadData();
      },
      () => {
        setIsSseActive(false);
      }
    );

    // Fallback polling every 15s if SSE is idle
    const interval = setInterval(loadData, 15000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [loadData]);

  if (loading && !metrics) {
    return <LoadingSpinner size="lg" label="Connecting to Action Bridge Governance telemetry..." />;
  }

  const toolUsage = metrics?.tool_usage_breakdown || {};
  const totalToolCalls = Object.values(toolUsage).reduce((acc, curr) => acc + curr, 0) || 1;

  return (
    <div className="space-y-6">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Governance & Security Overview</h2>
          <p className="text-xs text-kon-muted mt-0.5">
            Real-time audit telemetry, distributed OpenTelemetry tracing, and fail-closed security boundary evaluation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Live SSE Streaming Badge */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium transition-colors ${
              isSseActive
                ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                : "bg-slate-900 border-kon-border text-slate-400"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isSseActive ? "bg-emerald-400 animate-pulse" : "bg-slate-500"
              }`}
            />
            <span>{isSseActive ? "SSE Live Stream: Connected" : "Stream: Polling"}</span>
          </div>

          <button
            onClick={() => loadData()}
            className="flex items-center gap-1.5 py-1.5 px-3 rounded-lg bg-kon-surface hover:bg-kon-blue text-xs font-medium text-slate-200 border border-kon-border transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-kon-red" />
            <span>Refresh</span>
          </button>

          {lastRefreshed && (
            <span className="text-[11px] text-slate-500 hidden sm:inline">Updated {lastRefreshed}</span>
          )}
        </div>
      </div>

      {/* Neon Cloud Infrastructure Status */}
      <div className="p-4 rounded-xl border border-emerald-900/40 bg-gradient-to-r from-emerald-950/20 via-slate-900 to-slate-900/80 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-800/80 gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Neon Lakebase Cloud Services
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-900/50 border border-emerald-700/60 text-emerald-300">
              Branch: {neonData?.services?.realtime?.branch || "production"}
            </span>
          </div>
          <span className="text-xs text-slate-400">
            Project: <code className="text-slate-300">rough-base-82417865</code> (AWS us-east-2)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Postgres */}
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="font-medium text-slate-300">Lakebase Postgres</span>
              <span className="text-emerald-400 font-semibold text-[11px]">Active</span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              {neonData?.services?.postgres?.productsCount ?? 20} Products • asyncpg + @neon/serverless
            </p>
          </div>

          {/* Functions */}
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="font-medium text-slate-300">Neon Functions</span>
              <span className="text-emerald-400 font-semibold text-[11px]">200 OK Live</span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              Endpoint: <code className="text-slate-300">hello.ts</code> (HTTP/2)
            </p>
          </div>

          {/* AI Gateway */}
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="font-medium text-slate-300">AI Gateway</span>
              <span className="text-sky-400 font-semibold text-[11px]">Provisioned</span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              Catalog: {neonData?.services?.aiGateway?.catalogCount ?? "80+"} models linked
            </p>
          </div>

          {/* Realtime */}
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="font-medium text-slate-300">Realtime Engine</span>
              <span className="text-emerald-400 font-semibold text-[11px]">Connected</span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              WebSocket: <code className="text-slate-300">wss://...rt.c-8...</code>
            </p>
          </div>
        </div>
      </div>

      {/* Row 1: Separated & Precise Governance KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <MetricCard
          label="Total Agent Requests"
          value={metrics?.total_agent_requests || metrics?.total_actions || 0}
          icon={Bot}
          tone="blue"
          subtext="Customer conversation turns"
        />
        <MetricCard
          label="Total Tool Invocations"
          value={metrics?.total_tool_calls || 0}
          icon={Wrench}
          tone="blue"
          subtext="Attempted AI tool operations"
        />
        <MetricCard
          label="Policy Allow Rate"
          value={`${(metrics?.policy_allow_rate ?? 100).toFixed(1)}%`}
          icon={CheckCircle2}
          tone="green"
          subtext="Passed governance check"
        />
        <MetricCard
          label="Policy Denial Rate"
          value={`${(metrics?.policy_denial_rate ?? 0).toFixed(1)}%`}
          icon={XCircle}
          tone="red"
          subtext="Blocked by security rules"
        />
        <MetricCard
          label="Approval-Gated"
          value={metrics?.approval_required_actions || 0}
          icon={Shield}
          tone="purple"
          subtext="Requires explicit confirmation"
        />
        <MetricCard
          label="Tool Execution Success"
          value={`${(metrics?.tool_execution_success_rate ?? 100).toFixed(1)}%`}
          icon={Activity}
          tone="green"
          subtext="Of allowed actions only"
        />
      </div>

      {/* Row 2: OpenTelemetry Distributed Tracing & Latency Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-kon-dark/80 border-kon-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">End-to-End Request Latency</span>
            <Clock className="w-4 h-4 text-kon-blue" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {(metrics?.avg_e2e_latency_ms || metrics?.avg_duration_ms || 0).toFixed(0)} <span className="text-xs text-kon-muted font-normal">ms avg</span>
          </div>
          <p className="text-[11px] text-kon-muted mt-2">Overall customer roundtrip turn</p>
        </Card>

        <Card className="p-4 bg-kon-dark/80 border-kon-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">AI Inference Latency</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-300">
            {(metrics?.avg_ai_inference_ms || 0).toFixed(0)} <span className="text-xs text-kon-muted font-normal">ms avg</span>
          </div>
          <p className="text-[11px] text-kon-muted mt-2">Model prompt processing & generation</p>
        </Card>

        <Card className="p-4 bg-kon-dark/80 border-kon-border/70 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-300">Tool Execution Latency</span>
            <Wrench className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-300">
            {(metrics?.avg_tool_execution_ms || metrics?.avg_duration_ms || 0).toFixed(0)} <span className="text-xs text-kon-muted font-normal">ms avg</span>
          </div>
          <p className="text-[11px] text-kon-muted mt-2">Database query & stock validation</p>
        </Card>

        <Card className="p-4 bg-gradient-to-br from-kon-dark to-slate-900 border-kon-border/80 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <GitFork className="w-4 h-4 text-kon-red" />
              Trace Explorer
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono">
              OpenTelemetry
            </span>
          </div>
          <p className="text-[11px] text-kon-muted leading-relaxed mb-3">
            Inspect waterfall Gantt timelines for individual request stages.
          </p>
          <div className="flex gap-2">
            <Link
              href="/admin/traces"
              className="flex-1 py-1.5 px-2 bg-kon-surface hover:bg-kon-blue text-white text-xs font-semibold rounded-lg border border-kon-border transition-colors text-center"
            >
              Trace Explorer
            </Link>
            <a
              href="http://localhost:16686"
              target="_blank"
              rel="noreferrer"
              className="py-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium rounded-lg border border-kon-border transition-colors flex items-center gap-1"
              title="Open Jaeger UI in Docker"
            >
              <span>Jaeger</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </Card>
      </div>

      {/* Two Column Layout: Tool Breakdown & Governance Principles */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool Usage Breakdown (CSS-based Progress Bars) */}
        <Card
          title="Approved Tool Usage Distribution"
          subtitle="Frequency of commerce tool calls routed through the Action Bridge"
          className="lg:col-span-2"
        >
          <div className="space-y-3.5 pt-1">
            {Object.keys(toolUsage).length === 0 ? (
              <p className="text-xs text-kon-muted italic py-4 text-center">
                No tool executions recorded yet. Interact with the shopping assistant to populate telemetry.
              </p>
            ) : (
              Object.entries(toolUsage).map(([toolName, count]) => {
                const percentage = Math.round((count / totalToolCalls) * 100);
                return (
                  <div key={toolName} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-mono text-slate-300 font-medium">{toolName}</span>
                      <span className="text-kon-muted">
                        {count} call{count > 1 ? "s" : ""} ({percentage}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-kon-surface overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-kon-blue to-kon-red transition-all duration-500 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Security Engine State Overview */}
        <Card
          title="Governance Architecture"
          subtitle="Core enforcement model"
          className="flex flex-col justify-between"
        >
          <div className="space-y-3 text-xs text-kon-muted">
            <div className="p-3 rounded-lg bg-kon-surface/60 border border-kon-border/50">
              <span className="text-white font-semibold block mb-1">Fail-Closed Enforcement</span>
              Every action request is denied by default unless an active agent matches an active tool with valid parameters.
            </div>

            <div className="p-3 rounded-lg bg-kon-surface/60 border border-kon-border/50">
              <span className="text-white font-semibold block mb-1">State & Price Integrity</span>
              The AI never dictates unit prices or stock levels. Pricing is derived solely from the server database.
            </div>

            <div className="p-3 rounded-lg bg-kon-surface/60 border border-kon-border/50">
              <span className="text-white font-semibold block mb-1">Immutable Audit Trail</span>
              Both permitted and blocked attempts are permanently persisted with SHA-256 hash chaining and OpenTelemetry spans.
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-kon-border/40">
            <Link
              href="/admin/security"
              className="text-xs font-semibold text-kon-red hover:text-rose-400 flex items-center justify-between"
            >
              <span>Inspect Security & Denial Events</span>
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
        </Card>
      </div>

      {/* Recent Activity Logs Stream */}
      <Card
        title="Live Execution Audit Trail"
        subtitle="Last 20 tool requests evaluated by the policy engine (Click trace ID to inspect waterfall journey)"
        action={
          <Link
            href="/admin/logs"
            className="text-xs text-kon-red hover:text-rose-400 font-medium flex items-center gap-1"
          >
            <span>View All Logs</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        }
      >
        <Table
          headers={["Timestamp", "Trace ID", "Agent ID", "Tool Requested", "Governance Decision", "Status", "Duration"]}
          isEmpty={!metrics?.recent_logs || metrics.recent_logs.length === 0}
          emptyMessage="No execution events recorded yet."
        >
          {metrics?.recent_logs.map((log) => {
            const isAllowed = log.governance_decision === "allowed";
            const isSuccess = log.execution_status === "success";

            return (
              <tr key={log.id} className="hover:bg-kon-surface/40 transition-colors">
                <td className="py-2.5 px-4 font-mono text-[11px] text-kon-muted">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-2.5 px-4">
                  <Link
                    href={`/admin/traces?trace_id=${log.trace_id}`}
                    className="font-mono text-[11px] text-kon-blue hover:text-blue-400 hover:underline flex items-center gap-1"
                    title="Inspect Trace Waterfall"
                  >
                    <span>{log.trace_id.slice(0, 8)}...</span>
                    <GitFork className="w-3 h-3 text-kon-muted" />
                  </Link>
                </td>
                <td className="py-2.5 px-4 font-medium text-slate-200">
                  <span className="px-2 py-0.5 rounded bg-kon-surface text-[11px] font-mono">
                    {log.agent_id}
                  </span>
                </td>
                <td className="py-2.5 px-4 font-mono font-medium text-white">{log.tool_name || "conversation:reply"}</td>
                <td className="py-2.5 px-4">
                  <Badge variant={isAllowed ? "success" : "danger"}>
                    {isAllowed ? "Allowed" : "Denied"}
                  </Badge>
                </td>
                <td className="py-2.5 px-4">
                  <Badge variant={isSuccess ? "info" : "warning"}>
                    {log.execution_status}
                  </Badge>
                </td>
                <td className="py-2.5 px-4 font-mono text-[11px] text-slate-300">
                  {log.execution_duration_ms != null && log.execution_duration_ms > 0
                    ? `${log.execution_duration_ms.toFixed(1)} ms`
                    : "—"}
                </td>
              </tr>
            );
          })}
        </Table>
      </Card>
    </div>
  );
}

