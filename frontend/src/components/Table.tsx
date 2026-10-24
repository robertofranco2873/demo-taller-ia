import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { SkeletonTable } from "./Skeleton";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  numeric?: boolean;
  className?: string;
  hideOnMobile?: boolean;
}

/** Tabla responsive (scroll horizontal en celular) con skeleton y filas clicables. */
export function Table<T>({ rows, columns, loading, onRowClick, empty = "Sin datos.", rowKey, maxHeight }: {
  rows: T[] | null | undefined;
  columns: Column<T>[];
  loading?: boolean;
  onRowClick?: (row: T) => void;
  empty?: string;
  rowKey: (row: T, i: number) => string | number;
  maxHeight?: number;
}) {
  if (loading || !rows) return <SkeletonTable cols={Math.min(columns.length, 6)} />;
  if (!rows.length) return <p className="py-8 text-center text-sm text-muted">{empty}</p>;
  return (
    <div className="-mx-1 overflow-x-auto" style={maxHeight ? { maxHeight, overflowY: "auto" } : undefined}>
      <table className="table-base">
        <thead className={maxHeight ? "sticky top-0 bg-surface-solid" : undefined}>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`${c.numeric ? "num" : ""} ${c.hideOnMobile ? "hidden md:table-cell" : ""}`}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <motion.tr
              key={rowKey(r, i)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: Math.min(i * 0.015, 0.3) }}
              onClick={onRowClick ? () => onRowClick(r) : undefined}
              onKeyDown={onRowClick ? (e) => e.key === "Enter" && onRowClick(r) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              className={onRowClick ? "cursor-pointer" : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={`${c.numeric ? "num" : ""} ${c.hideOnMobile ? "hidden md:table-cell" : ""} ${c.className ?? ""}`}>{c.render(r)}</td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
