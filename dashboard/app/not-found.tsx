"use client";

import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-bg text-ink font-mono p-6 text-center">
      <h1 className="text-4xl font-bold mb-2">404</h1>
      <p className="text-sm text-muted mb-6">The requested telemetry page or resource does not exist.</p>
      <Link
        href="/"
        className="px-4 py-2 bg-accent text-white rounded-lg text-xs font-semibold hover:opacity-90 transition-opacity"
      >
        ← Return to Dynavec Observability
      </Link>
    </div>
  );
}
