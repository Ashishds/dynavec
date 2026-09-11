"use client";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import type { Metrics } from "@/lib/types";

export default function VolumeChart({ m }: { m: Metrics }) {
  const data = m.histogram.map((count, i) => ({ i, count }));
  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
  return (
    <div className="bg-surface border border-line rounded-xl2 px-[18px] py-4">
      <h3 className="m-0 mb-3.5 text-[14px] font-semibold">
        Query volume{" "}
        <span className="font-mono text-[11px] text-faint font-normal">
          {m.total} traces · {Math.round(m.bucket_width_s)}s buckets
        </span>
      </h3>
      <div style={{ width: "100%", height: 150 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <XAxis dataKey="i" hide />
            <Tooltip
              cursor={{ fill: isDark ? "rgba(240,122,88,0.1)" : "#fdeee8" }}
              contentStyle={{
                fontFamily: "JetBrains Mono",
                fontSize: 12,
                border: `1px solid ${isDark ? "#2a2a2e" : "#ece6df"}`,
                borderRadius: 8,
                background: isDark ? "#18181b" : "#ffffff",
                color: isDark ? "#f0eeec" : "#14110f",
              }}
              labelFormatter={() => ""}
              formatter={(v: number) => [v, "queries"]}
            />
            <Bar dataKey="count" fill={isDark ? "#f07a58" : "#e8623b"} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
