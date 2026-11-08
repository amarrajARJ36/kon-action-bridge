import React from "react";

interface TableProps {
  headers: string[];
  children: React.ReactNode;
  emptyMessage?: string;
  isEmpty?: boolean;
}

export function Table({ headers, children, emptyMessage = "No records found", isEmpty = false }: TableProps) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-kon-border/50">
      <table className="w-full text-left text-xs text-slate-300">
        <thead className="bg-kon-surface/80 text-[11px] uppercase tracking-wider text-kon-muted border-b border-kon-border/60">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="py-3 px-4 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-kon-border/30 bg-kon-dark/60">
          {isEmpty ? (
            <tr>
              <td colSpan={headers.length} className="py-8 text-center text-kon-muted italic">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            children
          )}
        </tbody>
      </table>
    </div>
  );
}

