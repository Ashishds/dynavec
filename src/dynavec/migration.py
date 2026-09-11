"""Migration tools: seamlessly migrate from Pinecone to dynavec.

Enables zero-downtime, batched migration of vectors and metadata from Pinecone
into dynavec. Supports:
- Namespaced migration and namespace remapping
- Automatic text extraction from vector metadata
- Custom metadata transformation and ID transformation callbacks
- Resumable migrations via pagination tokens
- Progress reporting callbacks
- Multi-namespace automated discovery via ``describe_index_stats()``

Example::

    from dynavec import Dynavec, DynavecConfig
    from dynavec.migration import PineconeMigrator

    dynavec_client = Dynavec(DynavecConfig(
        vector_bucket="my-vectors",
        index="prod-index",
        table="dynavec_prod",
        dimension=1536,
    ))

    migrator = PineconeMigrator(api_key="...", index_name="my-pinecone-index")
    report = migrator.migrate(
        dynavec_client,
        namespace="wiki",
        target_namespace="wiki-v2",
        batch_size=100,
        progress_callback=lambda count, total: print(f"Migrated {count}/{total}"),
    )
    print(report.to_dict())
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from .client import Dynavec
from .models import Document

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Summary of a completed or partial migration operation."""

    source_index: str
    source_namespace: str
    target_namespace: str
    total_found: int = 0
    migrated: int = 0
    failed: int = 0
    duration_sec: float = 0.0
    errors: list[str] = field(default_factory=list)
    resume_token: str | None = None

    @property
    def is_complete(self) -> bool:
        """True if all discovered vectors were successfully migrated without interruption."""
        return self.resume_token is None and self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_index": self.source_index,
            "source_namespace": self.source_namespace,
            "target_namespace": self.target_namespace,
            "total_found": self.total_found,
            "migrated": self.migrated,
            "failed": self.failed,
            "duration_sec": round(self.duration_sec, 2),
            "is_complete": self.is_complete,
            "resume_token": self.resume_token,
            "error_count": len(self.errors),
        }


