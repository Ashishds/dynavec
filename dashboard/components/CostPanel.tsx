"use client";
import React, { useState } from "react";

export default function CostPanel() {
  const [vectors, setVectors] = useState(1_000_000); // 1M vectors
  const [qps, setQps] = useState(25); // 25 QPS

  // Cost models based on AWS public list prices & competitor standard tiers
  const millionQueriesPerMonth = (qps * 3600 * 24 * 30.5) / 1_000_000;
  const gbStorage = (vectors * (1536 * 4 + 500)) / (1024 * 1024 * 1024); // 1536 float32 + 500 bytes metadata

  // Dynavec: S3 storage ($0.023/GB) + DynamoDB ($0.25/M reads) + S3 Vectors API ($0.03/M)
  const dynavecCost = +(gbStorage * 0.023 + millionQueriesPerMonth * 0.28).toFixed(2);

  // Pinecone Serverless: $0.33/GB storage + $8.25/M query units
  const pineconeCost = +(gbStorage * 0.33 + millionQueriesPerMonth * 8.25).toFixed(2);

  // OpenSearch Managed: 2x r6g.large instances ($0.267/hr each) + gp3 storage = ~$390/mo baseline
  const opensearchCost = +(390.0 + gbStorage * 0.12).toFixed(2);

  const savings = Math.max(0, Math.round(((pineconeCost - dynavecCost) / (pineconeCost || 1)) * 100));

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-sans tracking-tight text-ink">Total Cost of Ownership (TCO) &amp; Cloud ROI</h2>
          <p className="text-sm text-muted">
            Comparative financial analysis of in-account serverless AWS retrieval versus managed vector database architectures.
          </p>
        </div>
        <span className="font-mono text-xs px-3 py-1.5 bg-ok/10 text-ok font-semibold rounded-full border border-ok/30 flex items-center gap-1.5 self-start sm:self-auto">
          Estimated TCO Reduction: ~{savings}%
        </span>
      </div>

      {/* Workload Parameters */}
      <div className="bg-surface border border-line rounded-xl2 p-5 space-y-5">
        <h3 className="font-semibold text-sm font-sans text-ink">Workload Sizing Parameters</h3>
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
              <span className="text-muted">Query Throughput</span>
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

      {/* 3 Architecture Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Dynavec */}
        <div className="bg-surface border-2 border-emerald-500/50 rounded-xl2 p-5 relative shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-[10.5px] font-bold px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded-full uppercase tracking-wider border border-emerald-500/20">
                In-Account Serverless
              </span>
              <span className="text-xs font-mono text-ok font-medium">Optimal TCO</span>
            </div>
            <h4 className="text-sm font-bold font-mono text-ink mb-1">Dynavec on AWS</h4>
            <div className="text-3xl font-bold font-mono text-emerald-400 mb-2">
              ${dynavecCost} <span className="text-xs font-normal text-muted">/ month</span>
            </div>
            <p className="text-xs text-muted mb-4 leading-relaxed">
              Amazon S3 vector index storage paired with DynamoDB on-demand document hydration. Zero provisioned compute.
            </p>
          </div>

          <div className="space-y-2 border-t border-line/70 pt-3 text-xs font-mono text-muted">
            <div className="flex items-center gap-1.5 text-ink">
              <svg className="w-3.5 h-3.5 text-ok shrink-0 inline-block mr-1.5" viewBox="0 0 16 16" fill="currentColor"><path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" /></svg> Zero idle server footprint
            </div>
            <div className="flex items-center gap-1.5 text-ink">
              <svg className="w-3.5 h-3.5 text-ok shrink-0 inline-block mr-1.5" viewBox="0 0 16 16" fill="currentColor"><path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" /></svg> In-account VPC data residency
            </div>
            <div className="flex items-center gap-1.5 text-ink">
              <svg className="w-3.5 h-3.5 text-ok shrink-0 inline-block mr-1.5" viewBox="0 0 16 16" fill="currentColor"><path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" /></svg> 100% pay-per-request billing
            </div>
          </div>
        </div>

        {/* Pinecone */}
        <div className="bg-surface border border-line rounded-xl2 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-[10.5px] font-medium px-2 py-0.5 bg-line/60 text-muted rounded-full uppercase tracking-wider border border-line">
                Managed SaaS Provider
              </span>
            </div>
            <h4 className="text-sm font-bold font-mono text-ink mb-1">Pinecone Serverless Tier</h4>
            <div className="text-3xl font-bold font-mono text-ink mb-2">
              ${pineconeCost} <span className="text-xs font-normal text-muted">/ month</span>
            </div>
            <p className="text-xs text-muted mb-4 leading-relaxed">
              Third-party managed vector platform with query processing unit (QPU) consumption tiers and cross-cloud egress.
            </p>
          </div>

          <div className="space-y-2 border-t border-line/70 pt-3 text-xs font-mono text-muted">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> +${(pineconeCost - dynavecCost).toFixed(2)}/mo differential
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> Third-party SaaS infrastructure
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> Tiered QPU pricing model
            </div>
          </div>
        </div>

        {/* OpenSearch */}
        <div className="bg-surface border border-line rounded-xl2 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-[10.5px] font-medium px-2 py-0.5 bg-line/60 text-muted rounded-full uppercase tracking-wider border border-line">
                Dedicated Cluster
              </span>
            </div>
            <h4 className="text-sm font-bold font-mono text-ink mb-1">OpenSearch (2&times; r6g.large)</h4>
            <div className="text-3xl font-bold font-mono text-ink mb-2">
              ${opensearchCost} <span className="text-xs font-normal text-muted">/ month</span>
            </div>
            <p className="text-xs text-muted mb-4 leading-relaxed">
              Always-on dedicated EC2 memory-optimized instances with provisioned EBS gp3 storage volumes.
            </p>
          </div>

          <div className="space-y-2 border-t border-line/70 pt-3 text-xs font-mono text-muted">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> Fixed baseline even at 0 QPS
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> Provisioned RAM &amp; EBS costs
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/60 shrink-0 inline-block mr-1.5" /> Manual cluster lifecycle overhead
            </div>
          </div>
        </div>
      </div>

      {/* ── AWS Itemized Bill Breakdown ─────────────────────────────────── */}
      <div className="bg-surface border border-line rounded-xl2 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line/70 pb-3">
          <div>
            <h3 className="text-sm font-bold font-sans text-ink flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>AWS Direct Billing Line-Item Decomposition</span>
            </h3>
            <p className="text-xs text-muted mt-0.5">
              Estimated direct AWS billing line items for this workload ({vectors.toLocaleString()} vectors &middot; {qps} QPS)
            </p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20 font-semibold self-start sm:self-auto">
            In-Account AWS us-east-1
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-4 rounded-xl bg-bg border border-line space-y-1.5">
            <span className="text-faint text-[10.5px] uppercase tracking-wider">1. Amazon S3 Vector Storage</span>
            <div className="text-lg font-bold text-ink">${(gbStorage * 0.023).toFixed(2)}/mo</div>
            <p className="text-[11px] text-muted font-sans leading-tight">
              {gbStorage.toFixed(1)} GB @ $0.023 per GB-month. Float32 vector embeddings and candidate index metadata.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-bg border border-line space-y-1.5">
            <span className="text-faint text-[10.5px] uppercase tracking-wider">2. DynamoDB Read Request Units</span>
            <div className="text-lg font-bold text-ink">${((millionQueriesPerMonth * 0.25)).toFixed(2)}/mo</div>
            <p className="text-[11px] text-muted font-sans leading-tight">
              {millionQueriesPerMonth.toFixed(1)}M queries @ $0.25 per million reads. Parallel BatchGetItem document hydration.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-bg border border-line space-y-1.5">
            <span className="text-faint text-[10.5px] uppercase tracking-wider">3. S3 Vectors Query Execution</span>
            <div className="text-lg font-bold text-ink">${((millionQueriesPerMonth * 0.03)).toFixed(2)}/mo</div>
            <p className="text-[11px] text-muted font-sans leading-tight">
              ANN nearest-neighbor vector traversal API operations. Scales to $0.00 during idle periods.
            </p>
          </div>
        </div>
      </div>

      {/* FinOps Guarantee Callout */}
      <div className="p-4 rounded-xl bg-surface border border-line/70 flex items-start gap-3 text-xs font-mono">
        <div className="w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0 border border-emerald-500/20 font-bold mt-0.5">
          $
        </div>
        <div className="space-y-1">
          <span className="font-bold text-ink">FinOps Architectural Guarantee:</span>
          <p className="text-muted font-sans leading-relaxed text-[12px]">
            By storing embeddings directly in Amazon S3 and executing on-demand document hydration via DynamoDB, Dynavec converts fixed infrastructure overhead into purely elastic, usage-based pricing. When query volume ceases, monthly compute spend automatically drops to zero.
          </p>
        </div>
      </div>
    </div>
  );
}
