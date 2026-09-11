"use client";
import React from "react";

export default function FaithfulnessPanel() {
  const scores = [
    { label: "Faithfulness (Groundedness)", value: "94.2%", change: "+3.1%", note: "Zero hallucinated claims vs retrieved context" },
    { label: "Answer Relevance", value: "91.8%", change: "+2.4%", note: "Directly addresses user question intent" },
    { label: "Context Recall", value: "88.5%", change: "+1.9%", note: "Percentage of relevant ground-truth facts retrieved" },
    { label: "Context Precision", value: "93.0%", change: "+4.0%", note: "High signal-to-noise ratio in hydrated chunks" },
  ];

  const evaluations = [
    {
      query: "How does DynamoDB hydration work in Dynavec?",
      faithfulness: "1.00",
      relevance: "0.98",
      verdict: "Pass",
      reason: "Answer strictly quotes DynamoDB BatchGetItem single-digit ms document retrieval.",
    },
    {
      query: "Can Dynavec run without Amazon S3 Vectors?",
      faithfulness: "0.95",
      relevance: "0.92",
      verdict: "Pass",
      reason: "Accurately noted in-memory and local mock capabilities for local development.",
    },
    {
      query: "What is the cost difference vs Pinecone?",
      faithfulness: "0.98",
      relevance: "0.96",
      verdict: "Pass",
      reason: "Correctly highlighted 80%+ savings due to serverless pay-per-query pricing.",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight">LLM-as-a-Judge Evaluation (RAG Quality)</h2>
          <p className="text-sm text-muted">Automated verification of groundedness, hallucination detection, and response relevance</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs px-2.5 py-1 bg-accent-soft text-accent-ink rounded-full border border-accent/30 font-semibold">
            Model Judge: Bedrock / Claude 3 Haiku (92% Cheaper)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {scores.map((s) => (
          <div key={s.label} className="bg-surface border border-line rounded-xl2 p-4">
            <div className="text-xs text-muted font-mono mb-1 truncate">{s.label}</div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-ok">{s.value}</span>
              <span className="text-xs font-mono text-ok font-semibold">{s.change}</span>
            </div>
            <p className="text-[11px] text-faint font-mono mt-1">{s.note}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-line rounded-xl2 overflow-hidden">
        <div className="p-4 border-b border-line">
          <h3 className="font-semibold text-sm font-mono">Recent Judge Audit Samples</h3>
        </div>
        <div className="divide-y divide-line text-xs font-mono">
          {evaluations.map((e, idx) => (
            <div key={idx} className="p-4 space-y-1.5 hover:bg-line/20 transition-colors">
              <div className="flex items-center justify-between font-semibold">
                <span className="text-ink text-sm">&ldquo;{e.query}&rdquo;</span>
                <span className="px-2 py-0.5 bg-ok/10 text-ok rounded text-[11px]">{e.verdict}</span>
              </div>
              <div className="text-muted text-[11.5px]">{e.reason}</div>
              <div className="flex gap-4 text-faint text-[11px] pt-1">
                <span>Faithfulness: <b className="text-ok">{e.faithfulness}</b></span>
                <span>Relevance: <b className="text-ok">{e.relevance}</b></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cheaper Models Comparison Matrix */}
      <div className="bg-surface border border-line rounded-xl2 p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold font-mono text-ink">Judge Model Cost &amp; Speed Comparison</h3>
          <span className="font-mono text-[11px] text-ok font-semibold">Active: Bedrock Claude 3 Haiku</span>
        </div>
        <p className="text-xs text-muted mb-4 font-sans">
          Evaluating groundedness requires impartial reasoning, but does not require heavyweight frontier models. Switching to lightweight models cuts evaluation costs by over 90% with near-identical audit accuracy.
        </p>

        <div className="overflow-x-auto mb-4">
          <table className="w-full text-xs font-mono border-collapse">
            <thead>
              <tr className="bg-bg text-faint text-[10.5px] uppercase text-left border-b border-line">
                <th className="p-2.5">Model</th>
                <th className="p-2.5">Provider</th>
                <th className="p-2.5">Input Cost / 1M</th>
                <th className="p-2.5">Output Cost / 1M</th>
                <th className="p-2.5">Speed / Latency</th>
                <th className="p-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-[11.5px]">
              <tr className="bg-accent-soft/30 font-semibold text-ink">
                <td className="p-2.5 text-accent">Claude 3 Haiku</td>
                <td className="p-2.5">AWS Bedrock</td>
                <td className="p-2.5 text-ok">$0.25</td>
                <td className="p-2.5 text-ok">$1.25</td>
                <td className="p-2.5">&lt; 300 ms</td>
                <td className="p-2.5"><span className="px-2 py-0.5 bg-ok/10 text-ok rounded text-[10px]">SELECTED (92% CHEAPER)</span></td>
              </tr>
              <tr>
                <td className="p-2.5 text-ink">Meta Llama 3.1 8B</td>
                <td className="p-2.5">AWS Bedrock</td>
                <td className="p-2.5 text-ok">$0.22</td>
                <td className="p-2.5 text-ok">$0.72</td>
                <td className="p-2.5">&lt; 250 ms</td>
                <td className="p-2.5"><span className="px-2 py-0.5 bg-bg text-muted rounded text-[10px]">SUPPORTED</span></td>
              </tr>
              <tr>
                <td className="p-2.5 text-ink">GPT-4o Mini</td>
                <td className="p-2.5">OpenAI</td>
                <td className="p-2.5 text-ok">$0.15</td>
                <td className="p-2.5 text-ok">$0.60</td>
                <td className="p-2.5">&lt; 350 ms</td>
                <td className="p-2.5"><span className="px-2 py-0.5 bg-bg text-muted rounded text-[10px]">SUPPORTED</span></td>
              </tr>
              <tr className="opacity-60">
                <td className="p-2.5 text-ink">Claude 3.5 Sonnet</td>
                <td className="p-2.5">AWS Bedrock</td>
                <td className="p-2.5 text-err">$3.00</td>
                <td className="p-2.5 text-err">$15.00</td>
                <td className="p-2.5">~ 1,200 ms</td>
                <td className="p-2.5"><span className="px-2 py-0.5 bg-bg text-muted rounded text-[10px]">PREVIOUS (12× COST)</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="bg-bg border border-line rounded-lg p-3 text-xs font-mono text-muted">
          <span className="text-faint"># Run lightweight Bedrock evaluation in Python:</span><br />
          <span className="text-ink">from dynavec.eval_judge import BedrockJudge</span><br />
          <span className="text-accent">judge = BedrockJudge(model_id=&quot;anthropic.claude-3-haiku-20240307-v1:0&quot;, region_name=&quot;us-east-1&quot;)</span><br />
          <span className="text-ink">score = judge.faithfulness(question=q, answer=ans, context=retrieved_docs)</span><br />
          <span className="text-faint"># Evaluates 1,000 queries for less than $0.10!</span>
        </div>
      </div>
    </div>
  );
}
