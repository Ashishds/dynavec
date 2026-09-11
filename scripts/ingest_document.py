"""
Dynavec Production Document Ingestion Suite.
Ingests external files (PDF, Markdown, TXT) and arXiv research papers
directly into Amazon DynamoDB and Amazon S3 Vectors.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import sys
import time
from pathlib import Path
import urllib.request

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

# Load .env
env_file = root_dir / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("\"'")
                if k not in os.environ:
                    os.environ[k] = v

from dynavec import Dynavec, DynavecConfig, SemanticCache
from dynavec.embeddings.base import Embedder
from dynavec.ingest import Record, ingest

DIM = 16


class LocalDeterministicEmbedder(Embedder):
    def __init__(self, dimension: int = DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            for i, c in enumerate(t):
                v[i % self.dimension] += (ord(c) % 17) / 17.0
            norm = math.sqrt(sum(x * x for x in v)) or 1e-9
            out.append([x / norm for x in v])
        return out


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PDFs, text files, or arXiv papers into Dynavec AWS Cloud")
    parser.add_argument("--file", type=str, help="Path to local PDF, TXT, or MD file to ingest")
    parser.add_argument("--download-arxiv", type=str, help="arXiv paper ID (e.g. 1706.03762 for 'Attention Is All You Need')")
    parser.add_argument("--namespace", type=str, default="transformer-paper", help="Target namespace partition in AWS")
    parser.add_argument("--category", type=str, default="research-paper", help="Metadata category")
    parser.add_argument("--chunk-size", type=int, default=800, help="Target chunk size in characters")
    parser.add_argument("--overlap", type=int, default=120, help="Overlap between consecutive chunks")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 65)
    print(" DYNAVEC PRODUCTION DOCUMENT & RESEARCH PAPER INGESTION ")
    print("=" * 65)

    region = os.environ.get("AWS_REGION", "us-east-1")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

    print(f"Target AWS Region  : {region}")
    print(f"Target DynamoDB    : {table}")
    print(f"Target S3 Bucket   : {bucket}")
    print(f"Target Namespace   : {args.namespace}")
    print("-" * 65)

    # Initialize live client
    cfg = DynavecConfig(
        vector_bucket=bucket,
        index=index,
        table=table,
        dimension=DIM,
        distance_metric="cosine",
        region=region,
        auto_provision=False,
    )
    db = Dynavec(
        cfg,
        embedder=LocalDeterministicEmbedder(DIM),
        cache=SemanticCache(threshold=0.9),
    )

    records: list[Record] = []
    source_name = ""

    if args.download_arxiv:
        arxiv_id = args.download_arxiv.strip()
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        print(f"[*] Downloading arXiv paper {arxiv_id} from {url}...")
        source_name = f"arxiv_{arxiv_id}.pdf"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            pdf_bytes = resp.read()
        print(f"[OK] Downloaded {len(pdf_bytes) / 1024:.1f} KB PDF.")

        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        print(f"[*] Extracting text from {len(reader.pages)} PDF pages...")
        for p_num, page in enumerate(reader.pages, start=1):
            txt = page.extract_text() or ""
            if txt.strip():
                records.append(Record(
                    id=f"{source_name}#page{p_num}",
                    text=txt,
                    metadata={"source": "arxiv", "paper_id": arxiv_id, "page": p_num, "category": args.category}
                ))

    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[FAIL] Error: File '{file_path}' does not exist.")
            sys.exit(1)
        source_name = file_path.name
        print(f"[*] Reading '{file_path}'...")
        if file_path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            print(f"[*] Extracting text from {len(reader.pages)} PDF pages...")
            for p_num, page in enumerate(reader.pages, start=1):
                txt = page.extract_text() or ""
                if txt.strip():
                    records.append(Record(
                        id=f"{source_name}#page{p_num}",
                        text=txt,
                        metadata={"source": "file", "filename": source_name, "page": p_num, "category": args.category}
                    ))
        else:
            txt = file_path.read_text(encoding="utf-8", errors="replace")
            records.append(Record(
                id=source_name,
                text=txt,
                metadata={"source": "file", "filename": source_name, "category": args.category}
            ))
    else:
        print("[FAIL] Please provide either --file <path> or --download-arxiv <arxiv_id>")
        sys.exit(1)

    print(f"[*] Found {len(records)} sections to chunk (Chunk size: {args.chunk_size}, Overlap: {args.overlap})...")
    t0 = time.perf_counter()
    chunks_ingested = ingest(db, records, namespace=args.namespace, chunk_size=args.chunk_size, overlap=args.overlap)
    total_time = (time.perf_counter() - t0) * 1000

    print("-" * 65)
    print(f"[SUCCESS] Ingested {chunks_ingested} chunks into AWS DynamoDB & S3 Vectors!")
    print(f"          Total Ingestion Time: {total_time:.1f} ms ({total_time / max(1, chunks_ingested):.1f} ms / chunk)")
    print("=" * 65)
    print(f"\nYou can now query this paper in the UI Search Playground at:")
    print(f"  http://localhost:3000/")
    print(f"  Select Target Partition: '{args.namespace}'")


if __name__ == "__main__":
    main()
