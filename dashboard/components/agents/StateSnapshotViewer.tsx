"use client";

import React, { useState } from "react";
import { SimulationResult } from "./simulator";

interface StateSnapshotViewerProps {
  step: SimulationResult["nodeTraces"][0];
  onClose: () => void;
}

export function StateSnapshotViewer({ step, onClose }: StateSnapshotViewerProps) {
  const [activeTab, setActiveTab] = useState<"output" | "input">("output");
  const [copied, setCopied] = useState(false);

  const displayData = activeTab === "output" ? step.output : step.input;
  const jsonText = JSON.stringify(displayData, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="absolute left-4 bottom-24 z-30 w-[95%] max-w-md bg-surface/98 backdrop-blur-md border border-line rounded-xl shadow-2xl p-4 flex flex-col gap-2.5">
      <div className="flex items-center justify-between border-b border-line pb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-accent text-xs">◈</span>
          <div>
            <h4 className="font-bold text-xs text-ink font-mono">
              {step.nodeLabel} State
            </h4>
            <span className="text-[10px] text-faint font-mono">
              Latency: {step.latencyMs}ms · Type: {step.type}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
          aria-label="Close state snapshot"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("output")}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              activeTab === "output"
                ? "bg-accent text-white font-semibold"
                : "bg-bg text-muted hover:text-ink border border-line"
            }`}
          >
            Outbound State
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("input")}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              activeTab === "input"
                ? "bg-accent text-white font-semibold"
                : "bg-bg text-muted hover:text-ink border border-line"
            }`}
          >
            Inbound State
          </button>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="text-[11px] font-mono text-muted hover:text-ink px-2 py-0.5 rounded border border-line bg-bg transition-colors flex items-center gap-1 cursor-pointer"
        >
          {copied ? (
            <>
              <svg className="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              <span>Copied</span>
            </>
          ) : (
            <span>Copy JSON</span>
          )}
        </button>
      </div>

      {/* JSON Viewer */}
      <div className="bg-[#121214] border border-line rounded-lg p-2.5 max-h-48 overflow-y-auto">
        <pre className="font-mono text-[11px] text-[#e6edf3] whitespace-pre-wrap leading-relaxed">
          {jsonText}
        </pre>
      </div>
    </div>
  );
}
