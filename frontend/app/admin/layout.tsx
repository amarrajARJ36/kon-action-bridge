"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Wrench,
  ShieldAlert,
  ScrollText,
  AlertTriangle,
  ArrowLeft,
  Menu,
  X,
  ExternalLink,
  ShieldCheck,
  GitFork,
  UserCheck,
} from "lucide-react";
import { login } from "@/lib/api";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [adminUsername, setAdminUsername] = useState<string>("admin");

  // Ensure an admin session is silently active in localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const rawUser = localStorage.getItem("kon_user");
      const token = localStorage.getItem("kon_token");
      let role = "";
      if (rawUser) {
        const parsed = JSON.parse(rawUser);
        role = parsed.role;
        if (parsed.username) setAdminUsername(parsed.username);
      }
      // If no admin token is currently set, fetch demo admin token silently in background
      if (!token || role !== "admin") {
        login("admin", "admin123")
          .then((res) => {
            localStorage.setItem("kon_admin_token", res.access_token);
            localStorage.setItem("kon_token", res.access_token);
            localStorage.setItem("kon_user", JSON.stringify(res.user));
            setAdminUsername(res.user.username);
          })
          .catch(() => {
            // Demo bypass on backend allows requests regardless
          });
      }
    } catch {
      // Ignored - backend bypass handles direct access
    }
  }, []);

  const navItems = [
    { label: "Overview", href: "/admin", icon: LayoutDashboard },
    { label: "Approvals (HITL)", href: "/admin/approvals", icon: UserCheck },
    { label: "Trace Explorer", href: "/admin/traces", icon: GitFork },
    { label: "Agent Registry", href: "/admin/agents", icon: Bot },
    { label: "Tool Registry", href: "/admin/tools", icon: Wrench },
    { label: "Policy Engine", href: "/admin/policies", icon: ShieldAlert },
    { label: "Activity Logs", href: "/admin/logs", icon: ScrollText },
    { label: "Security Events", href: "/admin/security", icon: AlertTriangle },
  ];

  return (
    <div className="flex h-screen bg-kon-navy text-slate-100 overflow-hidden">
      {/* Sidebar for Desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-kon-dark border-r border-kon-border/60 shrink-0">
        {/* Brand Header */}
        <div className="h-16 border-b border-kon-border/60 px-5 flex items-center justify-between">
          <Link href="/admin" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-kon-blue to-kon-red flex items-center justify-center font-bold text-white text-xs shadow-md">
              KON
            </div>
            <div>
              <span className="font-bold text-sm tracking-tight text-white block">Action Bridge</span>
              <span className="text-[10px] uppercase font-semibold text-kon-red tracking-wider">Governance</span>
            </div>
          </Link>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-kon-blue text-white shadow-md shadow-blue-950/40 border border-blue-600/40"
                    : "text-slate-300 hover:bg-kon-surface hover:text-white"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-kon-red" : "text-kon-muted"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer Actions */}
        <div className="p-4 border-t border-kon-border/60 bg-kon-dark/80">
          <Link
            href="/shop"
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-kon-surface hover:bg-kon-blue text-slate-200 text-xs font-semibold border border-kon-border transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>KON Commerce Store</span>
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-kon-border/60 bg-kon-dark/70 px-4 sm:px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg bg-kon-surface text-slate-300 border border-kon-border"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <h1 className="text-sm sm:text-base font-bold text-white tracking-tight">
              Action Bridge Security & Governance Center
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-kon-border text-[11px] text-kon-muted">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Engine Status: Active (Fail-Closed)</span>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-[11px] text-emerald-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Admin: {adminUsername}</span>
            </div>

            <Link
              href="/shop"
              className="md:hidden flex items-center gap-1.5 p-2 rounded-lg bg-kon-surface text-slate-200 text-xs"
            >
              <ExternalLink className="w-4 h-4" />
            </Link>
          </div>
        </header>

        {/* Mobile Nav Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-kon-dark border-b border-kon-border p-3 space-y-1 z-30">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium ${
                    isActive ? "bg-kon-blue text-white" : "text-slate-300 hover:bg-kon-surface"
                  }`}
                >
                  <Icon className="w-4 h-4 text-kon-red" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        )}

        {/* Content Body - Direct Unrestricted Admin Access */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-kon-navy">
          {children}
        </main>
      </div>
    </div>
  );
}

