"use client";
import React, { useEffect } from "react";

interface LandingPageProps {
  onNavigate: (tab: string) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === "NAVIGATE_DASHBOARD") {
        onNavigate(e.data.tab || "playground");
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [onNavigate]);

  return (
    <div className="w-full h-screen overflow-hidden">
      {/* 100% Upstream Open Source Landing Page */}
      <iframe
        src="/landing/index.html"
        className="w-full h-full border-none block"
        title="dynavec — serverless hybrid vector database on AWS"
      />
    </div>
  );
}