class PineconeMigrator:
    """Migrate vectors, embeddings, and metadata from Pinecone to dynavec.

    Parameters
    ----------
    index:
        Pre-instantiated Pinecone Index instance or mock object.
    api_key:
        Pinecone API key. If not provided, reads from ``PINECONE_API_KEY`` env var.
    index_name:
        Name of the Pinecone index to connect to.
    host:
        Direct host URL for the Pinecone index (optional).
    """

    def __init__(
        self,
        index: Any = None,
        api_key: str | None = None,
        index_name: str | None = None,
        host: str | None = None,
    ) -> None:
        if index is not None:
            self._index = index
            self._index_name = getattr(index, "name", index_name or "pinecone-index")
            return

        api_key = api_key or os.environ.get("PINECONE_API_KEY")
        if not api_key:
            raise ValueError(
                "Must provide 'api_key' or set the PINECONE_API_KEY environment variable, "
                "or pass an existing 'index' instance."
            )
        if not index_name and not host:
            raise ValueError("Must provide either 'index_name' or 'host' to connect to Pinecone.")

        try:
            from pinecone import Pinecone
        except ImportError as exc:
            raise ImportError(
                "PineconeMigrator requires the 'pinecone' package. "
                "Install it with: pip install pinecone"
            ) from exc

        pc = Pinecone(api_key=api_key)
        if host:
            self._index = pc.Index(host=host)
            self._index_name = index_name or host
        else:
            self._index = pc.Index(index_name)
            self._index_name = index_name or "pinecone-index"

    @property
    def index(self) -> Any:
        """The underlying Pinecone index client."""
        return self._index

    def get_stats(self) -> dict[str, Any]:
        """Fetch index stats including total vector count and per-namespace counts."""
        stats = self._index.describe_index_stats()
        if hasattr(stats, "to_dict"):
            return stats.to_dict()
        if isinstance(stats, dict):
            return stats
        # fallback for protobuf or object types
        return {
            "total_vector_count": getattr(stats, "total_vector_count", 0),
            "namespaces": getattr(stats, "namespaces", {}),
        }

    def _list_vector_ids(
        self,
        namespace: str = "",
        batch_size: int = 100,
        pagination_token: str | None = None,
        limit: int | None = None,
    ) -> Iterator[tuple[list[str], str | None]]:
        """Yield batches of vector IDs along with the next pagination token.

        Supports both ``list_paginated`` (Pinecone v3/v5) and fallback methods.
        """
        token = pagination_token
        retrieved = 0

        while True:
            current_limit = batch_size
            if limit is not None:
                remaining = limit - retrieved
                if remaining <= 0:
                    break
                current_limit = min(batch_size, remaining)

            page_ids: list[str] = []
            next_token: str | None = None

            # Try list_paginated
            if hasattr(self._index, "list_paginated"):
                kwargs: dict[str, Any] = {"limit": current_limit}
                if namespace:
                    kwargs["namespace"] = namespace
                if token:
                    kwargs["pagination_token"] = token
                res = self._index.list_paginated(**kwargs)

                # res may have .vectors or be a dict
                vecs = getattr(res, "vectors", None)
                if vecs is None and isinstance(res, dict):
                    vecs = res.get("vectors", [])

                for item in vecs or []:
                    if isinstance(item, str):
                        page_ids.append(item)
                    elif isinstance(item, dict):
                        page_ids.append(item.get("id", ""))
                    elif hasattr(item, "id"):
                        page_ids.append(item.id)

                pagination = getattr(res, "pagination", None)
                if pagination and hasattr(pagination, "next"):
                    next_token = pagination.next
                elif isinstance(res, dict) and "pagination" in res:
                    next_token = res["pagination"].get("next")
            # Fallback to list() generator or method
            elif hasattr(self._index, "list"):
                kwargs = {}
                if namespace:
                    kwargs["namespace"] = namespace
                res = self._index.list(**kwargs)
                # If res is an iterable of id batches
                all_ids = []
                for item in res:
                    if isinstance(item, (list, tuple)):
                        all_ids.extend(item)
                    elif isinstance(item, str):
                        all_ids.append(item)
                # Slice by batch size
                for i in range(0, len(all_ids), batch_size):
                    chunk = all_ids[i : i + batch_size]
                    yield chunk, None
                return
            else:
                raise AttributeError("Pinecone index has neither 'list_paginated' nor 'list' method.")

            if not page_ids:
                break

            yield page_ids, next_token
            retrieved += len(page_ids)
            token = next_token

            if not next_token:
                break

    def _fetch_records(self, ids: list[str], namespace: str = "") -> list[dict[str, Any]]:
        """Fetch full vector records (id, values, metadata) by IDs."""
        if not ids:
            return []
        kwargs: dict[str, Any] = {"ids": ids}
        if namespace:
            kwargs["namespace"] = namespace

        resp = self._index.fetch(**kwargs)
        vectors_map = resp.get("vectors", {}) if isinstance(resp, dict) else getattr(resp, "vectors", {})

        records: list[dict[str, Any]] = []
        for vid in ids:
            rec = vectors_map.get(vid) if isinstance(vectors_map, dict) else getattr(vectors_map, vid, None)
            if rec is None:
                continue
            if isinstance(rec, dict):
                records.append(rec)
            else:
                records.append({
                    "id": getattr(rec, "id", vid),
                    "values": list(getattr(rec, "values", [])),
                    "metadata": dict(getattr(rec, "metadata", {}) or {}),
                })
        return records

    def migrate(
        self,
        dynavec: Dynavec,
        namespace: str = "",
        target_namespace: str | None = None,
        batch_size: int = 100,
        text_key: str = "text",
        metadata_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        id_transform: Callable[[str], str] | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
        resume_token: str | None = None,
        max_vectors: int | None = None,
    ) -> MigrationReport:
        """Migrate vectors from Pinecone to dynavec in batches.

        Parameters
        ----------
        dynavec:
            The target Dynavec client instance.
        namespace:
            Pinecone source namespace (empty string for default).
        target_namespace:
            Dynavec target namespace. If None, uses ``namespace`` (or "default").
        batch_size:
            Number of vectors to fetch and upsert per batch (default: 100).
        text_key:
            Metadata field to map to ``Document.text`` (default: "text").
        metadata_transform:
            Optional callback to transform or clean metadata dicts before upsert.
        id_transform:
            Optional callback to rename or remap document IDs.
        progress_callback:
            Optional ``callback(migrated_count, total_count)`` called after each batch.
        resume_token:
            Pagination token from a previous run to resume migration.
        max_vectors:
            Optional limit on total vectors to migrate.

        Returns
        -------
        MigrationReport
            Detailed report with counts, duration, and completion status.
        """
        start_time = time.time()
        dst_ns = target_namespace if target_namespace is not None else (namespace or "default")

        # Try getting total count for namespace from index stats
        total_in_ns: int | None = None
        try:
            stats = self.get_stats()
            ns_dict = stats.get("namespaces", {})
            if namespace in ns_dict:
                total_in_ns = ns_dict[namespace].get("vector_count")
            elif not namespace and "" in ns_dict:
                total_in_ns = ns_dict[""].get("vector_count")
            elif not namespace and stats.get("total_vector_count"):
                total_in_ns = stats.get("total_vector_count")
        except Exception:  # noqa: BLE001
            total_in_ns = None

        report = MigrationReport(
            source_index=self._index_name,
            source_namespace=namespace,
            target_namespace=dst_ns,
            total_found=total_in_ns or 0,
        )

        last_token: str | None = resume_token
        try:
            for id_batch, next_token in self._list_vector_ids(
                namespace=namespace,
                batch_size=batch_size,
                pagination_token=resume_token,
                limit=max_vectors,
            ):
                last_token = next_token

                # Fetch full vector records (embedding values + metadata)
                records = self._fetch_records(id_batch, namespace=namespace)
                if not records:
                    continue

                docs_to_upsert: list[Document] = []
                for rec in records:
                    doc_id = rec.get("id") or ""
                    if id_transform:
                        doc_id = id_transform(doc_id)

                    values = rec.get("values")
                    raw_meta = dict(rec.get("metadata") or {})
                    text_val = raw_meta.pop(text_key, None) if text_key in raw_meta else None

                    if metadata_transform:
                        final_meta = metadata_transform(raw_meta)
                    else:
                        final_meta = raw_meta

                    doc = Document(
                        id=doc_id,
                        vector=values if values else None,
                        text=text_val,
                        metadata=final_meta,
                    )
                    docs_to_upsert.append(doc)

                try:
                    dynavec.upsert(docs_to_upsert, namespace=dst_ns)
                    report.migrated += len(docs_to_upsert)
                except Exception as exc:
                    err_msg = f"Failed to upsert batch of {len(docs_to_upsert)} docs: {exc}"
                    logger.error(err_msg, exc_info=True)
                    report.failed += len(docs_to_upsert)
                    report.errors.append(err_msg)

                if progress_callback:
                    try:
                        progress_callback(report.migrated, total_in_ns)
                    except Exception:  # noqa: BLE001
                        pass

                if max_vectors and report.migrated >= max_vectors:
                    break

            report.resume_token = last_token

        except Exception as exc:
            err_msg = f"Migration interrupted: {exc}"
            logger.error(err_msg, exc_info=True)
            report.errors.append(err_msg)
            report.resume_token = last_token

        report.duration_sec = time.time() - start_time
        return report

    def migrate_all_namespaces(
        self,
        dynavec: Dynavec,
        namespace_map: dict[str, str] | None = None,
        batch_size: int = 100,
        text_key: str = "text",
        progress_callback: Callable[[str, int, int | None], None] | None = None,
    ) -> list[MigrationReport]:
        """Discover and migrate all namespaces found in the Pinecone index.

        Parameters
        ----------
        dynavec:
            The target Dynavec client.
        namespace_map:
            Optional mapping of ``{source_namespace: target_namespace}``.
            Namespaces not in the mapping use their original name.
        batch_size:
            Batch size for vector migration.
        text_key:
            Metadata field containing document text.
        progress_callback:
            Optional ``callback(namespace, migrated_count, total_count)``.

        Returns
        -------
        list[MigrationReport]
            One report per namespace migrated.
        """
        stats = self.get_stats()
        ns_dict = stats.get("namespaces", {})
        namespaces = list(ns_dict.keys()) if ns_dict else [""]

        mapping = namespace_map or {}
        reports: list[MigrationReport] = []

        for ns in namespaces:
            target_ns = mapping.get(ns, ns or "default")

            def _cb(count: int, total: int | None, current_ns: str = ns) -> None:
                if progress_callback:
                    progress_callback(current_ns, count, total)

            rep = self.migrate(
                dynavec=dynavec,
                namespace=ns,
                target_namespace=target_ns,
                batch_size=batch_size,
                text_key=text_key,
                progress_callback=_cb,
            )
            reports.append(rep)

        return reports
