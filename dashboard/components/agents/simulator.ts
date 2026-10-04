import { CustomAgentNode, CustomAgentEdge } from "./types";

export interface SimulationResult {
  traceId: string;
  totalLatencyMs: number;
  tokensUsed: number;
  costUsd: number;
  output: string;
  nodeTraces: Array<{
    nodeId: string;
    nodeLabel: string;
    type: string;
    latencyMs: number;
    input: any;
    output: any;
    status: "success" | "error";
  }>;
}

export async function runGraphSimulation(
  nodes: CustomAgentNode[],
  edges: CustomAgentEdge[],
  inputQuery: string,
  onNodeStateChange: (nodeId: string, status: "running" | "success" | "error", data?: any) => void
): Promise<SimulationResult> {
  const traceId = `tr-agent-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  let totalLatency = 0;
  let totalTokens = 0;
  const traces: SimulationResult["nodeTraces"] = [];

  // Reset all nodes to idle
  nodes.forEach((n) => onNodeStateChange(n.id, "running" as any));

  // Find start node
  const targetIds = new Set(edges.map((e) => e.target));
  let currentNode: CustomAgentNode | undefined = nodes.find((n) => !targetIds.has(n.id)) || nodes[0];
  let currentState: Record<string, any> = {
    query: inputQuery,
    trace_id: traceId,
  };

  const visited = new Set<string>();

  while (currentNode && !visited.has(currentNode.id)) {
    visited.add(currentNode.id);
    const n: CustomAgentNode = currentNode;

    // 1. Mark Running
    onNodeStateChange(n.id, "running");
    await new Promise((r) => setTimeout(r, 450)); // Visual step delay

    const startTime = performance.now();
    let nodeOutput: any = {};
    let latency = 0;
    let chosenSourceHandle: string | undefined = undefined;

    // Simulate node logic
    if (n.data.type === "cache") {
      const isHit = inputQuery.toLowerCase().includes("dynavec") && Math.random() > 0.65;
      latency = Math.floor(Math.random() * 8) + 3;
      if (isHit) {
        nodeOutput = {
          cache_hit: true,
          cached_answer: "dynavec enables sub-10ms vector similarity search directly against S3 vectors.",
          latency_ms: latency,
        };
        chosenSourceHandle = "hit";
      } else {
        nodeOutput = { cache_hit: false, message: "Cache miss; proceeding to vector store." };
        chosenSourceHandle = "miss";
      }
    } else if (n.data.type === "retriever") {
      latency = Math.floor(Math.random() * 30) + 15;
      const topK = n.data.config.top_k || 5;
      const retrievedDocs = [
        { id: "doc-842", score: 0.942, title: "dynavec Architecture Overview", text: "Zero-copy S3 vector parsing with DynamoDB metadata indexing." },
        { id: "doc-119", score: 0.891, title: "Latency Benchmarks", text: "p95 retrieval latency under 12ms across 5 million vectors." },
        { id: "doc-305", score: 0.854, title: "Namespace Isolation", text: "Enterprise multi-tenancy with cryptographic namespace separation." },
      ].slice(0, topK);
      nodeOutput = { retrieved_count: retrievedDocs.length, docs: retrievedDocs };
      currentState.retrieved_docs = retrievedDocs;
    } else if (n.data.type === "reranker") {
      latency = Math.floor(Math.random() * 25) + 10;
      nodeOutput = {
        reranked_docs: currentState.retrieved_docs || [],
        strategy: n.data.config.strategy || "cross-encoder",
        score_boost: "+0.08",
      };
    } else if (n.data.type === "guard") {
      latency = Math.floor(Math.random() * 15) + 8;
      const threshold = n.data.config.threshold ?? 0.85;
      const evaluatedScore = 0.92;
      const passed = evaluatedScore >= threshold;
      nodeOutput = {
        passed,
        score: evaluatedScore,
        threshold,
        metric: n.data.config.metric_name || "relevance",
      };
      currentState.guard_passed = passed;
      chosenSourceHandle = passed ? "pass" : "fail";
    } else if (n.data.type === "llm") {
      latency = Math.floor(Math.random() * 150) + 90;
      const tokens = Math.floor(Math.random() * 180) + 120;
      totalTokens += tokens;
      const answer = `Based on dynavec's architecture, sub-10ms latency is achieved by decoupling cold vector storage in S3 from an ultra-fast in-memory and DynamoDB metadata index layer, avoiding full table scans.`;
      nodeOutput = {
        response: answer,
        model: n.data.config.model || "gpt-4o",
        tokens,
      };
      currentState.answer = answer;
    } else if (n.data.type === "eval") {
      latency = Math.floor(Math.random() * 30) + 15;
      const faithfulness = 0.94;
      const relevance = 0.96;
      nodeOutput = { faithfulness, relevance, passed: true };
      chosenSourceHandle = "pass";
    } else if (n.data.type === "classifier") {
      latency = Math.floor(Math.random() * 20) + 10;
      const categories = n.data.config.categories || ["route_0", "route_1"];
      const matchedIdx = 0;
      nodeOutput = { category: categories[matchedIdx], confidence: 0.95 };
      chosenSourceHandle = `route-${matchedIdx}`;
    } else if (n.data.type === "response") {
      latency = 5;
      nodeOutput = {
        final_answer: currentState.answer || currentState.cached_answer || "Request executed successfully.",
        trace_id: traceId,
      };
    } else {
      latency = 12;
      nodeOutput = { status: "executed", config: n.data.config };
    }

    totalLatency += latency;

    // 2. Mark Succeeded
    onNodeStateChange(n.id, "success", {
      executionTimeMs: latency,
      lastOutput: nodeOutput,
    });

    traces.push({
      nodeId: n.id,
      nodeLabel: n.data.label,
      type: n.data.type,
      latencyMs: latency,
      input: { ...currentState },
      output: nodeOutput,
      status: "success",
    });

    // 3. Find next node
    const outgoingEdges: CustomAgentEdge[] = edges.filter((e) => e.source === n.id);
    let nextEdge: CustomAgentEdge | undefined = outgoingEdges[0];

    if (chosenSourceHandle) {
      const match = outgoingEdges.find((e) => e.sourceHandle === chosenSourceHandle);
      if (match) nextEdge = match;
    }

    if (nextEdge) {
      currentNode = nodes.find((node) => node.id === nextEdge!.target);
    } else {
      break;
    }
  }

  const cost = (totalTokens / 1000) * 0.005; // ~$0.005 per 1k tokens

  return {
    traceId,
    totalLatencyMs: totalLatency,
    tokensUsed: totalTokens,
    costUsd: cost,
    output:
      currentState.answer ||
      currentState.cached_answer ||
      "Agent execution completed across all active nodes.",
    nodeTraces: traces,
  };
}

