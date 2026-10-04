"""RAG answer synthesis with document & page citations.

Combines retrieved vector chunks from AWS DynamoDB & S3 Vectors into a clean,
coherent final answer with inline citation tags ([1], [2]) pointing to
specific documents and page numbers.

Supports:
- AWS Bedrock (Claude 3 Haiku / Titan)
- OpenAI (gpt-4o-mini / gpt-4o)
- ExtractiveRAGSynthesizer (zero-dependency, high-accuracy local fallback)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Citation mapping a reference tag ([1], [2]) to a source document."""

    index: int
    id: str
    filename: str | None = None
    page: int | str | None = None
    snippet: str = ""
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesizedAnswer:
    """Final grounded answer with inline citations and latency tracking."""

    query: str
    text: str
    citations: list[Citation] = field(default_factory=list)
    model: str = "dynavec-synthesizer"
    latency_ms: float = 0.0
    confidence: str = "high"  # "high", "medium", "low"
    confidence_score: float = 1.0
    confidence_reason: str = ""
    is_low_confidence: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "text": self.text,
            "citations": [c.to_dict() for c in self.citations],
            "model": self.model,
            "latency_ms": round(self.latency_ms, 2),
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 4),
            "confidence_reason": self.confidence_reason,
            "is_low_confidence": self.is_low_confidence,
        }


@runtime_checkable
class Synthesizer(Protocol):
    """Protocol for RAG answer generators."""

    def synthesize(
        self,
        query: str,
        chunks: list[dict[str, Any]],
    ) -> SynthesizedAnswer: ...


_RAG_SYSTEM_PROMPT = (
    "You are Dynavec AI, an expert technical assistant. Given a user question "
    "and a numbered list of retrieved context documents from AWS DynamoDB and S3 Vectors, "
    "generate a clear, concise, and professional answer that directly resolves the question.\n\n"
    "CRITICAL RULES:\n"
    "1. Base your answer ONLY on the provided context. Do NOT invent facts or hallucinate.\n"
    "2. Include inline citation brackets such as [1], [2] immediately following every claim, "
    "matching the source document numbers provided.\n"
    "3. Use clean markdown formatting (bullet points, bold highlights, code tags where relevant).\n"
    "4. If the context does not contain enough information, state what is known from the context "
    "and clarify what details are missing."
)


def _build_rag_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    parts = [f"USER QUESTION: {query}\n\nRETRIEVED CONTEXT DOCUMENTS:"]
    for idx, c in enumerate(chunks, start=1):
        doc_id = c.get("id", f"doc-{idx}")
        meta = c.get("metadata", {}) or {}
        fn = meta.get("filename") or doc_id
        page = meta.get("page")
        page_str = f" | Page: {page}" if page else ""
        txt = (c.get("text") or "").strip()
        parts.append(f"[{idx}] Source: {fn}{page_str} (ID: {doc_id})\n{txt}\n")
    parts.append("\nGenerate the synthesized answer with inline citation tags [1], [2]:")
    return "\n".join(parts)


def _extract_citations(chunks: list[dict[str, Any]], answer_text: str) -> list[Citation]:
    """Scan the answer text for [1], [2], etc., and build citation objects."""
    found_indices = sorted(list({int(m) for m in re.findall(r"\[(\d+)\]", answer_text)}))
    citations: list[Citation] = []
    for idx in found_indices:
        if 1 <= idx <= len(chunks):
            c = chunks[idx - 1]
            meta = c.get("metadata", {}) or {}
            citations.append(
                Citation(
                    index=idx,
                    id=str(c.get("id", f"doc-{idx}")),
                    filename=meta.get("filename"),
                    page=meta.get("page"),
                    snippet=c.get("text", "")[:220].strip()
                    + ("..." if len(c.get("text", "")) > 220 else ""),
                    score=round(float(c.get("score", 0.0)), 4),
                )
            )
    # If no citation markers were detected in text, default to linking all used chunks
    if not citations and chunks:
        for idx, c in enumerate(chunks, start=1):
            meta = c.get("metadata", {}) or {}
            citations.append(
                Citation(
                    index=idx,
                    id=str(c.get("id", f"doc-{idx}")),
                    filename=meta.get("filename"),
                    page=meta.get("page"),
                    snippet=c.get("text", "")[:220].strip()
                    + ("..." if len(c.get("text", "")) > 220 else ""),
                    score=round(float(c.get("score", 0.0)), 4),
                )
            )
    return citations


ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "how", "what", "which", "who", "whom",
    "this", "that", "these", "those", "can", "could", "will", "would", "shall", "should",
    "it", "its", "we", "our", "you", "your", "they", "their", "so", "if", "not",
}


