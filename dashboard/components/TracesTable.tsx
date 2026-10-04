"use client";
import type { TraceEvent, TraceFilters } from "@/lib/types";

const OP_CLASS: Record<string, string> = {
  search: "bg-[#eef3ff] text-[#3b5bdb] border-[#dbe3ff] dark:bg-[#1e2740] dark:text-[#8da4ef] dark:border-[#2e3d5f]",
  graph_search: "bg-[#f3eeff] text-[#7048e8] border-[#e5dbff] dark:bg-[#261e40] dark:text-[#b59aef] dark:border-[#3d2e5f]",
  upsert: "bg-[#eafaf1] text-ok border-[#d3f0e0] dark:bg-[#1a2e22] dark:text-ok dark:border-[#2a4e35]",
};

export default function TracesTable({
  traces, filters, onFilter, onSelect,
}: {
  traces: TraceEvent[];
  filters: TraceFilters;
  onFilter: (f: TraceFilters) => void;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="bg-surface border border-line rounded-xl2 overflow-hidden">
      <div className="flex items-center gap-3 px-[18px] py-3.5 border-b border-line">
        <h3 className="m-0 text-[14px] font-semibold font-sans">Execution Spans &amp; Traces</h3>
        <div className="ml-auto flex flex-wrap gap-2">
          <select
            value={filters.op || ""}
            onChange={(e) => onFilter({ ...filters, op: e.target.value })}
            className="font-mono text-[12px] border border-line rounded-md px-2.5 py-1.5 bg-bg text-ink cursor-pointer"
          >
            <option value="">All Operations</option>
            <option value="search">search (Vector ANN)</option>
            <option value="graph_search">graph_search (Hybrid)</option>
            <option value="upsert">upsert (Batch Ingest)</option>
          </select>
          <select
            value={filters.status || ""}
            onChange={(e) => onFilter({ ...filters, status: e.target.value })}
            className="font-mono text-[12px] border border-line rounded-md px-2.5 py-1.5 bg-bg text-ink cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="ok">Success (ok)</option>
            <option value="error">Error (error)</option>
          </select>
          <input
            placeholder="Filter namespace..."
            value={filters.namespace || ""}
            onChange={(e) => onFilter({ ...filters, namespace: e.target.value })}
            className="font-mono text-[12px] border border-line rounded-md px-2.5 py-1.5 bg-bg text-ink w-32 placeholder:text-faint"
          />
        </div>
      </div>

      {traces.length === 0 ? (
        <div className="p-10 text-center text-muted font-mono text-xs">No execution traces matching current filter criteria.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="text-left font-mono text-[11px] uppercase tracking-wider text-muted bg-table-head">
                {["Timestamp", "Operation", "Namespace", "Latency", "Results", "Cache", "Reranker", "Status"].map((h) => (
                  <th key={h} className="px-[18px] py-2.5 border-b border-line font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {traces.map((e) => (
                <tr
                  key={e.id}
                  onClick={() => onSelect(e.id)}
                  className="cursor-pointer hover:bg-accent-soft/40 [&>td]:px-[18px] [&>td]:py-2.5 [&>td]:border-b [&>td]:border-line tabular-nums transition-colors"
                >
                  <td className="font-mono text-xs text-muted">{new Date(e.ts * 1000).toLocaleTimeString()}</td>
                  <td>
                    <span className={"font-mono text-[11px] px-2 py-0.5 rounded-md border font-medium " + (OP_CLASS[e.op] || "border-line")}>
                      {e.op}
                    </span>
                  </td>
                  <td className="font-mono text-xs font-medium text-ink">{e.namespace}</td>
                  <td className="font-mono font-medium">{e.latency_ms.toFixed(1)} ms</td>
                  <td className="font-mono text-muted">{e.n_results}</td>
                  <td>
                    {e.cache_hit == null ? (
                      <span className="text-faint font-mono text-xs">—</span>
                    ) : e.cache_hit ? (
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-ok/10 text-ok font-semibold">HIT</span>
                    ) : (
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-line/60 text-muted">MISS</span>
                    )}
                  </td>
                  <td className="font-mono text-xs text-muted">{[e.rescore, e.rerank].filter(Boolean).join("+") || <span className="text-faint">—</span>}</td>
                  <td>
                    <span className={`font-mono text-[10.5px] px-2 py-0.5 rounded font-semibold inline-flex items-center gap-1 ${e.status === "error" ? "bg-red-500/10 text-red-500" : "bg-ok/10 text-ok"}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${e.status === "error" ? "bg-red-500" : "bg-ok"}`} />
                      {e.status === "error" ? "ERROR" : "SUCCESS"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
