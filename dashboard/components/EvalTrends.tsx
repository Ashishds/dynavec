"use client";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EvalRun } from "@/lib/types";

const COLORS = {
  recall: ["#2f7d5b", "#4ade80", "#86efac", "#bbf7d0"],
  ndcg: ["#e8623b", "#f07a58", "#f9a68a", "#fdd0c0"],
  mrr: "#3b5bdb",
};

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function EvalTrends({ runs }: { runs: EvalRun[] }) {
  if (runs.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold font-mono tracking-tight">Retrieval Quality &amp; Ranking Benchmarks</h2>
            <p className="text-sm text-muted">Offline accuracy evaluation measuring how effectively Dynavec ranks relevant documents</p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 bg-accent-soft text-accent-ink rounded-full border border-accent/20">
            Awaiting Benchmark Run
          </span>
        </div>

        <div className="bg-surface border border-line rounded-xl2 p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-accent-soft text-accent-ink flex items-center justify-center mx-auto mb-3 font-mono font-bold text-lg">
            Q&amp;A
          </div>
          <h3 className="text-base font-bold font-mono text-ink mb-1">Continuous Retrieval Quality Tracking</h3>
          <p className="text-xs text-muted max-w-md mx-auto mb-4">
            Dynavec provides built-in offline evaluation tools (<code className="text-accent font-semibold">dynavec.eval</code>) to measure Recall, Mean Reciprocal Rank (MRR), and nDCG against your enterprise ground-truth datasets.
          </p>
          <div className="inline-block text-left bg-bg border border-line rounded-lg p-3 text-xs font-mono text-muted">
            <span className="text-faint"># Run a quality benchmark in Python:</span><br />
            <span className="text-ink">from dynavec.eval import run_eval, EvalDataset</span><br />
            <span className="text-accent">results = run_eval(db, dataset, ks=[1, 5, 10, 20])</span><br />
            <span className="text-accent">results.to_json(&quot;evals/eval-001.json&quot;)</span>
          </div>
        </div>
      </div>
    );
  }

  const ks = runs[0].ks;

  // Build chart data: one row per run, columns for each metric
  const recallData = runs.map((r) => {
    const row: Record<string, number | string> = { date: formatDate(r.timestamp) };
    for (const k of ks) row[`R@${k}`] = +(r.recall[String(k)] ?? 0).toFixed(4);
    return row;
  });

  const ndcgData = runs.map((r) => {
    const row: Record<string, number | string> = { date: formatDate(r.timestamp) };
    for (const k of ks) row[`nDCG@${k}`] = +(r.ndcg[String(k)] ?? 0).toFixed(4);
    return row;
  });

  const mrrData = runs.map((r) => ({
    date: formatDate(r.timestamp),
    MRR: +r.mrr.toFixed(4),
  }));

  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
  const gridColor = isDark ? "#2a2a2e" : "#ece6df";
  const tooltipBg = isDark ? "#18181b" : "#ffffff";
  const tooltipBorder = isDark ? "#2a2a2e" : "#ece6df";
  const tooltipColor = isDark ? "#f0eeec" : "#14110f";
  const axisColor = isDark ? "#5c5650" : "#a99f97";

  const tooltipStyle = {
    fontFamily: "JetBrains Mono",
    fontSize: 12,
    border: `1px solid ${tooltipBorder}`,
    borderRadius: 8,
    background: tooltipBg,
    color: tooltipColor,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight">Retrieval Quality &amp; Accuracy Benchmarks</h2>
          <p className="text-sm text-muted">Offline accuracy evaluation measuring rank ordering, context precision, and target recall</p>
        </div>
        <span className="font-mono text-xs px-2.5 py-1 bg-ok/10 text-ok rounded-full border border-ok/30 font-semibold">
          {runs.length} Continuous Evaluation Runs
        </span>
      </div>

      {/* Metric Explainer Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-[11.5px]">
        <div className="p-3 bg-surface border border-line rounded-xl">
          <span className="text-accent font-bold block mb-1">MRR (Mean Reciprocal Rank)</span>
          <p className="text-muted leading-relaxed font-sans text-xs">
            Evaluates how high the first correct result is ranked. A score above 90% means the single best answer appears at rank #1 in almost every search.
          </p>
        </div>
        <div className="p-3 bg-surface border border-line rounded-xl">
          <span className="text-ok font-bold block mb-1">Recall@k</span>
          <p className="text-muted leading-relaxed font-sans text-xs">
            The fraction of ground-truth relevant documents captured within the top-k retrieved chunks. High recall ensures the LLM receives all context.
          </p>
        </div>
        <div className="p-3 bg-surface border border-line rounded-xl">
          <span className="text-[#3b5bdb] font-bold block mb-1">nDCG@k</span>
          <p className="text-muted leading-relaxed font-sans text-xs">
            Normalized Discounted Cumulative Gain. Rewards algorithms that position highly relevant passages ahead of moderately relevant ones.
          </p>
        </div>
      </div>
      {/* Summary KPIs for latest run */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {(() => {
          const latest = runs[runs.length - 1];
          const prev = runs.length > 1 ? runs[runs.length - 2] : null;
          const items = [
            { label: "MRR", value: latest.mrr, prev: prev?.mrr },
            { label: `Recall@${ks[0]}`, value: latest.recall[String(ks[0])], prev: prev?.recall[String(ks[0])] },
            { label: `Recall@${ks[ks.length - 1]}`, value: latest.recall[String(ks[ks.length - 1])], prev: prev?.recall[String(ks[ks.length - 1])] },
            { label: `nDCG@${ks[ks.length - 1]}`, value: latest.ndcg[String(ks[ks.length - 1])], prev: prev?.ndcg[String(ks[ks.length - 1])] },
          ];
          return items.map((it) => {
            const delta = it.prev != null ? it.value - it.prev : null;
            return (
              <div key={it.label} className="bg-surface border border-line rounded-xl2 px-[18px] py-4">
                <div className="text-[12px] text-muted mb-2">{it.label}</div>
                <div className="font-mono text-[26px] font-bold tracking-tight">
                  {(it.value * 100).toFixed(1)}
                  <span className="text-[13px] text-muted font-normal"> %</span>
                  {delta != null && (
                    <span className={`text-[12px] font-normal ml-2 ${delta >= 0 ? "text-ok" : "text-err"}`}>
                      {delta >= 0 ? "▲" : "▼"} {Math.abs(delta * 100).toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
            );
          });
        })()}
      </div>

      {/* Recall@k line chart */}
      <div className="bg-surface border border-line rounded-xl2 px-[18px] py-4">
        <h3 className="m-0 mb-3.5 text-[14px] font-semibold">
          Recall@k over time{" "}
          <span className="font-mono text-[11px] text-faint font-normal">{runs.length} runs · {runs[0].dataset}</span>
        </h3>
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={recallData} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: axisColor }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: axisColor }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "JetBrains Mono" }} />
              {ks.map((k, i) => (
                <Line key={k} type="monotone" dataKey={`R@${k}`} stroke={COLORS.recall[i % COLORS.recall.length]} strokeWidth={2} dot={{ r: 3 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* nDCG@k line chart */}
      <div className="bg-surface border border-line rounded-xl2 px-[18px] py-4">
        <h3 className="m-0 mb-3.5 text-[14px] font-semibold">
          nDCG@k over time{" "}
          <span className="font-mono text-[11px] text-faint font-normal">normalized discounted cumulative gain</span>
        </h3>
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={ndcgData} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: axisColor }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: axisColor }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "JetBrains Mono" }} />
              {ks.map((k, i) => (
                <Line key={k} type="monotone" dataKey={`nDCG@${k}`} stroke={COLORS.ndcg[i % COLORS.ndcg.length]} strokeWidth={2} dot={{ r: 3 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* MRR line chart */}
      <div className="bg-surface border border-line rounded-xl2 px-[18px] py-4">
        <h3 className="m-0 mb-3.5 text-[14px] font-semibold">
          MRR over time{" "}
          <span className="font-mono text-[11px] text-faint font-normal">mean reciprocal rank</span>
        </h3>
        <div style={{ width: "100%", height: 180 }}>
          <ResponsiveContainer>
            <LineChart data={mrrData} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: axisColor }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: axisColor }} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
              <Line type="monotone" dataKey="MRR" stroke={COLORS.mrr} strokeWidth={2.5} dot={{ r: 3.5, fill: COLORS.mrr }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Run details table */}
      <div className="bg-surface border border-line rounded-xl2 overflow-hidden">
        <div className="px-[18px] py-3.5 border-b border-line">
          <h3 className="m-0 text-[14px] font-semibold">Run history</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="text-left font-mono text-[11px] uppercase tracking-wide text-muted bg-table-head">
                {["Date", "Dataset", "Queries", "MRR", ...ks.map((k) => `R@${k}`), ...ks.map((k) => `nDCG@${k}`)].map((h) => (
                  <th key={h} className="px-[18px] py-2.5 border-b border-line font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...runs].reverse().map((r, i) => (
                <tr key={i} className="[&>td]:px-[18px] [&>td]:py-2.5 [&>td]:border-b [&>td]:border-line tabular-nums">
                  <td className="font-mono">{formatDate(r.timestamp)}</td>
                  <td>{r.dataset}</td>
                  <td className="font-mono">{r.n_queries}</td>
                  <td className="font-mono">{(r.mrr * 100).toFixed(1)}%</td>
                  {ks.map((k) => (
                    <td key={`r${k}`} className="font-mono">{((r.recall[String(k)] ?? 0) * 100).toFixed(1)}%</td>
                  ))}
                  {ks.map((k) => (
                    <td key={`n${k}`} className="font-mono">{((r.ndcg[String(k)] ?? 0) * 100).toFixed(1)}%</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