export function convertTraceEventToSimulation(t: any): SimulationResult {
  const nodeTraces: SimulationResult["nodeTraces"] = [];

  // 1. Semantic Cache Check
  nodeTraces.push({
    nodeId: "node-cache",
    nodeLabel: "Semantic Cache",
    type: "cache",
    latencyMs: 4,
    input: { query: t.query_preview || "Vector query", namespace: t.namespace },
    output: {
      cache_hit: t.cache_hit ?? false,
      similarity_score: t.cache_hit ? 0.96 : 0.62,
    },
    status: "success",
  });

  // 2. Vector Retrieval (dynavec)
  const retLatency = Math.max(8, Math.round(t.ann_ms || t.latency_ms * 0.35 || 28));
  nodeTraces.push({
    nodeId: "node-retriever",
    nodeLabel: "Dynavec Retriever",
    type: "retriever",
    latencyMs: retLatency,
    input: { namespace: t.namespace, top_k: t.top_k || 5, filtered: t.filtered },
    output: {
      n_results: t.n_results || 5,
      score_top: t.score_top || 0.942,
      score_mean: t.score_mean || 0.887,
      rescore: t.rescore || "none",
    },
    status: "success",
  });

  // 3. Reranker
  const rerankLatency = Math.max(5, Math.round(t.rerank_ms || t.latency_ms * 0.2 || 18));
  nodeTraces.push({
    nodeId: "node-reranker",
    nodeLabel: "Cross-Encoder Reranker",
    type: "reranker",
    latencyMs: rerankLatency,
    input: { strategy: t.rerank || "cross-encoder/ms-marco", top_n: 3 },
    output: { reranked_docs: 3, score_boost: "+0.07" },
    status: "success",
  });

  // 4. Guard Gate
  nodeTraces.push({
    nodeId: "node-guard",
    nodeLabel: "Confidence Guard",
    type: "guard",
    latencyMs: 11,
    input: { threshold: 0.85, score_top: t.score_top || 0.94 },
    output: { passed: true, score: t.score_top || 0.94, metric: "relevance" },
    status: "success",
  });

  // 5. LLM Synthesizer
  const llmLatency = Math.max(45, Math.round(t.latency_ms * 0.4 || 95));
  nodeTraces.push({
    nodeId: "node-llm",
    nodeLabel: "LLM Synthesizer",
    type: "llm",
    latencyMs: llmLatency,
    input: { model: "gpt-4o", temperature: 0.2 },
    output: {
      response: `Synthesized answer from namespace '${t.namespace}' retrieved context.`,
      tokens: 168,
    },
    status: "success",
  });

  // 6. Response
  nodeTraces.push({
    nodeId: "node-response",
    nodeLabel: "Response Delivery",
    type: "response",
    latencyMs: 3,
    input: { status: t.status },
    output: { delivered: true, trace_id: t.id },
    status: "success",
  });

  const total = nodeTraces.reduce((sum, s) => sum + s.latencyMs, 0);

  return {
    traceId: t.id,
    totalLatencyMs: total,
    tokensUsed: 168,
    costUsd: 0.0012,
    output: `Verified response for query: "${t.query_preview || "Vector query"}"`,
    nodeTraces,
  };
}

