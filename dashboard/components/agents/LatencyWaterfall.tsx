"use client";

import React from "react";
import { SimulationResult } from "./simulator";

interface LatencyWaterfallProps {
  trace: SimulationResult;
  currentStepIndex: number;
  onSelectStep: (idx: number) => void;
  onClose: () => void;
}

export function LatencyWaterfall({
  trace,
  currentStepIndex,
  onSelectStep,
  onClose,
}: LatencyWaterfallProps) {
  const steps = trace.nodeTraces;
  const totalMs = Math.max(1, trace.totalLatencyMs);

  // Compute accumulated start offsets for waterfall layout
  let runningOffset = 0;
  const stepsWithOffsets = steps.map((s, idx) => {
    const offset = runningOffset;
    runningOffset += s.latencyMs;
    const pctWidth = Math.max(2, (s.latencyMs / totalMs) * 100);
    const pctLeft = (offset / totalMs) * 100;
    return { ...s, idx, offset, pctWidth, pctLeft };
  });

  // Find longest step (bottleneck)
  const bottleneck = steps.reduce(
    (max, s) => (s.latencyMs > max.latencyMs ? s : max),
    steps[0]
  );

  return (
    <div className="absolute right-4 bottom-24 z-30 w-[95%] max-w-xl bg-surface/98 backdrop-blur-md border border-line rounded-xl shadow-2xl p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-line pb-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-accent font-bold uppercase tracking-wider">Metrics:</span>
          <div>
            <h4 className="font-bold text-xs text-ink font-mono uppercase tracking-wider">
              Latency Waterfall Analysis
            </h4>
            <span className="text-[11px] text-faint font-mono">
              Total End-to-End: <span className="text-ink font-bold">{totalMs}ms</span>
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
          aria-label="Close waterfall"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Bottleneck highlight */}
      {bottleneck && (
        <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-amber-500 font-bold font-mono text-xs uppercase tracking-wider">Critical Path:</span>
            <span className="font-mono text-ink font-medium">{bottleneck.nodeLabel}</span>
          </div>
          <span className="font-mono text-amber-500 font-semibold">
            {bottleneck.latencyMs}ms ({Math.round((bottleneck.latencyMs / totalMs) * 100)}%)
          </span>
        </div>
      )}

      {/* Waterfall Bars Table */}
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {stepsWithOffsets.map((step) => {
          const isSelected = step.idx === currentStepIndex;
          const isBottleneck = step.nodeId === bottleneck?.nodeId;

          return (
            <div
              key={step.idx}
              onClick={() => onSelectStep(step.idx)}
              className={`p-2 rounded-lg border cursor-pointer transition-all ${
                isSelected
                  ? "bg-accent-soft/40 border-accent shadow-sm"
                  : "bg-bg/60 border-line hover:border-line/80 hover:bg-bg"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                <div className="flex items-center gap-2">
                  <svg className="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="font-semibold text-ink truncate max-w-[180px]">
                    {step.nodeLabel}
                  </span>
                  <span className="text-[10px] text-faint">({step.type})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-accent font-semibold">{step.latencyMs}ms</span>
                  <span className="text-[10px] text-muted w-10 text-right">
                    {Math.round((step.latencyMs / totalMs) * 100)}%
                  </span>
                </div>
              </div>

              {/* Bar track */}
              <div className="w-full bg-chart-track h-2 rounded-full overflow-hidden relative">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    isBottleneck
                      ? "bg-amber-500"
                      : isSelected
                      ? "bg-accent"
                      : "bg-ok"
                  }`}
                  style={{
                    marginLeft: `${step.pctLeft}%`,
                    width: `${step.pctWidth}%`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-[10.5px] font-mono text-faint flex items-center justify-between border-t border-line/60 pt-2">
        <span>Click any span to jump to replay step</span>
        <span>OpenTelemetry span compatible</span>
      </div>
    </div>
  );
}
