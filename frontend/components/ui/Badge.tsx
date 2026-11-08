import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "success" | "danger" | "warning" | "info" | "neutral";
  size?: "sm" | "md";
}

export function Badge({ children, variant = "neutral", size = "sm" }: BadgeProps) {
  const variantStyles = {
    success: "bg-emerald-950 text-emerald-300 border-emerald-700/50",
    danger: "bg-rose-950 text-rose-300 border-rose-700/50",
    warning: "bg-amber-950 text-amber-300 border-amber-700/50",
    info: "bg-sky-950 text-sky-300 border-sky-700/50",
    neutral: "bg-slate-800 text-slate-300 border-slate-700",
  };

  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm",
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {children}
    </span>
  );
}

