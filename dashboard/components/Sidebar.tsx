"use client";

const GROUPS: { title: string; items: { label: string; id: string; badge?: string; soon?: boolean }[] }[] = [
  {
    title: "Studio",
    items: [
      { label: "Agent Canvas", id: "canvas" },
      { label: "Deployed Workflows", id: "workflows" },
      { label: "Query Playground", id: "playground" },
    ],
  },
  {
    title: "Observability",
    items: [
      { label: "Tracing", id: "tracing" },
      { label: "Latency", id: "latency" },
      { label: "Cost", id: "cost" },
    ],
  },
  {
    title: "Evaluation",
    items: [
      { label: "Retrieval Benchmarks", id: "eval" },
      { label: "Faithfulness & Safety", id: "faithfulness" },
    ],
  },
  {
    title: "Infrastructure",
    items: [
      { label: "S3 Vector Indexes", id: "resources" },
      { label: "DynamoDB Namespaces", id: "namespaces" },
    ],
  },
];

const ICONS: Record<string, React.ReactNode> = {
  canvas: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <path strokeWidth="1.7" strokeLinecap="round" d="M10 6.5h4M6.5 10v7.5a1.5 1.5 0 0 0 1.5 1.5H14" />
    </svg>
  ),
  workflows: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z" />
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M14 10v4M10 14h8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h4" />
    </svg>
  ),
  playground: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <circle cx="11" cy="11" r="7" strokeWidth="1.7" />
      <path strokeWidth="1.7" strokeLinecap="round" d="m20 20-3.5-3.5" />
    </svg>
  ),
  tracing: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h14" />
      <circle cx="18" cy="12" r="2" strokeWidth="1.7" />
    </svg>
  ),
  latency: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  ),
  cost: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <circle cx="12" cy="12" r="9" strokeWidth="1.7" />
      <path strokeWidth="1.7" strokeLinecap="round" d="M12 6v12M15 9.5a3 3 0 0 0-3-2.5h-1a2.5 2.5 0 0 0 0 5h2a2.5 2.5 0 0 1 0 5h-1a3 3 0 0 1-3-2.5" />
    </svg>
  ),
  eval: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M18 20V10M12 20V4M6 20v-6" />
    </svg>
  ),
  faithfulness: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" d="m9 12 2 2 4-4" />
    </svg>
  ),
  resources: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <ellipse cx="12" cy="5" rx="9" ry="3" strokeWidth="1.7" />
      <path strokeWidth="1.7" d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
  namespaces: (
    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" strokeWidth="1.7" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" strokeWidth="1.7" />
    </svg>
  ),
};

export default function Sidebar({ view, onView }: { view: string; onView: (v: string) => void }) {
  return (
    <nav
      className="w-[230px] shrink-0 border-r border-line p-3 hidden md:block sticky top-[52px] h-[calc(100vh-52px)] self-start overflow-y-auto"
      style={{ background: "var(--color-surface)" }}
    >
      {GROUPS.map((g) => (
        <div key={g.title} className="mb-4">
          <h4 className="font-mono text-[10.5px] uppercase tracking-wider text-faint mb-1.5 px-2.5">
            {g.title}
          </h4>
          {g.items.map((it) => (
            <button
              type="button"
              key={it.label}
              onClick={() => it.id && onView(it.id)}
              className={
                "w-full text-left flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-[13px] mb-0.5 transition-all cursor-pointer " +
                (it.id && view === it.id
                  ? "bg-accent-soft text-accent-ink font-semibold shadow-xs"
                  : it.soon
                  ? "text-faint cursor-default"
                  : "text-muted hover:text-ink hover:bg-accent-soft/30")
              }
            >
              <span className={it.id && view === it.id ? "text-accent" : "text-muted/80"}>
                {ICONS[it.id] || null}
              </span>
              <span className="truncate">{it.label}</span>
              {it.soon && <span className="font-mono text-[9.5px] text-faint ml-auto">soon</span>}
            </button>
          ))}
        </div>
      ))}
    </nav>
  );
}
