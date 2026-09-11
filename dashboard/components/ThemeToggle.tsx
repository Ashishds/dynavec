"use client";

import { useEffect, useState } from "react";

/** Reads theme preference: localStorage → system preference → "light" */
function getInitial(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem("dynavec-theme");
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

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
      className="font-mono text-[12px] border-[1.5px] border-ink rounded-lg px-3 py-1.5 bg-surface text-ink hover:bg-accent hover:text-white transition-colors"
    >
      {theme === "dark" ? "☀ Light" : "● Dark"}
    </button>
  );
}
