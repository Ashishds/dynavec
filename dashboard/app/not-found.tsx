"use client";

import { getLandingUrl } from "@/lib/paths";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-bg text-ink font-mono p-6 text-center">
      <h1 className="text-4xl font-bold mb-2 text-accent">404</h1>
      <p className="text-sm text-muted mb-6">The requested telemetry page or resource does not exist.</p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <a
          href={getLandingUrl()}
          className="px-4 py-2 bg-accent text-white rounded-lg text-xs font-semibold hover:opacity-90 transition-opacity"
        >
          ← Return to Dynavec Home
        </a>
        <a
          href="?tab=playground"
          className="px-4 py-2 bg-surface text-ink border border-line rounded-lg text-xs font-semibold hover:bg-accent-soft/30 transition-colors"
        >
          Open Query Studio
        </a>
      </div>
    </div>
  );
}
