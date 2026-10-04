"use client";

import { useEffect, useState } from "react";

/** Reads theme preference: localStorage → system preference → dark (default, matches landing page) */
function getInitial(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("dynavec-theme");
  if (stored === "dark" || stored === "light") return stored;
  // Default to dark to match landing page — ignore system preference
  return "dark";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  // Hydrate from localStorage on mount (avoids SSR mismatch)
  useEffect(() => {
    const t = getInitial();
    setTheme(t);
    document.documentElement.classList.toggle("dark", t === "dark");
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("dynavec-theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
  };

  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className="font-mono text-[12px] border-[1.5px] border-line rounded-lg px-2.5 py-1.5 bg-surface text-ink hover:border-accent transition-colors cursor-pointer flex items-center gap-1.5 shadow-sm"
    >
      {theme === "dark" ? (
        <>
          <svg className="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <circle cx="12" cy="12" r="4" strokeWidth="2" />
            <path strokeWidth="2" strokeLinecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
          </svg>
          <span>Light</span>
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
          <span>Dark</span>
        </>
      )}
    </button>
  );
}
