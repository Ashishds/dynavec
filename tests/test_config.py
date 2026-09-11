"""Unit tests for DynavecConfig, environment loading, and validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dynavec.config import DynavecConfig


class TestDynavecConfigFromEnv:
    def test_from_env_all_present(self):
        env = {
            "DYNAVEC_VECTOR_BUCKET": "my-bucket",
            "DYNAVEC_INDEX": "docs-index",
            "DYNAVEC_TABLE": "my_table",
            "DYNAVEC_DIMENSION": "1536",
            "DYNAVEC_DISTANCE_METRIC": "euclidean",
            "DYNAVEC_REGION": "us-west-2",
            "DYNAVEC_AUTO_PROVISION": "true",
            "DYNAVEC_MAX_WORKERS": "16",
            "DYNAVEC_PARALLEL_WRITES": "false",
        }
        with patch.dict("os.environ", env, clear=True):
            cfg = DynavecConfig.from_env()
            assert cfg.vector_bucket == "my-bucket"
            assert cfg.index == "docs-index"
            assert cfg.table == "my_table"
            assert cfg.dimension == 1536
            assert cfg.distance_metric == "euclidean"
            assert cfg.region == "us-west-2"
            assert cfg.auto_provision is True
            assert cfg.max_workers == 16
            assert cfg.parallel_writes is False

    def test_from_env_defaults(self):
        env = {
            "DYNAVEC_VECTOR_BUCKET": "my-bucket",
            "DYNAVEC_INDEX": "docs-index",
            "DYNAVEC_TABLE": "my_table",
            "DYNAVEC_DIMENSION": "384",
            "AWS_REGION": "eu-central-1",
        }
        with patch.dict("os.environ", env, clear=True):
            cfg = DynavecConfig.from_env()
            assert cfg.distance_metric == "cosine"
            assert cfg.region == "eu-central-1"
            assert cfg.auto_provision is False
            assert cfg.max_workers == 8
            assert cfg.parallel_writes is True

    def test_from_env_missing_required(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Missing required environment variable"):
                DynavecConfig.from_env()

    def test_from_env_custom_prefix(self):
        env = {
            "APP_VECTOR_BUCKET": "b",
            "APP_INDEX": "i",
            "APP_TABLE": "t",
            "APP_DIMENSION": "512",
        }
        with patch.dict("os.environ", env, clear=True):
            cfg = DynavecConfig.from_env(prefix="APP_")
            assert cfg.vector_bucket == "b"
            assert cfg.dimension == 512

    def test_from_env_overrides(self):
        env = {
            "DYNAVEC_VECTOR_BUCKET": "env-bucket",
            "DYNAVEC_INDEX": "env-index",
            "DYNAVEC_TABLE": "env-table",
            "DYNAVEC_DIMENSION": "768",
        }
        with patch.dict("os.environ", env, clear=True):
            cfg = DynavecConfig.from_env(dimension=1024, auto_provision=True)
            assert cfg.dimension == 1024
            assert cfg.auto_provision is True


class TestDynavecConfigValidation:
    def test_valid_config(self):
        cfg = DynavecConfig(
            vector_bucket="my-valid-bucket.1",
            index="valid_index-1",
            table="valid_table.v1",
            dimension=1536,
        )
        cfg.validate()  # Should not raise

    def test_invalid_bucket_name_uppercase(self):
        cfg = DynavecConfig(
            vector_bucket="Invalid-Bucket",
            index="valid-index",
            table="valid_table",
            dimension=1536,
        )
        with pytest.raises(ValueError, match="Invalid S3 vector bucket name"):
            cfg.validate()

    def test_invalid_index_name_chars(self):
        cfg = DynavecConfig(
            vector_bucket="valid-bucket",
            index="invalid index with spaces",
            table="valid_table",
            dimension=1536,
        )
        with pytest.raises(ValueError, match="Invalid vector index name"):
            cfg.validate()

    def test_invalid_table_name_chars(self):
        cfg = DynavecConfig(
            vector_bucket="valid-bucket",
            index="valid-index",
            table="invalid/table!",
            dimension=1536,
        )
        with pytest.raises(ValueError, match="Invalid DynamoDB table name"):
            cfg.validate()
