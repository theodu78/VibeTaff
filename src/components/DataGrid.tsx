import { useState, useMemo, useCallback } from "react";

interface DataGridProps {
  data: Record<string, unknown>[];
  tableName?: string;
}

export default function DataGrid({ data, tableName }: DataGridProps) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [copied, setCopied] = useState(false);

  const columns = useMemo(() => {
    if (!data.length) return [];
    const keys = new Set<string>();
    data.forEach((row) => Object.keys(row).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [data]);

  const sortedData = useMemo(() => {
    if (!sortCol) return data;
    return [...data].sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return sortAsc ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [data, sortCol, sortAsc]);

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  const copyCSV = useCallback(() => {
    const header = columns.join(",");
    const rows = data.map((row) =>
      columns.map((col) => {
        const val = row[col];
        const str = val == null ? "" : String(val);
        return str.includes(",") || str.includes('"')
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      }).join(",")
    );
    const csv = [header, ...rows].join("\n");
    navigator.clipboard.writeText(csv).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data, columns]);

  if (!data.length || !columns.length) {
    return <div className="text-zinc-500 text-xs py-2">Tableau vide</div>;
  }

  return (
    <div className="my-2 rounded-lg border border-zinc-700 bg-zinc-900/50 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
        <span className="text-xs font-medium text-zinc-400">
          {tableName ? `${tableName}` : "Tableau"} ({data.length} lignes)
        </span>
        <button
          onClick={copyCSV}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {copied ? "Copié !" : "Copier CSV"}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-zinc-800">
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2 text-left text-zinc-400 font-medium cursor-pointer hover:text-zinc-200 transition-colors select-none"
                >
                  {col}
                  {sortCol === col && (
                    <span className="ml-1">{sortAsc ? "▲" : "▼"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, i) => (
              <tr
                key={i}
                className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col} className="px-3 py-1.5 text-zinc-300">
                    {row[col] == null ? "" : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
