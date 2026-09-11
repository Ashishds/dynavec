"""dynavec — serverless hybrid vector database on DynamoDB + Amazon S3 Vectors.

Quick start
-----------
    from dynavec import Dynavec, DynavecConfig
    from dynavec.embeddings import OpenAIEmbedder

    cfg = DynavecConfig(
        vector_bucket="my-vectors",
        index="docs",
        table="dynavec_docs",
        dimension=1536,
        auto_provision=True,
    )
    db = Dynavec(cfg, embedder=OpenAIEmbedder(model="text-embedding-3-small"))

    db.upsert([{"id": "a", "text": "hello world", "metadata": {"lang": "en"}}])
    hits = db.search("greetings", top_k=3, filter={"lang": "en"})
"""

from __future__ import annotations

from .cache import BaseCache, DynamoDBCache, RedisCache, SemanticCache
from .client import Dynavec
from .config import DynavecConfig
from .credentials import AWSCredentials
from .eval import EvalDataset, EvalQuery, EvalResult, run_eval
from .eval_judge import BedrockJudge, JudgeScore, LLMJudge, OpenAIJudge
from .exceptions import (
    ConfigurationError,
    DimensionMismatchError,
    DynavecError,
    EmbeddingError,
    MissingDependencyError,
    NotFoundError,
    ProvisioningError,
)
from .graph import GraphStore
from .migration import MigrationReport, PineconeMigrator
from .models import Document, SearchResult, UpsertResult
from .namespace import NamespaceView
from .quantization import ProductQuantizer
from .retrieval import (
    maximal_marginal_relevance,
    reciprocal_rank_fusion,
)
from .scalar_quantization import ScalarQuantizer
from .spfresh import (
    Partition,
    SPFreshConfig,
    SPFreshHotIndex,
    SPFreshRebalancer,
)
from .transforms import LambdaTransform, TransformContext, TransformPipeline

__version__ = "0.3.0"

__all__ = [
    "Dynavec",
    "DynavecConfig",
    "AWSCredentials",
    "Document",
    "SearchResult",
    "UpsertResult",
    "NamespaceView",
    "ProductQuantizer",
    "ScalarQuantizer",
    "GraphStore",
    "BaseCache",
    "SemanticCache",
    "DynamoDBCache",
    "RedisCache",
    "reciprocal_rank_fusion",
    "maximal_marginal_relevance",
    "Partition",
    "SPFreshConfig",
    "SPFreshHotIndex",
    "SPFreshRebalancer",
    "TransformPipeline",
    "TransformContext",
    "LambdaTransform",
    # eval & quality
    "EvalDataset",
    "EvalQuery",
    "EvalResult",
    "run_eval",
    "LLMJudge",
    "JudgeScore",
    "OpenAIJudge",
    "BedrockJudge",
    # migration
    "PineconeMigrator",
    "MigrationReport",
    # exceptions
    "DynavecError",
    "ConfigurationError",
    "ProvisioningError",
    "EmbeddingError",
    "DimensionMismatchError",
    "NotFoundError",
    "MissingDependencyError",
]
