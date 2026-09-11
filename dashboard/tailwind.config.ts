import type { Config } from "tailwindcss";

// dynavec brand tokens — kept in sync with the landing page (styles.css).
// Dark mode uses `class` strategy for localStorage-persisted toggle.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        faint: "var(--color-faint)",
        line: "var(--color-line)",
        accent: "var(--color-accent)",
        "accent-ink": "var(--color-accent-ink)",
        "accent-soft": "var(--color-accent-soft)",
        ok: "var(--color-ok)",
        err: "var(--color-err)",
        "table-head": "var(--color-table-head)",
        "chart-track": "var(--color-chart-track)",
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: "0 6px 30px rgba(20,17,15,.07)",
      },
      borderRadius: {
        xl2: "14px",
      },
    },
  },
  plugins: [],
};
export default config;
