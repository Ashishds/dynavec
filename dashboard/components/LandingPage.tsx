"use client";
import React, { useEffect } from "react";
import { getLandingUrl } from "@/lib/paths";

interface LandingPageProps {
  onNavigate: (tab: string) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.location.href = getLandingUrl();
    }
  }, []);

  return (
    <div className="w-full h-screen overflow-hidden flex items-center justify-center bg-bg text-ink font-mono text-sm">
      <div className="flex items-center gap-2">
        <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span>Redirecting to dynavec home...</span>
      </div>
    </div>
  );
}
