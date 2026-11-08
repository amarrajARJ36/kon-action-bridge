"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Bot,
  Shield,
  CheckCircle,
  XCircle,
  Plus,
  Power,
  Cpu,
  Building,
  Layers,
  Wrench,
  Search,
  Filter,
  AlertTriangle,
  UserCheck,
  Activity,
  Edit2,
  X,
  Check,
} from "lucide-react";
import { AgentRegistry, ToolRegistry } from "@/lib/types";
import { getAgents, getTools, toggleAgentStatus, updateAgent, createAgent } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function AgentRegistryPage() {
  const [agents, setAgents] = useState<AgentRegistry[]>([]);
  const [availableTools, setAvailableTools] = useState<ToolRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Modal States
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AgentRegistry | null>(null);
  const [modalFormError, setModalFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New Agent Form State
  const [formData, setFormData] = useState({
    agent_id: "",
    name: "",
    description: "",
    role: "assistant",
    department: "Retail Commerce",
    model_provider: "Google Gemini",
    model_version: "gemini-1.5-pro",
    owner_tenant: "KON Retail Org",
    status: "active" as "active" | "inactive",
    allowed_tools: [] as string[],
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [agentList, toolList] = await Promise.all([getAgents(), getTools()]);
      setAgents(agentList);
      setAvailableTools(toolList);
    } catch (err) {
      console.error("Failed to load agent registry data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggleStatus = async (agentId: string) => {
    try {
      setTogglingId(agentId);
      const updated = await toggleAgentStatus(agentId);
      setAgents((prev) =>
        prev.map((a) => (a.agent_id === agentId ? { ...a, status: updated.status } : a))
      );
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to toggle agent status");
    } finally {
      setTogglingId(null);
    }
  };

  const handleSaveEditTools = async () => {
    if (!editingAgent) return;
    try {
      setIsSubmitting(true);
      const updated = await updateAgent(editingAgent.agent_id, {
        allowed_tools: editingAgent.allowed_tools,
      });
      setAgents((prev) =>
        prev.map((a) => (a.agent_id === updated.agent_id ? updated : a))
      );
      setEditingAgent(null);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to update agent permissions");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalFormError(null);
    if (!formData.agent_id || !formData.name) {
      setModalFormError("Agent ID and Name are required.");
      return;
    }
    try {
      setIsSubmitting(true);
      const created = await createAgent(formData);
      setAgents((prev) => [...prev, created]);
      setShowRegisterModal(false);
      setFormData({
        agent_id: "",
        name: "",
        description: "",
        role: "assistant",
        department: "Retail Commerce",
        model_provider: "Google Gemini",
        model_version: "gemini-1.5-pro",
        owner_tenant: "KON Retail Org",
        status: "active",
        allowed_tools: [],
      });
    } catch (err: any) {
      setModalFormError(err.response?.data?.detail || "Failed to register new agent");
    } finally {
      setIsSubmitting(false);
    }
  };

  const departments = ["ALL", ...Array.from(new Set(agents.map((a) => a.department || "Retail Commerce")))];

  const filteredAgents = agents.filter((agent) => {
    const matchesDept = departmentFilter === "ALL" || (agent.department || "Retail Commerce") === departmentFilter;
    const matchesStatus = statusFilter === "ALL" || agent.status === statusFilter;
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      agent.name.toLowerCase().includes(q) ||
      agent.agent_id.toLowerCase().includes(q) ||
      (agent.description && agent.description.toLowerCase().includes(q));
    return matchesDept && matchesStatus && matchesSearch;
  });

  if (loading) {
    return <LoadingSpinner size="lg" label="Hydrating AI Employees directory..." />;
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">AI Employees & Agent Registry</h2>
            <span className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-[10px] text-emerald-300 font-mono">
              Role-Based Governance (RBAC)
            </span>
          </div>
          <p className="text-xs text-kon-muted mt-0.5">
            Enterprise database of recognized AI employees, model specifications, department responsibilities, and tool privileges.
          </p>
        </div>

        <button
          onClick={() => setShowRegisterModal(true)}
          className="flex items-center gap-1.5 py-2 px-3.5 rounded-xl bg-gradient-to-r from-kon-blue to-kon-red hover:from-blue-600 hover:to-rose-600 text-white text-xs font-bold shadow-lg shadow-rose-950/30 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Register AI Employee</span>
        </button>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-kon-dark/80 border border-kon-border/70 rounded-2xl">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-kon-muted mr-1">Department:</span>
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => setDepartmentFilter(dept)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                departmentFilter === dept
                  ? "bg-kon-blue text-white shadow-sm"
                  : "bg-kon-surface text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              {dept}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="py-1.5 px-3 bg-kon-surface border border-kon-border rounded-lg text-xs text-slate-200 focus:outline-none focus:border-kon-blue"
          >
            <option value="ALL">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>

          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-kon-muted" />
            <input
              type="text"
              placeholder="Search AI employees..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-kon-surface border border-kon-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-kon-blue"
            />
          </div>
        </div>
      </div>

      {/* AI Employees Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredAgents.map((agent) => {
          const isActive = agent.status === "active";
          const isToggling = togglingId === agent.agent_id;

          return (
            <div
              key={agent.id}
              className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                isActive
                  ? "bg-kon-dark/90 border-kon-border/70 hover:border-kon-blue/60"
                  : "bg-slate-950/60 border-slate-800/80 opacity-75"
              }`}
            >
              {/* Employee Card Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-white shadow-md ${
                      isActive
                        ? "bg-gradient-to-tr from-kon-blue to-kon-red"
                        : "bg-slate-800 text-slate-500"
                    }`}
                  >
                    <Bot className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white tracking-tight">{agent.name}</h3>
                      <Badge variant={isActive ? "success" : "neutral"}>
                        {agent.status.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-kon-muted mt-0.5">
                      <span className="font-mono text-[11px] text-blue-300">{agent.agent_id}</span>
                      <span>•</span>
                      <span className="text-slate-300 font-medium">{agent.department || "Retail Commerce"}</span>
                    </div>
                  </div>
                </div>

                {/* 1-Click Status Toggle Button */}
                <button
                  type="button"
                  onClick={() => handleToggleStatus(agent.agent_id)}
                  disabled={isToggling}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all disabled:opacity-50 ${
                    isActive
                      ? "bg-rose-950/40 hover:bg-rose-900/60 border-rose-800 text-rose-300"
                      : "bg-emerald-950/40 hover:bg-emerald-900/60 border-emerald-800 text-emerald-300"
                  }`}
                  title={isActive ? "Disable this agent immediately" : "Activate this agent"}
                >
                  <Power className="w-3.5 h-3.5" />
                  <span>{isToggling ? "Updating..." : isActive ? "Deactivate" : "Activate"}</span>
                </button>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 leading-relaxed min-h-[36px]">
                {agent.description || "No description provided for this AI employee."}
              </p>

              {/* Employee Specifications Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
                <div className="p-2.5 rounded-xl bg-kon-surface/50 border border-kon-border/40">
                  <span className="text-kon-muted block text-[10px] font-sans font-semibold uppercase">Business Role</span>
                  <span className="text-slate-200 truncate block font-bold">{agent.role}</span>
                </div>

                <div className="p-2.5 rounded-xl bg-kon-surface/50 border border-kon-border/40">
                  <span className="text-kon-muted block text-[10px] font-sans font-semibold uppercase">Model / Engine</span>
                  <span className="text-purple-300 truncate block font-bold">{agent.model_version || "gemini-1.5-pro"}</span>
                </div>

                <div className="p-2.5 rounded-xl bg-kon-surface/50 border border-kon-border/40">
                  <span className="text-kon-muted block text-[10px] font-sans font-semibold uppercase">Owner / Tenant</span>
                  <span className="text-slate-300 truncate block">{agent.owner_tenant || "KON Retail Org"}</span>
                </div>

                <div className="p-2.5 rounded-xl bg-kon-surface/50 border border-kon-border/40">
                  <span className="text-kon-muted block text-[10px] font-sans font-semibold uppercase">Requests / Errors</span>
                  <div className="flex items-center gap-1.5 font-bold">
                    <span className="text-emerald-400">{agent.total_requests || 0} req</span>
                    <span>/</span>
                    <span className={(agent.failure_count || 0) > 0 ? "text-rose-400" : "text-slate-400"}>
                      {agent.failure_count || 0} fail
                    </span>
                  </div>
                </div>
              </div>

              {/* Permitted Tools Matrix */}
              <div className="pt-2 border-t border-kon-border/40">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-kon-muted uppercase tracking-wider">
                    Permitted Governance Tools ({agent.allowed_tools.length})
                  </span>
                  <button
                    onClick={() => setEditingAgent(agent)}
                    className="flex items-center gap-1 text-[11px] text-kon-blue hover:text-blue-300 font-semibold"
                  >
                    <Edit2 className="w-3 h-3" />
                    <span>Edit Tools</span>
                  </button>
                </div>

                {agent.allowed_tools.length === 0 ? (
                  <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-900/50 text-[11px] text-amber-300 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Strict Isolation: Zero commerce tool permissions granted.</span>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {agent.allowed_tools.map((tool) => (
                      <span
                        key={tool}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-kon-surface/80 border border-kon-border text-[11px] font-mono text-slate-200"
                      >
                        <Shield className="w-3 h-3 text-emerald-400" />
                        <span>{tool}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit Permissions Modal */}
      {editingAgent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-kon-dark border border-kon-border rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-kon-border/60">
              <div>
                <h3 className="text-base font-bold text-white">Edit Tool Permissions</h3>
                <p className="text-xs text-kon-muted font-mono">{editingAgent.name} ({editingAgent.agent_id})</p>
              </div>
              <button
                onClick={() => setEditingAgent(null)}
                className="p-1.5 rounded-lg hover:bg-kon-surface text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Select which commerce tools this AI employee is authorized to invoke through the Action Bridge governance boundary:
            </p>

            <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
              {availableTools.map((t) => {
                const isSelected = editingAgent.allowed_tools.includes(t.tool_name);
                return (
                  <label
                    key={t.tool_name}
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? "bg-blue-950/40 border-blue-800 text-white"
                        : "bg-kon-surface/40 border-kon-border/60 text-slate-300 hover:bg-kon-surface"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const newTools = e.target.checked
                          ? [...editingAgent.allowed_tools, t.tool_name]
                          : editingAgent.allowed_tools.filter((tn) => tn !== t.tool_name);
                        setEditingAgent({ ...editingAgent, allowed_tools: newTools });
                      }}
                      className="mt-0.5 rounded bg-kon-surface border-kon-border text-kon-blue focus:ring-0"
                    />
                    <div className="flex-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold">{t.tool_name}</span>
                        <Badge variant={t.permission_level === "restricted" ? "warning" : "info"}>
                          {t.permission_level}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-kon-muted mt-0.5">{t.description}</p>
                    </div>
                  </label>
                );
              })}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-kon-border/60">
              <button
                type="button"
                onClick={() => setEditingAgent(null)}
                className="px-4 py-2 rounded-xl bg-kon-surface hover:bg-slate-800 text-xs font-semibold text-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEditTools}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl bg-kon-blue hover:bg-blue-600 text-xs font-semibold text-white shadow-md disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : "Save Tool Privileges"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Register New AI Employee Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-xl w-full bg-kon-dark border border-kon-border rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-kon-border/60">
              <div>
                <h3 className="text-base font-bold text-white">Register New AI Employee</h3>
                <p className="text-xs text-kon-muted">Onboard an AI agent to the company registry</p>
              </div>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="p-1.5 rounded-lg hover:bg-kon-surface text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {modalFormError && (
              <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 text-xs">
                {modalFormError}
              </div>
            )}

            <form onSubmit={handleCreateAgent} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Agent ID *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. kon-marketing-agent"
                    value={formData.agent_id}
                    onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                    className="w-full px-3 py-2 bg-kon-surface border border-kon-border rounded-xl text-xs text-slate-200 font-mono focus:outline-none focus:border-kon-blue"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Employee Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Growth Marketing Assistant"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 bg-kon-surface border border-kon-border rounded-xl text-xs text-slate-200 focus:outline-none focus:border-kon-blue"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Primary role responsibilities..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-kon-surface border border-kon-border rounded-xl text-xs text-slate-200 focus:outline-none focus:border-kon-blue"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Department</label>
                  <select
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 bg-kon-surface border border-kon-border rounded-xl text-xs text-slate-200 focus:outline-none focus:border-kon-blue"
                  >
                    <option value="Retail Commerce">Retail Commerce</option>
                    <option value="Customer Care">Customer Care</option>
                    <option value="Finance & Accounting">Finance & Accounting</option>
                    <option value="Human Resources">Human Resources</option>
                    <option value="Marketing & Growth">Marketing & Growth</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Model & Provider</label>
                  <select
                    value={formData.model_version}
                    onChange={(e) => setFormData({ ...formData, model_version: e.target.value })}
                    className="w-full px-3 py-2 bg-kon-surface border border-kon-border rounded-xl text-xs text-slate-200 font-mono focus:outline-none focus:border-kon-blue"
                  >
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Initial Permitted Commerce Tools ({formData.allowed_tools.length})
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto p-2 rounded-xl bg-slate-950/60 border border-kon-border/60">
                  {availableTools.map((t) => {
                    const isChecked = formData.allowed_tools.includes(t.tool_name);
                    return (
                      <label key={t.tool_name} className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            const newT = e.target.checked
                              ? [...formData.allowed_tools, t.tool_name]
                              : formData.allowed_tools.filter((x) => x !== t.tool_name);
                            setFormData({ ...formData, allowed_tools: newT });
                          }}
                          className="rounded bg-kon-surface border-kon-border text-kon-blue focus:ring-0"
                        />
                        <span className="truncate">{t.tool_name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-kon-border/60">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 rounded-xl bg-kon-surface hover:bg-slate-800 text-xs font-semibold text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-kon-blue to-kon-red hover:from-blue-600 hover:to-rose-600 text-xs font-bold text-white shadow-md disabled:opacity-50"
                >
                  {isSubmitting ? "Registering..." : "Onboard Employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
