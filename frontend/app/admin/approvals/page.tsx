"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  UserCheck,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  ShoppingBag,
  ExternalLink,
  ShieldAlert,
  Search,
  Filter,
  Check,
  X,
  FileText,
  DollarSign,
  User,
  GitFork,
} from "lucide-react";
import {
  getApprovals,
  approveRequest,
  rejectRequest,
  createAdminEventSource,
} from "@/lib/api";
import { ApprovalRequest } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"pending" | "approved" | "rejected" | "all">("pending");
  const [searchTerm, setSearchTerm] = useState("");
  const [actionModal, setActionModal] = useState<{
    type: "approve" | "reject";
    approval: ApprovalRequest;
  } | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [submittingAction, setSubmittingAction] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadApprovals = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getApprovals();
      setApprovals(data);
    } catch (err) {
      console.error("Failed to load approvals", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApprovals();

    // Listen to real-time approval events via SSE
    const unsubscribe = createAdminEventSource((type, data) => {
      if (type === "approval_request") {
        setApprovals((prev) => {
          if (prev.some((a) => a.id === data.id)) return prev;
          return [data, ...prev];
        });
        showToast(`New approval request intercepted: ${data.tool_name || "submit_order"}`);
      } else if (type === "approval_resolved") {
        setApprovals((prev) =>
          prev.map((a) => (a.id === data.id ? { ...a, ...data } : a))
        );
      }
    });

    return () => {
      unsubscribe();
    };
  }, [loadApprovals]);

  const handleConfirmAction = async () => {
    if (!actionModal) return;
    setSubmittingAction(true);
    try {
      let resolved: ApprovalRequest;
      if (actionModal.type === "approve") {
        resolved = await approveRequest(
          actionModal.approval.id,
          resolutionNotes || "Approval decision recorded (Execution: Not performed in this MVP)"
        );
        showToast(`Request ${actionModal.approval.id.slice(0, 8)} approved (decision recorded).`);
      } else {
        resolved = await rejectRequest(
          actionModal.approval.id,
          resolutionNotes || "Action rejected by supervisor"
        );
        showToast(`Request ${actionModal.approval.id.slice(0, 8)} rejected.`);
      }
      setApprovals((prev) =>
        prev.map((a) => (a.id === resolved.id ? resolved : a))
      );
      setActionModal(null);
      setResolutionNotes("");
    } catch (err) {
      console.error("Failed to resolve approval request", err);
      showToast("Error resolving request. Please try again.");
    } finally {
      setSubmittingAction(false);
    }
  };

  // Stats calculation
  const pendingCount = approvals.filter((a) => a.status === "pending").length;
  const approvedCount = approvals.filter((a) => a.status === "approved").length;
  const rejectedCount = approvals.filter((a) => a.status === "rejected").length;

  const filteredApprovals = approvals.filter((a) => {
    if (activeTab !== "all" && a.status !== activeTab) return false;
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchId = a.id.toLowerCase().includes(q);
      const matchTrace = a.trace_id.toLowerCase().includes(q);
      const matchAgent = a.agent_id.toLowerCase().includes(q);
      const matchTool = a.tool_name.toLowerCase().includes(q);
      const matchReason = (a.reason || "").toLowerCase().includes(q);
      return matchId || matchTrace || matchAgent || matchTool || matchReason;
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Toast notification */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-50 bg-violet-600 text-white px-4 py-2.5 rounded-xl shadow-xl flex items-center gap-2 border border-violet-400/30 text-xs font-medium animate-in fade-in slide-in-from-top-2">
          <Sparkles className="w-4 h-4 text-amber-300 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
            <UserCheck className="w-5 h-5 text-amber-400" />
            Human-in-the-Loop (HITL) Approvals
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Supervisory queue for high-risk autonomous agent actions requiring explicit human verification before execution.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadApprovals()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-kon-dark hover:bg-kon-border/60 text-slate-300 text-xs border border-kon-border/40 transition-colors"
            title="Refresh requests"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-kon-dark border border-amber-500/30 rounded-xl p-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Pending Actions</span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-2">{pendingCount}</p>
          <p className="text-[10px] text-slate-500 mt-0.5">Awaiting administrator decision</p>
        </div>

        <div className="bg-kon-dark border border-emerald-500/20 rounded-xl p-4">
          <span className="text-xs text-slate-400">Approved</span>
          <p className="text-2xl font-bold text-emerald-400 mt-2">{approvedCount}</p>
          <p className="text-[10px] text-slate-500 mt-0.5">Approval recorded (Execution: Not performed in MVP)</p>
        </div>

        <div className="bg-kon-dark border border-rose-500/20 rounded-xl p-4">
          <span className="text-xs text-slate-400">Rejected</span>
          <p className="text-2xl font-bold text-rose-400 mt-2">{rejectedCount}</p>
          <p className="text-[10px] text-slate-500 mt-0.5">Action rejected by supervisor</p>
        </div>

        <div className="bg-kon-dark border border-kon-border/40 rounded-xl p-4">
          <span className="text-xs text-slate-400">Target Policy Rule</span>
          <p className="text-sm font-semibold text-violet-300 mt-2 truncate">submit_order (High Risk)</p>
          <p className="text-[10px] text-slate-500 mt-0.5">Automated policy intercept</p>
        </div>
      </div>

      {/* Filters and search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Tabs */}
        <div className="flex items-center gap-1.5 bg-kon-dark p-1 rounded-xl border border-kon-border/40 self-start">
          {[
            { id: "pending", label: "Pending", count: pendingCount, color: "text-amber-400" },
            { id: "approved", label: "Approved", count: approvedCount, color: "text-emerald-400" },
            { id: "rejected", label: "Rejected", count: rejectedCount, color: "text-rose-400" },
            { id: "all", label: "All Records", count: approvals.length, color: "text-slate-400" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === tab.id
                    ? "bg-slate-700 text-white"
                    : "bg-slate-900/60 " + tab.color
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID, agent, trace..."
            className="w-full bg-kon-dark border border-kon-border/50 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Approvals List */}
      {loading ? (
        <div className="text-center py-16 text-slate-500 text-xs flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />
          Loading authorization queue...
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className="bg-kon-dark border border-kon-border/40 rounded-2xl p-12 text-center">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mx-auto mb-3 text-slate-400">
            <CheckCircle2 className="w-6 h-6 text-emerald-400/80" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">
            {activeTab === "pending"
              ? "All Clear — No Pending Approvals"
              : "No Records Found"}
          </h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {activeTab === "pending"
              ? "Autonomous agents are operating within designated policy boundaries. High-risk actions like submit_order requested by shoppers will appear here for review."
              : "No approval entries match the current filter criteria."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredApprovals.map((item) => {
            const isPending = item.status === "pending";
            const isApproved = item.status === "approved";
            const isRejected = item.status === "rejected";

            const params = item.parameters || {};
            const itemsList = params.items || [];
            const totalAED = params.total_aed || params.estimated_total || 0;
            const deliveryAddress = params.delivery_address || params.destination || "Standard Delivery (Dubai)";

            return (
              <div
                key={item.id}
                className={`bg-kon-dark border rounded-2xl p-5 transition-all ${
                  isPending
                    ? "border-amber-500/40 shadow-lg shadow-amber-500/5 hover:border-amber-500/60"
                    : isApproved
                    ? "border-emerald-500/20 hover:border-emerald-500/40"
                    : "border-rose-500/20 hover:border-rose-500/40"
                }`}
              >
                {/* Header row */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-kon-border/40 pb-4">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                        isPending
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          : isApproved
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      <ShoppingBag className="w-4 h-4" />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-100">
                          {item.tool_name || "submit_order"}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            item.risk_level === "HIGH"
                              ? "bg-rose-950/60 text-rose-300 border-rose-700/60"
                              : item.risk_level === "MEDIUM"
                              ? "bg-amber-950/60 text-amber-300 border-amber-700/60"
                              : "bg-slate-800 text-slate-300 border-slate-700"
                          }`}
                        >
                          {item.risk_level} RISK
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            isPending
                              ? "bg-amber-400/20 text-amber-300 border border-amber-400/40 animate-pulse"
                              : isApproved
                              ? "bg-emerald-400/20 text-emerald-300 border border-emerald-400/40"
                              : "bg-rose-400/20 text-rose-300 border border-rose-400/40"
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-2 font-mono">
                        <span>ID: {item.id.slice(0, 12)}</span>
                        <span>•</span>
                        <span>Agent: {item.agent_id}</span>
                        <span>•</span>
                        <span>{new Date(item.created_at).toLocaleString()}</span>
                      </p>
                    </div>
                  </div>

                  {/* Actions for Pending */}
                  {isPending ? (
                    <div className="flex items-center gap-2 shrink-0 self-start md:self-auto">
                      <button
                        onClick={() => setActionModal({ type: "reject", approval: item })}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/70 hover:bg-rose-900 text-rose-200 border border-rose-700/60 text-xs font-semibold transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                        Reject
                      </button>
                      <button
                        onClick={() => setActionModal({ type: "approve", approval: item })}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-xs font-bold shadow-md shadow-emerald-900/30 transition-all"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Approve Order
                      </button>
                    </div>
                  ) : (
                    <div className="text-right text-xs text-slate-400 shrink-0">
                      <p className="text-slate-300 font-medium">
                        Resolved by: <span className="text-slate-100">{item.resolved_by || "admin"}</span>
                      </p>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        {item.resolved_at ? new Date(item.resolved_at).toLocaleString() : ""}
                      </p>
                    </div>
                  )}
                </div>

                {/* Details Body */}
                <div className="pt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* Left: Intercept Reason & Governance Context */}
                  <div className="lg:col-span-2 space-y-3">
                    <div className="bg-kon-navy/50 border border-kon-border/40 rounded-xl p-3 text-xs">
                      <div className="flex items-center gap-1.5 text-amber-300 font-semibold mb-1">
                        <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                        <span>Policy Engine Intercept Trigger</span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        {item.reason ||
                          "Governance security requirement: 'submit_order' is a high-risk commerce action requiring Human-in-the-Loop supervisor authorization before transaction execution."}
                      </p>
                    </div>

                    {/* Items payload breakdown */}
                    {itemsList.length > 0 && (
                      <div className="bg-kon-navy/40 border border-kon-border/30 rounded-xl p-3 text-xs">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                          Basket Items Requested ({itemsList.length})
                        </p>
                        <div className="space-y-1.5">
                          {itemsList.map((prod: any, idx: number) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between text-[11px] bg-slate-900/40 px-2.5 py-1.5 rounded-lg border border-slate-800"
                            >
                              <span className="text-slate-200 font-medium">
                                {prod.quantity ? `${prod.quantity}× ` : ""}
                                {prod.name || prod.product_id}
                              </span>
                              {prod.unit_price && (
                                <span className="text-slate-400 font-mono">
                                  AED {(prod.unit_price * (prod.quantity || 1)).toFixed(2)}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Resolution Notes if resolved */}
                    {!isPending && item.resolution_notes && (
                      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3 text-xs">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                          Supervisor Resolution Notes
                        </p>
                        <p className="text-slate-300 text-[11px] italic">
                          &ldquo;{item.resolution_notes}&rdquo;
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Right: Metadata Panel */}
                  <div className="bg-kon-navy/30 border border-kon-border/30 rounded-xl p-3 text-xs space-y-2.5 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Order Estimate:</span>
                        <span className="text-sm font-bold text-emerald-400 font-mono">
                          {totalAED > 0 ? `AED ${Number(totalAED).toFixed(2)}` : "Preview"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Delivery Target:</span>
                        <span className="text-slate-200 font-medium truncate max-w-[140px]" title={deliveryAddress}>
                          {deliveryAddress}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">User / Customer:</span>
                        <span className="text-slate-200 font-mono text-[11px]">
                          {item.user_id || "guest-session"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Session ID:</span>
                        <span className="text-slate-400 font-mono text-[11px] truncate max-w-[120px]">
                          {item.session_id || "n/a"}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-kon-border/30">
                      <Link
                        href={`/admin/traces?trace=${item.trace_id}`}
                        className="inline-flex items-center gap-1.5 text-[11px] text-violet-400 hover:text-violet-300 transition-colors"
                      >
                        <GitFork className="w-3 h-3" />
                        <span>Inspect Trace: {item.trace_id.slice(0, 10)}...</span>
                        <ExternalLink className="w-2.5 h-2.5 ml-0.5 opacity-60" />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Confirmation Modal */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-kon-dark border border-kon-border rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-kon-border/50">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                {actionModal.type === "approve" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Approve Autonomous Action
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-rose-400" />
                    Reject Autonomous Action
                  </>
                )}
              </h3>
              <button
                onClick={() => setActionModal(null)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3 text-xs">
              <p className="text-slate-300">
                You are about to{" "}
                <strong
                  className={actionModal.type === "approve" ? "text-emerald-400" : "text-rose-400"}
                >
                  {actionModal.type.toUpperCase()}
                </strong>{" "}
                the high-risk action{" "}
                <code className="px-1.5 py-0.5 bg-slate-800 rounded font-mono text-amber-300">
                  {actionModal.approval.tool_name}
                </code>{" "}
                requested by agent{" "}
                <span className="font-semibold text-slate-200">
                  {actionModal.approval.agent_id}
                </span>
                .
              </p>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Supervisor Notes / Reason (Optional):
                </label>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder={
                    actionModal.type === "approve"
                      ? "e.g., Approval decision recorded (Execution: Not performed in this MVP)"
                      : "e.g., Action rejected by supervisor"
                  }
                  rows={3}
                  className="w-full bg-kon-navy/80 border border-kon-border/60 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-kon-border/50">
              <button
                onClick={() => setActionModal(null)}
                className="px-3.5 py-1.5 rounded-lg bg-kon-dark hover:bg-kon-border/40 text-slate-400 hover:text-slate-200 text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                disabled={submittingAction}
                className={`px-4 py-1.5 rounded-lg font-bold text-xs shadow-md transition-all flex items-center gap-1.5 ${
                  actionModal.type === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/30"
                    : "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/30"
                }`}
              >
                {submittingAction && <RefreshCw className="w-3 h-3 animate-spin" />}
                Confirm {actionModal.type === "approve" ? "Approval" : "Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