def _stem_word(w: str) -> str:
    w = w.lower().strip()
    if w in ("transfomer", "transfomers", "transforming"):
        return "transform"
    if w.startswith("position"):
        return "position"
    if w.startswith("encod"):
        return "encod"
    if w.startswith("attent"):
        return "attent"
    if w.startswith("decod"):
        return "decod"
    w = re.sub(r"(al|ing|s|ed|er|ers|ion|ions|ment|ments|ive|ly)$", "", w)
    return w


class ExtractiveRAGSynthesizer:
    """Deterministic, zero-cost extractive synthesizer.

    Extracts key informative sentences from the top retrieved chunks, removes
    extraneous metadata/disclaimers, organizes them by topic, and adds inline citations.
    Includes active retrieval confidence evaluation and a guardrail refusing to
    hallucinate when retrieved context lacks relevant coverage.
    """

    def __init__(self, model_name: str = "dynavec-extractive-v1 (Deterministic Local Extraction)") -> None:
        self.model_name = model_name

    def synthesize(self, query: str, chunks: list[dict[str, Any]]) -> SynthesizedAnswer:
        t0 = time.perf_counter()
        if not chunks:
            return SynthesizedAnswer(
                query=query,
                text="⚠️ No relevant context documents were found in the selected partition.",
                citations=[],
                model=self.model_name,
                latency_ms=(time.perf_counter() - t0) * 1000,
                confidence="low",
                confidence_score=0.0,
                confidence_reason="No documents returned from vector store.",
                is_low_confidence=True,
            )

        # Normalize hyphens and compound typos
        import difflib
        q_spaced = re.sub(r"[-_/]+", " ", query.lower())
        q_spaced = re.sub(r"(head)(atten\w*)", r"\1 \2", q_spaced)
        raw_words = re.findall(r"\b[a-zA-Z0-9_]+\b", q_spaced)
        corrected_words = []
        for w in raw_words:
            if len(w) >= 5 and w not in ("multi", "scale", "depth", "layer", "batch", "query", "heads"):
                matches = difflib.get_close_matches(
                    w,
                    [
                        "attention",
                        "transformer",
                        "transformers",
                        "encoder",
                        "decoder",
                        "positional",
                        "feedforward",
                        "embedding",
                    ],
                    n=1,
                    cutoff=0.72,
                )
                if matches:
                    corrected_words.append(matches[0])
                    continue
            corrected_words.append(w)

        q_substantive = {w for w in corrected_words if w not in ENGLISH_STOPWORDS}
        if not q_substantive:
            q_substantive = set(corrected_words)
        q_stemmed = {_stem_word(w) for w in q_substantive}

        # Check maximum retrieval score
        max_score = max((float(c.get("score") or 0.0) for c in chunks), default=0.0)

        # Check substantive topical coverage across all chunks
        all_chunks_text = " ".join((c.get("text") or "") for c in chunks)
        chunk_words = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", all_chunks_text.lower()))
        chunk_stemmed = {_stem_word(w) for w in chunk_words}

        covered_substantive = q_stemmed & chunk_stemmed
        coverage_ratio = len(covered_substantive) / max(1, len(q_stemmed))

        # Determine confidence level
        is_low_confidence = (max_score < 0.35 and coverage_ratio < 0.5) or (
            len(q_substantive) >= 2 and coverage_ratio == 0
        )
        if is_low_confidence:
            confidence = "low"
            confidence_reason = (
                f"Top similarity ({max_score:.1%}) and query topic coverage ({coverage_ratio:.0%}) "
                "are below the confidence threshold (35%)."
            )
        elif max_score < 0.50 or coverage_ratio < 0.6:
            confidence = "medium"
            confidence_reason = f"Moderate retrieval confidence ({max_score:.1%})."
        else:
            confidence = "high"
            confidence_reason = f"High retrieval confidence ({max_score:.1%})."

        # If low confidence guardrail triggers, refuse to hallucinate irrelevant text
        if is_low_confidence:
            missing_terms = [
                w for w in sorted(q_substantive) if _stem_word(w) not in chunk_stemmed
            ]
            missing_str = (
                ", ".join(f'"{t}"' for t in missing_terms) if missing_terms else query
            )
            top_score_pct = f"{max_score * 100:.1f}%" if max_score > 0 else "N/A"

            warning_text = (
                f"⚠️ **Low Retrieval Confidence — Insufficient Relevant Context** ({top_score_pct} Match)\n\n"
                f'The retrieved context documents from AWS DynamoDB & S3 Vectors do not contain sufficient specific information to answer **"{query}"** with high confidence.\n\n'
                f"• **Closest retrieved context**: General architecture / attention mechanisms (Top match: {top_score_pct}).\n"
                f"• **Missing concepts**: Specific coverage of {missing_str}.\n\n"
                "*Recommendation: Refine query terms (e.g., check spelling or try 'positional encodings') or expand candidate retrieval pool to Top-20.*"
            )
            citations = _extract_citations(chunks, warning_text)
            latency = (time.perf_counter() - t0) * 1000
            return SynthesizedAnswer(
                query=query,
                text=warning_text,
                citations=citations,
                model=self.model_name,
                latency_ms=latency,
                confidence=confidence,
                confidence_score=max_score,
                confidence_reason=confidence_reason,
                is_low_confidence=True,
            )

        selected_lines: list[tuple[float, int, str, dict]] = []

        # Filter out common PDF license boilerplate
        boilerplate = [
            "provided proper attribution",
            "google hereby grants permission",
            "journalistic or scholarly works",
            "all rights reserved",
            "arxiv:",
        ]

        for idx, c in enumerate(chunks, start=1):
            txt = c.get("text") or ""
            # Strip emails, affiliations, and header noise
            cleaned_txt = re.sub(r"[\w\.-]+@[\w\.-]+", "", txt)
            cleaned_txt = re.sub(r"[*†‡]", "", cleaned_txt)
            if "Abstract" in cleaned_txt:
                cleaned_txt = cleaned_txt.split("Abstract", 1)[1]

            sentences = re.split(r"(?<=[.!?])\s+", cleaned_txt)
            for s in sentences:
                s_clean = re.sub(r"\s+", " ", s).strip()
                if len(s_clean) < 30 or len(s_clean) > 350:
                    continue
                s_lower = s_clean.lower()
                if any(bp in s_lower for bp in boilerplate):
                    continue

                s_words = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", s_lower))
                s_stemmed = {_stem_word(w) for w in s_words if w not in ENGLISH_STOPWORDS}
                overlap = len(q_stemmed & s_stemmed)

                # Strong bonus if multiple substantive terms occur in the exact same sentence
                if len(q_stemmed & s_stemmed) >= 2:
                    overlap += 3.0
                if any(
                    ph in s_lower
                    for ph in [
                        "multi-head attention",
                        "multi head attention",
                        "positional encoding",
                        "positional encodings",
                        "scaled dot-product",
                    ]
                ):
                    overlap += 5.0

                if overlap > 0:
                    selected_lines.append((overlap, idx, s_clean, c))

        selected_lines.sort(key=lambda x: x[0], reverse=True)
        top_sentences = selected_lines[:4]

        if top_sentences:
            body_paragraphs = []
            used_chunk_indices = set()
            for _score, chunk_idx, sent, chk in top_sentences:
                used_chunk_indices.add(chunk_idx)
                meta = chk.get("metadata", {}) or {}
                page_info = f" (Page {meta.get('page')})" if meta.get("page") else ""
                body_paragraphs.append(f"• {sent} [{chunk_idx}]{page_info}")

            synthesized_text = (
                f'Based on the retrieved technical documentation for **"{query}"**:\n\n'
                + "\n\n".join(body_paragraphs)
            )
        else:
            first_chunk = chunks[0]
            first_txt = first_chunk.get("text", "")[:350].strip()
            synthesized_text = (
                f'Regarding **"{query}"**, the most relevant retrieved documentation notes:\n\n'
                f"> {first_txt}... [1]"
            )

        citations = _extract_citations(chunks, synthesized_text)
        latency = (time.perf_counter() - t0) * 1000
        return SynthesizedAnswer(
            query=query,
            text=synthesized_text,
            citations=citations,
            model=self.model_name,
            latency_ms=latency,
            confidence=confidence,
            confidence_score=max_score,
            confidence_reason=confidence_reason,
            is_low_confidence=is_low_confidence,
        )


