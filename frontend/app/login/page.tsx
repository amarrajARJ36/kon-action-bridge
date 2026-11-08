"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Lock, User, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";
import { login } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("demo_customer");
  const [password, setPassword] = useState("customer123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await login(username, password);
      setToken(res.access_token);
      if (res.user.role === "admin") {
        router.push("/admin");
      } else {
        router.push("/shop");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid login credentials");
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = (userRole: "customer" | "admin") => {
    if (userRole === "admin") {
      setUsername("admin");
      setPassword("admin123");
    } else {
      setUsername("demo_customer");
      setPassword("customer123");
    }
  };

  return (
    <div className="min-h-screen bg-kon-navy flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-kon-dark border border-kon-border/70 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
        <div className="text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-kon-blue to-kon-red flex items-center justify-center mx-auto mb-3 shadow-lg">
            <Lock className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">KON Action Bridge Sign In</h2>
          <p className="text-xs text-kon-muted mt-1">
            Access Governed Conversational Commerce or Admin Telemetry
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Username</label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-kon-navy border border-kon-border rounded-xl px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-kon-blue"
              />
              <User className="w-4 h-4 text-slate-500 absolute right-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-kon-navy border border-kon-border rounded-xl px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-kon-blue"
              />
              <Lock className="w-4 h-4 text-slate-500 absolute right-3 top-3" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-kon-red hover:bg-rose-600 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-rose-950/50 transition-all disabled:opacity-50"
          >
            <span>{loading ? "Signing In..." : "Sign In with JWT"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Demo Credentials Autofill */}
        <div className="pt-4 border-t border-kon-border/40 text-xs">
          <span className="text-[11px] font-semibold text-kon-muted uppercase tracking-wider block mb-2 text-center">
            Quick Demo Autofill Credentials
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleFillDemo("customer")}
              className="p-2 rounded-lg bg-kon-surface hover:bg-slate-700 text-[11px] text-slate-300 border border-kon-border text-center"
            >
              <span className="font-semibold text-white block">Customer Demo</span>
              <span className="text-kon-muted">demo_customer</span>
            </button>
            <button
              type="button"
              onClick={() => handleFillDemo("admin")}
              className="p-2 rounded-lg bg-kon-surface hover:bg-slate-700 text-[11px] text-slate-300 border border-kon-border text-center"
            >
              <span className="font-semibold text-white block">Admin Demo</span>
              <span className="text-kon-muted">admin</span>
            </button>
          </div>
        </div>

        <div className="text-center">
          <Link href="/shop" className="text-xs text-kon-muted hover:text-white transition-colors">
            ← Continue as Guest to Shopping Interface
          </Link>
        </div>
      </div>
    </div>
  );
}

