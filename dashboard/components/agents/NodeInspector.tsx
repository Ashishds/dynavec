import React from "react";
import { CustomAgentNode } from "./types";

interface NodeInspectorProps {
  node: CustomAgentNode | null;
  onUpdateConfig: (nodeId: string, updates: Partial<CustomAgentNode["data"]>) => void;
  onDeleteNode: (nodeId: string) => void;
  onDuplicateNode: (nodeId: string) => void;
  onClose: () => void;
}

export function NodeInspector({
  node,
  onUpdateConfig,
  onDeleteNode,
  onDuplicateNode,
  onClose,
}: NodeInspectorProps) {
  if (!node) return null;

  const { data } = node;
  const config = data.config || {};

  const handleConfigChange = (key: string, val: any) => {
    onUpdateConfig(node.id, {
      ...data,
      config: {
        ...config,
        [key]: val,
      },
    });
  };

  const handleLabelChange = (newLabel: string) => {
    onUpdateConfig(node.id, {
      ...data,
      label: newLabel,
    });
  };

  const handleDescriptionChange = (newDesc: string) => {
    onUpdateConfig(node.id, {
      ...data,
      description: newDesc,
    });
  };

  return (
    <div className="fixed right-0 top-[52px] bottom-0 w-88 md:w-96 border-l border-line bg-surface/98 backdrop-blur-md z-40 flex flex-col shadow-2xl overflow-hidden transition-all">
      {/* Top Header */}
      <div className="p-4 border-b border-line flex items-center justify-between bg-bg/40">
        <div>
          <span className="font-mono text-[10px] text-faint uppercase tracking-wider block">
            Node Configuration
          </span>
          <h2 className="font-bold text-sm text-ink flex items-center gap-1.5 mt-0.5">
            <span className="text-accent">◈</span> {data.label}
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
          title="Close Inspector"
          aria-label="Close Inspector"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Scrollable Form Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Basic Info */}
        <div className="space-y-2">
          <div>
            <label className="block text-[11px] font-mono text-muted mb-1">
              Node Label
            </label>
            <input
              type="text"
              value={data.label}
              onChange={(e) => handleLabelChange(e.target.value)}
              className="w-full text-xs font-semibold bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-[11px] font-mono text-muted mb-1">
              Description
            </label>
            <textarea
              rows={2}
              value={data.description}
              onChange={(e) => handleDescriptionChange(e.target.value)}
              className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:outline-none focus:border-accent resize-none"
            />
          </div>
        </div>

        {/* Node Specific Controls */}
        <div className="border-t border-line pt-3 space-y-3">
          <span className="font-mono text-[10.5px] uppercase font-semibold text-accent tracking-wider block">
            {data.type.toUpperCase()} Parameters
          </span>

          {/* Retriever Parameters */}
          {data.type === "retriever" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Namespace (Vector Collection)
                </label>
                <input
                  type="text"
                  value={config.namespace || "default"}
                  onChange={(e) => handleConfigChange("namespace", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Top K Chunks: {config.top_k || 5}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="25"
                    value={config.top_k || 5}
                    onChange={(e) => handleConfigChange("top_k", parseInt(e.target.value, 10))}
                    className="w-full accent-accent"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Metric
                  </label>
                  <select
                    value={config.metric || "cosine"}
                    onChange={(e) => handleConfigChange("metric", e.target.value)}
                    className="w-full text-xs bg-bg border border-line rounded px-2 py-1.5 text-ink"
                  >
                    <option value="cosine">Cosine</option>
                    <option value="l2">Euclidean (L2)</option>
                    <option value="dot">Dot Product</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Metadata Filter Expression
                </label>
                <input
                  type="text"
                  placeholder="e.g. department = 'engineering'"
                  value={config.filter_expr || ""}
                  onChange={(e) => handleConfigChange("filter_expr", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink"
                />
              </div>
            </>
          )}

          {/* LLM Synthesizer Parameters */}
          {data.type === "llm" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Model
                </label>
                <select
                  value={config.model || "gpt-4o"}
                  onChange={(e) => handleConfigChange("model", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2 py-1.5 text-ink"
                >
                  <option value="gpt-4o">OpenAI gpt-4o</option>
                  <option value="gpt-4o-mini">OpenAI gpt-4o-mini</option>
                  <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet</option>
                  <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
                  <option value="local-deepseek-r1">Local DeepSeek-R1 (Ollama)</option>
                  <option value="bedrock-titan">AWS Bedrock Titan</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Temperature: {config.temperature ?? 0.2}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.temperature ?? 0.2}
                    onChange={(e) => handleConfigChange("temperature", parseFloat(e.target.value))}
                    className="w-full accent-accent"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={config.max_tokens || 1024}
                    onChange={(e) => handleConfigChange("max_tokens", parseInt(e.target.value, 10))}
                    className="w-full text-xs bg-bg border border-line rounded px-2 py-1.5 text-ink"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  System Prompt
                </label>
                <textarea
                  rows={4}
                  value={config.system_prompt || ""}
                  onChange={(e) => handleConfigChange("system_prompt", e.target.value)}
                  placeholder="You are an enterprise AI assistant..."
                  className="w-full text-xs font-mono bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
                />
              </div>
            </>
          )}

          {/* Guard Parameters */}
          {data.type === "guard" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Confidence Threshold: {(config.threshold ?? 0.85).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={config.threshold ?? 0.85}
                  onChange={(e) => handleConfigChange("threshold", parseFloat(e.target.value))}
                  className="w-full accent-accent"
                />
                <span className="text-[10px] text-faint">
                  Outputs scoring below this route to the Fail / Fallback port.
                </span>
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Metric Guarded
                </label>
                <input
                  type="text"
                  value={config.metric_name || "relevance"}
                  onChange={(e) => handleConfigChange("metric_name", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Fallback Message
                </label>
                <textarea
                  rows={2}
                  value={config.fallback_message || ""}
                  onChange={(e) => handleConfigChange("fallback_message", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink"
                />
              </div>
            </>
          )}

          {/* Semantic Cache Parameters */}
          {data.type === "cache" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Similarity Threshold: {(config.similarity_threshold ?? 0.94).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.80"
                  max="0.99"
                  step="0.01"
                  value={config.similarity_threshold ?? 0.94}
                  onChange={(e) => handleConfigChange("similarity_threshold", parseFloat(e.target.value))}
                  className="w-full accent-accent"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  TTL in Seconds
                </label>
                <input
                  type="number"
                  value={config.ttl_seconds || 86400}
                  onChange={(e) => handleConfigChange("ttl_seconds", parseInt(e.target.value, 10))}
                  className="w-full text-xs bg-bg border border-line rounded px-2.5 py-1.5 text-ink"
                />
              </div>
            </>
          )}

          {/* Intent Classifier Parameters */}
          {data.type === "classifier" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Output Branch Routes
                </label>
                <div className="space-y-1.5">
                  {(config.categories || ["tech_docs", "billing_api", "general"]).map(
                    (cat: string, i: number) => (
                      <div key={i} className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] text-faint w-5">{i}:</span>
                        <input
                          type="text"
                          value={cat}
                          onChange={(e) => {
                            const newCats = [...(config.categories || [])];
                            newCats[i] = e.target.value;
                            handleConfigChange("categories", newCats);
                          }}
                          className="flex-1 text-xs bg-bg border border-line rounded px-2 py-1 text-ink"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const newCats = (config.categories || []).filter((_: any, idx: number) => idx !== i);
                            handleConfigChange("categories", newCats);
                          }}
                          className="text-faint hover:text-err p-1 rounded transition-colors cursor-pointer"
                          aria-label="Remove route"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    )
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      const newCats = [...(config.categories || []), `route_${(config.categories || []).length}`];
                      handleConfigChange("categories", newCats);
                    }}
                    className="text-[11px] font-mono text-accent hover:underline block pt-1"
                  >
                    + Add Branch Route
                  </button>
                </div>
              </div>
            </>
          )}

          {/* RAGAS Eval Parameters */}
          {data.type === "eval" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Minimum Passing Score: {(config.min_score ?? 0.85).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={config.min_score ?? 0.85}
                  onChange={(e) => handleConfigChange("min_score", parseFloat(e.target.value))}
                  className="w-full accent-accent"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Active Ragas Metrics
                </label>
                {["faithfulness", "answer_relevance", "context_precision", "context_recall"].map((metric) => {
                  const currentMetrics = config.metrics || ["faithfulness", "answer_relevance"];
                  const isChecked = currentMetrics.includes(metric);
                  return (
                    <label key={metric} className="flex items-center gap-2 text-xs text-ink cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          const updated = e.target.checked
                            ? [...currentMetrics, metric]
                            : currentMetrics.filter((m: string) => m !== metric);
                          handleConfigChange("metrics", updated);
                        }}
                        className="accent-accent"
                      />
                      <span className="font-mono text-[11px]">{metric}</span>
                    </label>
                  );
                })}
              </div>
            </>
          )}

          {/* Python Code Node Parameters */}
          {data.type === "code" && (
            <div>
              <label className="block text-[11px] font-mono text-muted mb-1">
                Python Transform Script
              </label>
              <textarea
                rows={6}
                value={config.code || ""}
                onChange={(e) => handleConfigChange("code", e.target.value)}
                className="w-full text-xs font-mono bg-bg border border-line rounded px-2.5 py-1.5 text-ink focus:border-accent"
              />
            </div>
          )}

          {/* HTTP Node Parameters */}
          {data.type === "http" && (
            <>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Endpoint URL
                </label>
                <input
                  type="text"
                  value={config.url || ""}
                  onChange={(e) => handleConfigChange("url", e.target.value)}
                  className="w-full text-xs font-mono bg-bg border border-line rounded px-2.5 py-1.5 text-ink"
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1">
                  Method
                </label>
                <select
                  value={config.method || "POST"}
                  onChange={(e) => handleConfigChange("method", e.target.value)}
                  className="w-full text-xs bg-bg border border-line rounded px-2 py-1.5 text-ink"
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
            </>
          )}
        </div>

        {/* Execution Inspector if node has run */}
        {data.lastOutput && (
          <div className="border-t border-line pt-3">
            <span className="font-mono text-[10.5px] uppercase font-semibold text-emerald-500 tracking-wider block mb-1">
              Last Execution State
            </span>
            <div className="bg-bg border border-line rounded p-2 text-[11px] font-mono max-h-36 overflow-y-auto">
              <pre className="text-ink/90 whitespace-pre-wrap">
                {JSON.stringify(data.lastOutput, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons Footer */}
      <div className="p-3 border-t border-line bg-bg/50 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onDuplicateNode(node.id)}
          className="flex-1 py-1.5 px-3 rounded text-xs font-mono font-medium border border-line bg-surface text-ink hover:bg-bg transition-colors"
        >
          Duplicate
        </button>
        <button
          type="button"
          onClick={() => onDeleteNode(node.id)}
          className="py-1.5 px-3 rounded text-xs font-mono font-medium border border-err/30 bg-err/10 text-err hover:bg-err/20 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
