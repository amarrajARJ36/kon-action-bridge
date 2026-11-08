import React from "react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

export function LoadingSpinner({ size = "md", label }: LoadingSpinnerProps) {
  const sizeMap = {
    sm: "w-4 h-4 border-2",
    md: "w-7 h-7 border-2",
    lg: "w-10 h-10 border-3",
  };

  return (
    <div className="flex flex-col items-center justify-center py-6 gap-2">
      <div
        className={`${sizeMap[size]} border-kon-blue border-t-kon-red rounded-full animate-spin`}
      />
      {label && <span className="text-xs text-kon-muted">{label}</span>}
    </div>
  );
}

