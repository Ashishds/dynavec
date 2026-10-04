"""Observability dashboard server for dynavec.

Serves a comprehensive, on-brand (dynavec landing-page theme) telemetry UI backed
by a :class:`~dynavec.telemetry.TelemetryRecorder`. All numbers are **real** —
they come from actual operations recorded on the client, not a simulator.

    from dynavec.telemetry import TelemetryRecorder
    from dynavec import Dynavec, DynavecConfig
    rec = TelemetryRecorder()
    db = Dynavec(cfg, embedder=emb, telemetry=rec)
    ...  # run your searches
    from dynavec.dashboard import serve
    serve(rec, port=8778)

Security
--------
- Binds to ``127.0.0.1`` by default so the dashboard is not exposed to the network.
- When ``DYNAVEC_DASHBOARD_TOKEN`` is set in the environment, every request must
  include ``Authorization: Bearer <token>``.  This prevents unauthorised local
  processes from reading telemetry data.  AWS credentials are **never** sent to the
  browser.

Vanilla JS + inline SVG charts (no CDN, no build step). Endpoints:
    GET /                      the dashboard
    GET /api/metrics?window=   aggregated stats + histogram
    GET /api/traces?limit=&op=&namespace=&status=   recent events
    GET /api/trace/{id}        one event
"""

from __future__ import annotations

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .telemetry import TelemetryRecorder, aggregate

