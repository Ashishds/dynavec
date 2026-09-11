"use client";
import React, { useState } from "react";

export default function CostPanel() {
  const [vectors, setVectors] = useState(1_000_000); // 1M vectors
  const [qps, setQps] = useState(25); // 25 QPS

  // Cost models based on AWS public list prices & competitor standard tiers
  const millionQueriesPerMonth = (qps * 3600 * 24 * 30.5) / 1_000_000;
  const gbStorage = (vectors * (1536 * 4 + 500)) / (1024 * 1024 * 1024); // 1536 float32 + 500 bytes metadata

  // Dynavec: S3 storage ($0.023/GB) + DynamoDB ($1.25/M writes, $0.25/M reads) + S3 Vectors API ($0.005/M)
  const dynavecCost = +(gbStorage * 0.023 + millionQueriesPerMonth * 0.28).toFixed(2);

  // Pinecone Serverless: $0.33/GB storage + $8.25/M query units
  const pineconeCost = +(gbStorage * 0.33 + millionQueriesPerMonth * 8.25).toFixed(2);

  // OpenSearch Managed: 2x r6g.large instances ($0.267/hr each) + gp3 storage = ~$390/mo baseline
  const opensearchCost = +(390.0 + gbStorage * 0.12).toFixed(2);

  const savings = Math.max(0, Math.round(((pineconeCost - dynavecCost) / (pineconeCost || 1)) * 100));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight">Interactive Cost Modeling & Cloud ROI</h2>
          <p className="text-sm text-muted">Compare serverless in-account AWS costs against managed vector database providers</p>
        </div>
        <span className="font-mono text-xs px-3 py-1 bg-ok/10 text-ok font-bold rounded-full border border-ok/30">
          Save ~{savings}% with Dynavec
        </span>
      </div>

      <div className="bg-surface border border-line rounded-xl2 p-6 space-y-6">
        <h3 className="font-semibold text-sm">Workload Parameters</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="flex justify-between text-xs font-mono mb-2">
              <span className="text-muted">Indexed Vectors</span>
              <span className="font-bold text-accent-ink">{vectors.toLocaleString()} vectors ({gbStorage.toFixed(1)} GB)</span>
            </div>
            <input
              type="range"
              min={100_000}
              max={10_000_000}
              step={100_000}
              value={vectors}
              onChange={(e) => setVectors(Number(e.target.value))}
              className="w-full accent-accent cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-faint font-mono mt-1">
              <span>100K</span>
              <span>5M</span>
              <span>10M</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-mono mb-2">
              <span className="text-muted">Query Traffic</span>
              <span className="font-bold text-accent-ink">{qps} QPS (~{millionQueriesPerMonth.toFixed(1)}M queries/mo)</span>
            </div>
            <input
              type="range"
              min={1}
              max={200}
              step={5}
              value={qps}
              onChange={(e) => setQps(Number(e.target.value))}
              className="w-full accent-accent cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-faint font-mono mt-1">
              <span>1 QPS</span>
              <span>100 QPS</span>
              <span>200 QPS</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface border-2 border-accent rounded-xl2 p-6 relative shadow-sm">
          <span className="absolute -top-2.5 right-4 font-mono text-[10px] font-bold px-2 py-0.5 bg-accent text-white rounded-full uppercase tracking-wider">
            Your Architecture
          </span>
          <div className="text-xs text-muted font-mono uppercase tracking-wider mb-2">Dynavec (AWS Serverless)</div>
          <div className="text-3xl font-bold font-mono text-accent-ink mb-2">
            ${dynavecCost} <span className="text-xs font-normal text-muted">/ month</span>
          </div>
          <p className="text-xs text-muted mb-4">S3 Vectors storage + DynamoDB on-demand hydration. Zero idle servers.</p>
          <div className="text-[11.5px] font-mono text-ok flex items-center gap-1.5">
            <span>✔</span> Pure pay-per-query pricing
          </div>
        </div>

        <div className="bg-surface border border-line rounded-xl2 p-6 opacity-90">
          <div className="text-xs text-muted font-mono uppercase tracking-wider mb-2">Pinecone (Serverless)</div>
          <div className="text-3xl font-bold font-mono text-ink mb-2">
            ${pineconeCost} <span className="text-xs font-normal text-muted">/ month</span>
          </div>
          <p className="text-xs text-muted mb-4">Proprietary managed cloud. High markup on storage &amp; read units.</p>
          <div className="text-[11.5px] font-mono text-err flex items-center gap-1.5">
            <span>✖</span> Up to {(pineconeCost / (dynavecCost || 1)).toFixed(1)}× more expensive
          </div>
        </div>

        <div className="bg-surface border border-line rounded-xl2 p-6 opacity-85">
          <div className="text-xs text-muted font-mono uppercase tracking-wider mb-2">OpenSearch (2x r6g.large)</div>
          <div className="text-3xl font-bold font-mono text-ink mb-2">
            ${opensearchCost} <span className="text-xs font-normal text-muted">/ month</span>
          </div>
          <p className="text-xs text-muted mb-4">Provisioned EC2 clusters running 24/7 even with 0 incoming traffic.</p>
          <div className="text-[11.5px] font-mono text-err flex items-center gap-1.5">
            <span>✖</span> Massive idle server costs
          </div>
        </div>
      </div>
    </div>
  );
}
