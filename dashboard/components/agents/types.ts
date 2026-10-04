import { Node, Edge } from "reactflow";

export type NodeType =
  | "retriever"
  | "llm"
  | "guard"
  | "classifier"
  | "reranker"
  | "cache"
  | "eval"
  | "code"
  | "http"
  | "response";

export type NodeExecutionStatus = "idle" | "running" | "success" | "error" | "skipped";

export interface AgentNodeData {
  label: string;
  type: NodeType;
  description: string;
  config: Record<string, any>;
  status?: NodeExecutionStatus;
  executionTimeMs?: number;
  lastOutput?: any;
  lastInput?: any;
  error?: string;
}

export type CustomAgentNode = Node<AgentNodeData>;
export type CustomAgentEdge = Edge;

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: "RAG" | "Autonomous" | "Guardrailed" | "Observability";
  nodes: CustomAgentNode[];
  edges: CustomAgentEdge[];
  tags: string[];
}

export interface WorkflowMeta {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  updatedAt: string;
  status: "Active" | "Draft" | "Testing";
  lastRunLatency?: string;
  successRate?: string;
  graph: {
    nodes: CustomAgentNode[];
    edges: CustomAgentEdge[];
  };
}