export function createDemoReplayTrace(): SimulationResult {
  return {
    traceId: "tr-demo-replay-001",
    totalLatencyMs: 178,
    tokensUsed: 215,
    costUsd: 0.0018,
    output:
      "Dynavec achieves sub-10ms latency by coupling cold S3 parquet vector storage with hot in-memory indices and DynamoDB metadata caching, avoiding full table scans.",
    nodeTraces: [
      {
        nodeId: "node-cache",
        nodeLabel: "Semantic Cache",
        type: "cache",
        latencyMs: 4,
        input: { query: "How does dynavec achieve sub-10ms vector search?" },
        output: { cache_hit: false, reason: "Cache miss; querying vector store" },
        status: "success",
      },
      {
        nodeId: "node-retriever",
        nodeLabel: "Dynavec Retriever",
        type: "retriever",
        latencyMs: 29,
        input: { namespace: "knowledge-base", top_k: 5 },
        output: { retrieved_count: 5, top_score: 0.952 },
        status: "success",
      },
      {
        nodeId: "node-reranker",
        nodeLabel: "Cross-Encoder Reranker",
        type: "reranker",
        latencyMs: 24,
        input: { strategy: "cross-encoder/ms-marco-MiniLM-L-6-v2", top_n: 3 },
        output: { reranked_count: 3, score_boost: "+0.08" },
        status: "success",
      },
      {
        nodeId: "node-guard",
        nodeLabel: "Confidence Guard",
        type: "guard",
        latencyMs: 12,
        input: { threshold: 0.85, evaluated_score: 0.94 },
        output: { passed: true, score: 0.94, metric: "relevance" },
        status: "success",
      },
      {
        nodeId: "node-llm",
        nodeLabel: "LLM Synthesizer",
        type: "llm",
        latencyMs: 105,
        input: { model: "gpt-4o", prompt_length: 840 },
        output: {
          response:
            "Dynavec achieves sub-10ms latency by coupling cold S3 parquet vector storage with hot in-memory indices and DynamoDB metadata caching, avoiding full table scans.",
          tokens: 215,
        },
        status: "success",
      },
      {
        nodeId: "node-response",
        nodeLabel: "Response Delivery",
        type: "response",
        latencyMs: 4,
        input: { output_format: "markdown" },
        output: { delivered: true, trace_id: "tr-demo-replay-001" },
        status: "success",
      },
    ],
  };
}
