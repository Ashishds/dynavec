"use client";

import ThemeToggle from "./ThemeToggle";
import { getLandingUrl } from "@/lib/paths";

const RANGES = [
  { label: "30m", w: 1800 },
  { label: "1h", w: 3600 },
  { label: "6h", w: 21600 },
  { label: "24h", w: 86400 },
];

export default function TopBar({
  window: win, onWindow, auto, onAuto, live, hideControls, onHome, onToggleMobileMenu,
}: {
  window: number;
  onWindow: (w: number) => void;
  auto: boolean;
  onAuto: () => void;
  live: boolean;
  hideControls?: boolean;
  onHome?: () => void;
  onToggleMobileMenu?: () => void;
}) {
  return (
    <header
      className="h-[52px] flex items-center gap-2.5 sm:gap-4 px-3 sm:px-5 shrink-0 z-10 select-none overflow-x-hidden"
      style={{
        background: "var(--nav-blur-bg)",
        backdropFilter: "blur(20px) saturate(180%)",
        WebkitBackdropFilter: "blur(20px) saturate(180%)",
        borderBottom: "1px solid var(--nav-blur-border)",
        boxShadow: "0 1px 0 rgba(0,0,0,0.12)",
      }}
    >
      {/* ── Mobile menu hamburger button ── */}
      {onToggleMobileMenu && (
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="md:hidden p-1.5 rounded-lg text-muted hover:text-ink hover:bg-surface border border-line cursor-pointer shrink-0 transition-colors"
          aria-label="Toggle navigation menu"
          title="Open menu"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      )}

      {/* ── Brand logo — matches open source original dynavec brand mark ── */}
      <a
        href={getLandingUrl()}
        className="flex items-center gap-2 font-mono font-bold text-[16px] sm:text-[17px] text-ink hover:opacity-85 transition-opacity cursor-pointer tracking-tight shrink-0"
        title="dynavec home"
        aria-label="dynavec home"
      >
        <svg
          className="text-accent shrink-0"
          width="20"
          height="20"
          viewBox="0 0 22 22"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          aria-hidden="true"
        >
          <rect x="1" y="1" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <line x1="1" y1="11" x2="21" y2="11" stroke="currentColor" strokeWidth="1.5" />
          <line x1="11" y1="1" x2="11" y2="21" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="6" cy="6" r="2" fill="currentColor" stroke="none" />
          <circle cx="16" cy="16" r="2" fill="currentColor" stroke="none" />
        </svg>
        <span>dynavec</span>
      </a>

      {/* ── Live cluster status badge ── */}
      <span className="text-muted text-[12px] sm:text-[13px] mr-auto flex items-center gap-1.5 sm:gap-2 truncate">
        <span className="hidden sm:inline">Console</span>
        <span className={"font-mono text-[10.5px] sm:text-[11px] px-2 sm:px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 shrink-0 " + (live ? "bg-ok/10 text-ok border-ok/30" : "bg-accent-soft text-accent-ink border-accent/20")}>
          <span className={"w-1.5 h-1.5 rounded-full " + (live ? "bg-ok animate-pulse" : "bg-accent")} />
          <span>{live ? "Live" : "Sample"}</span>
          <span className="hidden md:inline">{live ? "Cluster" : "Data"}</span>
        </span>
      </span>

      {/* ── Time window + auto-refresh controls ── */}
      {!hideControls && (
        <>
          <div className="hidden sm:flex border-[1.5px] border-line rounded-lg overflow-hidden shrink-0">
            {RANGES.map((r) => (
              <button
                key={r.w}
                onClick={() => onWindow(r.w)}
                className={
                  "font-mono text-[11.5px] px-2.5 py-1 border-r border-line last:border-r-0 transition-colors " +
                  (win === r.w
                    ? "bg-accent text-white"
                    : "bg-surface text-muted hover:text-ink")
                }
              >
                {r.label}
              </button>
            ))}
          </div>
          <button
            onClick={onAuto}
            className={
              "hidden sm:flex font-mono text-[11.5px] border-[1.5px] border-line rounded-lg px-2.5 py-1 transition-colors items-center gap-1.5 cursor-pointer shrink-0 " +
              (auto
                ? "bg-ink text-bg font-semibold"
                : "bg-surface text-ink hover:border-accent")
            }
          >
            {auto && <span className="w-1.5 h-1.5 rounded-full bg-ok animate-pulse" />}
            Auto
          </button>
        </>
      )}

      <ThemeToggle />
    </header>
  );
}
