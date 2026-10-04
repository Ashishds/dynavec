"""Delete old S3 Vectors index and create a new one with updated dimensions.

Run this whenever you change the embedding model (which changes output dimension).
This deletes all ANN vectors; DynamoDB documents are preserved.

Usage:
    python examples/reprovision_index.py --dim 384
"""
import os, sys, time, argparse
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())

import boto3

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dim", type=int, default=384)
    parser.add_argument("--metric", default="cosine")
    args = parser.parse_args()

    BUCKET = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    INDEX  = os.environ.get("DYNAVEC_INDEX", "docs-index")
    REGION = os.environ.get("AWS_REGION", "us-east-1")

    print(f"Bucket:  {BUCKET}")
    print(f"Index:   {INDEX}")
    print(f"Region:  {REGION}")
    print(f"New Dim: {args.dim} ({args.metric})")

    client = boto3.client("s3vectors", region_name=REGION)

    # 1. Check existing index
    try:
        info = client.get_index(vectorBucketName=BUCKET, indexName=INDEX)
        idx = info.get("index", {})
        print(f"\nCurrent index: dim={idx.get('dimension')}, metric={idx.get('distanceMetric')}")
        if idx.get("dimension") == args.dim:
            print(f"Index already has dim={args.dim}. No re-provisioning needed.")
            sys.exit(0)
    except Exception as e:
        print(f"\nNo existing index found ({e}). Creating fresh.")

    # 2. Delete old index
    try:
        client.delete_index(vectorBucketName=BUCKET, indexName=INDEX)
        print("\nDeleted old index.")
        for _ in range(30):
            try:
                client.get_index(vectorBucketName=BUCKET, indexName=INDEX)
                print("  Waiting for deletion...")
                time.sleep(2)
            except Exception:
                print("  Index deleted confirmed.")
                break
    except Exception as e:
        print(f"\nDelete note: {e}")

    # 3. Create new index
    print(f"\nCreating new {args.dim}-dim index '{INDEX}'...")
    result = client.create_index(
        vectorBucketName=BUCKET,
        indexName=INDEX,
        dataType="float32",
        dimension=args.dim,
        distanceMetric=args.metric,
    )
    arn = result.get("indexArn", "N/A")
    print(f"Created. ARN: {arn}")
    print(f"\nNow run: python examples/ingest_attention_paper.py")

if __name__ == "__main__":
    main()
