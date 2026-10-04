import React, { useState } from "react";
import { NodeType } from "./types";

interface PaletteItem {
  type: NodeType;
  label: string;
  category: "Retrieval" | "AI & Logic" | "Routing & Safety" | "Evaluation";
  icon: string;
  description: string;
  badge: string;
  defaultConfig: Record<string, any>;
}

export const PALETTE_ITEMS: PaletteItem[] = [
  {
    type: "retriever",
    label: "Dynavec Retriever",
    category: "Retrieval",
    icon: "DB",
    badge: "Vector DB",
    description: "S3 Vectors & DynamoDB hybrid semantic search",
    defaultConfig: { namespace: "default", top_k: 5, metric: "cosine", filter_expr: "" },
  },
  {
    type: "cache",
    label: "Semantic Cache",
    category: "Retrieval",
    icon: "RNK",
    badge: "Cache",
    description: "Check DynamoDB vector cache before invoking models",
    defaultConfig: { similarity_threshold: 0.94, ttl_seconds: 86400 },
  },
  {
    type: "reranker",
    label: "Cross-Reranker",
    category: "Retrieval",
    icon: "RNK",
    badge: "MMR / Cross",
    description: "Rerank retrieved chunks for higher relevance",
    defaultConfig: { strategy: "cross-encoder", top_n: 3 },
  },
  {
    type: "llm",
    label: "LLM Synthesizer",
    category: "AI & Logic",
    icon: "LLM",
    badge: "Generator",
    description: "OpenAI, Bedrock, Gemini, or local models",
    defaultConfig: {
      model: "gpt-4o",
      temperature: 0.2,
      max_tokens: 1024,
      system_prompt: "You are an enterprise AI assistant.",
    },
  },
  {
    type: "code",
    label: "Python Code",
    category: "AI & Logic",
    icon: "PY",
    badge: "Transform",
    description: "Execute Python transformation on state data",
    defaultConfig: { code: "def transform(state):\n    return state" },
  },
  {
    type: "http",
    label: "HTTP / Webhook",
    category: "AI & Logic",
    icon: "API",
    badge: "Integration",
    description: "Call external REST APIs and CRM webhooks",
    defaultConfig: { url: "https://api.example.com/v1", method: "POST" },
  },
  {
    type: "guard",
    label: "Confidence Guard",
    category: "Routing & Safety",
    icon: "GRD",
    badge: "Safety",
    description: "Branch on confidence score, toxicity, or PII",
    defaultConfig: { threshold: 0.85, metric_name: "relevance" },
  },
  {
    type: "classifier",
    label: "Intent Router",
    category: "Routing & Safety",
    icon: "RTR",
    badge: "Branching",
    description: "Route input into specific sub-agent paths",
    defaultConfig: { categories: ["docs_query", "action_request", "general_qa"] },
  },
  {
    type: "eval",
    label: "RAGAS Evaluator",
    category: "Evaluation",
    icon: "EVL",
    badge: "Metrics",
    description: "Inline faithfulness and context recall grading",
    defaultConfig: { metrics: ["faithfulness", "answer_relevance"], min_score: 0.85 },
  },
  {
    type: "response",
    label: "Response Output",
    category: "Evaluation",
    icon: "OUT",
    badge: "Sink",
    description: "Terminal node formatting final agent output",
    defaultConfig: { format: "markdown", include_citations: true },
  },
];

interface NodePaletteProps {
  onAddNode: (type: NodeType, label: string, description: string, config: Record<string, any>) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function NodePalette({ onAddNode, isOpen, onToggle }: NodePaletteProps) {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const categories = ["All", "Retrieval", "AI & Logic", "Routing & Safety", "Evaluation"];

  const filteredItems = PALETTE_ITEMS.filter((item) => {
    const matchesCategory = activeCategory === "All" || item.category === activeCategory;
    const matchesSearch =
      item.label.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase()) ||
      item.badge.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const onDragStart = (event: React.DragEvent, item: PaletteItem) => {
    event.dataTransfer.setData("application/reactflow", JSON.stringify(item));
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div
      className={`fixed lg:absolute left-0 top-0 bottom-0 z-30 transition-all duration-200 border-r border-line bg-surface/95 backdrop-blur-md flex flex-col ${
        isOpen ? "w-80 shadow-2xl" : "w-12 border-r"
      }`}
    >
      {/* Toggle header */}
      <div className="h-12 border-b border-line flex items-center justify-between px-3">
        {isOpen && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent inline-block mr-1"></span>
            <span className="font-semibold text-xs text-ink uppercase tracking-wider font-mono">
              Node Library
            </span>
          </div>
        )}
        <button
          onClick={onToggle}
          title={isOpen ? "Collapse Palette" : "Expand Palette"}
          className="p-1.5 rounded hover:bg-bg text-muted hover:text-ink transition-colors ml-auto"
        >
          {isOpen ? "←" : "→"}
        </button>
      </div>

      {isOpen ? (
        <div className="flex-1 flex flex-col p-3 overflow-hidden">
          {/* Search */}
          <div className="relative mb-2">
            <input
              type="text"
              placeholder="Search components..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs bg-bg border border-line rounded-lg px-2.5 py-1.5 text-ink placeholder:text-faint focus:outline-none focus:border-accent"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2 top-2 text-muted hover:text-ink cursor-pointer"
                aria-label="Clear search"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Categories */}
          <div className="flex flex-wrap gap-1 mb-3">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`text-[10px] px-2 py-0.5 rounded-full font-mono transition-colors ${
                  activeCategory === cat
                    ? "bg-accent text-white font-medium"
                    : "bg-bg text-muted hover:text-ink border border-line"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Node Cards List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            <p className="text-[11px] text-faint mb-1 italic">
              Drag onto canvas or click + Add:
            </p>
            {filteredItems.map((item) => (
              <div
                key={item.type}
                draggable
                onDragStart={(e) => onDragStart(e, item)}
                className="group border border-line rounded-lg p-2.5 bg-bg/60 hover:bg-bg hover:border-accent/40 cursor-grab active:cursor-grabbing transition-all hover:shadow-sm"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-base select-none">{item.icon}</span>
                    <span className="font-semibold text-xs text-ink group-hover:text-accent transition-colors">
                      {item.label}
                    </span>
                  </div>
                  <span className="font-mono text-[9.5px] px-1.5 py-0.5 rounded bg-surface border border-line text-muted">
                    {item.badge}
                  </span>
                </div>
                <p className="text-[11px] text-muted line-clamp-2 leading-relaxed mb-2">
                  {item.description}
                </p>
                <button
                  type="button"
                  onClick={() => onAddNode(item.type, item.label, item.description, item.defaultConfig)}
                  className="w-full text-center py-1 text-[11px] font-mono font-medium rounded border border-line bg-surface text-ink hover:bg-accent hover:text-white hover:border-accent transition-all"
                >
                  + Add to Canvas
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Collapsed Icon Bar */
        <div className="flex-1 flex flex-col items-center py-3 gap-2">
          {PALETTE_ITEMS.slice(0, 7).map((item) => (
            <button
              key={item.type}
              onClick={onToggle}
              title={`${item.label} - Click to expand`}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-sm hover:bg-accent-soft hover:text-accent transition-all"
            >
              {item.icon}
            </button>
          ))}
          <button
            onClick={onToggle}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono text-muted hover:bg-bg mt-auto"
          >
            +3
          </button>
        </div>
      )}
    </div>
  );
}
