"""Tests for the Pinecone migration module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dynavec.migration import MigrationReport, PineconeMigrator
from dynavec.models import Document


class FakePaginatedResponse:
    def __init__(self, vectors, next_token=None):
        self.vectors = vectors
        self.pagination = MagicMock(next=next_token)


class FakePineconeIndex:
    def __init__(self, vectors_data, namespaces=None):
        self.name = "fake-pinecone-index"
        self._vectors_data = vectors_data  # dict: id -> {values: [...], metadata: {...}}
        self._namespaces = namespaces or {"": {"vector_count": len(vectors_data)}}

    def describe_index_stats(self):
        return {
            "total_vector_count": len(self._vectors_data),
            "namespaces": self._namespaces,
        }

    def list_paginated(self, namespace="", limit=100, pagination_token=None):
        all_ids = sorted(self._vectors_data.keys())
        start_idx = 0
        if pagination_token:
            try:
                start_idx = all_ids.index(pagination_token)
            except ValueError:
                start_idx = 0

        batch_ids = all_ids[start_idx : start_idx + limit]
        next_idx = start_idx + limit
        next_token = all_ids[next_idx] if next_idx < len(all_ids) else None
        return FakePaginatedResponse(vectors=batch_ids, next_token=next_token)

    def fetch(self, ids, namespace=""):
        res = {}
        for vid in ids:
            if vid in self._vectors_data:
                res[vid] = {
                    "id": vid,
                    "values": self._vectors_data[vid].get("values", [0.1, 0.2]),
                    "metadata": dict(self._vectors_data[vid].get("metadata", {})),
                }
        return {"vectors": res}


class TestMigrationReport:
    def test_report_properties(self):
        rep = MigrationReport(
            source_index="test-index",
            source_namespace="src",
            target_namespace="dst",
            total_found=10,
            migrated=10,
            failed=0,
            duration_sec=1.5,
        )
        assert rep.is_complete is True
        d = rep.to_dict()
        assert d["migrated"] == 10
        assert d["is_complete"] is True
        assert d["error_count"] == 0

    def test_incomplete_report(self):
        rep = MigrationReport(
            source_index="test-index",
            source_namespace="src",
            target_namespace="dst",
            total_found=10,
            migrated=5,
            failed=2,
            resume_token="tok123",
        )
        assert rep.is_complete is False
        assert rep.to_dict()["resume_token"] == "tok123"


class TestPineconeMigrator:
    @pytest.fixture
    def mock_dynavec(self):
        mock_db = MagicMock()
        mock_db.upsert.return_value = MagicMock(count=0)
        return mock_db

    @pytest.fixture
    def sample_vectors(self):
        return {
            f"doc-{i}": {
                "values": [float(i), float(i + 1)],
                "metadata": {"text": f"Document text {i}", "category": "tech", "version": 1},
            }
            for i in range(10)
        }

    def test_basic_migration(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        report = migrator.migrate(
            dynavec=mock_dynavec,
            namespace="articles",
            target_namespace="articles-v2",
            batch_size=5,
        )

        assert report.is_complete is True
        assert report.migrated == 10
        assert report.failed == 0
        assert mock_dynavec.upsert.call_count == 2

        # Verify documents passed to upsert
        first_call_docs = mock_dynavec.upsert.call_args_list[0][0][0]
        assert len(first_call_docs) == 5
        doc = first_call_docs[0]
        assert isinstance(doc, Document)
        assert doc.id == "doc-0"
        assert doc.text == "Document text 0"
        assert doc.vector == [0.0, 1.0]
        assert doc.metadata == {"category": "tech", "version": 1}

    def test_migration_with_id_transform(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        report = migrator.migrate(
            dynavec=mock_dynavec,
            id_transform=lambda id_: f"migrated_{id_}",
            batch_size=10,
        )

        assert report.migrated == 10
        upserted_docs = mock_dynavec.upsert.call_args[0][0]
        assert upserted_docs[0].id == "migrated_doc-0"

    def test_migration_with_metadata_transform(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        def add_source(meta):
            meta["source"] = "pinecone"
            return meta

        report = migrator.migrate(
            dynavec=mock_dynavec,
            metadata_transform=add_source,
            batch_size=10,
        )

        assert report.migrated == 10
        upserted_docs = mock_dynavec.upsert.call_args[0][0]
        assert upserted_docs[0].metadata["source"] == "pinecone"

    def test_progress_callback(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        progress_records = []
        report = migrator.migrate(
            dynavec=mock_dynavec,
            batch_size=4,
            progress_callback=lambda count, total: progress_records.append((count, total)),
        )

        assert report.migrated == 10
        assert len(progress_records) >= 3
        assert progress_records[-1][0] == 10

    def test_migration_limit(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        report = migrator.migrate(
            dynavec=mock_dynavec,
            batch_size=3,
            max_vectors=5,
        )

        assert report.migrated == 5

    def test_upsert_error_handling(self, mock_dynavec, sample_vectors):
        fake_idx = FakePineconeIndex(sample_vectors)
        migrator = PineconeMigrator(index=fake_idx)

        mock_dynavec.upsert.side_effect = RuntimeError("DynamoDB throttle")

        report = migrator.migrate(dynavec=mock_dynavec, batch_size=5)

        assert report.migrated == 0
        assert report.failed == 10
        assert len(report.errors) == 2
        assert "DynamoDB throttle" in report.errors[0]

    def test_migrate_all_namespaces(self, mock_dynavec):
        vectors = {
            "d1": {"values": [0.1, 0.2], "metadata": {"text": "one"}},
            "d2": {"values": [0.3, 0.4], "metadata": {"text": "two"}},
        }
        namespaces = {
            "ns1": {"vector_count": 1},
            "ns2": {"vector_count": 1},
        }
        fake_idx = FakePineconeIndex(vectors, namespaces=namespaces)
        migrator = PineconeMigrator(index=fake_idx)

        reports = migrator.migrate_all_namespaces(
            dynavec=mock_dynavec,
            namespace_map={"ns1": "dyn-ns1"},
            batch_size=5,
        )

        assert len(reports) == 2
        target_namespaces = {r.target_namespace for r in reports}
        assert "dyn-ns1" in target_namespaces
        assert "ns2" in target_namespaces

    def test_init_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Must provide 'api_key'"):
                PineconeMigrator(index_name="test")

    def test_init_missing_index_name(self):
        with pytest.raises(ValueError, match="Must provide either 'index_name'"):
            PineconeMigrator(api_key="key")
