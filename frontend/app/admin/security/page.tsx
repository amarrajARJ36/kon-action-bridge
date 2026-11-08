"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ShieldAlert,
  XCircle,
  Play,
  CheckCircle2,
  AlertOctagon,
  Flame,
} from "lucide-react";
import { AuditLog } from "@/lib/types";
import { getSecurityEvents, simulateBlockedAction } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function SecurityEventsPage() {
  const [events, setEvents] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStatus, setSimulationStatus] = useState<string | null>(null);
  const [simulationSuccess, setSimulationSuccess] = useState(false);

  const loadEvents = async () => {
    try {
      const data = await getSecurityEvents();
      setEvents(data);
    } catch (err) {
      console.error("Failed to load security events:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  // Admin-only: triggers the dedicated backend simulation endpoint
  // No customer session required — uses admin JWT directly
  const handleSimulateBlockedAction = async () => {
    setIsSimulating(true);
    setSimulationStatus(null);
    setSimulationSuccess(false);
    try {
      const result = await simulateBlockedAction();
      setSimulationSuccess(true);
      setSimulationStatus(
        `✓ Security policy defense successful: Unauthorized tool '${result.tool_attempted}' was intercepted and BLOCKED. ` +
        `Zero-trust governance protected the database. Reason: ${result.denial_reason}.`
      );
      // Reload security events to show new denial
      await loadEvents();
    } catch (err: any) {
      setSimulationSuccess(false);
      setSimulationStatus(
        err.response?.data?.detail || "Simulation failed — ensure you are logged in as admin."
      );
    } finally {
      setIsSimulating(false);
      setTimeout(() => setSimulationStatus(null), 7000);
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" label="Analyzing security telemetry & denial logs..." />;
  }

  const deniedCount = events.filter((e) => e.governance_decision === "denied").length;
  const failedCount = events.filter((e) => e.execution_status === "failed").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Security Events & Incident Log</h2>
          <p className="text-xs text-kon-muted mt-0.5">
            Audit surface displaying blocked actions, policy rejections, invalid parameters, and boundary breaches.
          </p>
        </div>

        {/* Live Demo Simulation Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isSimulating}
            onClick={handleSimulateBlockedAction}
            className="flex items-center gap-1.5 py-1.5 px-3 rounded-lg bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-800 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          >
            {isSimulating ? (
              <span className="w-3.5 h-3.5 border-2 border-rose-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>{isSimulating ? "Simulating..." : "Simulate Blocked Action"}</span>
          </button>
        </div>
      </div>

      {simulationStatus && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-start gap-2 animate-fade-in ${
            simulationSuccess
              ? "bg-emerald-950/80 border-emerald-800 text-emerald-200"
              : "bg-amber-950/80 border-amber-800 text-amber-200"
          }`}
        >
          <AlertOctagon className={`w-4 h-4 shrink-0 mt-0.5 ${simulationSuccess ? "text-emerald-400" : "text-amber-400"}`} />
          <span>{simulationStatus}</span>
        </div>
      )}

      {/* Incident Summary Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/40 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block">
              Policy Denials
            </span>
            <span className="text-2xl font-bold text-white">{deniedCount}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-rose-900/40 text-rose-400">
            <XCircle className="w-6 h-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/40 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider block">
              Execution Failures
            </span>
            <span className="text-2xl font-bold text-white">{failedCount}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-900/40 text-amber-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/40 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider block">
              Enforcement Mode
            </span>
            <span className="text-sm font-bold text-emerald-400 mt-1 block">Fail-Closed Active</span>
          </div>
          <div className="p-2.5 rounded-lg bg-blue-900/40 text-blue-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Simulation Instructions */}
      <div className="p-3 rounded-xl bg-kon-surface/60 border border-kon-border/50 text-xs text-kon-muted">
        <span className="font-semibold text-slate-300">Demo tip:</span> Click{" "}
        <span className="text-rose-300 font-mono">Simulate Blocked Action</span> to watch the governance engine instantly
        deny <span className="font-mono text-white">admin_drop_database</span> — a tool not in the registry. The denial
        appears in the table below and in the Audit Logs dashboard in real time.
      </div>

      {/* Security Incident Table */}
      <Card
        title="Security & Violation Incident Feed"
        subtitle="All attempts rejected by policy validation or terminated with runtime exceptions"
      >
        <Table
          headers={["Timestamp", "Agent ID", "Tool / Action", "Decision", "Status", "Reason for Denial / Fault"]}
          isEmpty={events.length === 0}
          emptyMessage="No security violations recorded yet. Click 'Simulate Blocked Action' above to generate one."
        >
          {events.map((evt) => {
            const isDenied = evt.governance_decision === "denied";

            return (
              <tr key={evt.id} className="hover:bg-kon-surface/40 transition-colors">
                <td className="py-3 px-4 font-mono text-[11px] text-kon-muted whitespace-nowrap">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-3 px-4 text-xs font-mono text-slate-200">
                  {evt.agent_id}
                </td>
                <td className="py-3 px-4 font-mono font-medium text-white text-xs">
                  {evt.tool_name}
                </td>
                <td className="py-3 px-4">
                  <Badge variant={isDenied ? "danger" : "warning"}>
                    {evt.governance_decision}
                  </Badge>
                </td>
                <td className="py-3 px-4">
                  <Badge variant="neutral">
                    {evt.execution_status}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-xs text-rose-300 font-medium">
                  {evt.denial_reason || "Action blocked by governance engine"}
                </td>
              </tr>
            );
          })}
        </Table>
      </Card>
    </div>
  );
}