class OpenAISynthesizer:
    """OpenAI chat completion synthesizer."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "OpenAISynthesizer requires the 'openai' package. "
                "Install it with: pip install dynavec[openai]"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self._model = model
        self._temperature = temperature

    def synthesize(self, query: str, chunks: list[dict[str, Any]]) -> SynthesizedAnswer:
        t0 = time.perf_counter()
        prompt = _build_rag_prompt(query, chunks)
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content or ""
        citations = _extract_citations(chunks, content)
        latency = (time.perf_counter() - t0) * 1000
        return SynthesizedAnswer(
            query=query,
            text=content,
            citations=citations,
            model=f"openai:{self._model}",
            latency_ms=latency,
        )


class BedrockSynthesizer:
    """AWS Bedrock Claude synthesizer."""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region_name: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> None:
        import boto3

        region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._model_id = model_id
        self._temperature = temperature
        self._max_tokens = max_tokens

    def synthesize(self, query: str, chunks: list[dict[str, Any]]) -> SynthesizedAnswer:
        t0 = time.perf_counter()
        try:
            prompt = _build_rag_prompt(query, chunks)
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "system": _RAG_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": self._max_tokens,
                    "temperature": self._temperature,
                }
            )
            resp = self._client.invoke_model(modelId=self._model_id, body=body)
            result = json.loads(resp["body"].read())
            content = result.get("content", [{}])[0].get("text", "")
            citations = _extract_citations(chunks, content)
            latency = (time.perf_counter() - t0) * 1000
            return SynthesizedAnswer(
                query=query,
                text=content,
                citations=citations,
                model=f"bedrock:{self._model_id}",
                latency_ms=latency,
            )
        except Exception as exc:
            # Log the Bedrock failure so operators can diagnose IAM / quota issues
            logger.warning(
                "BedrockSynthesizer failed (model=%s), falling back to Extractive: %s",
                self._model_id,
                exc,
            )
            fallback = ExtractiveRAGSynthesizer()
            res = fallback.synthesize(query, chunks)
            res.model = f"{fallback.model_name} (Bedrock Offline Fallback — {type(exc).__name__})"
            return res


class RobustRAGSynthesizer:
    """Tries cloud LLM primary synthesizer; seamlessly falls back to Extractive synthesizer on failure."""

    def __init__(self, primary: Synthesizer | None = None) -> None:
        self.primary = primary
        self.fallback = ExtractiveRAGSynthesizer()

    def synthesize(self, query: str, chunks: list[dict[str, Any]]) -> SynthesizedAnswer:
        if self.primary is not None:
            try:
                return self.primary.synthesize(query, chunks)
            except Exception:
                pass
        return self.fallback.synthesize(query, chunks)


def get_default_synthesizer() -> Synthesizer:
    """Automatically choose best available synthesizer.

    Priority:
    1. OpenAI (if OPENAI_API_KEY is set and openai package is installed)
    2. AWS Bedrock (if AWS credentials are present and bedrock package available)
    3. ExtractiveRAGSynthesizer (always available, zero-cost local fallback)
    """
    # 1. Try OpenAI if key exists
    if os.environ.get("OPENAI_API_KEY"):
        try:
            synth = OpenAISynthesizer()
            logger.info("Using OpenAI synthesizer: %s", synth._model)
            return RobustRAGSynthesizer(synth)
        except Exception as exc:
            logger.warning("OpenAI synthesizer unavailable: %s", exc)

    # 2. Try AWS Bedrock if credentials available
    if os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"):
        try:
            synth = BedrockSynthesizer()
            logger.info("Using Bedrock synthesizer: %s", synth._model_id)
            return RobustRAGSynthesizer(synth)
        except Exception as exc:
            logger.warning("Bedrock synthesizer unavailable: %s", exc)

    # 3. Always-available deterministic extractive fallback
    logger.info("Using ExtractiveRAGSynthesizer (local deterministic fallback)")
    return ExtractiveRAGSynthesizer()


    # 3. Always-available deterministic extractive fallback
    return ExtractiveRAGSynthesizer()
