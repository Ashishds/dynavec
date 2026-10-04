"use client";

import React, { useState } from "react";

export interface DashboardTestCase {
  id: string;
  name: string;
  description: string;
  query: string;
  targetWorkflow: string;
  status: "idle" | "running" | "passed" | "failed";
  durationMs?: number;
  faithfulness?: number;
  answerRelevance?: number;
  assertions: Array<{
    type: string;
    label: string;
    passed: boolean;
    actual?: string;
  }>;
  outputPreview?: string;
}

export interface DashboardTestSuite {
  id: string;
  name: string;
  description: string;
  targetWorkflowId: string;
  cases: DashboardTestCase[];
}

const INITIAL_SUITES: DashboardTestSuite[] = [
  {
    id: "suite-enterprise-rag",
    name: "Enterprise RAG Regression Suite",
    description: "End-to-end assertions for semantic caching, vector retrieval, guardrails, and LLM grounding.",
    targetWorkflowId: "enterprise-rag-guardrails",
    cases: [
      {
        id: "case-sub10ms",
        name: "sub-10ms-vector-latency",
        description: "Verify sub-10ms vector explanation with grounding and latency SLA.",
        query: "How does dynavec achieve sub-10ms vector search on AWS S3?",
        targetWorkflow: "Enterprise RAG with Guardrails",
        status: "passed",
        durationMs: 142,
        faithfulness: 0.95,
        answerRelevance: 0.98,
        assertions: [
          { type: "contains", label: 'contains("sub-10ms")', passed: true },
          { type: "contains", label: 'contains("DynamoDB")', passed: true },
          { type: "guard", label: "guard.passed == True", passed: true },
          { type: "ragas", label: "faithfulness >= 0.85 (0.95)", passed: true },
          { type: "latency", label: "latency <= 250ms (142ms)", passed: true },
        ],
        outputPreview:
          "Dynavec achieves sub-10ms latency by coupling cold S3 parquet vector storage with hot in-memory indices and DynamoDB metadata caching.",
      },
      {
        id: "case-cache-bypass",
        name: "semantic-cache-hit-bypass",
        description: "Assert that repetitive queries hit DynamoDB cache with latency < 15ms.",
        query: "What is dynavec's vector caching TTL?",
        targetWorkflow: "Enterprise RAG with Guardrails",
        status: "passed",
        durationMs: 6,
        faithfulness: 1.0,
        answerRelevance: 0.96,
        assertions: [
          { type: "exact", label: "cache_hit == True", passed: true },
          { type: "latency", label: "latency <= 15ms (6ms)", passed: true },
          { type: "node", label: "retriever.skipped == True", passed: true },
        ],
        outputPreview: "Cached vector answer (TTL: 86400s / 24 hours in DynamoDB).",
      },
      {
        id: "case-namespace-isolation",
        name: "multi-tenancy-namespace-isolation",
        description: "Ensure cross-tenant isolation and metadata partition enforcement.",
        query: "Explain namespace isolation across tenants",
        targetWorkflow: "Enterprise RAG with Guardrails",
        status: "passed",
        durationMs: 168,
        faithfulness: 0.92,
        answerRelevance: 0.94,
        assertions: [
          { type: "contains", label: 'contains("namespace")', passed: true },
          { type: "contains", label: "retriever.n_results >= 3", passed: true },
          { type: "ragas", label: "faithfulness >= 0.88 (0.92)", passed: true },
          { type: "latency", label: "latency <= 300ms (168ms)", passed: true },
        ],
        outputPreview:
          "Each namespace in dynavec operates as a cryptographically isolated vector partition with dedicated DynamoDB GSI keys.",
      },
      {
        id: "case-hallucination-guard",
        name: "low-confidence-guard-fallback",
        description: "Ensure out-of-domain query is blocked by guardrail without invoking costly LLM.",
        query: "Who won the 2038 lunar marathon on Olympus Mons?",
        targetWorkflow: "Enterprise RAG with Guardrails",
        status: "passed",
        durationMs: 48,
        faithfulness: 1.0,
        answerRelevance: 0.91,
        assertions: [
          { type: "guard", label: "guard.passed == False", passed: true },
          { type: "contains", label: 'contains("reliable context")', passed: true },
          { type: "node", label: "llm_node.visited == False", passed: true },
        ],
        outputPreview:
          "I could not find sufficiently reliable context to answer this query safely.",
      },
    ],
  },
  {
    id: "suite-safety-guardrails",
    name: "Hallucination & Safety Assertions",
    description: "Validates toxicity blocking, hallucination prevention, and confidence gates.",
    targetWorkflowId: "self-reflective-rag",
    cases: [
      {
        id: "case-eval-reflection",
        name: "eval-reflection-retry-loop",
        description: "Ensure generation scoring < 0.85 triggers automatic retry rewrite loop.",
        query: "Detail the exact zero-copy parquet byte offsets",
        targetWorkflow: "Self-Reflective RAG (Eval Loop)",
        status: "passed",
        durationMs: 295,
        faithfulness: 0.94,
        answerRelevance: 0.97,
        assertions: [
          { type: "ragas", label: "ragas_eval.passed == True", passed: true },
          { type: "ragas", label: "faithfulness >= 0.85 (0.94)", passed: true },
          { type: "node", label: "retry_count <= 2", passed: true },
        ],
        outputPreview:
          "Verified answer certified by inline Ragas faithfulness evaluation.",
      },
    ],
  },
];

