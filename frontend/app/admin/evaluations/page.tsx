"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  TrendingUp,
  Bot,
  Eye,
  RefreshCw,
} from "lucide-react";
import api from "@/lib/api";

interface EvalRecord {
  id: string;
  timestamp: string;
  session_id: string;
  user_message: string;
  agent_response: string;
  tool_name_called: string | null;
  items_requested: Array<{ name: string; quantity: number }>;
  items_unavailable: Array<{ name: string }>;
  items_ambiguous: Array<{ name: string }>;
  items_added: Array<{ name: string; quantity: number }>;
  hallucination_detected: boolean;
  omission_detected: boolean;
  premature_action_detected: boolean;
  intent_coverage_score: number | null;
  evaluation_notes: string;
  evaluation_verdict: "pass" | "warn" | "fail";
}

interface EvalSummary {
  total_turns_evaluated: number;
  verdict_pass: number;
  verdict_warn: number;
  verdict_fail: number;
  quality_score_pct: number;
  hallucination_count: number;
  omission_count: number;
  premature_action_count: number;
  avg_intent_coverage_pct: number;
}

const verdictColor = {
  pass: "bg-emerald-900/40 text-emerald-300 border-emerald-600/40",
  warn: "bg-amber-900/40 text-amber-300 border-amber-600/40",
  fail: "bg-rose-900/40 text-rose-300 border-rose-600/40",
};
const verdictIcon = {
  pass: <ShieldCheck className="w-3.5 h-3.5" />,
  warn: <AlertTriangle className="w-3.5 h-3.5" />,
  fail: <XCircle className="w-3.5 h-3.5" />,
};

export default function EvaluationsPage() {
  const [summary, setSummary] = useState<EvalSummary | null>(null);
  const [records, setRecords] = useState<EvalRecord[]>([]);
  const [verdictFilter, setVerdictFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async (vf = verdictFilter) => {
    setLoading(true);
    try {
      const [sumRes, recRes] = await Promise.all([
        api.get("/admin/evaluations/summary"),
        api.get("/admin/evaluations", {
          params: { verdict: vf === "all" ? undefined : vf, limit: 100 },
        }),
      ]);
      setSummary(sumRes.data);
      setRecords(recRes.data);
    } catch (err) {
      console.error("Failed to load evaluation data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verdictFilter]);

  const pct = (n: number) => `${Math.round(n * 100)}%`;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Conversation Quality Checks
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic semantic verification: catalog grounding · hallucination detection · omission checks · premature action · intent coverage
          </p>
        </div>
        <button
          onClick={() => load()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-kon-border/40 hover:bg-kon-border/70 text-slate-300 text-xs transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Quality Score", value: `${summary.quality_score_pct}%`, color: "text-emerald-400", sub: `${summary.verdict_pass} / ${summary.total_turns_evaluated} turns passed` },
            { label: "Avg Intent Coverage", value: `${summary.avg_intent_coverage_pct}%`, color: "text-violet-400", sub: "Items requested → addressed" },
            { label: "Hallucinations", value: summary.hallucination_count, color: "text-rose-400", sub: "Claimed action without tool execution" },
            { label: "Omissions", value: summary.omission_count, color: "text-amber-400", sub: "Requested items silently skipped" },
          ].map((c) => (
            <div key={c.label} className="bg-kon-dark border border-kon-border/50 rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-1">{c.label}</p>
              <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
              <p className="text-[10px] text-slate-500 mt-1">{c.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* Verdict filter tabs */}
      <div className="flex gap-2">
        {["all", "pass", "warn", "fail"].map((v) => (
          <button
            key={v}
            onClick={() => setVerdictFilter(v)}
            className={`px-3 py-1 rounded-full text-xs font-bold border transition-colors ${
              verdictFilter === v
                ? "bg-violet-600 text-white border-violet-500"
                : "bg-kon-dark border-kon-border/40 text-slate-400 hover:text-slate-200"
            }`}
          >
            {v.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Records table */}
      {loading ? (
        <div className="text-slate-400 text-sm text-center py-10">Loading evaluations…</div>
      ) : records.length === 0 ? (
        <div className="text-slate-500 text-sm text-center py-10">
          No evaluations yet — start chatting on the shop page!
        </div>
      ) : (
        <div className="space-y-2">
          {records.map((r) => (
            <div
              key={r.id}
              className="bg-kon-dark border border-kon-border/40 rounded-xl overflow-hidden"
            >
              {/* Row header */}
              <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-kon-border/10 transition-colors"
                onClick={() => setExpanded(expanded === r.id ? null : r.id)}
              >
                {/* Verdict badge */}
                <span
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${verdictColor[r.evaluation_verdict]}`}
                >
                  {verdictIcon[r.evaluation_verdict]}
                  {r.evaluation_verdict.toUpperCase()}
                </span>

                {/* User message */}
                <span className="flex-1 text-xs text-slate-300 truncate">{r.user_message}</span>

                {/* Flag pills */}
                <div className="hidden sm:flex items-center gap-1.5">
                  {r.hallucination_detected && (
                    <span className="px-1.5 py-0.5 rounded bg-rose-900/50 text-rose-300 text-[9px] font-bold">HALLUC</span>
                  )}
                  {r.omission_detected && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-900/50 text-amber-300 text-[9px] font-bold">OMIT</span>
                  )}
                  {r.premature_action_detected && (
                    <span className="px-1.5 py-0.5 rounded bg-violet-900/50 text-violet-300 text-[9px] font-bold">PREMATURE</span>
                  )}
                  {r.intent_coverage_score !== null && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      {pct(r.intent_coverage_score)} coverage
                    </span>
                  )}
                </div>

                <Eye className="w-4 h-4 text-slate-500 shrink-0" />
              </div>

              {/* Expanded detail */}
              {expanded === r.id && (
                <div className="border-t border-kon-border/30 px-4 py-3 space-y-3 text-xs">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <p className="text-slate-500 font-bold mb-1">USER</p>
                      <p className="text-slate-200">{r.user_message}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-bold mb-1">AGENT RESPONSE</p>
                      <p className="text-slate-200">{r.agent_response}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {[
                      { label: "Requested", items: r.items_requested, color: "text-slate-300" },
                      { label: "Unavailable", items: r.items_unavailable, color: "text-rose-400" },
                      { label: "Ambiguous", items: r.items_ambiguous, color: "text-amber-400" },
                      { label: "Added to Cart", items: r.items_added, color: "text-emerald-400" },
                    ].map((g) => (
                      <div key={g.label} className="bg-kon-navy/40 rounded-lg p-2">
                        <p className="text-[10px] text-slate-500 font-bold mb-1">{g.label}</p>
                        {g.items.length === 0 ? (
                          <p className="text-[10px] text-slate-600 italic">none</p>
                        ) : (
                          g.items.map((it, i) => (
                            <p key={i} className={`text-[10px] ${g.color}`}>
                              {"quantity" in it ? `${(it as any).quantity}× ` : ""}{it.name}
                            </p>
                          ))
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="bg-kon-navy/40 rounded-lg p-2">
                    <p className="text-[10px] text-slate-500 font-bold mb-1">EVALUATION NOTES</p>
                    <pre className="text-[10px] text-slate-300 whitespace-pre-wrap">{r.evaluation_notes}</pre>
                  </div>

                  <p className="text-[10px] text-slate-600">
                    Session: {r.session_id} · Tool: {r.tool_name_called ?? "none"} ·{" "}
                    {new Date(r.timestamp).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

