"""
Ingest the complete text of 'Attention Is All You Need' into AWS DynamoDB & S3.
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

# Windows UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
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

from dynavec import Document, Dynavec, DynavecConfig, SemanticCache
from dynavec.embeddings.base import Embedder
from dynavec.ingest import Record, ingest

DIM = 16


class LocalDeterministicEmbedder(Embedder):
    def __init__(self, dimension: int = DIM) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        import re
        out = []
        for t in texts:
            v = [0.0] * self.dimension
            words = re.findall(r"\w+", t.lower())
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 8) & 1) else -1.0
                v[idx] += sign
            norm = math.sqrt(sum(x * x for x in v)) or 1e-9
            out.append([x / norm for x in v])
        return out


PAGES = [
    (
        "page-1-abstract",
        "Attention Is All You Need. Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin. "
        "Abstract: The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. "
        "The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, "
        "based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models "
        "to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 "
        "English-to-German translation task, improving over existing best results by over 2 BLEU. On WMT 2014 English-to-French, our model establishes a new "
        "single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs.",
        {"section": "abstract", "page": 1, "authors": "Vaswani et al."}
    ),
    (
        "page-2-introduction",
        "1 Introduction: Recurrent models factor computation along symbol positions of input and output sequences. Aligning positions to steps in computation time, "
        "they generate hidden states ht as a function of previous state ht-1 and input for position t. This inherently sequential nature precludes parallelization "
        "within training examples. The fundamental constraint of sequential computation remains. In this work we propose the Transformer, eschewing recurrence "
        "and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for significantly "
        "more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours on eight P100 GPUs.",
        {"section": "introduction", "page": 2}
    ),
    (
        "page-3-architecture",
        "3 Model Architecture: 3.1 Encoder and Decoder Stacks. Encoder: The encoder is composed of a stack of N = 6 identical layers. Each layer has two sub-layers. "
        "The first is a multi-head self-attention mechanism, and the second is a simple, position-wise fully connected feed-forward network. We employ a residual "
        "connection around each of the two sub-layers, followed by layer normalization. The output of each sub-layer is LayerNorm(x + Sublayer(x)). To facilitate "
        "these residual connections, all sub-layers produce outputs of dimension dmodel = 512. Decoder: The decoder is also composed of a stack of N = 6 identical layers. "
        "In addition to the two sub-layers in each encoder layer, the decoder inserts a third sub-layer, which performs multi-head attention over the encoder output. "
        "Masked self-attention prevents positions from attending to subsequent positions.",
        {"section": "architecture", "page": 3, "layers": 6, "dmodel": 512}
    ),
    (
        "page-4-attention",
        "3.2.1 Scaled Dot-Product Attention: The input consists of queries and keys of dimension dk, and values of dimension dv. We compute the dot products of the "
        "query with all keys, divide each by sqrt(dk), and apply a softmax function to obtain weights on values: Attention(Q, K, V) = softmax((Q K^T) / sqrt(dk)) V. "
        "Dot-product attention is faster and more space-efficient than additive attention since it can be implemented using highly optimized matrix multiplication code. "
        "For large values of dk, dot products grow large in magnitude, pushing softmax into regions with extremely small gradients. To counteract this effect, we scale "
        "dot products by 1 / sqrt(dk). 3.2.2 Multi-Head Attention: We linearly project queries, keys and values h = 8 times with learned linear projections to dk, dk "
        "and dv dimensions respectively, performing attention in parallel.",
        {"section": "attention_equation", "page": 4, "formula": "softmax(QK^T/sqrt(dk))V"}
    ),
    (
        "page-5-multihead-ffn",
        "MultiHead(Q, K, V) = Concat(head1, ..., headh) W^O where headi = Attention(Q W_i^Q, K W_i^K, V W_i^V). In this work we employ h = 8 parallel attention layers, "
        "or heads. For each of these we use dk = dv = dmodel / h = 64. Total computational cost is similar to single-head attention with full dimensionality. "
        "3.3 Position-wise Feed-Forward Networks: In addition to attention sub-layers, each layer in encoder and decoder contains a fully connected feed-forward network: "
        "FFN(x) = max(0, x W1 + b1) W2 + b2. This consists of two linear transformations with a ReLU activation in between. Dimensionality of input and output is "
        "dmodel = 512, and inner-layer dimensionality is dff = 2048.",
        {"section": "multi_head_ffn", "page": 5, "heads": 8, "dff": 2048}
    ),
    (
        "page-6-positional-encoding",
        "3.5 Positional Encoding: Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, "
        "we must inject information about the relative or absolute position of tokens in the sequence. To this end, we add positional encodings to input embeddings: "
        "PE(pos, 2i) = sin(pos / 10000^(2i / dmodel)) and PE(pos, 2i+1) = cos(pos / 10000^(2i / dmodel)), where pos is the position and i is the dimension. "
        "Wavelengths form a geometric progression from 2*pi to 10000 * 2*pi. 4 Why Self-Attention: Table 1 shows maximum path length is O(1) for self-attention, "
        "compared to O(n) for recurrent networks and O(logk(n)) for convolutional networks.",
        {"section": "positional_encoding", "page": 6}
    ),
    (
        "page-7-training-hardware",
        "5 Training: 5.1 Training Data and Batching: Standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. WMT 2014 English-French "
        "dataset consisting of 36M sentences. 5.2 Hardware and Schedule: We trained our models on one machine with 8 NVIDIA P100 GPUs. For our base models, each "
        "training step took about 0.4 seconds, trained for 100,000 steps or 12 hours. Big models step time was 1.0 seconds, trained for 300,000 steps (3.5 days). "
        "5.3 Optimizer: Adam optimizer with beta1 = 0.9, beta2 = 0.98 and epsilon = 10^-9. Learning rate varied with warmup_steps = 4000. 5.4 Regularization: "
        "Residual Dropout rate Pdrop = 0.1, Label Smoothing epsilon_ls = 0.1.",
        {"section": "training_hardware", "page": 7, "gpus": "8 NVIDIA P100", "optimizer": "Adam"}
    ),
    (
        "page-8-results-bleu",
        "6 Results: 6.1 Machine Translation: On WMT 2014 English-to-German translation task, the big transformer model (Transformer big) achieves state-of-the-art "
        "BLEU score of 28.4, outperforming previously reported models by more than 2.0 BLEU. Training took 3.5 days on 8 P100 GPUs. Base model achieves 27.3 BLEU. "
        "On WMT 2014 English-to-French translation task, big model achieves BLEU score of 41.8, outperforming all previously published single models at less than "
        "1/4 the training cost of previous state-of-the-art models (2.3 * 10^19 FLOPs vs 1.2 * 10^21 FLOPs for ensembles).",
        {"section": "bleu_results", "page": 8, "en_de_bleu": 28.4, "en_fr_bleu": 41.8}
    ),
    (
        "page-9-model-variations",
        "Table 3: Variations on the Transformer architecture. Base model: N = 6, dmodel = 512, dff = 2048, h = 8, dk = 64, dv = 64, Pdrop = 0.1, 100K train steps, "
        "25.8 BLEU (dev), 65M parameters. Big model: N = 6, dmodel = 1024, dff = 4096, h = 16, Pdrop = 0.3, 300K train steps, 26.4 BLEU (dev), 213M parameters. "
        "6.3 English Constituency Parsing: Trained 4-layer transformer with dmodel = 1024 on Wall Street Journal (WSJ) portion of Penn Treebank (40K sentences), "
        "achieving 91.3 F1 discriminative and 92.7 F1 semi-supervised.",
        {"section": "model_variations", "page": 9, "base_params": "65M", "big_params": "213M"}
    ),
    (
        "page-10-conclusion",
        "7 Conclusion: In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing recurrent layers "
        "most commonly used in encoder-decoder architectures with multi-headed self-attention. For translation tasks, the Transformer can be trained significantly "
        "faster than architectures based on recurrent or convolutional layers. On both WMT 2014 English-to-German and WMT 2014 English-to-French translation tasks, "
        "we achieve a new state of the art. Code used to train and evaluate our models is available at https://github.com/tensorflow/tensor2tensor.",
        {"section": "conclusion", "page": 10}
    ),
]


def main():
    print("=" * 65)
    print(" INGESTING 'ATTENTION IS ALL YOU NEED' INTO AWS CLOUD ")
    print("=" * 65)

    region = os.environ.get("AWS_REGION", "us-east-1")
    table = os.environ.get("DYNAVEC_TABLE", "dynavec_docs")
    bucket = os.environ.get("DYNAVEC_VECTOR_BUCKET", "dynavec-vectors-212919533030")
    index = os.environ.get("DYNAVEC_INDEX", "docs-index")

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

    docs = [
        Document(id=doc_id, text=text, metadata=meta)
        for doc_id, text, meta in PAGES
    ]

    t0 = time.perf_counter()
    res = db.upsert(docs, namespace="transformer-paper")
    latency = (time.perf_counter() - t0) * 1000

    print(f"[OK] Ingested {res.count} curated sections of 'Attention Is All You Need'")
    print(f"     Target Namespace : transformer-paper")
    print(f"     Target DynamoDB  : {table}")
    print(f"     Target S3 Bucket : {bucket}")
    print(f"     Ingestion Latency: {latency:.2f} ms")
    print("=" * 65)


if __name__ == "__main__":
    main()