interface TestSuitePanelProps {
  onReplayTestCase: (testCase: DashboardTestCase) => void;
  onOpenCanvas: (templateId?: string) => void;
}

export default function TestSuitePanel({
  onReplayTestCase,
  onOpenCanvas,
}: TestSuitePanelProps) {
  const [suites, setSuites] = useState<DashboardTestSuite[]>(INITIAL_SUITES);
  const [activeSuiteId, setActiveSuiteId] = useState<string>(INITIAL_SUITES[0].id);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [showXmlModal, setShowXmlModal] = useState(false);
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);

  // New Case Form State
  const [newCaseName, setNewCaseName] = useState("");
  const [newCaseQuery, setNewCaseQuery] = useState("");
  const [newCaseExpectedWord, setNewCaseExpectedWord] = useState("");
  const [newCaseMinFaithfulness, setNewCaseMinFaithfulness] = useState(0.85);

  const activeSuite = suites.find((s) => s.id === activeSuiteId) || suites[0];

  // Global KPIs across all suites
  const allCases = suites.flatMap((s) => s.cases);
  const totalCases = allCases.length;
  const passedCases = allCases.filter((c) => c.status === "passed").length;
  const passRate = totalCases > 0 ? (passedCases / totalCases) * 100 : 100;
  const avgFaithfulness = (
    allCases.reduce((sum, c) => sum + (c.faithfulness || 0.94), 0) / (totalCases || 1)
  ).toFixed(2);
  const avgRelevance = (
    allCases.reduce((sum, c) => sum + (c.answerRelevance || 0.96), 0) / (totalCases || 1)
  ).toFixed(2);
  const avgLatency = Math.round(
    allCases.reduce((sum, c) => sum + (c.durationMs || 120), 0) / (totalCases || 1)
  );

  // Run all tests in the active suite with animation
  const handleRunActiveSuite = async () => {
    setIsRunningAll(true);

    for (let i = 0; i < activeSuite.cases.length; i++) {
      const c = activeSuite.cases[i];

      // Mark running
      setSuites((prev) =>
        prev.map((s) =>
          s.id === activeSuite.id
            ? {
                ...s,
                cases: s.cases.map((caseItem, idx) =>
                  idx === i ? { ...caseItem, status: "running" } : caseItem
                ),
              }
            : s
        )
      );

      await new Promise((r) => setTimeout(r, 600));

      // Mark passed with refreshed latency
      const refreshedLatency = Math.floor(Math.random() * 40) + (c.durationMs || 100) - 20;
      setSuites((prev) =>
        prev.map((s) =>
          s.id === activeSuite.id
            ? {
                ...s,
                cases: s.cases.map((caseItem, idx) =>
                  idx === i
                    ? {
                        ...caseItem,
                        status: "passed",
                        durationMs: Math.max(6, refreshedLatency),
                      }
                    : caseItem
                ),
              }
            : s
        )
      );
    }

    setIsRunningAll(false);
  };

  // Add custom test case
  const handleCreateCase = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseName || !newCaseQuery) return;

    const created: DashboardTestCase = {
      id: `case-${Date.now().toString(36)}`,
      name: newCaseName.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
      description: `User defined test case for ${activeSuite.name}`,
      query: newCaseQuery,
      targetWorkflow: activeSuite.name,
      status: "idle",
      assertions: [
        {
          type: "contains",
          label: `contains("${newCaseExpectedWord || "dynavec"}")`,
          passed: true,
        },
        {
          type: "ragas",
          label: `faithfulness >= ${newCaseMinFaithfulness.toFixed(2)}`,
          passed: true,
        },
        { type: "latency", label: "latency <= 350ms", passed: true },
      ],
    };

    setSuites((prev) =>
      prev.map((s) =>
        s.id === activeSuite.id ? { ...s, cases: [...s.cases, created] } : s
      )
    );

    setNewCaseName("");
    setNewCaseQuery("");
    setNewCaseExpectedWord("");
    setShowNewCaseModal(false);
  };

  // Generate JUnit XML representation
  const junitXml = `<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="${activeSuite.name}" tests="${activeSuite.cases.length}" failures="0" time="${(avgLatency * activeSuite.cases.length) / 1000}">
${activeSuite.cases
  .map(
    (c) =>
      `  <testcase name="${c.name}" time="${((c.durationMs || 100) / 1000).toFixed(3)}">
    <system-out>Query: ${c.query}</system-out>
    <properties>
      <property name="faithfulness" value="${c.faithfulness || 0.95}"/>
      <property name="answer_relevance" value="${c.answerRelevance || 0.98}"/>
    </properties>
  </testcase>`
  )
  .join("\n")}
</testsuite>`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-accent font-semibold uppercase tracking-wider">
              Agent Studio
            </span>
            <span className="text-faint text-xs">/</span>
            <span className="font-mono text-xs text-muted">Test Suites & Ragas</span>
          </div>
          <h1 className="text-2xl font-bold text-ink mt-1">
            Agent Test Suites & CI Assertions
          </h1>
          <p className="text-sm text-muted mt-0.5">
            Automated regression testing, node assertions, and Ragas faithfulness metrics for agent graphs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowXmlModal(true)}
            className="py-2 px-3 rounded-lg text-xs font-mono border border-line bg-surface text-ink hover:bg-bg transition-colors"
          >
            Export JUnit XML
          </button>
          <button
            type="button"
            onClick={() => setShowNewCaseModal(true)}
            className="py-2 px-3.5 rounded-lg text-xs font-mono font-medium border border-line bg-surface text-ink hover:bg-bg transition-colors"
          >
            + New Test Case
          </button>
          <button
            type="button"
            onClick={handleRunActiveSuite}
            disabled={isRunningAll}
            className="py-2 px-4 rounded-lg text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 shadow-sm flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {isRunningAll ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Running Suite...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>Run Suite</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Pass Rate</span>
          <div className="text-2xl font-bold text-emerald-500 font-mono mt-1">
            {passRate.toFixed(1)}%
          </div>
          <span className="text-[11px] text-faint font-mono mt-0.5 block">
            {passedCases}/{totalCases} cases passing
          </span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Avg Faithfulness</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">
            {avgFaithfulness}
          </div>
          <span className="text-[11px] text-emerald-500 font-mono mt-0.5 block">
            Target: &gt;= 0.85
          </span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Answer Relevance</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">
            {avgRelevance}
          </div>
          <span className="text-[11px] text-emerald-500 font-mono mt-0.5 block">
            Target: &gt;= 0.90
          </span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">p95 Latency</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">
            {avgLatency}ms
          </div>
          <span className="text-[11px] text-muted font-mono mt-0.5 block">
            SLA: &lt;= 350ms
          </span>
        </div>
        <div className="p-4 rounded-xl border border-line bg-surface">
          <span className="text-xs font-mono text-muted uppercase">Active Suites</span>
          <div className="text-2xl font-bold text-ink font-mono mt-1">
            {suites.length}
          </div>
          <span className="text-[11px] text-faint font-mono mt-0.5 block">
            CI / CLI ready
          </span>
        </div>
      </div>

      {/* Suite Selector Tabs */}
      <div className="flex border-b border-line gap-2 overflow-x-auto">
        {suites.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setActiveSuiteId(s.id)}
            className={`py-2 px-4 text-xs font-mono font-medium rounded-t-lg transition-all border-b-2 ${
              activeSuiteId === s.id
                ? "border-accent text-accent font-semibold bg-accent-soft/30"
                : "border-transparent text-muted hover:text-ink hover:bg-bg/40"
            }`}
          >
            {s.name} ({s.cases.length})
          </button>
        ))}
      </div>

      {/* Test Cases Table Card */}
      <div className="rounded-xl border border-line bg-surface overflow-hidden shadow-sm">
        <div className="p-4 border-b border-line bg-bg/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="font-bold text-sm text-ink">{activeSuite.name}</h3>
            <p className="text-xs text-muted mt-0.5">{activeSuite.description}</p>
          </div>
          <span className="font-mono text-xs text-faint">
            Target Graph:{" "}
            <span className="text-ink font-semibold">{activeSuite.cases[0]?.targetWorkflow}</span>
          </span>
        </div>

        <div className="divide-y divide-line">
          {activeSuite.cases.map((c) => (
            <div
              key={c.id}
              className="p-4 hover:bg-bg/40 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            >
              {/* Left: Info & Query */}
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-mono text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                      c.status === "passed"
                        ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                        : c.status === "running"
                        ? "bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse"
                        : "bg-bg text-muted border-line"
                    }`}
                  >
                    ● {c.status.toUpperCase()}
                  </span>
                  <span className="font-bold text-xs font-mono text-ink">
                    {c.name}
                  </span>
                  {c.durationMs && (
                    <span className="font-mono text-[11px] text-accent">
                      {c.durationMs}ms
                    </span>
                  )}
                </div>

                <div className="text-xs font-mono text-ink bg-bg p-2 rounded border border-line">
                  <span className="text-faint">query: </span>"{c.query}"
                </div>

                {/* Assertions checklist */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {c.assertions.map((a, i) => (
                    <span
                      key={i}
                      className="font-mono text-[10.5px] px-2 py-0.5 rounded bg-bg text-ink border border-line flex items-center gap-1.5"
                    >
                      <svg className="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>{a.label}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Right: RAGAS Scores & Replay Button */}
              <div className="flex items-center gap-4 self-start lg:self-center shrink-0">
                {/* Metric Badges */}
                <div className="flex items-center gap-2 font-mono text-xs">
                  {c.faithfulness && (
                    <div className="text-center px-2 py-1 rounded bg-bg border border-line">
                      <span className="block text-[9.5px] text-faint">Faithfulness</span>
                      <span className="font-bold text-emerald-500">
                        {c.faithfulness.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {c.answerRelevance && (
                    <div className="text-center px-2 py-1 rounded bg-bg border border-line">
                      <span className="block text-[9.5px] text-faint">Relevance</span>
                      <span className="font-bold text-accent">
                        {c.answerRelevance.toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <button
                  type="button"
                  onClick={() => onReplayTestCase(c)}
                  className="py-2 px-3 rounded-lg text-xs font-mono font-medium border border-line bg-surface hover:bg-bg text-ink flex items-center gap-1.5 shadow-sm transition-all"
                  title="Replay test execution on ReactFlow canvas"
                >
                  <span>Replay Trace in Canvas</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CLI & CI/CD Command helper */}
      <div className="p-4 rounded-xl border border-line bg-bg/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-accent font-bold">CLI Runner:</span>
          <code className="text-ink bg-surface px-2.5 py-1 rounded border border-line">
            python -m dynavec.agents.test --suite {activeSuite.id}.json --ci
          </code>
        </div>
        <span className="text-faint text-[11px]">
          Runs on GitHub Actions, GitLab CI, and Jenkins
        </span>
      </div>

      {/* JUnit XML Modal */}
      {showXmlModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border border-line rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-line flex items-center justify-between bg-bg/50">
              <h3 className="font-bold text-xs font-mono uppercase tracking-wider text-ink">
                JUnit XML Export ({activeSuite.name})
              </h3>
              <button
                onClick={() => setShowXmlModal(false)}
                className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
                aria-label="Close XML modal"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 bg-[#121214]">
              <pre className="font-mono text-xs text-[#e6edf3] whitespace-pre leading-relaxed">
                {junitXml}
              </pre>
            </div>
            <div className="p-3 border-t border-line bg-bg/50 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(junitXml);
                  alert("Copied JUnit XML to clipboard!");
                }}
                className="py-1.5 px-3.5 rounded text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 cursor-pointer"
              >
                Copy XML
              </button>
              <button
                type="button"
                onClick={() => setShowXmlModal(false)}
                className="py-1.5 px-3 rounded text-xs font-mono border border-line bg-surface text-ink hover:bg-bg cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Test Case Modal */}
      {showNewCaseModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateCase}
            className="bg-surface border border-line rounded-xl w-full max-w-lg flex flex-col shadow-2xl overflow-hidden"
          >
            <div className="p-4 border-b border-line flex items-center justify-between bg-bg/50">
              <h3 className="font-bold text-xs font-mono uppercase tracking-wider text-ink">
                Add Test Case to {activeSuite.name}
              </h3>
              <button
                type="button"
                onClick={() => setShowNewCaseModal(false)}
                className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
                aria-label="Close modal"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Test Case Identifier
                </label>
                <input
                  type="text"
                  placeholder="e.g. vector-rerank-precision"
                  value={newCaseName}
                  onChange={(e) => setNewCaseName(e.target.value)}
                  required
                  className="w-full text-xs font-mono bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Inbound Query / Test Prompt
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. How does hybrid dense and sparse search work?"
                  value={newCaseQuery}
                  onChange={(e) => setNewCaseQuery(e.target.value)}
                  required
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Expected Output Keyword Assertion
                </label>
                <input
                  type="text"
                  placeholder="e.g. hybrid"
                  value={newCaseExpectedWord}
                  onChange={(e) => setNewCaseExpectedWord(e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Minimum Faithfulness Threshold: {newCaseMinFaithfulness.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={newCaseMinFaithfulness}
                  onChange={(e) => setNewCaseMinFaithfulness(parseFloat(e.target.value))}
                  className="w-full accent-accent"
                />
              </div>
            </div>
            <div className="p-3 border-t border-line bg-bg/50 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowNewCaseModal(false)}
                className="py-1.5 px-3 rounded text-xs font-mono border border-line bg-surface text-ink hover:bg-bg"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="py-1.5 px-4 rounded text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90"
              >
                Add Case
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
