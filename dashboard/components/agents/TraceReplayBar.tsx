"use client";

import React, { useEffect, useState } from "react";
import { SimulationResult } from "./simulator";

interface TraceReplayBarProps {
  trace: SimulationResult;
  currentStepIndex: number;
  onStepChange: (index: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  onCloseReplay: () => void;
  onToggleWaterfall: () => void;
  showWaterfall: boolean;
}

export function TraceReplayBar({
  trace,
  currentStepIndex,
  onStepChange,
  isPlaying,
  onTogglePlay,
  speed,
  onSpeedChange,
  onCloseReplay,
  onToggleWaterfall,
  showWaterfall,
}: TraceReplayBarProps) {
  const steps = trace.nodeTraces;
  const currentStep = steps[currentStepIndex] || steps[0];
  const totalSteps = steps.length;

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 w-[95%] max-w-4xl bg-surface/95 backdrop-blur-md border border-line rounded-2xl shadow-2xl p-3.5 flex flex-col gap-2.5 transition-all">
      {/* Top row: Status, Step name, and Quick info */}
      <div className="flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-accent animate-ping" />
          <span className="font-mono font-bold text-accent uppercase tracking-wider text-[11px]">
            Visual Trace Replay
          </span>
          <span className="font-mono text-faint">·</span>
          <span className="font-mono text-ink text-[11.5px] truncate max-w-xs sm:max-w-md">
            Step {currentStepIndex + 1}/{totalSteps}:{" "}
            <span className="font-bold text-accent">{currentStep?.nodeLabel}</span>{" "}
            <span className="text-muted">({currentStep?.latencyMs}ms)</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleWaterfall}
            className={`font-mono text-[11px] px-2.5 py-1 rounded-md border transition-all ${
              showWaterfall
                ? "bg-accent text-white border-accent font-semibold"
                : "bg-bg text-muted hover:text-ink border-line"
            }`}
          >
            Latency Profiling Waterfall
          </button>
          <button
            type="button"
            onClick={onCloseReplay}
            className="p-1 text-muted hover:text-ink rounded-md hover:bg-bg transition-colors cursor-pointer"
            title="Exit Replay"
            aria-label="Exit Replay"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Middle row: Interactive Scrubber / Timeline Bar */}
      <div className="flex items-center gap-1.5 w-full">
        {steps.map((st, idx) => {
          const isPassed = idx <= currentStepIndex;
          const isCurrent = idx === currentStepIndex;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onStepChange(idx)}
              className="flex-1 group relative py-1 focus:outline-none"
              title={`${st.nodeLabel} (${st.latencyMs}ms)`}
            >
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  isCurrent
                    ? "bg-accent ring-2 ring-accent/40 scale-y-125"
                    : isPassed
                    ? "bg-emerald-500"
                    : "bg-line hover:bg-line/80"
                }`}
              />
              <span className="absolute -bottom-4 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity font-mono text-[9px] text-faint whitespace-nowrap bg-bg px-1 rounded border border-line pointer-events-none">
                {st.nodeLabel}
              </span>
            </button>
          );
        })}
      </div>

      {/* Bottom row: Media Controls */}
      <div className="flex items-center justify-between pt-1 border-t border-line/60">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onStepChange(Math.max(0, currentStepIndex - 1))}
            disabled={currentStepIndex === 0}
            className="py-1 px-2.5 rounded bg-bg text-ink border border-line text-xs font-mono disabled:opacity-30 hover:bg-surface transition-all"
            title="Previous Step"
          >
            &laquo; Prev Step
          </button>

          <button
            type="button"
            onClick={onTogglePlay}
            className="py-1 px-4 rounded bg-accent text-white font-mono font-semibold text-xs flex items-center gap-1.5 hover:bg-accent/90 shadow-sm transition-all active:scale-95"
          >
            {isPlaying ? "Pause Execution" : "Play Execution"}
          </button>

          <button
            type="button"
            onClick={() => onStepChange(Math.min(totalSteps - 1, currentStepIndex + 1))}
            disabled={currentStepIndex === totalSteps - 1}
            className="py-1 px-2.5 rounded bg-bg text-ink border border-line text-xs font-mono disabled:opacity-30 hover:bg-surface transition-all"
            title="Next Step"
          >
            Next Step &raquo;
          </button>

          <button
            type="button"
            onClick={() => onStepChange(0)}
            className="py-1 px-2 rounded text-faint hover:text-ink text-xs font-mono hover:bg-bg transition-colors"
            title="Rewind to start"
          >
            ↺
          </button>
        </div>

        {/* Speed Controls & Total Latency */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 font-mono text-[10.5px]">
            <span className="text-faint">Speed:</span>
            {[0.5, 1, 2, 4].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSpeedChange(s)}
                className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                  speed === s
                    ? "bg-accent/20 text-accent font-bold border border-accent/40"
                    : "text-muted hover:text-ink"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="h-3 w-[1px] bg-line hidden sm:block" />

          <div className="font-mono text-[11px] text-faint hidden sm:block">
            Trace: <span className="text-ink font-semibold">{trace.traceId}</span> (
            {trace.totalLatencyMs}ms)
          </div>
        </div>
      </div>
    </div>
  );
}
