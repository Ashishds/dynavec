"use client";

const GROUPS: { title: string; items: { label: string; id: string; badge?: string; soon?: boolean }[] }[] = [
  { title: "Query Studio", items: [{ label: "Search Playground", id: "playground" }] },
  { title: "Observability", items: [{ label: "Tracing", id: "tracing" }, { label: "Latency", id: "latency" }, { label: "Cost", id: "cost" }] },
  { title: "Evaluation", items: [{ label: "Scores", id: "eval" }, { label: "Faithfulness", id: "faithfulness" }] },
  { title: "Resources", items: [{ label: "Buckets & Indexes", id: "resources" }, { label: "Namespaces", id: "namespaces" }] },
];

export default function Sidebar({ view, onView }: { view: string; onView: (v: string) => void }) {
  return (
    <nav className="w-[210px] shrink-0 border-r border-line bg-surface p-4 hidden md:block">
      {GROUPS.map((g) => (
        <div key={g.title}>
          <h4 className="font-mono text-[11px] uppercase tracking-wider text-faint mt-4 mb-2 px-2">{g.title}</h4>
          {g.items.map((it) => (
            <a
              key={it.label}
              onClick={() => it.id && onView(it.id)}
              className={
                "flex items-center justify-between px-2.5 py-1.5 rounded-md text-[13.5px] mb-0.5 " +
                (it.id && view === it.id
                  ? "bg-accent-soft text-accent-ink font-semibold border-l-2 border-accent"
                  : it.soon
                  ? "text-faint cursor-default"
                  : it.id
                  ? "text-muted hover:text-ink cursor-pointer"
                  : "text-muted")
              }
            >
              {it.label}
              {it.soon && <span className="font-mono text-[10px] text-faint">soon</span>}
            </a>
          ))}
        </div>
      ))}
    </nav>
  );
}
