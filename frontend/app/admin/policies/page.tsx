"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Lock } from "lucide-react";
import { PolicyConfig } from "@/lib/types";
import { getPolicies } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function PolicyManagementPage() {
  const [policyConfig, setPolicyConfig] = useState<PolicyConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPolicies() {
      try {
        const data = await getPolicies();
        setPolicyConfig(data);
      } catch (err) {
        console.error("Failed to load policy configuration:", err);
      } finally {
        setLoading(false);
      }
    }
    loadPolicies();
  }, []);

  if (loading) {
    return <LoadingSpinner size="lg" label="Loading governance policy matrix..." />;
  }

  const defaultSecurityPrinciples = [
    "1. The LLM cannot directly access the database.",
    "2. The LLM cannot call arbitrary APIs.",
    "3. Only registered tools can be executed.",
    "4. Every tool execution passes through the governance engine.",
    "5. Validate inputs strictly on the backend via Pydantic schemas.",
    "6. Check authenticated user and session ownership before cart operations.",
    "7. Verify product IDs and live stock using server database data.",
    "8. Never trust frontend or LLM supplied prices.",
    "9. Every denied action is logged with reason and trace ID.",
    "10. Sensitive credentials stored in environment variables, never hardcoded.",
    "11. Use trace UUIDs to correlate agent requests with backend events.",
    "12. Redact passwords, tokens, and payment secrets from audit logs.",
    "13. Protect administrative routes using role-based JWT claims.",
    "14. Do not execute real payments or dispatch physical grocery orders.",
  ];

  const policies = policyConfig?.policies || [];
  const principles = policyConfig?.security_principles || defaultSecurityPrinciples;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Policy Engine & Security Rules</h2>
        <p className="text-xs text-kon-muted mt-0.5">
          Centralized policy engine configuration enforcing fail-closed boundaries between conversational AI and commerce systems.
        </p>
      </div>

      {/* Target Agent Policy Status Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-kon-dark to-kon-blue/40 border border-kon-border/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-kon-surface text-kon-red border border-kon-border">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white">Target Agent:</span>
              <span className="font-mono text-xs text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                {policyConfig?.agent_id || "kon-shopping-agent"}
              </span>
            </div>
            <p className="text-xs text-kon-muted mt-0.5">
              Evaluation Strategy: Fail-Closed (unmatched or unauthorized actions are immediately denied)
            </p>
          </div>
        </div>

        <Badge variant="success" size="md">
          Policy Active & Enforced
        </Badge>
      </div>

      {/* Policies Evaluation Matrix Table */}
      <Card
        title="Action Authorization Matrix"
        subtitle="Policy decisions mapped per tool action"
      >
        <Table
          headers={["Tool / Action", "Policy Decision", "Validation Constraints", "Enforcement Note"]}
        >
          {policies.map((pol) => {
            let badgeVariant: "success" | "danger" | "warning" = "success";
            let Icon = CheckCircle2;

            if (pol.policy === "Denied") {
              badgeVariant = "danger";
              Icon = XCircle;
            } else if (pol.policy === "Approval Required") {
              badgeVariant = "warning";
              Icon = AlertTriangle;
            }

            return (
              <tr key={pol.tool} className="hover:bg-kon-surface/40 transition-colors">
                <td className="py-3 px-4">
                  <span className="font-mono text-xs font-bold text-white block">{pol.tool}</span>
                  <span className="text-[11px] text-kon-muted">{pol.action_name}</span>
                </td>
                <td className="py-3 px-4">
                  <Badge variant={badgeVariant}>
                    <span className="flex items-center gap-1">
                      <Icon className="w-3 h-3" />
                      <span>{pol.policy}</span>
                    </span>
                  </Badge>
                </td>
                <td className="py-3 px-4">
                  <div className="space-y-1">
                    {pol.checks?.map((chk, i) => (
                      <span
                        key={i}
                        className="inline-block bg-kon-surface px-2 py-0.5 rounded text-[10px] text-slate-300 font-mono mr-1 mb-1 border border-kon-border/60"
                      >
                        {chk}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3 px-4 text-xs text-kon-muted">{pol.description}</td>
              </tr>
            );
          })}
        </Table>
      </Card>

      {/* 14 Core Security Principles */}
      <Card
        title="14 Core Security & Governance Principles"
        subtitle="Mandatory security controls implemented within the Action Bridge"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {principles.map((principle, index) => (
            <div
              key={index}
              className="p-3 bg-kon-navy/80 rounded-lg border border-kon-border/50 flex items-start gap-2.5 text-xs text-slate-300"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>{principle}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

