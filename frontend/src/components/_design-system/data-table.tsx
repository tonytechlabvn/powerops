// DataTable — generic typed table with sticky header + zebra-free dense rows.
// No internal data fetching/sorting — pure presentational. Wrap in your own state.
// Usage:
//   <DataTable
//     columns={[{ key: "name", header: "Name" }, { key: "status", header: "Status" }]}
//     rows={workspaces}
//     getRowKey={(r) => r.id}
//     onRowClick={(r) => nav(`/workspaces/${r.id}`)}
//   />

import type { ReactNode } from "react";
import { cn } from "./lib/cn";

export interface Column<TRow> {
  key: string;
  header: ReactNode;
  render?: (row: TRow) => ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
}

interface DataTableProps<TRow> {
  columns: Column<TRow>[];
  rows: TRow[];
  getRowKey: (row: TRow) => string | number;
  onRowClick?: (row: TRow) => void;
  emptyState?: ReactNode;
  className?: string;
}

export function DataTable<TRow>({
  columns, rows, getRowKey, onRowClick, emptyState, className,
}: DataTableProps<TRow>) {
  if (rows.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div className={cn("overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900", className)}>
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-zinc-900">
          <tr className="border-b border-zinc-800">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-zinc-400",
                  col.align === "right" && "text-right",
                  col.align === "center" && "text-center",
                  col.align !== "right" && col.align !== "center" && "text-left",
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {rows.map((row) => {
            const key = getRowKey(row);
            return (
              <tr
                key={key}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  "transition-colors duration-100",
                  onRowClick && "cursor-pointer hover:bg-zinc-800/50"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-4 py-2.5 text-zinc-300",
                      col.align === "right" && "text-right",
                      col.align === "center" && "text-center",
                      col.className
                    )}
                  >
                    {col.render ? col.render(row) : (row as Record<string, ReactNode>)[col.key]}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
