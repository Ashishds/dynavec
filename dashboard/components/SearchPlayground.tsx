"use client";

import React, { useEffect, useRef, useState } from "react";
import { searchKnowledgeBase, upsertDocument, getNamespacesList, type SearchItem } from "@/lib/api";

const SUGGESTED_QUERIES = [
  "What is the formula for scaled dot-product attention?",
  "How does DynamoDB achieve single-digit millisecond latency?",
  "Why is self-attention faster than recurrent layers?",
  "Serverless vector database cost savings and infrastructure",
  "Vector memory compression accuracy and quantization",
];

export default function SearchPlayground() {
  const [query, setQuery] = useState("");
  const [namespace, setNamespace] = useState("production-core");
  const [topK, setTopK] = useState(3);
  const [namespaces, setNamespaces] = useState<string[]>(["production-core", "live-demo"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchItem[]>([]);
  const [latency, setLatency] = useState<number | null>(null);
  const [searchedQuery, setSearchedQuery] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Ingestion form state
  const [showIngest, setShowIngest] = useState(false);
  const [ingestMode, setIngestMode] = useState<"file" | "text">("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [ingestId, setIngestId] = useState("");
  const [ingestText, setIngestText] = useState("");
  const [ingestTopic, setIngestTopic] = useState("research");
  const [ingesting, setIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getNamespacesList().then(setNamespaces);
  }, []);

  const handleSearch = async (e?: React.FormEvent, customQ?: string) => {
    if (e) e.preventDefault();
    const q = customQ ?? query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await searchKnowledgeBase(q.trim(), namespace, topK);
      setResults(res.results);
      setLatency(res.latency_ms);
      setSearchedQuery(q.trim());
    } catch (err: any) {
      setError(err.message || "Search failed. Ensure backend API is active.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setIngestError(null);
    setIngestSuccess(null);
    setIngestId(file.name.replace(/\.[^/.]+$/, ""));

    if (file.name.endsWith(".txt") || file.name.endsWith(".md") || file.name.endsWith(".json")) {
      file.text().then((txt) => setIngestText(txt));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleIngestFile = async () => {
    if (!selectedFile) {
      setIngestError("Please select or drop a file first.");
      return;
    }

    setIngesting(true);
    setIngestError(null);
    setIngestSuccess(null);

    const apiBase = process.env.NEXT_PUBLIC_DYNAVEC_API || "http://127.0.0.1:8779";

    if (selectedFile.name.endsWith(".pdf")) {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).split(",")[1];
        try {
          const res = await fetch(`${apiBase}/api/ingest-file`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: selectedFile.name,
              content_base64: base64,
              namespace,
              category: ingestTopic || "pdf-research",
            }),
          });
          const data = await res.json();
          if (res.ok) {
            setIngestSuccess(
              `✓ Successfully parsed PDF! Ingested ${data.chunks_ingested} chunks across ${data.pages} pages into AWS DynamoDB & S3 (${data.latency_ms} ms)`
            );
            setSelectedFile(null);
          } else {
            setIngestError(data.error || "Failed to parse and ingest PDF.");
          }
        } catch (err: any) {
          setIngestError(err.message || "Failed to upload file.");
        } finally {
          setIngesting(false);
        }
      };
      reader.readAsDataURL(selectedFile);
    } else {
      try {
        const text = await selectedFile.text();
        const res = await upsertDocument(
          text,
          namespace,
          ingestId.trim() || selectedFile.name,
          { topic: ingestTopic || "file-upload", filename: selectedFile.name, timestamp: Date.now() }
        );
        setIngestSuccess(`✓ Ingested file "${selectedFile.name}" into AWS Cloud! ID: ${res.id} (${res.latency_ms} ms)`);
        setSelectedFile(null);
      } catch (err: any) {
        setIngestError(err.message || "Failed to ingest file.");
      } finally {
        setIngesting(false);
      }
    }
  };

  const handleIngestText = async () => {
    if (!ingestText.trim()) {
      setIngestError("Please paste or type document text into the box before ingesting.");
      return;
    }

    setIngesting(true);
    setIngestError(null);
    setIngestSuccess(null);

    try {
      const res = await upsertDocument(
        ingestText.trim(),
        namespace,
        ingestId.trim() || undefined,
        { topic: ingestTopic || "general", source: "playground-ui", timestamp: Date.now() }
      );
      setIngestSuccess(`✓ Successfully written into AWS DynamoDB & S3! Item ID: ${res.id} (${res.latency_ms} ms)`);
      setIngestId("");
      setIngestText("");
    } catch (err: any) {
      setIngestError(err.message || "Failed to ingest document into AWS.");
    } finally {
      setIngesting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-mono tracking-tight">Interactive Query &amp; RAG Playground</h2>
          <p className="text-sm text-muted">
            Direct end-user semantic search over AWS DynamoDB document text and Amazon S3 Vectors
          </p>
        </div>
        <button
          onClick={() => setShowIngest(!showIngest)}
          className={`font-mono text-xs px-3.5 py-1.5 border rounded-lg transition-colors flex items-center gap-1.5 self-start sm:self-auto cursor-pointer ${
            showIngest
              ? "bg-line/40 text-ink border-line"
              : "bg-accent-soft text-accent-ink border-accent/40 hover:bg-accent-soft/80 font-semibold"
          }`}
        >
          <span>{showIngest ? "× Close Ingestion" : "+ Ingest Document"}</span>
        </button>
      </div>

      {/* Modern Ingestion Panel */}
      {showIngest && (
        <div className="bg-surface border border-accent/30 rounded-xl2 p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
            <div>
              <h3 className="text-sm font-bold font-mono text-ink">Enterprise Document Ingestion</h3>
              <p className="text-xs text-muted">Upload multi-page research papers, docs, or paste raw text</p>
            </div>

            {/* Segmented Mode Tabs */}
            <div className="flex bg-bg border border-line rounded-lg p-0.5 font-mono text-xs self-start sm:self-auto">
              <button
                type="button"
                onClick={() => {
                  setIngestMode("file");
                  setIngestError(null);
                  setIngestSuccess(null);
                }}
                className={`px-3 py-1 rounded-md transition-colors ${
                  ingestMode === "file" ? "bg-accent text-white font-semibold shadow-sm" : "text-muted hover:text-ink"
                }`}
              >
                📁 Upload Document
              </button>
              <button
                type="button"
                onClick={() => {
                  setIngestMode("text");
                  setIngestError(null);
                  setIngestSuccess(null);
                }}
                className={`px-3 py-1 rounded-md transition-colors ${
                  ingestMode === "text" ? "bg-accent text-white font-semibold shadow-sm" : "text-muted hover:text-ink"
                }`}
              >
                ✍️ Raw Text Snippet
              </button>
            </div>
          </div>

          {/* TAB 1: Modern File Upload Dropzone */}
          {ingestMode === "file" && (
            <div className="space-y-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md,.json"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileSelect(e.target.files[0]);
                  }
                }}
              />

              {!selectedFile ? (
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    isDragging
                      ? "border-accent bg-accent-soft/30 scale-[0.99]"
                      : "border-line hover:border-accent/60 bg-bg/50 hover:bg-bg"
                  }`}
                >
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div className="w-12 h-12 rounded-full bg-accent-soft text-accent-ink flex items-center justify-center text-xl">
                      ☁️
                    </div>
                    <div>
                      <p className="text-sm font-bold text-ink">
                        Drag &amp; drop your document here, or <span className="text-accent underline">browse</span>
                      </p>
                      <p className="text-xs text-muted font-mono mt-1">
                        Supports <span className="text-ink font-semibold">.pdf</span>,{" "}
                        <span className="text-ink font-semibold">.txt</span>,{" "}
                        <span className="text-ink font-semibold">.md</span>,{" "}
                        <span className="text-ink font-semibold">.json</span> (Multi-page auto-chunking)
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-bg border border-line rounded-xl p-4 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-accent-soft text-accent-ink flex items-center justify-center text-lg shrink-0">
                      📄
                    </div>
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-bold text-ink truncate">{selectedFile.name}</p>
                      <p className="font-mono text-[11px] text-faint">
                        {formatFileSize(selectedFile.size)} • Ready for automated sliding-window vectorization
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="font-mono text-xs text-faint hover:text-err px-2 py-1 rounded hover:bg-line/40 transition-colors"
                  >
                    × Remove
                  </button>
                </div>
              )}

              {/* Ingestion Settings Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div>
                  <label className="block font-mono text-[10.5px] text-faint uppercase mb-1">Target Partition</label>
                  <div className="font-mono text-xs px-3 py-2 bg-bg border border-line rounded-lg text-ink">
                    {namespace}
                  </div>
                </div>
                <div>
                  <label className="block font-mono text-[10.5px] text-faint uppercase mb-1">Category / Domain</label>
                  <input
                    type="text"
                    placeholder="e.g. ai-research, cloud, devops"
                    value={ingestTopic}
                    onChange={(e) => setIngestTopic(e.target.value)}
                    className="w-full font-mono text-xs px-3 py-2 bg-bg border border-line rounded-lg text-ink"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10.5px] text-faint uppercase mb-1">Chunk Strategy</label>
                  <div className="font-mono text-xs px-3 py-2 bg-bg border border-line rounded-lg text-faint">
                    Sliding 800c / 120 overlap
                  </div>
                </div>
              </div>

              {ingestError && (
                <div className="p-3 bg-err/10 border border-err/30 rounded-lg text-xs font-mono text-err">
                  ⚠️ {ingestError}
                </div>
              )}
              {ingestSuccess && (
                <div className="p-3 bg-ok/10 border border-ok/30 rounded-lg text-xs font-mono text-ok">
                  {ingestSuccess}
                </div>
              )}

              <div className="flex items-center justify-end pt-2">
                <button
                  type="button"
                  onClick={handleIngestFile}
                  disabled={ingesting || !selectedFile}
                  className="font-mono text-xs px-5 py-2.5 bg-accent text-white font-semibold rounded-lg hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40 flex items-center gap-2"
                >
                  {ingesting && <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                  <span>{ingesting ? "Extracting & Ingesting to AWS..." : "Ingest Document to AWS Cloud"}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: Clean Raw Text Editor */}
          {ingestMode === "text" && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Document ID (optional, e.g. doc-cloud-custom-01)"
                  value={ingestId}
                  onChange={(e) => setIngestId(e.target.value)}
                  className="font-mono text-xs px-3 py-2 bg-bg border border-line rounded-lg text-ink"
                />
                <input
                  type="text"
                  placeholder="Topic / Category (e.g. cloud, ai, notes)"
                  value={ingestTopic}
                  onChange={(e) => setIngestTopic(e.target.value)}
                  className="font-mono text-xs px-3 py-2 bg-bg border border-line rounded-lg text-ink"
                />
              </div>

              <textarea
                rows={4}
                placeholder="Type or paste document text to embed and hydrate into DynamoDB..."
                value={ingestText}
                onChange={(e) => setIngestText(e.target.value)}
                className="w-full font-mono text-xs p-3 bg-bg border border-line rounded-lg text-ink leading-relaxed"
              />

              {ingestError && (
                <div className="p-3 bg-err/10 border border-err/30 rounded-lg text-xs font-mono text-err">
                  ⚠️ {ingestError}
                </div>
              )}
              {ingestSuccess && (
                <div className="p-3 bg-ok/10 border border-ok/30 rounded-lg text-xs font-mono text-ok">
                  {ingestSuccess}
                </div>
              )}

              <div className="flex items-center justify-end pt-2">
                <button
                  type="button"
                  onClick={handleIngestText}
                  disabled={ingesting || !ingestText.trim()}
                  className="font-mono text-xs px-5 py-2.5 bg-accent text-white font-semibold rounded-lg hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40 flex items-center gap-2"
                >
                  {ingesting && <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                  <span>{ingesting ? "Writing to DynamoDB & S3..." : "Ingest Snippet to AWS Cloud"}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Search Input Bar */}
      <form onSubmit={(e) => handleSearch(e)} className="bg-surface border border-line rounded-xl2 p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Namespace Selector */}
          <div className="w-full md:w-56 shrink-0">
            <label className="block font-mono text-[11px] text-faint uppercase mb-1">Target Partition</label>
            <select
              value={namespace}
              onChange={(e) => setNamespace(e.target.value)}
              className="w-full font-mono text-xs border border-line rounded-lg px-3 py-2.5 bg-bg text-ink cursor-pointer"
            >
              {namespaces.map((ns) => (
                <option key={ns} value={ns}>{ns}</option>
              ))}
            </select>
          </div>

          {/* Search Query Input */}
          <div className="flex-1">
            <label className="block font-mono text-[11px] text-faint uppercase mb-1">Semantic Search Query</label>
            <div className="relative flex items-center">
              <input
                type="text"
                placeholder="Ask any natural language question or search prompt..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full font-mono text-xs border border-line rounded-lg pl-3.5 pr-28 py-2.5 bg-bg text-ink focus:outline-none focus:border-accent"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-1 px-3.5 py-1.5 bg-accent text-white rounded-md font-mono text-xs font-semibold hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40 flex items-center gap-1.5"
              >
                {loading && <span className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                <span>{loading ? "Searching..." : "Search →"}</span>
              </button>
            </div>
          </div>

          {/* Top-K Results */}
          <div className="w-28 shrink-0">
            <label className="block font-mono text-[11px] text-faint uppercase mb-1">Top-K Docs</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full font-mono text-xs border border-line rounded-lg px-3 py-2.5 bg-bg text-ink cursor-pointer"
            >
              {[1, 2, 3, 5, 8].map((k) => (
                <option key={k} value={k}>{k} results</option>
              ))}
            </select>
          </div>
        </div>

        {/* Suggested Queries Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[11px]">
          <span className="text-faint">Suggestions:</span>
          {SUGGESTED_QUERIES.map((sq) => (
            <button
              key={sq}
              type="button"
              onClick={() => {
                setQuery(sq);
                handleSearch(undefined, sq);
              }}
              className="px-2.5 py-1 bg-bg hover:bg-line/40 border border-line rounded-full text-muted hover:text-ink transition-colors cursor-pointer"
            >
              {sq}
            </button>
          ))}
        </div>
      </form>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-err/10 border border-err/30 rounded-xl font-mono text-xs text-err">
          {error}
        </div>
      )}

      {/* Search Results Area */}
      {searchedQuery && (
        <div className="space-y-4">
          {/* Metadata Bar */}
          <div className="flex items-center justify-between px-2 font-mono text-xs text-muted">
            <div>
              <span>Retrieved </span>
              <strong className="text-ink">{results.length} documents</strong>
              <span> for &ldquo;{searchedQuery}&rdquo;</span>
            </div>
            {latency !== null && (
              <span className={`px-2.5 py-0.5 rounded-full border ${latency < 10 ? "bg-ok/10 text-ok border-ok/30 font-semibold" : "bg-bg text-muted border-line"}`}>
                Latency: {latency} ms {latency < 10 ? "(Sub-ms Warm Cache Hit)" : "(AWS Roundtrip)"}
              </span>
            )}
          </div>

          {/* AI Grounded Synthesis / Answer Card */}
          {results.length > 0 && (
            <div className="bg-surface border border-accent/30 rounded-xl2 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                  <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-accent">
                    Grounded Synthesis (RAG Context)
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => handleCopyText(results[0].text)}
                  className="font-mono text-[11px] px-2.5 py-1 rounded bg-bg hover:bg-line/40 border border-line text-muted hover:text-ink transition-colors cursor-pointer flex items-center gap-1"
                >
                  <span>{copied ? "✓ Copied!" : "📋 Copy Context"}</span>
                </button>
              </div>
              <p className="text-sm text-ink leading-relaxed font-sans bg-bg/40 p-3.5 rounded-lg border border-line/40">
                {results[0].text}
              </p>
              <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-faint pt-1 gap-2">
                <span>
                  Source: Primary matching document from DynamoDB partition key <code className="text-accent font-semibold">{namespace}#{results[0].id}</code>
                </span>
                {results[0].metadata?.page && (
                  <span className="px-2 py-0.5 bg-accent-soft text-accent-ink rounded font-semibold border border-accent/20">
                    📄 Page {results[0].metadata.page}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Retrieved Document Cards */}
          <div className="space-y-3">
            {results.map((r, i) => (
              <div
                key={r.id || i}
                className="bg-surface border border-line rounded-xl2 p-4 hover:border-accent/40 transition-colors space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-6 h-6 rounded-full bg-accent-soft text-accent-ink font-mono font-bold text-xs flex items-center justify-center shrink-0">
                      #{i + 1}
                    </span>
                    <span className="font-mono text-xs font-bold text-ink truncate">{r.id}</span>
                    {r.metadata?.page && (
                      <span className="px-2 py-0.5 bg-accent-soft/80 text-accent-ink font-mono text-[10.5px] rounded font-semibold border border-accent/20 shrink-0">
                        📄 Page {r.metadata.page}
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-xs px-2.5 py-0.5 bg-ok/10 text-ok border border-ok/30 rounded font-semibold shrink-0">
                    {(r.score * 100).toFixed(1)}% Match
                  </span>
                </div>

                <p className="text-xs text-muted leading-relaxed font-sans bg-bg/50 p-3 rounded-lg border border-line/60">
                  {r.text}
                </p>

                {r.metadata && Object.keys(r.metadata).length > 0 && (
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 font-mono text-[10.5px]">
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(r.metadata).map(([k, v]) => (
                        <span key={k} className="px-2 py-0.5 bg-line/40 rounded text-muted">
                          <b className="text-faint">{k}:</b> {String(v)}
                        </span>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopyText(r.text)}
                      className="text-faint hover:text-ink px-2 py-0.5 rounded hover:bg-line/40 transition-colors cursor-pointer"
                    >
                      Copy
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