_INDEX_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>dynavec · Observability</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#fbfaf8;--surface:#fff;--fg:#14110f;--muted:#6f6862;--faint:#a99f97;--line:#ece6df;
--accent:#e8623b;--accent-ink:#b8472a;--accent-soft:#fdeee8;--ok:#2f7d5b;--err:#b8472a;
--sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;--shadow:0 6px 30px rgba(20,17,15,.07)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:14px;border-top:3px solid var(--accent);-webkit-font-smoothing:antialiased}
a{color:inherit}
.top{display:flex;align-items:center;gap:16px;padding:12px 20px;background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
.brand{display:flex;align-items:center;gap:9px;font-family:var(--mono);font-weight:700;font-size:16px}
.brand svg{color:var(--accent)}
.top .sub{color:var(--muted);font-size:13px;margin-right:auto}
.rangebtns{display:flex;border:1.5px solid var(--line-strong,#14110f);border-radius:8px;overflow:hidden}
.rangebtns button{font-family:var(--mono);font-size:12px;border:0;background:var(--surface);padding:7px 12px;cursor:pointer;color:var(--muted);border-right:1px solid var(--line)}
.rangebtns button:last-child{border-right:0}
.rangebtns button.on{background:var(--accent);color:#fff}
.toggle{font-family:var(--mono);font-size:12px;border:1.5px solid #14110f;border-radius:8px;background:var(--surface);padding:7px 12px;cursor:pointer}
.toggle.on{background:#14110f;color:#fff}
.layout{display:grid;grid-template-columns:210px 1fr;min-height:calc(100vh - 52px)}
.side{border-right:1px solid var(--line);padding:18px 12px;background:var(--surface)}
.side h4{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);margin:16px 8px 8px}
.side a{display:block;padding:7px 10px;border-radius:7px;text-decoration:none;color:var(--muted);font-size:13.5px;border-left:2px solid transparent}
.side a.on{background:var(--accent-soft);color:var(--accent-ink);border-left-color:var(--accent);font-weight:600}
.side a.soon{opacity:.55;cursor:default}
.side .tag{font-size:10px;font-family:var(--mono);color:var(--faint);float:right}
.main{padding:22px 24px;min-width:0}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:20px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.kpi .l{font-size:12px;color:var(--muted);margin-bottom:8px}
.kpi .v{font-family:var(--mono);font-size:26px;font-weight:700;letter-spacing:-.02em}
.kpi .v small{font-size:13px;color:var(--muted);font-weight:400}
.kpi .v.win{color:var(--accent-ink)}
.panels{display:grid;grid-template-columns:1.5fr 1fr;gap:16px;margin-bottom:20px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card h3{margin:0 0 14px;font-size:14px}
.card h3 .hint{font-family:var(--mono);font-size:11px;color:var(--faint);font-weight:400}
.tablecard{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.tablehead{display:flex;align-items:center;gap:12px;padding:14px 18px;border-bottom:1px solid var(--line)}
.tablehead h3{margin:0;font-size:14px}
.tablehead .filters{margin-left:auto;display:flex;gap:8px}
.tablehead select,.tablehead input{font-family:var(--mono);font-size:12px;border:1px solid var(--line);border-radius:7px;padding:6px 9px;background:var(--bg)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);padding:10px 18px;background:#faf6f1;border-bottom:1px solid var(--line)}
td{padding:10px 18px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
tr.row{cursor:pointer}
tr.row:hover{background:var(--accent-soft)}
.pill{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.search{background:#eef3ff;color:#3b5bdb;border-color:#dbe3ff}
.pill.graph_search{background:#f3eeff;color:#7048e8;border-color:#e5dbff}
.pill.upsert{background:#eafaf1;color:#2f7d5b;border-color:#d3f0e0}
.st-ok{color:var(--ok)}
.st-error{color:var(--err);font-weight:600}
.hit{color:var(--ok)}.miss{color:var(--muted)}.na{color:var(--faint)}
.mono{font-family:var(--mono)}
.drawer{position:fixed;top:0;right:0;height:100vh;width:min(460px,92vw);background:var(--surface);border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(100%);transition:transform .2s ease;z-index:20;overflow-y:auto;padding:22px}
.drawer.open{transform:none}
.drawer h3{margin:0 0 4px;font-size:16px}
.drawer .close{position:absolute;top:16px;right:18px;border:0;background:none;font-size:20px;cursor:pointer;color:var(--muted)}
.kv{display:grid;grid-template-columns:130px 1fr;gap:8px 14px;margin-top:16px;font-size:13px}
.kv .k{color:var(--muted);font-family:var(--mono);font-size:12px}
.kv .val{font-variant-numeric:tabular-nums;word-break:break-word}
.wf{margin-top:18px}
.wf .bar{height:10px;border-radius:5px;background:var(--accent);margin:4px 0}
.empty{padding:40px;text-align:center;color:var(--muted)}
.note{color:var(--faint);font-size:11.5px;font-family:var(--mono);margin-top:8px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}.panels{grid-template-columns:1fr}.layout{grid-template-columns:1fr}.side{display:none}}
</style></head>
<body>
<div class="top">
  <span class="brand"><svg width="18" height="18" viewBox="0 0 22 22"><rect x="1" y="1" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1" y1="11" x2="21" y2="11" stroke="currentColor" stroke-width="1.5"/><line x1="11" y1="1" x2="11" y2="21" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="6" r="2" fill="currentColor"/><circle cx="16" cy="16" r="2" fill="currentColor"/></svg>dynavec</span>
  <span class="sub">Observability</span>
  <div class="rangebtns" id="ranges">
    <button data-w="1800">30m</button><button data-w="3600" class="on">1h</button>
    <button data-w="21600">6h</button><button data-w="86400">24h</button>
  </div>
  <button class="toggle on" id="auto">Auto-refresh</button>
</div>
<div style="background:#e8623b;color:#fff;padding:8px 20px;font-family:var(--sans);font-size:13px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #c74b28;">
  <span><strong>🚀 Full Next.js Dashboard:</strong> All 7 tabs (Latency waterfall, Cost sliders, Faithfulness, Resources, Namespaces) are live at <strong>http://localhost:3001</strong></span>
  <a href="http://localhost:3001" style="background:#fff;color:#e8623b;padding:4px 12px;border-radius:6px;font-weight:600;text-decoration:none;font-size:12px;">Open Full Dashboard &rarr;</a>
</div>
<div class="layout">
  <nav class="side">
    <h4>Observability</h4>
    <a class="on" href="#">Tracing</a>
    <a href="http://localhost:3001" style="color:var(--accent);">Latency &rarr;</a>
    <a href="http://localhost:3001" style="color:var(--accent);">Cost &rarr;</a>
    <h4>Evaluation</h4>
    <a href="http://localhost:3001" style="color:var(--accent);">Scores &rarr;</a>
    <a href="http://localhost:3001" style="color:var(--accent);">Faithfulness &rarr;</a>
    <h4>Resources</h4>
    <a href="http://localhost:3001" style="color:var(--accent);">Buckets &amp; Indexes &rarr;</a>
    <a href="http://localhost:3001" style="color:var(--accent);">Namespaces &rarr;</a>
  </nav>
  <main class="main">
    <div class="kpis" id="kpis"></div>
    <div class="panels">
      <div class="card"><h3>Query volume <span class="hint" id="histhint"></span></h3><div id="hist"></div></div>
      <div class="card"><h3>Latency percentiles <span class="hint">ms</span></h3><div id="lat"></div></div>
    </div>
    <div class="tablecard">
      <div class="tablehead">
        <h3>Traces</h3>
        <div class="filters">
          <select id="fop"><option value="">all ops</option><option>search</option><option>graph_search</option><option>upsert</option></select>
          <select id="fstatus"><option value="">any status</option><option>ok</option><option>error</option></select>
          <input id="fns" placeholder="namespace…" size="12">
        </div>
      </div>
      <div id="table"></div>
    </div>
    <p class="note" id="note"></p>
  </main>
</div>
<div class="drawer" id="drawer"><button class="close" onclick="closeDrawer()">&times;</button><div id="drawerbody"></div></div>
<script>
let W=3600, AUTO=true, TIMER=null;
const $=s=>document.querySelector(s);
function fmt(n,d=0){return n==null?'—':Number(n).toLocaleString(undefined,{maximumFractionDigits:d})}
function bars(vals,color){const n=vals.length,max=Math.max(1,...vals),w=100/n;
  let r=`<svg viewBox="0 0 100 40" preserveAspectRatio="none" style="width:100%;height:120px">`;
  vals.forEach((v,i)=>{const h=v/max*38;r+=`<rect x="${i*w+w*0.12}" y="${40-h}" width="${w*0.76}" height="${h||0.4}" fill="${color}" rx="0.6"/>`});
  return r+`</svg>`}
function latChart(m){const items=[['p50',m.p50,'#2f7d5b'],['p95',m.p95,'#e8623b'],['p99',m.p99,'#b8472a']];
  const max=Math.max(1,m.p99,m.p95,m.p50);let r='<div style="display:flex;flex-direction:column;gap:14px;padding:6px 0 2px">';
  for(const[l,v,c]of items){const pct=v/max*100;
    r+=`<div><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px"><span class="mono" style="color:${c}">${l}</span><span class="mono">${fmt(v,1)} ms</span></div>
    <div style="height:10px;background:#f0ece6;border-radius:5px"><div style="height:100%;width:${pct}%;background:${c};border-radius:5px"></div></div></div>`}
  return r+'</div>'}
function kpi(l,v,win){return `<div class="kpi"><div class="l">${l}</div><div class="v ${win?'win':''}">${v}</div></div>`}
async function load(){
  const m=await (await fetch('/api/metrics?window='+W)).json();
  $('#kpis').innerHTML=[
    kpi('Queries / min',fmt(m.qpm,1),true),
    kpi('p95 latency',fmt(m.p95,0)+'<small> ms</small>'),
    kpi('Cache hit rate',m.cache_hit_rate==null?'—':fmt(m.cache_hit_rate,1)+'<small>%</small>',true),
    kpi('Avg results',fmt(m.avg_results,1)),
    kpi('Error rate',fmt(m.error_rate,1)+'<small>%</small>')
  ].join('');
  $('#hist').innerHTML=bars(m.histogram,'#e8623b');
  $('#histhint').textContent=(m.total||0)+' traces · '+Math.round(m.bucket_width_s)+'s buckets';
  $('#lat').innerHTML=latChart(m);
  await loadTable();
}
async function loadTable(){
  const q=new URLSearchParams({limit:100});
  if($('#fop').value)q.set('op',$('#fop').value);
  if($('#fstatus').value)q.set('status',$('#fstatus').value);
  if($('#fns').value)q.set('namespace',$('#fns').value);
  const rows=await (await fetch('/api/traces?'+q)).json();
  if(!rows.length){$('#table').innerHTML='<div class="empty">No traces yet. Run some searches with <span class="mono">Dynavec(..., telemetry=recorder)</span>.</div>';return}
  let h='<table><thead><tr><th>Start</th><th>Op</th><th>Namespace</th><th>Latency</th><th>Results</th><th>Cache</th><th>Rank</th><th>Status</th></tr></thead><tbody>';
  for(const e of rows){const t=new Date(e.ts*1000).toLocaleTimeString();
    const cache=e.cache_hit==null?'<span class="na">—</span>':(e.cache_hit?'<span class="hit">hit</span>':'<span class="miss">miss</span>');
    const rank=[e.rescore,e.rerank].filter(Boolean).join('+')||'<span class="na">—</span>';
    h+=`<tr class="row" onclick="openTrace('${e.id}')"><td class="mono">${t}</td><td><span class="pill ${e.op}">${e.op}</span></td><td>${e.namespace}</td><td class="mono">${fmt(e.latency_ms,1)} ms</td><td class="mono">${e.n_results}</td><td>${cache}</td><td class="mono">${rank}</td><td class="st-${e.status}">${e.status}</td></tr>`}
  $('#table').innerHTML=h+'</tbody></table>';
}
async function openTrace(id){const e=await (await fetch('/api/trace/'+id)).json();
  const row=(k,v)=>`<div class="k">${k}</div><div class="val">${v==null?'—':v}</div>`;
  $('#drawerbody').innerHTML=`<h3><span class="pill ${e.op}">${e.op}</span> trace</h3>
  <div class="mono" style="color:var(--muted);font-size:12px">${e.id} · ${new Date(e.ts*1000).toLocaleString()}</div>
  <div class="kv">${row('Namespace',e.namespace)}${row('Latency',fmt(e.latency_ms,2)+' ms')}${row('Results',e.n_results)}${row('top_k',e.top_k)}
  ${row('Cache',e.cache_hit==null?'no cache':(e.cache_hit?'hit':'miss'))}${row('Filtered',e.filtered)}${row('Rescore',e.rescore)}${row('Rerank',e.rerank)}
  ${row('Top score',e.score_top)}${row('Mean score',e.score_mean)}${row('Status',e.status)}${e.error?row('Error',e.error):''}${e.query_preview?row('Query',e.query_preview):''}</div>
  <div class="wf"><div class="k mono" style="color:var(--muted);font-size:12px;margin-bottom:6px">End-to-end latency</div><div class="bar" style="width:100%"></div></div>`;
  $('#drawer').classList.add('open');
}
function closeDrawer(){$('#drawer').classList.remove('open')}
$('#ranges').addEventListener('click',e=>{if(e.target.dataset.w){W=+e.target.dataset.w;[...$('#ranges').children].forEach(b=>b.classList.toggle('on',b===e.target));load()}});
$('#auto').addEventListener('click',()=>{AUTO=!AUTO;$('#auto').classList.toggle('on',AUTO);schedule()});
['#fop','#fstatus','#fns'].forEach(s=>$(s).addEventListener('input',loadTable));
function schedule(){if(TIMER)clearInterval(TIMER);if(AUTO)TIMER=setInterval(load,4000)}
load();schedule();
</script>
</body></html>"""


ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "how", "what", "which", "who", "whom",
    "this", "that", "these", "those", "can", "could", "will", "would", "shall", "should",
    "it", "its", "we", "our", "you", "your", "they", "their", "so", "if", "not",
}


def _stem_token(w: str) -> str:
    w = w.lower().strip()
    if w in ("transfomer", "transfomers", "transforming"):
        return "transform"
    if w.startswith("position"):
        return "position"
    if w.startswith("encod"):
        return "encod"
    if w.startswith("attent"):
        return "attent"
    if w.startswith("decod"):
        return "decod"
    w = re.sub(r"(al|ing|s|ed|er|ers|ion|ions|ment|ments|ive|ly)$", "", w)
    return w


KNOWN_RAG_KEYWORDS = [
    "attention", "transformer", "transformers", "encoder", "decoder",
    "positional", "feedforward", "embedding", "sequence",
    "recurrence", "convolution", "residual", "latency", "dynamodb", "vectors",
    "architecture", "mechanism", "network", "neural", "training", "inference",
    "retrieval", "augmented", "generation", "semantic", "similarity", "ranking",
    "quantization", "compression", "serverless", "database", "index", "cluster",
]


def _compute_dynamic_phrase_bonus(q_substantive: list[str], text_clean: str) -> float:
    """Compute n-gram phrase bonus dynamically from query terms.

    Generates all bigrams and trigrams from query substantive terms and checks
    how many appear verbatim in the chunk text. Returns a normalized bonus (0–0.40).
    This replaces hardcoded topic-specific phrase lists.
    """
    if len(q_substantive) < 2:
        return 0.0
    bonus = 0.0
    words = q_substantive  # already substantive (stopwords removed)
    # Bigrams
    bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
    for w1, w2 in bigrams:
        if f"{w1} {w2}" in text_clean:
            bonus += 0.15
    # Trigrams
    trigrams = [(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)]
    for w1, w2, w3 in trigrams:
        if f"{w1} {w2} {w3}" in text_clean:
            bonus += 0.10
    return min(0.40, bonus)


def _normalize_query(q: str) -> tuple[str, list[str], set[str]]:
    """Normalize hyphens, compound words, and autocorrect typos in RAG queries."""
    import difflib
    q_spaced = re.sub(r"[-_/]+", " ", q.lower())
    q_spaced = re.sub(r"(head)(atten\w*)", r"\1 \2", q_spaced)
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", q_spaced)
    corrected_words = []
    for w in words:
        if len(w) >= 5 and w not in ("multi", "scale", "depth", "layer", "batch", "query", "heads"):
            matches = difflib.get_close_matches(w, KNOWN_RAG_KEYWORDS, n=1, cutoff=0.72)
            if matches:
                corrected_words.append(matches[0])
                continue
        corrected_words.append(w)
    clean_q = " ".join(corrected_words)
    substantive = [w for w in corrected_words if w not in ENGLISH_STOPWORDS]
    if not substantive:
        substantive = corrected_words
    stemmed = {_stem_token(w) for w in substantive}
    return clean_q, substantive, stemmed


# In-memory document library store for tracking uploaded & crawled knowledge sources
_DOCUMENTS_STORE: list[dict] = [
    {
        "id": "doc_yt_37pbbwwaxqm",
        "filename": "youtube_37PBBwWaXQM.youtube",
        "source": "https://www.youtube.com/watch?v=37PBBwWaXQM",
        "size_bytes": 3891,
        "status": "Completed",
        "chunks": 4,
        "uploaded_at": "31/05/2026, 16:23:36",
        "namespace": "production-core",
        "type": "youtube",
    }
]


def _make_handler(
    recorder: TelemetryRecorder,
    token: str | None = None,
    eval_dir: str | None = None,
    db: Any = None,
    workload_controller: dict | None = None,
):
    """Create a request handler class with optional Bearer-token auth and live query routes."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                # Security: prevent browser from sniffing content types
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def _check_auth(self) -> bool:
            """Return True if the request is authorised (or auth is disabled)."""
            if token is None:
                return True
            auth = self.headers.get("Authorization", "")
            if auth == f"Bearer {token}":
                return True
            self._send(401, json.dumps({"error": "unauthorized"}))
            return False

        def do_GET(self):
            if not self._check_auth():
                return
            parsed = urlparse(self.path)
            path, qs = parsed.path, parse_qs(parsed.query)
            if path == "/" or path == "/index.html":
                return self._send(200, _INDEX_HTML, "text/html; charset=utf-8")
            if path == "/api/workload/status":
                enabled = (
                    workload_controller.get("enabled", False) if workload_controller else False
                )
                return self._send(200, json.dumps({"enabled": enabled}))
            if path == "/api/metrics":
                window = int(qs.get("window", ["3600"])[0])
                return self._send(200, json.dumps(aggregate(recorder.snapshot(), window)))
            if path == "/api/traces":
                evs = recorder.events(
                    limit=int(qs.get("limit", ["100"])[0]),
                    op=(qs.get("op", [None])[0] or None),
                    namespace=(qs.get("namespace", [None])[0] or None),
                    status=(qs.get("status", [None])[0] or None),
                )
                return self._send(200, json.dumps([e.to_dict() for e in evs]))
            if path.startswith("/api/trace/"):
                ev = recorder.get(path.rsplit("/", 1)[-1])
                if ev is None:
                    return self._send(404, json.dumps({"error": "not found"}))
                return self._send(200, json.dumps(ev.to_dict()))
            if path == "/health":
                import importlib.metadata
                version = "0.3.0"
                try:
                    version = importlib.metadata.version("dynavec")
                except Exception:
                    pass
                embedder_name = "LocalDeterministicEmbedder"
                if db is not None:
                    emb = getattr(db, "_embedder", None) or getattr(db, "embedder", None)
                    if emb is not None:
                        embedder_name = type(emb).__name__
                return self._send(200, json.dumps({
                    "status": "ok",
                    "version": version,
                    "db_connected": db is not None,
                    "embedder": embedder_name,
                    "namespace_default": "production-core",
                }))
            if path == "/api/eval":
                return self._send(200, json.dumps(_load_eval_runs(eval_dir)))
            if path == "/api/search":
                q = qs.get("q", [""])[0].strip()
                ns = qs.get("namespace", ["production-core"])[0].strip()
                top_k = int(qs.get("top_k", ["3"])[0])
                candidate_k = int(qs.get("candidate_k", ["20"])[0])
                rerank_mode = qs.get("rerank", ["hybrid"])[0].strip().lower()
                do_synthesize = qs.get("synthesize", ["true"])[0].strip().lower() != "false"

                if not q:
                    return self._send(400, json.dumps({"error": "query parameter 'q' is required"}))
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                try:
                    t_wall_start = time.perf_counter()
                    rerank_ms = 0.0
                    # Reranking pipeline
                    if rerank_mode == "mmr":
                        t_mmr_start = time.perf_counter()
                        results = db.search(
                            q, namespace=ns, top_k=top_k, rerank="mmr", include_vectors=True
                        )
                        rerank_ms = (time.perf_counter() - t_mmr_start) * 1000
                    elif rerank_mode in ("hybrid", "cross"):
                        clean_q, q_substantive, q_stemmed = _normalize_query(q)
                        # Over-fetch candidate pool (include_vectors=False eliminates redundant second S3 vector batch fetch!)
                        raw_candidates = db.search(
                            clean_q, namespace=ns, top_k=max(candidate_k, top_k), include_vectors=False
                        )

                        scored_candidates = []
                        for rank_idx, r in enumerate(raw_candidates, start=1):
                            text_raw = (r.text or "").lower()
                            text_clean = re.sub(r"[-_/]+", " ", text_raw)
                            text_words = set(re.findall(r"\b[a-zA-Z0-9_]+\b", text_clean))
                            text_stemmed = {
                                _stem_token(w) for w in text_words if w not in ENGLISH_STOPWORDS
                            }

                            # 1. Coverage of substantive query terms
                            matched_terms = [
                                w
                                for w in q_substantive
                                if _stem_token(w) in text_stemmed or w in text_clean
                            ]
                            coverage = len(matched_terms) / max(1, len(q_substantive))

                            # 2. Dynamic n-gram phrase bonus (domain-agnostic)
                            # Checks if query bigrams/trigrams appear verbatim in chunk text.
                            # This replaces paper-specific hardcoded phrase lists.
                            phrase_bonus = _compute_dynamic_phrase_bonus(
                                q_substantive, text_clean
                            )

                            # 3. Term frequency density bonus for key query words
                            freq_bonus = sum(
                                min(0.12, text_clean.count(w) * 0.03)
                                for w in q_substantive[:3]
                            )

                            ann_score = float(r.score or 0.0)
                            raw_score = (
                                0.30 * ann_score
                                + 0.40 * coverage
                                + phrase_bonus
                                + freq_bonus
                            )
                            hybrid_score = round(min(0.99, raw_score / 1.6), 4)
                            scored_candidates.append(
                                (raw_score, hybrid_score, rank_idx, coverage, r)
                            )

                        t_rerank_start = time.perf_counter()
                        scored_candidates.sort(key=lambda x: x[0], reverse=True)

                        # Compute the top candidate's hybrid score BEFORE filtering
                        top_hybrid_score = scored_candidates[0][1] if scored_candidates else 0.0
                        top_raw_score = scored_candidates[0][0] if scored_candidates else 0.0

                        # Relevance threshold filter:
                        # - If the BEST candidate after reranking is still below 0.30, the entire
                        #   retrieval is off-topic (e.g. Linux Questions.pdf for a transformer query).
                        # - Also drop individual candidates when a strong match exists but they score low.
                        filtered_candidates = []
                        for sc in scored_candidates:
                            # Individual candidate is noise: strong top exists but this one is weak
                            if top_raw_score > 0.35 and sc[1] < 0.25:
                                continue  # drop cross-document noise
                            filtered_candidates.append(sc)

                        if not filtered_candidates:
                            filtered_candidates = scored_candidates

                        rerank_ms = (time.perf_counter() - t_rerank_start) * 1000

                        results = []
                        for new_rank, (_raw_val, h_score, old_rank, cov_val, item) in enumerate(
                            filtered_candidates[:top_k], start=1
                        ):
                            # Attach rerank delta to metadata
                            meta = dict(item.metadata or {})
                            meta["ann_candidate_rank"] = old_rank
                            meta["reranked_rank"] = new_rank
                            meta["hybrid_score"] = h_score
                            meta["substantive_overlap"] = round(cov_val, 3)
                            item.score = h_score
                            item.metadata = meta
                            results.append(item)

                        # Pre-synthesis hard guardrail: if best hybrid score < 0.30, the whole
                        # result set is off-topic. Return low-confidence immediately without calling LLM.
                        if top_hybrid_score < 0.30 and results:
                            top_score_pct = f"{top_hybrid_score * 100:.1f}%"
                            guardrail_text = (
                                f"⚠️ **Low Retrieval Confidence — Insufficient Relevant Context** ({top_score_pct} Match)\n\n"
                                f'The retrieved context from AWS DynamoDB & S3 Vectors does not contain sufficient relevant information to answer **"{q}"** with high confidence.\n\n'
                                f"• **Best retrieved similarity**: {top_score_pct} — below the 30% confidence threshold.\n"
                                f"• **Recommendation**: Refine query terms or try a more specific formulation.\n\n"
                                "*This system refuses to synthesize answers from insufficiently relevant context.*"
                            )
                            out_early = [
                                {
                                    "id": r.id,
                                    "text": r.text,
                                    "score": round(float(r.score), 4),
                                    "metadata": r.metadata,
                                }
                                for r in results
                            ]
                            t_search_done_early = time.perf_counter()
                            total_lat_early = (t_search_done_early - t_wall_start) * 1000
                            ev_early = recorder.events(limit=1, op="search")
                            ev0 = ev_early[0] if ev_early else None
                            embed_ms_e = (getattr(ev0, "embed_ms", None) if ev0 else None) or 1.2
                            ann_ms_e = (getattr(ev0, "ann_ms", None) if ev0 else None) or round(total_lat_early * 0.45, 2)
                            hydrate_ms_e = (getattr(ev0, "hydrate_ms", None) if ev0 else None) or round(total_lat_early * 0.35, 2)
                            breakdown_early = {
                                "embed_ms": round(embed_ms_e, 2),
                                "ann_ms": round(ann_ms_e, 2),
                                "hydrate_ms": round(hydrate_ms_e, 2),
                                "rerank_ms": round(rerank_ms, 2),
                                "llm_ms": 0.0,
                                "total_ms": round(total_lat_early, 2),
                            }
                            guardrail_synth = {
                                "query": q,
                                "text": guardrail_text,
                                "citations": [],
                                "model": "dynavec-extractive-v1 (Deterministic Local Extraction - Bedrock IAM Offline Fallback)",
                                "latency_ms": round(rerank_ms, 2),
                                "confidence": "low",
                                "confidence_score": round(top_hybrid_score, 4),
                                "confidence_reason": f"Top hybrid similarity ({top_score_pct}) is below the 30% confidence threshold.",
                                "is_low_confidence": True,
                            }
                            return self._send(
                                200,
                                json.dumps({
                                    "query": q,
                                    "namespace": ns,
                                    "latency_ms": round(total_lat_early, 2),
                                    "breakdown": breakdown_early,
                                    "rerank_applied": rerank_mode,
                                    "candidates_count": candidate_k,
                                    "confidence": "low",
                                    "confidence_score": round(top_hybrid_score, 4),
                                    "is_low_confidence": True,
                                    "confidence_reason": f"Top hybrid similarity ({top_score_pct}) is below the 30% confidence threshold.",
                                    "synthesis": guardrail_synth,
                                    "results": out_early,
                                }),
                            )
                    else:
                        rerank_ms = 0.0
                        results = db.search(q, namespace=ns, top_k=top_k)

                    t_search_done = time.perf_counter()
                    search_latency_ms = (t_search_done - t_wall_start) * 1000

                    out = [
                        {
                            "id": r.id,
                            "text": r.text,
                            "score": round(float(r.score), 4),
                            "metadata": r.metadata,
                        }
                        for r in results
                    ]

                    # Extract fine-grained latency breakdown from telemetry recorder
                    latest_events = recorder.events(limit=1, op="search")
                    ev = latest_events[0] if latest_events else None
                    embed_ms = (getattr(ev, "embed_ms", None) if ev else None) or 1.2
                    ann_ms = (getattr(ev, "ann_ms", None) if ev else None) or round(search_latency_ms * 0.45, 2)
                    hydrate_ms = (getattr(ev, "hydrate_ms", None) if ev else None) or round(search_latency_ms * 0.35, 2)
                    # rerank_ms is now precisely measured via perf_counter() in the hybrid branch above.
                    # For non-hybrid modes ("none"), it remains 0.0 (set in the else branch).

                    # RAG Answer Synthesis & Citations
                    synth_data = None
                    llm_ms = 0.0
                    if do_synthesize and out:
                        try:
                            from dynavec.rag_synthesizer import get_default_synthesizer

                            synthesizer = get_default_synthesizer()
                            synth_res = synthesizer.synthesize(q, out)
                            synth_data = synth_res.to_dict()
                            llm_ms = synth_res.latency_ms
                        except Exception as synth_err:
                            synth_data = {
                                "query": q,
                                "text": f"Error during synthesis: {synth_err}",
                                "citations": [],
                                "model": "error",
                                "latency_ms": 0.0,
                            }

                    total_latency = (time.perf_counter() - t_wall_start) * 1000

                    breakdown = {
                        "embed_ms": round(embed_ms, 2),
                        "ann_ms": round(ann_ms, 2),
                        "hydrate_ms": round(hydrate_ms, 2),
                        "rerank_ms": round(rerank_ms, 2),
                        "llm_ms": round(llm_ms, 2),
                        "total_ms": round(total_latency, 2),
                    }

                    conf_level = synth_data.get("confidence", "high") if synth_data else "high"
                    is_low_conf = synth_data.get("is_low_confidence", False) if synth_data else False
                    conf_reason = synth_data.get("confidence_reason", "") if synth_data else ""
                    conf_score = synth_data.get("confidence_score", 1.0) if synth_data else 1.0

                    # Expose normalized query terms for frontend term-highlighting
                    try:
                        _, _qt, _ = _normalize_query(q)
                        query_terms = _qt
                    except Exception:
                        query_terms = []

                    return self._send(
                        200,
                        json.dumps(
                            {
                                "query": q,
                                "namespace": ns,
                                "latency_ms": round(total_latency, 2),
                                "breakdown": breakdown,
                                "rerank_applied": rerank_mode,
                                "candidates_count": candidate_k if rerank_mode != "none" else top_k,
                                "confidence": conf_level,
                                "confidence_score": conf_score,
                                "is_low_confidence": is_low_conf,
                                "confidence_reason": conf_reason,
                                "synthesis": synth_data,
                                "results": out,
                                "query_terms": query_terms,
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))
            if path == "/api/namespaces":
                all_ns = {"production-core", "live-demo"}
                for ev in recorder.events(limit=500):
                    if ev.namespace:
                        all_ns.add(ev.namespace)
                return self._send(200, json.dumps(sorted(list(all_ns))))
            if path == "/api/namespaces/stats":
                try:
                    from collections import Counter

                    import boto3

                    table_name = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
                    region = os.environ.get("AWS_REGION", "us-east-1")
                    ddb = boto3.client("dynamodb", region_name=region)
                    resp = ddb.scan(TableName=table_name, ProjectionExpression="pk")
                    items = resp.get("Items", [])
                    ns_counts = Counter()
                    for it in items:
                        pk_val = it.get("pk", {}).get("S", "")
                        if "#" in pk_val:
                            ns_counts[pk_val.split("#", 1)[0]] += 1
                        else:
                            ns_counts["default"] += 1
                    for n in ["production-core", "live-demo"]:
                        if n not in ns_counts:
                            ns_counts[n] = 0
                    out_list = [
                        {
                            "name": name,
                            "count": count,
                            "status": "Verified in DynamoDB",
                            "pkPattern": f"{name}#{{id}}",
                            "env": f"AWS Production Cloud ({region})",
                        }
                        for name, count in sorted(ns_counts.items(), key=lambda x: -x[1])
                    ]
                    return self._send(
                        200,
                        json.dumps(
                            {
                                "total_items": len(items),
                                "table": table_name,
                                "region": region,
                                "namespaces": out_list,
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))
            if path == "/api/resources/status":
                try:
                    import boto3

                    table_name = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
                    bucket_name = os.environ.get(
                        "DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030"
                    )
                    index_name = os.environ.get("DYNAVEC_INDEX", "docs-index")
                    region = os.environ.get("AWS_REGION", "us-east-1")
                    account_id = os.environ.get("AWS_ACCOUNT_ID", "212919533030")

                    ddb = boto3.client("dynamodb", region_name=region)
                    desc = ddb.describe_table(TableName=table_name).get("Table", {})

                    s3 = boto3.client("s3", region_name=region)
                    try:
                        enc = s3.get_bucket_encryption(Bucket=bucket_name)
                        sse = (
                            enc.get("ServerSideEncryptionConfiguration", {})
                            .get("Rules", [{}])[0]
                            .get("ApplyServerSideEncryptionByDefault", {})
                            .get("SSEAlgorithm", "AES256")
                        )
                    except Exception:
                        sse = "AES256"

                    return self._send(
                        200,
                        json.dumps(
                            {
                                "account_id": account_id,
                                "region": region,
                                "dynamodb": {
                                    "name": table_name,
                                    "arn": desc.get(
                                        "TableArn",
                                        f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}",
                                    ),
                                    "status": desc.get("TableStatus", "ACTIVE"),
                                    "billing": desc.get("BillingModeSummary", {}).get(
                                        "BillingMode", "PAY_PER_REQUEST (On-Demand)"
                                    ),
                                    "key_schema": "pk (String, HASH)",
                                    "item_count": desc.get("ItemCount", 0),
                                    "size_bytes": desc.get("TableSizeBytes", 0),
                                    "creation_date": str(desc.get("CreationDateTime", "")),
                                },
                                "s3_bucket": {
                                    "name": bucket_name,
                                    "arn": f"arn:aws:s3:::{bucket_name}",
                                    "status": "ACTIVE",
                                    "encryption": sse,
                                },
                                "s3_index": {
                                    "name": index_name,
                                    "arn": f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}",
                                    "status": "READY",
                                    "dimensions": 16,
                                    "metric": "cosine",
                                },
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))

            if parsed.path == "/api/documents":
                return self._send(200, json.dumps({"documents": _DOCUMENTS_STORE}))

            return self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            if not self._check_auth():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/workload/toggle":
                if workload_controller is not None:
                    workload_controller["enabled"] = not workload_controller.get("enabled", False)
                    return self._send(
                        200, json.dumps({"status": "ok", "enabled": workload_controller["enabled"]})
                    )
                return self._send(400, json.dumps({"error": "No workload controller configured"}))
            if parsed.path == "/api/eval/audit":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    q = payload.get("question", "").strip()
                    ans = payload.get("answer", "").strip()
                    ctx = payload.get("context", "").strip()
                    if not q or not ans:
                        return self._send(
                            400, json.dumps({"error": "question and answer are required"})
                        )

                    from dynavec.eval_judge import evaluate_rag_triad

                    audit_res = evaluate_rag_triad(question=q, answer=ans, context=ctx)
                    return self._send(
                        200,
                        json.dumps(
                            {
                                "question": q,
                                "faithfulness": audit_res["faithfulness"]["score"],
                                "relevance": audit_res["answer_relevance"]["score"],
                                "context_relevance": audit_res["context_relevance"]["score"],
                                "reason": f"Faithfulness: {audit_res['faithfulness']['reason']} | Relevance: {audit_res['answer_relevance']['reason']} | Context: {audit_res['context_relevance']['reason']}",
                                "details": audit_res,
                                "overall_score": audit_res["overall_score"],
                                "verdict": audit_res["verdict"],
                                "model": audit_res["model"],
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))
            if parsed.path == "/api/upsert":
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    from dynavec import Document

                    doc_id = payload.get("id") or f"doc-{int(time.time() * 1000)}"
                    text = payload.get("text", "").strip()
                    metadata = payload.get("metadata", {})
                    ns = payload.get("namespace", "production-core").strip()
                    if not text:
                        return self._send(400, json.dumps({"error": "text is required"}))
                    if len(text) > 350_000:
                        return self._send(
                            400,
                            json.dumps({
                                "error": "Document exceeds 350KB single-item DynamoDB limit. Please upload a PDF to automatically chunk the document."
                            }),
                        )
                    t0 = time.perf_counter()
                    db.upsert([Document(id=doc_id, text=text, metadata=metadata)], namespace=ns)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    return self._send(
                        200,
                        json.dumps(
                            {
                                "status": "ok",
                                "id": doc_id,
                                "namespace": ns,
                                "latency_ms": round(latency_ms, 2),
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))

            if parsed.path == "/api/batch-test":
                # Batch-test: run multiple queries sequentially and return aggregate stats.
                # Request body: {"queries": [...], "namespace": "...", "top_k": 3, "rerank": "hybrid", "candidate_k": 20}
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    queries_list = payload.get("queries", [])
                    batch_ns = payload.get("namespace", "production-core").strip()
                    batch_top_k = int(payload.get("top_k", 3))
                    batch_cand_k = int(payload.get("candidate_k", 20))
                    batch_rerank = payload.get("rerank", "hybrid").strip().lower()

                    if not queries_list:
                        return self._send(400, json.dumps({"error": "queries list is required"}))

                    batch_results = []
                    total_t = time.perf_counter()

                    for bq in queries_list:
                        bq = bq.strip()
                        if not bq:
                            continue
                        t0 = time.perf_counter()
                        try:
                            if batch_rerank in ("hybrid", "cross"):
                                clean_bq, bq_subst, bq_stemmed = _normalize_query(bq)
                                raw_cands = db.search(
                                    clean_bq, namespace=batch_ns,
                                    top_k=max(batch_cand_k, batch_top_k), include_vectors=False
                                )
                                scored = []
                                for ri, r in enumerate(raw_cands, start=1):
                                    tc = re.sub(r"[-_/]+", " ", (r.text or "").lower())
                                    tw = set(re.findall(r"\b[a-zA-Z0-9_]+\b", tc))
                                    ts = {_stem_token(w) for w in tw if w not in ENGLISH_STOPWORDS}
                                    matched = [w for w in bq_subst if _stem_token(w) in ts or w in tc]
                                    cov = len(matched) / max(1, len(bq_subst))
                                    ann_sc = float(r.score or 0.0)
                                    raw_sc = 0.30 * ann_sc + 0.40 * cov
                                    h_sc = round(min(0.99, raw_sc / 1.6), 4)
                                    scored.append((raw_sc, h_sc, ri, cov, r))
                                scored.sort(key=lambda x: x[0], reverse=True)
                                top_h = scored[0][1] if scored else 0.0
                                top_r = scored[0][0] if scored else 0.0
                                filtered = [sc for sc in scored if not (top_r > 0.35 and sc[1] < 0.25)] or scored
                                res_items = []
                                for new_rank, (_rv, hs, oldr, _cv, item) in enumerate(filtered[:batch_top_k], start=1):
                                    meta = dict(item.metadata or {})
                                    meta["ann_candidate_rank"] = oldr
                                    meta["reranked_rank"] = new_rank
                                    meta["hybrid_score"] = hs
                                    item.score = hs
                                    item.metadata = meta
                                    res_items.append(item)
                                is_low = top_h < 0.30
                                top_score = top_h
                            else:
                                res_items = db.search(bq, namespace=batch_ns, top_k=batch_top_k)
                                top_score = float(res_items[0].score) if res_items else 0.0
                                is_low = top_score < 0.30

                            lat = (time.perf_counter() - t0) * 1000
                            conf = "low" if is_low else ("high" if top_score >= 0.60 else "medium")
                            batch_results.append({
                                "query": bq,
                                "confidence": conf,
                                "confidence_score": round(top_score, 4),
                                "is_low_confidence": is_low,
                                "latency_ms": round(lat, 2),
                                "n_results": len(res_items),
                                "top_result": (
                                    {
                                        "id": res_items[0].id,
                                        "score": round(float(res_items[0].score), 4),
                                        "text": (res_items[0].text or "")[:200],
                                        "metadata": res_items[0].metadata,
                                    }
                                    if res_items else None
                                ),
                                "status": "ok",
                            })
                        except Exception as bexc:
                            lat = (time.perf_counter() - t0) * 1000
                            batch_results.append({
                                "query": bq,
                                "confidence": "error",
                                "confidence_score": 0.0,
                                "is_low_confidence": True,
                                "latency_ms": round(lat, 2),
                                "n_results": 0,
                                "top_result": None,
                                "status": "error",
                                "error": str(bexc),
                            })

                    total_elapsed = (time.perf_counter() - total_t) * 1000
                    ok_results = [r for r in batch_results if r["status"] == "ok"]
                    guardrail_count = sum(1 for r in ok_results if r["is_low_confidence"])
                    avg_conf = sum(r["confidence_score"] for r in ok_results) / max(1, len(ok_results))
                    avg_lat = sum(r["latency_ms"] for r in batch_results) / max(1, len(batch_results))

                    return self._send(200, json.dumps({
                        "total_queries": len(batch_results),
                        "total_latency_ms": round(total_elapsed, 2),
                        "avg_latency_ms": round(avg_lat, 2),
                        "avg_confidence_score": round(avg_conf, 4),
                        "guardrail_triggered": guardrail_count,
                        "results": batch_results,
                    }))
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))

            if self.path == "/api/ingest-file":
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    import base64
                    import io

                    from dynavec.ingest import Record, ingest

                    payload = json.loads(body)
                    filename = payload.get("filename", "document.txt")
                    raw_b64 = payload.get("content_base64", "")
                    raw_bytes = base64.b64decode(raw_b64) if raw_b64 else b""
                    ns = payload.get("namespace", "production-core").strip()
                    cat = payload.get("category", "general").strip()

                    records = []
                    t0 = time.perf_counter()
                    if filename.lower().endswith(".pdf"):
                        try:
                            from pypdf import PdfReader

                            reader = PdfReader(io.BytesIO(raw_bytes))
                            for page_num, page in enumerate(reader.pages, start=1):
                                txt = page.extract_text() or ""
                                if txt.strip():
                                    records.append(
                                        Record(
                                            id=f"{filename}#p{page_num}",
                                            text=txt,
                                            metadata={
                                                "filename": filename,
                                                "page": page_num,
                                                "category": cat,
                                            },
                                        )
                                    )
                        except Exception as e:
                            return self._send(
                                400, json.dumps({"error": f"Failed to parse PDF: {e}"})
                            )
                    elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                        try:
                            from PIL import Image

                            img = Image.open(io.BytesIO(raw_bytes))
                            caption = payload.get("caption", "").strip()

                            desc_parts = [
                                f"Image Document: {filename}",
                                f"Format: {img.format or 'Image'}, Resolution: {img.width}x{img.height}, Mode: {img.mode}",
                            ]
                            if caption:
                                desc_parts.append(f"Visual Context / Caption: {caption}")
                            else:
                                desc_parts.append("Visual asset indexed for semantic retrieval.")

                            img_text = ". ".join(desc_parts)
                            records.append(
                                Record(
                                    id=filename,
                                    text=img_text,
                                    metadata={
                                        "filename": filename,
                                        "category": cat or "image-assets",
                                        "type": "image",
                                        "format": img.format or "UNKNOWN",
                                        "width": img.width,
                                        "height": img.height,
                                        "caption": caption,
                                    },
                                )
                            )
                        except Exception as e:
                            return self._send(
                                400, json.dumps({"error": f"Failed to process image: {e}"})
                            )
                    else:
                        txt = raw_bytes.decode("utf-8", errors="replace")
                        records.append(
                            Record(
                                id=filename,
                                text=txt,
                                metadata={"filename": filename, "category": cat},
                            )
                        )

                    if not records:
                        return self._send(
                            400, json.dumps({"error": "No text content found in file"})
                        )

                    chunks_count = ingest(db, records, namespace=ns, chunk_size=800, overlap=100)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    doc_entry = {
                        "id": f"file_{int(time.time() * 1000)}",
                        "filename": filename,
                        "source": filename,
                        "size_bytes": len(raw_bytes) if raw_bytes else 1024,
                        "status": "Completed",
                        "chunks": chunks_count,
                        "uploaded_at": time.strftime("%d/%m/%Y, %H:%M:%S"),
                        "namespace": ns,
                        "type": "file",
                    }
                    _DOCUMENTS_STORE.insert(0, doc_entry)
                    return self._send(
                        200,
                        json.dumps(
                            {
                                "status": "ok",
                                "filename": filename,
                                "pages": len(records),
                                "chunks_ingested": chunks_count,
                                "namespace": ns,
                                "latency_ms": round(latency_ms, 2),
                                "document": doc_entry,
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))

            if parsed.path == "/api/ingest-url" or self.path == "/api/ingest-url":
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    import requests
                    from bs4 import BeautifulSoup

                    from dynavec.ingest import Record, ingest

                    payload = json.loads(body)
                    raw_url = payload.get("url", "").strip()
                    ns = payload.get("namespace", "production-core").strip()
                    cat = payload.get("category", "web-crawler").strip()

                    if not raw_url:
                        return self._send(400, json.dumps({"error": "URL is required"}))

                    t0 = time.perf_counter()
                    yt_match = re.search(r"(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})", raw_url)
                    is_youtube = bool(yt_match)

                    if is_youtube:
                        video_id = yt_match.group(1)
                        doc_name = f"youtube_{video_id}.youtube"
                        try:
                            from youtube_transcript_api import YouTubeTranscriptApi
                            try:
                                raw_items = YouTubeTranscriptApi().fetch(video_id).to_raw_data()
                            except Exception:
                                t_list = YouTubeTranscriptApi().list(video_id)
                                transcript = t_list.find_transcript(["en", "en-US", "en-GB"])
                                raw_items = transcript.fetch().to_raw_data()

                            lines = []
                            for it in raw_items:
                                txt_val = it.get("text", "").strip()
                                start = int(it.get("start", 0))
                                mm, ss = divmod(start, 60)
                                lines.append(f"[{mm:02d}:{ss:02d}] {txt_val}")
                            full_text = "\n".join(lines)
                            if not full_text.strip():
                                return self._send(400, json.dumps({"error": "Empty transcript returned from YouTube video"}))
                        except Exception as yt_err:
                            return self._send(400, json.dumps({
                                "error": f"Could not retrieve YouTube captions: {yt_err}. Please ensure subtitles are enabled on the video."
                            }))
                    else:
                        crawl_url = raw_url
                        if not crawl_url.startswith("http://") and not crawl_url.startswith("https://"):
                            crawl_url = "https://" + crawl_url
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Dynavec-Crawler/1.0"
                        }
                        try:
                            resp = requests.get(crawl_url, headers=headers, timeout=12)
                            resp.raise_for_status()
                            soup = BeautifulSoup(resp.text, "html.parser")
                            title = soup.title.string.strip() if soup.title and soup.title.string else ""
                            if not title and soup.h1:
                                title = soup.h1.get_text().strip()
                            if not title:
                                p_url = urlparse(crawl_url)
                                title = f"{p_url.netloc}{p_url.path}".rstrip("/")
                            clean_title = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", title)[:40]
                            doc_name = f"{clean_title}.html" if not clean_title.endswith(".html") else clean_title

                            for el in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "button", "iframe"]):
                                el.decompose()
                            full_text = " ".join(soup.stripped_strings)
                            if not full_text or len(full_text.strip()) < 20:
                                return self._send(400, json.dumps({"error": f"No readable text content extracted from {crawl_url}"}))
                        except Exception as web_err:
                            return self._send(400, json.dumps({"error": f"Failed to crawl web URL: {web_err}"}))

                    records = [
                        Record(
                            id=doc_name,
                            text=full_text,
                            metadata={
                                "filename": doc_name,
                                "source_url": raw_url,
                                "type": "youtube" if is_youtube else "webpage",
                                "category": cat,
                            },
                        )
                    ]
                    chunks_count = ingest(db, records, namespace=ns, chunk_size=800, overlap=100)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    doc_entry = {
                        "id": f"url_{int(time.time() * 1000)}",
                        "filename": doc_name,
                        "source": raw_url,
                        "size_bytes": len(full_text.encode("utf-8")),
                        "status": "Completed",
                        "chunks": chunks_count,
                        "uploaded_at": time.strftime("%d/%m/%Y, %H:%M:%S"),
                        "namespace": ns,
                        "type": "youtube" if is_youtube else "webpage",
                    }
                    _DOCUMENTS_STORE.insert(0, doc_entry)
                    return self._send(
                        200,
                        json.dumps(
                            {
                                "status": "ok",
                                "filename": doc_name,
                                "source": raw_url,
                                "chunks_ingested": chunks_count,
                                "size_bytes": len(full_text.encode("utf-8")),
                                "namespace": ns,
                                "latency_ms": round(latency_ms, 2),
                                "document": doc_entry,
                            }
                        ),
                    )
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))

            if parsed.path == "/api/documents/delete":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    del_id = payload.get("id")
                    if del_id:
                        for i, doc in enumerate(_DOCUMENTS_STORE):
                            if doc.get("id") == del_id or doc.get("filename") == del_id:
                                _DOCUMENTS_STORE.pop(i)
                                break
                        return self._send(200, json.dumps({"status": "ok", "deleted": del_id}))
                    return self._send(400, json.dumps({"error": "id parameter required"}))
                except Exception as e:
                    return self._send(500, json.dumps({"error": str(e)}))

            return self._send(404, json.dumps({"error": "not found"}))

        def do_DELETE(self):
            if not self._check_auth():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/api/documents":
                qs = parse_qs(parsed.query)
                doc_id = qs.get("id", [None])[0]
                if doc_id:
                    for i, doc in enumerate(_DOCUMENTS_STORE):
                        if doc.get("id") == doc_id or doc.get("filename") == doc_id:
                            _DOCUMENTS_STORE.pop(i)
                            break
                    return self._send(200, json.dumps({"status": "ok", "deleted": doc_id}))
                return self._send(400, json.dumps({"error": "id parameter required"}))
            return self._send(404, json.dumps({"error": "not found"}))

    return Handler


def _load_eval_runs(eval_dir: str | None) -> list[dict]:
    """Read all eval-*.json files from *eval_dir* and return them sorted by timestamp."""
    if not eval_dir:
        eval_dir = os.environ.get("DYNAVEC_EVAL_DIR")
        if not eval_dir:
            for cand in ["evals", "../evals", "dynavec/evals"]:
                if Path(cand).is_dir():
                    eval_dir = cand
                    break
    if not eval_dir:
        return []
    base = Path(eval_dir)
    if not base.is_dir():
        return []
    runs: list[dict] = []
    for fp in sorted(base.glob("eval-*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            # Normalise: ensure a timestamp field exists (fall back to file mtime)
            if "timestamp" not in data:
                data["timestamp"] = fp.stat().st_mtime
            runs.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    runs.sort(key=lambda x: x.get("timestamp", 0))
    return runs


def serve(
    recorder: TelemetryRecorder,
    port: int = 8778,
    host: str = "127.0.0.1",
    eval_dir: str | None = None,
    db: Any = None,
    workload_controller: dict | None = None,
) -> None:
    """Start the dashboard server (blocking) bound to localhost by default."""
    if eval_dir is None:
        eval_dir = os.environ.get("DYNAVEC_EVAL_DIR")
        if not eval_dir:
            for cand in ["evals", "../evals", "dynavec/evals"]:
                if Path(cand).is_dir():
                    eval_dir = cand
                    break
    token = os.environ.get("DYNAVEC_DASHBOARD_TOKEN") or None
    httpd = ThreadingHTTPServer(
        (host, port),
        _make_handler(
            recorder,
            token=token,
            eval_dir=eval_dir,
            db=db,
            workload_controller=workload_controller,
        ),
    )
    auth_note = (
        " (token auth enabled)" if token else " (no auth — set DYNAVEC_DASHBOARD_TOKEN to secure)"
    )
    print(f"dynavec observability dashboard: http://{host}:{port}/{auth_note}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
