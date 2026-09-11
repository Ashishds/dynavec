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
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
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


def _make_handler(
    recorder: TelemetryRecorder,
    token: str | None = None,
    eval_dir: str | None = None,
    db: Any = None,
):
    """Create a request handler class with optional Bearer-token auth and live query routes."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            # Security: prevent browser from sniffing content types
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
            if path == "/api/eval":
                return self._send(200, json.dumps(_load_eval_runs(eval_dir)))
            if path == "/api/search":
                q = qs.get("q", [""])[0].strip()
                ns = qs.get("namespace", ["production-core"])[0].strip()
                top_k = int(qs.get("top_k", ["3"])[0])
                if not q:
                    return self._send(400, json.dumps({"error": "query parameter 'q' is required"}))
                if not db:
                    return self._send(503, json.dumps({"error": "Dynavec client not attached"}))
                try:
                    t0 = time.perf_counter()
                    results = db.search(q, namespace=ns, top_k=top_k)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    out = [
                        {
                            "id": r.id,
                            "text": r.text,
                            "score": round(float(r.score), 4),
                            "metadata": r.metadata,
                        }
                        for r in results
                    ]
                    return self._send(200, json.dumps({"query": q, "namespace": ns, "latency_ms": round(latency_ms, 2), "results": out}))
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))
            if path == "/api/namespaces":
                all_ns = {"production-core", "live-demo"}
                for ev in recorder.events(limit=500):
                    if ev.namespace:
                        all_ns.add(ev.namespace)
                return self._send(200, json.dumps(sorted(list(all_ns))))
            return self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            if not self._check_auth():
                return
            parsed = urlparse(self.path)
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
                    t0 = time.perf_counter()
                    db.upsert([Document(id=doc_id, text=text, metadata=metadata)], namespace=ns)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    return self._send(200, json.dumps({"status": "ok", "id": doc_id, "namespace": ns, "latency_ms": round(latency_ms, 2)}))
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
                                    records.append(Record(
                                        id=f"{filename}#p{page_num}",
                                        text=txt,
                                        metadata={"filename": filename, "page": page_num, "category": cat}
                                    ))
                        except Exception as e:
                            return self._send(400, json.dumps({"error": f"Failed to parse PDF: {e}"}))
                    else:
                        txt = raw_bytes.decode("utf-8", errors="replace")
                        records.append(Record(id=filename, text=txt, metadata={"filename": filename, "category": cat}))

                    if not records:
                        return self._send(400, json.dumps({"error": "No text content found in file"}))

                    chunks_count = ingest(db, records, namespace=ns, chunk_size=800, overlap=100)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    return self._send(200, json.dumps({
                        "status": "ok",
                        "filename": filename,
                        "pages": len(records),
                        "chunks_ingested": chunks_count,
                        "namespace": ns,
                        "latency_ms": round(latency_ms, 2)
                    }))
                except Exception as exc:
                    return self._send(500, json.dumps({"error": str(exc)}))
            return self._send(404, json.dumps({"error": "not found"}))

    return Handler


def _load_eval_runs(eval_dir: str | None) -> list[dict]:
    """Read all eval-*.json files from *eval_dir* and return them sorted by timestamp."""
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
    return runs


def serve(
    recorder: TelemetryRecorder,
    port: int = 8778,
    host: str = "127.0.0.1",
    eval_dir: str | None = None,
    db: Any = None,
) -> None:
    """Start the dashboard server (blocking) bound to localhost by default."""
    token = os.environ.get("DYNAVEC_DASHBOARD_TOKEN") or None
    httpd = HTTPServer(
        (host, port), _make_handler(recorder, token=token, eval_dir=eval_dir, db=db)
    )
    auth_note = " (token auth enabled)" if token else " (no auth — set DYNAVEC_DASHBOARD_TOKEN to secure)"
    print(f"dynavec observability dashboard: http://{host}:{port}/{auth_note}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()

