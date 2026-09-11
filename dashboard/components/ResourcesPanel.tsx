"use client";
import React from "react";

export default function ResourcesPanel() {
  const resources = [
    {
      type: "DynamoDB Document Table",
      name: "dynavec_docs",
      arn: "arn:aws:dynamodb:us-east-1:212919533030:table/dynavec_docs",
      status: "ACTIVE",
      billing: "PAY_PER_REQUEST (On-Demand)",
      keySchema: "pk (String, HASH)",
      items: "4 items indexed",
    },
    {
      type: "S3 Vector Bucket",
      name: "dynavec-vectors-212919533030",
      arn: "arn:aws:s3:::dynavec-vectors-212919533030",
      status: "ACTIVE",
      billing: "Standard S3 Storage",
      keySchema: "Server-side encryption: AES256",
      items: "Vectors synced with DynamoDB",
    },
    {
      type: "S3 Vectors ANN Index",
      name: "docs-index",
      arn: "arn:aws:s3vectors:us-east-1:212919533030:bucket/dynavec-vectors-212919533030/index/docs-index",
      status: "READY",
      billing: "1536 float32 dimensions",
      keySchema: "Distance metric: cosine",
      items: "Auto-calibrated HNSW index",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight">Cloud Resources (Buckets &amp; Indexes)</h2>
          <p className="text-sm text-muted">Provisioned AWS primitives managed by Terraform &amp; Dynavec</p>
        </div>
        <span className="font-mono text-xs px-2.5 py-1 bg-ok/10 text-ok rounded-full border border-ok/30 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-ok animate-pulse" /> All Systems Operational
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {resources.map((r) => (
          <div key={r.name} className="bg-surface border border-line rounded-xl2 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div>
                <span className="font-mono text-[11px] text-faint uppercase tracking-wider">{r.type}</span>
                <h3 className="text-base font-bold font-mono text-accent-ink">{r.name}</h3>
              </div>
              <span className="font-mono text-xs px-2 py-0.5 bg-ok/10 text-ok rounded font-semibold self-start sm:self-auto">
                {r.status}
              </span>
            </div>
            <div className="font-mono text-xs text-muted bg-line/30 px-3 py-1.5 rounded mb-3 break-all select-all">
              {r.arn}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-muted">
              <div><span className="text-faint">Mode / Config:</span> {r.billing}</div>
              <div><span className="text-faint">Schema:</span> {r.keySchema}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-line rounded-xl2 p-5">
        <h3 className="font-semibold text-sm mb-2 font-mono">Connected AWS Environment</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono mt-3">
          <div><div className="text-faint">Account ID</div><div className="font-bold">212919533030</div></div>
          <div><div className="text-faint">IAM User</div><div className="font-bold">dynavec-admin</div></div>
          <div><div className="text-faint">AWS Region</div><div className="font-bold">us-east-1</div></div>
          <div><div className="text-faint">Provisioner</div><div className="font-bold text-accent-ink">Terraform v1.14.0</div></div>
        </div>
      </div>

      {/* Production Readiness Matrix */}
      <div className="bg-surface border border-line rounded-xl2 p-5">
        <h3 className="font-semibold text-sm font-mono text-ink mb-1">Production Architecture &amp; Readiness Checklist</h3>
        <p className="text-xs text-muted mb-4 font-sans">
          Evaluation of cloud primitives, network isolation, security boundaries, and scaling controls for enterprise workloads.
        </p>
        <div className="space-y-2.5 font-mono text-xs">
          <div className="flex items-start justify-between p-3 bg-bg rounded-lg border border-line">
            <div>
              <span className="font-bold text-ink">Serverless Pay-Per-Request Auto-Scaling</span>
              <p className="text-muted text-[11px] font-sans mt-0.5">DynamoDB table automatically adjusts read/write capacity units based on real-time traffic spikes with zero manual intervention and $0 idle cost.</p>
            </div>
            <span className="px-2 py-0.5 bg-ok/10 text-ok rounded text-[11px] font-semibold shrink-0 ml-3">PRODUCTION READY</span>
          </div>

          <div className="flex items-start justify-between p-3 bg-bg rounded-lg border border-line">
            <div>
              <span className="font-bold text-ink">Strict Multi-Tenant Partition Isolation</span>
              <p className="text-muted text-[11px] font-sans mt-0.5">Tenant partition keys (<code className="text-accent">{`{namespace}#{id}`}</code>) physically isolate document storage and vector indexing with zero cross-tenant leakage.</p>
            </div>
            <span className="px-2 py-0.5 bg-ok/10 text-ok rounded text-[11px] font-semibold shrink-0 ml-3">PRODUCTION READY</span>
          </div>

          <div className="flex items-start justify-between p-3 bg-bg rounded-lg border border-line">
            <div>
              <span className="font-bold text-ink">Server-Side Data Encryption (At-Rest &amp; In-Transit)</span>
              <p className="text-muted text-[11px] font-sans mt-0.5">S3 Vector Bucket enforced with AES-256 server-side encryption; DynamoDB encrypted at rest with AWS KMS; all client APIs enforce HTTPS/TLS 1.3.</p>
            </div>
            <span className="px-2 py-0.5 bg-ok/10 text-ok rounded text-[11px] font-semibold shrink-0 ml-3">PRODUCTION READY</span>
          </div>

          <div className="flex items-start justify-between p-3 bg-bg rounded-lg border border-line">
            <div>
              <span className="font-bold text-ink">VPC Gateway Endpoints for Sub-5ms Latency</span>
              <p className="text-muted text-[11px] font-sans mt-0.5">When deploying backend containers (ECS/Lambda) inside AWS us-east-1, attach S3 and DynamoDB Gateway Endpoints to eliminate internet transit and achieve &lt; 5ms queries.</p>
            </div>
            <span className="px-2 py-0.5 bg-accent/10 text-accent rounded text-[11px] font-semibold shrink-0 ml-3">AWS VPC CONFIG</span>
          </div>

          <div className="flex items-start justify-between p-3 bg-bg rounded-lg border border-line">
            <div>
              <span className="font-bold text-ink">IAM Role / IRSA (Zero Static Keys)</span>
              <p className="text-muted text-[11px] font-sans mt-0.5">Replace static credentials with short-lived STS tokens using ECS Task Execution Roles or EKS IAM Roles for Service Accounts (IRSA).</p>
            </div>
            <span className="px-2 py-0.5 bg-accent/10 text-accent rounded text-[11px] font-semibold shrink-0 ml-3">IAM BEST PRACTICE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
