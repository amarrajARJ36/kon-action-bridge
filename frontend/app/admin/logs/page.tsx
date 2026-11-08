"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ScrollText,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Code2,
  X,
  Copy,
  Check,
  ShieldCheck,
  GitFork,
  ExternalLink,
} from "lucide-react";
import { AuditLog } from "@/lib/types";
import { getAuditLogs, getTools } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function ActivityLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [copied, setCopied] = useState(false);

  // Filters
  const [selectedTool, setSelectedTool] = useState("");
  const [selectedDecision, setSelectedDecision] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");
  const [toolsList, setToolsList] = useState<string[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const filters: any = { limit: 50 };
      if (selectedTool) filters.tool_name = selectedTool;
      if (selectedDecision) filters.decision = selectedDecision;
      if (selectedStatus) filters.status = selectedStatus;

      const data = await getAuditLogs(filters);
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedTool, selectedDecision, selectedStatus]);

  useEffect(() => {
    async function loadTools() {
      try {
        const tools = await getTools();
        setToolsList(tools.map((t) => t.tool_name));
      } catch (err) {
        console.warn("Could not load tool names:", err);
      }
    }
    loadTools();
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Activity & Audit Logs</h2>
        <p className="text-xs text-kon-muted mt-0.5">
          Immutable event log of every tool execution attempt, policy decision, parameter verification, and latency metric.
        </p>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 bg-kon-dark border border-kon-border/60 rounded-xl flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-kon-red" />
          <span className="text-xs font-semibold text-white">Filters:</span>
        </div>

        {/* Tool Filter */}
        <select
          value={selectedTool}
          onChange={(e) => setSelectedTool(e.target.value)}
          className="bg-kon-surface border border-kon-border rounded-lg text-xs py-1.5 px-3 text-slate-200 focus:outline-none focus:border-kon-blue"
        >
          <option value="">All Tools</option>
          {toolsList.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        {/* Decision Filter */}
        <select
          value={selectedDecision}
          onChange={(e) => setSelectedDecision(e.target.value)}
          className="bg-kon-surface border border-kon-border rounded-lg text-xs py-1.5 px-3 text-slate-200 focus:outline-none focus:border-kon-blue"
        >
          <option value="">All Decisions</option>
          <option value="allowed">Allowed</option>
          <option value="denied">Denied</option>
        </select>

        {/* Status Filter */}
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="bg-kon-surface border border-kon-border rounded-lg text-xs py-1.5 px-3 text-slate-200 focus:outline-none focus:border-kon-blue"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
        </select>

        {(selectedTool || selectedDecision || selectedStatus) && (
          <button
            onClick={() => {
              setSelectedTool("");
              setSelectedDecision("");
              setSelectedStatus("");
            }}
            className="text-xs text-kon-red hover:underline py-1 px-2"
          >
            Clear Filters
          </button>
        )}

        <div className="ml-auto text-xs text-kon-muted">
          Showing {logs.length} of {total} events
        </div>
      </div>

      {/* Logs Table */}
      <Card>
        {loading ? (
          <LoadingSpinner size="md" label="Loading audit logs..." />
        ) : (
          <Table
            headers={["Timestamp", "Event ID", "Agent", "Tool", "Decision", "Status", "Duration", "Details"]}
            isEmpty={logs.length === 0}
            emptyMessage="No matching audit logs found."
          >
            {logs.map((log) => {
              const isAllowed = log.governance_decision === "allowed";
              const isSuccess = log.execution_status === "success";

              return (
                <tr
                  key={log.id}
                  onClick={() => setSelectedLog(log)}
                  className="hover:bg-kon-surface/50 cursor-pointer transition-colors"
                >
                  <td className="py-2.5 px-4 font-mono text-[11px] text-kon-muted">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-[11px] text-slate-400">
                    {log.event_id?.substring(0, 8)}...
                  </td>
                  <td className="py-2.5 px-4 font-medium text-slate-200 text-xs">
                    {log.agent_id}
                  </td>
                  <td className="py-2.5 px-4 font-mono font-medium text-white text-xs">
                    {log.tool_name}
                  </td>
                  <td className="py-2.5 px-4">
                    <Badge variant={isAllowed ? "success" : "danger"}>
                      {log.governance_decision}
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
                  <td className="py-2.5 px-4 text-xs text-kon-blue font-medium hover:underline">
                    Inspect ➔
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>

      {/* Event Details Inspection Drawer / Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm animate-fade-in">
          <div className="bg-kon-dark border border-kon-border rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-kon-border/60">
              <div className="flex items-center gap-2">
                <Code2 className="w-5 h-5 text-kon-red" />
                <h3 className="text-base font-bold text-white">Audit Event Inspection</h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg text-kon-muted hover:text-white hover:bg-kon-surface"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-kon-surface/70 border border-kon-border/50">
                <span className="text-kon-muted block text-[10px] uppercase">Event ID</span>
                <span className="font-mono text-white text-[11px]">{selectedLog.event_id}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-kon-surface/70 border border-kon-border/50">
                <span className="text-kon-muted block text-[10px] uppercase">Trace ID</span>
                <Link
                  href={`/admin/traces?trace_id=${selectedLog.trace_id}`}
                  className="font-mono text-kon-blue hover:text-blue-300 text-[11px] underline flex items-center gap-1"
                  title="Inspect journey in Trace Explorer"
                >
                  <span className="truncate">{selectedLog.trace_id}</span>
                  <ExternalLink className="w-3 h-3 shrink-0" />
                </Link>
              </div>
              <div className="p-2.5 rounded-lg bg-kon-surface/70 border border-kon-border/50">
                <span className="text-kon-muted block text-[10px] uppercase">Agent ID</span>
                <span className="font-mono text-white">{selectedLog.agent_id}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-kon-surface/70 border border-kon-border/50">
                <span className="text-kon-muted block text-[10px] uppercase">Session ID</span>
                <span className="font-mono text-white text-[11px] truncate block">
                  {selectedLog.session_id}
                </span>
              </div>
            </div>

            {selectedLog.governance_decision === "denied" && (
              <div className="p-3 rounded-lg bg-emerald-950/70 border border-emerald-500/60 text-xs text-emerald-200">
                <div className="flex items-center gap-1.5 font-bold text-emerald-300 mb-1">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Security Defense Active: Threat Blocked</span>
                </div>
                <span>
                  The Policy Engine successfully intercepted and denied an unauthorized action (
                  <span className="font-mono text-emerald-300">{selectedLog.tool_name || "unregistered tool"}</span>
                  ). Fail-closed zero-trust policy safeguarded the database.
                </span>
              </div>
            )}

            {selectedLog.denial_reason && (
              <div className="p-3 rounded-lg bg-rose-950/70 border border-rose-800 text-xs text-rose-200">
                <span className="font-bold block mb-0.5">
                  {selectedLog.governance_decision === "denied"
                    ? "Security Policy Interception Reason:"
                    : "Failure Reason:"}
                </span>
                <span>{selectedLog.denial_reason}</span>
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-300">
                  Full Event Audit Record (JSON)
                </span>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(selectedLog, null, 2))}
                  className="flex items-center gap-1 text-[11px] text-kon-muted hover:text-white"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy JSON"}</span>
                </button>
              </div>
              <pre className="p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-emerald-300 overflow-x-auto max-h-60">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Link
                href={`/admin/traces?trace_id=${selectedLog.trace_id}`}
                className="py-1.5 px-3 rounded-xl bg-kon-blue hover:bg-blue-600 text-xs font-semibold text-white transition-colors flex items-center gap-1.5"
              >
                <GitFork className="w-3.5 h-3.5" />
                <span>Open in Trace Explorer</span>
              </Link>
              <button
                onClick={() => setSelectedLog(null)}
                className="py-1.5 px-4 rounded-xl bg-kon-surface hover:bg-slate-700 text-xs font-medium text-white transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

