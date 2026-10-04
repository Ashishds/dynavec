"use client";
import type { TraceEvent } from "@/lib/types";

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <>
      <div className="font-mono text-[12px] text-muted">{k}</div>
      <div className="tabular-nums break-words">{v == null || v === "" ? "—" : v}</div>
    </>
  );
}

export default function TraceDrawer({
  trace,
  onClose,
  onReplayTrace,
}: {
  trace: TraceEvent | null;
  onClose: () => void;
  onReplayTrace?: (trace: TraceEvent) => void;
}) {
  if (!trace) return null;

  return (
    <div className="fixed top-0 right-0 h-screen w-[min(460px,92vw)] bg-surface border-l border-line shadow-card z-20 overflow-y-auto p-[22px]">
      <button
        onClick={onClose}
        className="absolute top-4 right-[18px] p-1 rounded-md text-muted hover:text-ink hover:bg-accent-soft/30 transition-colors cursor-pointer"
        aria-label="Close trace drawer"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <h3 className="m-0 mb-1 text-[16px] font-semibold flex items-center gap-2">
        <span className="font-mono text-[11px] px-2 py-0.5 rounded-md border border-line bg-surface-raised font-normal">{trace.op}</span>
        <span>Trace Details</span>
      </h3>
      <div className="font-mono text-[12px] text-muted">
        {trace.id} · {new Date(trace.ts * 1000).toLocaleString()}
      </div>
      <div className="grid grid-cols-[130px_1fr] gap-x-3.5 gap-y-2 mt-4 text-[13px]">
        <Row k="Namespace" v={trace.namespace} />
        <Row k="Latency" v={`${trace.latency_ms.toFixed(2)} ms`} />
        <Row k="Result Count" v={trace.n_results} />
        <Row k="Top K" v={trace.top_k} />
        <Row k="Index Cache" v={trace.cache_hit == null ? "No Cache" : trace.cache_hit ? "Hit" : "Miss"} />
        <Row k="Metadata Filter" v={trace.filtered ? "Applied" : "None"} />
        <Row k="Rescore Metric" v={trace.rescore || "—"} />
        <Row k="Reranker" v={trace.rerank || "None"} />
        <Row k="Top Score" v={trace.score_top != null ? trace.score_top.toFixed(4) : "—"} />
        <Row k="Mean Score" v={trace.score_mean != null ? trace.score_mean.toFixed(4) : "—"} />
        <Row
          k="Status"
          v={
            <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] px-2 py-0.5 rounded-md ${trace.status === "ok" ? "bg-ok/10 text-ok" : "bg-red-500/10 text-red-500"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${trace.status === "ok" ? "bg-ok" : "bg-red-500"}`} />
              {trace.status === "ok" ? "SUCCESS" : "ERROR"}
            </span>
          }
        />
        {trace.error && <Row k="Error Detail" v={trace.error} />}
        {trace.query_preview && <Row k="Query Preview" v={trace.query_preview} />}
      </div>
      <div className="mt-[18px]">
        <div className="font-mono text-[12px] text-muted mb-1.5">End-to-End Latency Duration</div>
        <div className="h-2 rounded-full bg-accent/20 overflow-hidden">
          <div className="h-full bg-accent rounded-full" style={{ width: "100%" }} />
        </div>
      </div>

      {onReplayTrace && (
        <div className="mt-6 pt-4 border-t border-line">
          <button
            type="button"
            onClick={() => onReplayTrace(trace)}
            className="w-full py-2.5 px-4 rounded-lg bg-accent text-white font-mono text-xs font-semibold hover:bg-accent/90 transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" strokeWidth="1" />
            </svg>
            <span>Replay Execution Span in Studio</span>
            <span className="ml-1">&rarr;</span>
          </button>
          <p className="font-mono text-[11px] text-faint text-center mt-1.5">
            Visualize execution graph and node-by-node latency breakdown
          </p>
        </div>
      )}
    </div>
  );
}
