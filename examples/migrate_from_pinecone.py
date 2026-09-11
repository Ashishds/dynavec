"""Migrate vectors, metadata, and namespaces from Pinecone to dynavec.

Prerequisites
-------------
    pip install pinecone dynavec[sentence-transformers]

Usage
-----
    export PINECONE_API_KEY="pcsk_..."
    export AWS_REGION="us-east-1"
    python examples/migrate_from_pinecone.py
"""

from __future__ import annotations

import os

from dynavec import Dynavec, DynavecConfig
from dynavec.migration import PineconeMigrator


def main() -> None:
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")
    if not pinecone_api_key:
        print("Please set PINECONE_API_KEY before running this example.")
        return

    pinecone_index_name = os.environ.get("PINECONE_INDEX_NAME", "my-pinecone-index")

    # Target Dynavec configuration
    cfg = DynavecConfig(
        vector_bucket="dynavec-migration-demo",
        index="prod-vectors",
        table="dynavec_prod",
        dimension=1536,  # match Pinecone index dimension
        region=os.environ.get("AWS_REGION", "us-east-1"),
        auto_provision=True,
    )
    dynavec_db = Dynavec(cfg)

    print(f"Connecting to Pinecone index: {pinecone_index_name}...")
    migrator = PineconeMigrator(api_key=pinecone_api_key, index_name=pinecone_index_name)

    # Inspect source index
    stats = migrator.get_stats()
    print(f"Source index stats: {stats.get('total_vector_count', 0)} total vectors across "
          f"{len(stats.get('namespaces', {}))} namespace(s)")

    def progress(count: int, total: int | None) -> None:
        total_str = str(total) if total else "unknown"
        print(f"  [Progress] Migrated {count}/{total_str} vectors...")

    # Optional metadata transformation: tag source and clean up keys
    def transform_meta(meta: dict) -> dict:
        meta["migrated_from"] = "pinecone"
        return meta

    # Run migration
    print("\nStarting migration...")
    report = migrator.migrate(
        dynavec=dynavec_db,
        namespace="",  # default namespace
        target_namespace="default",
        batch_size=100,
        text_key="text",
        metadata_transform=transform_meta,
        progress_callback=progress,
    )

    print("\n--- Migration Complete ---")
    print(f"Status:    {'Success' if report.is_complete else 'Partial/Failed'}")
    print(f"Migrated:  {report.migrated} vectors")
    print(f"Failed:    {report.failed} vectors")
    print(f"Duration:  {report.duration_sec:.2f} seconds")

    if report.resume_token:
        print(f"Resume Token for next run: {report.resume_token}")


if __name__ == "__main__":
    main()
