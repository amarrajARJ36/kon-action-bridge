import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  subtext?: string;
  tone?: "blue" | "green" | "red" | "amber" | "purple";
}

export function MetricCard({ label, value, icon: Icon, subtext, tone = "blue" }: MetricCardProps) {
  const toneStyles = {
    blue: {
      bg: "bg-blue-950/40 border-blue-800/40",
      iconBg: "bg-blue-900/50 text-blue-400",
    },
    green: {
      bg: "bg-emerald-950/40 border-emerald-800/40",
      iconBg: "bg-emerald-900/50 text-emerald-400",
    },
    red: {
      bg: "bg-rose-950/40 border-rose-800/40",
      iconBg: "bg-rose-900/50 text-rose-400",
    },
    amber: {
      bg: "bg-amber-950/40 border-amber-800/40",
      iconBg: "bg-amber-900/50 text-amber-400",
    },
    purple: {
      bg: "bg-purple-950/40 border-purple-800/40",
      iconBg: "bg-purple-900/50 text-purple-400",
    },
  };

  const style = toneStyles[tone];

  return (
    <div className={`p-5 rounded-xl border ${style.bg} transition-all hover:border-kon-blue/80 shadow-md`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-kon-muted uppercase tracking-wider">{label}</span>
        <div className={`p-2 rounded-lg ${style.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
        {subtext && <p className="text-xs text-kon-muted mt-1">{subtext}</p>}
      </div>
    </div>
  );
}

