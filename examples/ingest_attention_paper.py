"""Ingest the 'Attention Is All You Need' PDF into AWS DynamoDB + S3 Vectors.

Uses the production-grade SentenceTransformersEmbedder (all-MiniLM-L6-v2, 384-dim)
for proper semantic search quality. Re-provisions the S3 Vector index to 384 dimensions
if it currently exists with different dimensions.

Usage:
    python examples/ingest_attention_paper.py [--pdf-path <path>] [--namespace production-core]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from pathlib import Path

# Load .env
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from dynavec import Document, Dynavec, DynavecConfig
from dynavec.embeddings.base import Embedder
from dynavec.embeddings.openai import OpenAIEmbedder

DIM = 384  # Matches S3 Vectors index dimension
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_ST_MODEL = "all-MiniLM-L6-v2"


class ProductionSentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = DEFAULT_ST_MODEL) -> None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
        print(f"  Loading SentenceTransformer model: {model_name} ...")
        self._st = SentenceTransformer(model_name)
        self.dimension = self._st.get_embedding_dimension() if hasattr(self._st, "get_embedding_dimension") else self._st.get_sentence_embedding_dimension()
        print(f"  Model loaded. Embedding dimension: {self.dimension}")

    def embed_documents(self, texts):
        arr = self._st.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10,
        )
        return arr.tolist()


def extract_pages(pdf_path):
    print(f"\n Extracting text from: {pdf_path}")
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        text = text.strip()
        if len(text) < 50:
            continue
        section_match = re.search(r"^(\d+(?:\.\d+)*)\s+([A-Z][^\n]+)", text, re.MULTILINE)
        section = section_match.group(0).strip()[:80] if section_match else f"Page {page_num}"
        word_count = len(re.findall(r"\b\w+\b", text))
        pages.append({"page": page_num, "section": section, "text": text, "word_count": word_count})
        print(f"  Page {page_num}: {word_count} words | Section: {section[:50]}")
    doc.close()
    print(f"\n Extracted {len(pages)} pages with content.")
    return pages


def chunk_page(page_data, chunk_size=500, overlap=100):
    text = page_data["text"]
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    idx = 0
    chunk_num = 0
    while idx < len(words):
        chunk_words = words[idx : idx + chunk_size]
        chunk_text = " ".join(chunk_words).strip()
        if len(chunk_text) >= 80:
            chunks.append({"chunk_num": chunk_num, "text": chunk_text, "page": page_data["page"], "section": page_data["section"], "word_count": len(chunk_words)})
            chunk_num += 1
        idx += step
    return chunks


def ingest_pdf(pdf_path, namespace="production-core", chunk_size=500, overlap=100, provider=None, model=None):
    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")
    filename = Path(pdf_path).name

    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    if provider is None:
        provider = "openai" if has_openai else "sentence-transformers"

    if provider == "openai":
        model_name = model or DEFAULT_OPENAI_MODEL
        print(f"\n Instantiating Enterprise OpenAI Embedder: {model_name} (384-dim Matryoshka) ...")
        embedder = OpenAIEmbedder(model=model_name, dimension=DIM)
    else:
        model_name = model or DEFAULT_ST_MODEL
        print(f"\n Instantiating SentenceTransformer Embedder: {model_name} ({DIM}-dim) ...")
        embedder = ProductionSentenceTransformerEmbedder(model_name)

    print("\n" + "="*60)
    print(" Dynavec Semantic PDF Ingestion")
    print(f" PDF:       {pdf_path}")
    print(f" Provider:  {provider} ({model_name}, {DIM}-dim)")
    print(f" AWS:       {region} / {bucket} / {table}")
    print(f" Namespace: {namespace}")
    print("="*60)

    cfg = DynavecConfig(vector_bucket=bucket, index=index, table=table, dimension=DIM, distance_metric="cosine", region=region, auto_provision=True)
    print("\n Connecting to AWS DynamoDB + S3 Vectors ...")
    db = Dynavec(cfg, embedder=embedder)
    print(" Connected.")

    pages = extract_pages(pdf_path)
    if not pages:
        print(" No text extracted. Aborting.")
        return

    print("\n Chunking pages ...")
    all_chunks = []
    for page_data in pages:
        all_chunks.extend(chunk_page(page_data, chunk_size=chunk_size, overlap=overlap))
    print(f"   Total chunks: {len(all_chunks)}")

    documents = []
    for ch in all_chunks:
        doc_id = f"{filename}#p{ch['page']}#c{ch['chunk_num']}"
        documents.append(Document(id=doc_id, text=ch["text"], metadata={"filename": filename, "page": ch["page"], "section": ch["section"], "word_count": ch["word_count"], "chunk_num": ch["chunk_num"], "model": model_name, "dim": DIM, "namespace": namespace}))

    BATCH_SIZE = 25
    n_batches = math.ceil(len(documents) / BATCH_SIZE)
    total_upserted = 0
    print(f"\n Upserting {len(documents)} chunks in {n_batches} batches ...")
    for i in range(n_batches):
        batch = documents[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        db.upsert(batch, namespace=namespace)
        total_upserted += len(batch)
        print(f"   Batch {i+1}/{n_batches} -- {total_upserted}/{len(documents)} chunks")

    print(f"\n DONE! Ingested {total_upserted} chunks from '{filename}' into namespace '{namespace}'.")
    print(f"   Embedder: {model_name} ({DIM}-dim cosine)")

    print("\n Verification query: 'multi-head attention mechanism' ...")
    results = db.search("multi-head attention mechanism", namespace=namespace, top_k=3)
    if results:
        print(f"   Top result: Page {results[0].metadata.get('page')} | Score: {results[0].score:.4f}")
        for r in results:
            print(f"     - [Page {r.metadata.get('page')}] (Score: {r.score:.4f}): {r.text[:90]}...")
    else:
        print("   No results returned. Check index provisioning.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-path", default=str(Path(__file__).resolve().parent.parent.parent / "1706.03762v7 (3).pdf"))
    parser.add_argument("--namespace", default="production-core")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--provider", choices=["openai", "sentence-transformers"], default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    if not Path(args.pdf_path).exists():
        print(f" PDF not found: {args.pdf_path}")
        sys.exit(1)
    ingest_pdf(
        pdf_path=args.pdf_path,
        namespace=args.namespace,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        provider=args.provider,
        model=args.model,
    )


if __name__ == "__main__":
    main()
