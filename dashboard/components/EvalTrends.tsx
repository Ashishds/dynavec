"use client";
import React, { useState } from "react";
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
  recall: ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b"],
  ndcg: ["#06b6d4", "#6366f1", "#ec4899", "#f97316"],
  mrr: "#10b981",
};

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function EvalTrends({ runs }: { runs: EvalRun[] }) {
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [activeChartTab, setActiveChartTab] = useState<"recall" | "ranking">("recall");

  if (runs.length === 0) {
    return (
      <div className="space-y-6 max-w-6xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold font-sans tracking-tight text-ink">Retrieval Quality &amp; Accuracy Benchmarks</h2>
            <p className="text-sm text-muted">Offline accuracy evaluation measuring rank ordering, context precision, and target recall</p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 bg-accent-soft text-accent-ink rounded-full border border-accent/20 self-start sm:self-auto">
            Awaiting Benchmark Run
          </span>
        </div>

        <div className="bg-surface border border-line rounded-xl2 p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-accent-soft text-accent-ink flex items-center justify-center mx-auto mb-3 font-mono font-bold text-lg">
            Q&amp;A
          </div>
          <h3 className="text-base font-bold font-sans text-ink mb-1">Continuous Retrieval Quality Tracking</h3>
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

  const datasets = Array.from(new Set(runs.map((r) => r.dataset)));
  const defaultDataset = datasets.includes("production-rag-benchmark") ? "production-rag-benchmark" : datasets[0] || "";
  const activeDataset = (selectedDataset && datasets.includes(selectedDataset)) ? selectedDataset : defaultDataset;

  // Filter runs strictly by the active dataset so deltas and Ks are statistically coherent
  const displayRuns = runs.filter((r) => r.dataset === activeDataset);

  // Extract Ks that strictly exist in this dataset
  const ks = Array.from(new Set(displayRuns.flatMap((r) => r.ks || []))).sort((a, b) => a - b);

  // Build chart datasets
  const chartData = displayRuns.map((r) => {
    const row: Record<string, number | string> = {
      date: formatDate(r.timestamp),
      MRR: +(r.mrr * 100).toFixed(1),
    };
    for (const k of ks) {
      if (r.recall && r.recall[String(k)] != null) {
        row[`R@${k}`] = +(r.recall[String(k)] * 100).toFixed(1);
      }
      if (r.ndcg && r.ndcg[String(k)] != null) {
        row[`nDCG@${k}`] = +(r.ndcg[String(k)] * 100).toFixed(1);
      }
    }
    return row;
  });

  const latest = displayRuns[displayRuns.length - 1];
  const prev = displayRuns.length > 1 ? displayRuns[displayRuns.length - 2] : null;

  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
  const gridColor = isDark ? "#27272a" : "#e4e4e7";
  const tooltipBg = isDark ? "#18181b" : "#ffffff";
  const tooltipBorder = isDark ? "#27272a" : "#e4e4e7";
  const tooltipColor = isDark ? "#f4f4f5" : "#09090b";
  const axisColor = isDark ? "#71717a" : "#a1a1aa";

  const tooltipStyle = {
    fontFamily: "JetBrains Mono, monospace",
    fontSize: 12,
    border: `1px solid ${tooltipBorder}`,
    borderRadius: 8,
    background: tooltipBg,
    color: tooltipColor,
    padding: "8px 12px",
  };

  // KPI calculations for latest run
  const kpis = [
    {
      label: "MRR (Mean Reciprocal Rank)",
      value: latest?.mrr != null ? (latest.mrr * 100).toFixed(1) : "—",
      delta: latest?.mrr != null && prev?.mrr != null ? +((latest.mrr - prev.mrr) * 100).toFixed(1) : null,
      desc: "Rank-1 accuracy of first ground-truth document",
    },
    {
      label: `Top-1 Recall (R@${ks[0] ?? 1})`,
      value: latest?.recall?.[String(ks[0] ?? 1)] != null ? (latest.recall[String(ks[0] ?? 1)] * 100).toFixed(1) : "—",
      delta: latest?.recall?.[String(ks[0] ?? 1)] != null && prev?.recall?.[String(ks[0] ?? 1)] != null
        ? +((latest.recall[String(ks[0] ?? 1)] - prev.recall[String(ks[0] ?? 1)]) * 100).toFixed(1)
        : null,
      desc: "Single-shot accuracy at rank #1",
    },
    {
      label: `Top-5 Recall (R@${ks.find((k) => k === 5) ?? ks[1] ?? 5})`,
      value: (() => {
        const kTarget = ks.find((k) => k === 5) ?? ks[1] ?? 5;
        return latest?.recall?.[String(kTarget)] != null ? (latest.recall[String(kTarget)] * 100).toFixed(1) : "—";
      })(),
      delta: (() => {
        const kTarget = ks.find((k) => k === 5) ?? ks[1] ?? 5;
        if (latest?.recall?.[String(kTarget)] != null && prev?.recall?.[String(kTarget)] != null) {
          return +((latest.recall[String(kTarget)] - prev.recall[String(kTarget)]) * 100).toFixed(1);
        }
        return null;
      })(),
      desc: "Relevant context capture within top-5 candidates",
    },
    {
      label: `Top-10 Recall (R@${ks.find((k) => k === 10) ?? ks[ks.length - 1] ?? 10})`,
      value: (() => {
        const kTarget = ks.find((k) => k === 10) ?? ks[ks.length - 1] ?? 10;
        return latest?.recall?.[String(kTarget)] != null ? (latest.recall[String(kTarget)] * 100).toFixed(1) : "—";
      })(),
      delta: (() => {
        const kTarget = ks.find((k) => k === 10) ?? ks[ks.length - 1] ?? 10;
        if (latest?.recall?.[String(kTarget)] != null && prev?.recall?.[String(kTarget)] != null) {
          return +((latest.recall[String(kTarget)] - prev.recall[String(kTarget)]) * 100).toFixed(1);
        }
        return null;
      })(),
      desc: "Cumulative knowledge retrieval coverage",
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-sans tracking-tight text-ink">Retrieval Quality &amp; Accuracy Benchmarks</h2>
          <p className="text-sm text-muted">
            Continuous offline evaluation measuring rank ordering, context precision, and target recall.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="font-mono text-xs px-2.5 py-1 bg-ok/10 text-ok rounded-full border border-ok/30 font-semibold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-ok animate-pulse" /> {displayRuns.length} Benchmark Runs Synced
          </span>
        </div>
      </div>

      {/* Dataset Selector Tabs */}
      <div className="flex items-center gap-2 border-b border-line pb-3">
        <span className="text-xs font-mono text-muted mr-1">Benchmark Dataset:</span>
        {datasets.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setSelectedDataset(d)}
            className={
              "px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer " +
              (activeDataset === d
                ? "bg-accent text-white shadow-sm"
                : "bg-surface text-muted hover:text-ink border border-line")
            }
          >
            {d}
            <span className="ml-1.5 text-[10.5px] opacity-80">
              ({runs.filter((r) => r.dataset === d).length} runs)
            </span>
          </button>
        ))}
      </div>

      {/* Metric Explainer Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
        <div className="p-3.5 bg-surface border border-line rounded-xl">
          <span className="text-emerald-400 font-bold block mb-1">MRR (Mean Reciprocal Rank)</span>
          <p className="text-muted leading-relaxed font-sans text-[11.5px]">
            Measures position of the first correct chunk. A score above 90% guarantees the best answer appears at rank #1 for almost every query.
          </p>
        </div>
        <div className="p-3.5 bg-surface border border-line rounded-xl">
          <span className="text-blue-400 font-bold block mb-1">Recall@k</span>
          <p className="text-muted leading-relaxed font-sans text-[11.5px]">
            The percentage of ground-truth documents successfully retrieved in top-k chunks. High recall ensures the LLM receives full grounding context.
          </p>
        </div>
        <div className="p-3.5 bg-surface border border-line rounded-xl">
          <span className="text-purple-400 font-bold block mb-1">nDCG@k</span>
          <p className="text-muted leading-relaxed font-sans text-[11.5px]">
            Normalized Discounted Cumulative Gain. Rewards algorithms that order highly relevant passages above moderately relevant chunks.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-surface border border-line rounded-xl2 p-4">
            <div className="text-[11.5px] text-muted font-mono mb-1">{kpi.label}</div>
            <div className="font-mono text-2xl font-bold tracking-tight text-ink flex items-baseline gap-1.5">
              <span>{kpi.value}%</span>
              {kpi.delta != null && (
                <span className={`text-xs font-normal font-mono ${kpi.delta >= 0 ? "text-ok" : "text-err"}`}>
                  {kpi.delta >= 0 ? "▲ +" : "▼ "}
                  {Math.abs(kpi.delta)}%
                </span>
              )}
            </div>
            <p className="text-[11px] text-faint font-sans mt-1 leading-tight">{kpi.desc}</p>
          </div>
        ))}
      </div>

      {/* Interactive Trend Chart */}
      <div className="bg-surface border border-line rounded-xl2 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="font-semibold text-sm font-sans text-ink">
              {activeChartTab === "recall" ? "Recall@k Multi-Cutoff Trends" : "Ranking Quality (MRR & nDCG) Trends"}
            </h3>
            <p className="text-xs text-muted">
              Progression across {displayRuns.length} runs on <span className="font-mono text-accent">{activeDataset}</span>
            </p>
          </div>
          <div className="flex items-center border border-line rounded-lg overflow-hidden self-start sm:self-auto font-mono text-xs">
            <button
              type="button"
              onClick={() => setActiveChartTab("recall")}
              className={`px-3 py-1 transition-colors cursor-pointer ${
                activeChartTab === "recall" ? "bg-accent text-white font-medium" : "bg-bg text-muted hover:text-ink"
              }`}
            >
              Recall@k
            </button>
            <button
              type="button"
              onClick={() => setActiveChartTab("ranking")}
              className={`px-3 py-1 transition-colors cursor-pointer border-l border-line ${
                activeChartTab === "ranking" ? "bg-accent text-white font-medium" : "bg-bg text-muted hover:text-ink"
              }`}
            >
              MRR &amp; nDCG
            </button>
          </div>
        </div>

        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            {activeChartTab === "recall" ? (
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: axisColor }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: axisColor }} tickFormatter={(v: number) => `${v}%`} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 12, fontFamily: "JetBrains Mono" }} />
                {ks.map((k, i) => (
                  <Line
                    key={k}
                    type="monotone"
                    dataKey={`R@${k}`}
                    name={`Recall@${k}`}
                    stroke={COLORS.recall[i % COLORS.recall.length]}
                    strokeWidth={2}
                    dot={{ r: 3.5 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            ) : (
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: axisColor }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: axisColor }} tickFormatter={(v: number) => `${v}%`} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 12, fontFamily: "JetBrains Mono" }} />
                <Line
                  type="monotone"
                  dataKey="MRR"
                  name="MRR"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                {ks.map((k, i) => (
                  <Line
                    key={`ndcg${k}`}
                    type="monotone"
                    dataKey={`nDCG@${k}`}
                    name={`nDCG@${k}`}
                    stroke={COLORS.ndcg[i % COLORS.ndcg.length]}
                    strokeWidth={1.75}
                    strokeDasharray="4 4"
                    dot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* Run Details Table */}
      <div className="bg-surface border border-line rounded-xl2 overflow-hidden shadow-sm">
        <div className="px-5 py-3.5 border-b border-line flex items-center justify-between">
          <h3 className="m-0 text-sm font-semibold font-sans text-ink">
            Benchmark Execution History ({activeDataset})
          </h3>
          <span className="text-xs text-muted font-mono">{displayRuns.length} Total Runs</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs font-mono">
            <thead>
              <tr className="text-left uppercase tracking-wider text-muted bg-table-head border-b border-line">
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Dataset</th>
                <th className="px-4 py-3 font-medium text-right">Queries</th>
                <th className="px-4 py-3 font-medium text-right text-emerald-400">MRR</th>
                {ks.map((k) => (
                  <th key={`hdr-r${k}`} className="px-4 py-3 font-medium text-right">
                    R@{k}
                  </th>
                ))}
                {ks.map((k) => (
                  <th key={`hdr-n${k}`} className="px-4 py-3 font-medium text-right">
                    nDCG@{k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...displayRuns].reverse().map((r, i) => (
                <tr key={i} className="border-b border-line/60 hover:bg-line/20 transition-colors">
                  <td className="px-4 py-3 text-ink font-semibold">{formatDate(r.timestamp)}</td>
                  <td className="px-4 py-3 text-muted">{r.dataset}</td>
                  <td className="px-4 py-3 text-right text-muted">{r.n_queries}</td>
                  <td className="px-4 py-3 text-right font-bold text-ok">
                    {!isNaN(Number(r.mrr)) ? (r.mrr * 100).toFixed(1) + "%" : "—"}
                  </td>
                  {ks.map((k) => {
                    const val = Number(r.recall?.[String(k)]);
                    return (
                      <td key={`r${k}`} className="px-4 py-3 text-right text-ink">
                        {!isNaN(val) && val !== 0 ? (val * 100).toFixed(1) + "%" : "—"}
                      </td>
                    );
                  })}
                  {ks.map((k) => {
                    const val = Number(r.ndcg?.[String(k)]);
                    return (
                      <td key={`n${k}`} className="px-4 py-3 text-right text-muted">
                        {!isNaN(val) && val !== 0 ? (val * 100).toFixed(1) + "%" : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
