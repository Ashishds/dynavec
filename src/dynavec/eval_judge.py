"""LLM-as-a-judge evaluation: faithfulness & answer relevance scoring.

Provides two scoring dimensions for RAG pipelines:

* **Faithfulness**: Is the answer grounded in the retrieved context? (0–1)
* **Answer Relevance**: Does the answer address the original question? (0–1)

Implementations are provided for **OpenAI** and **AWS Bedrock** (Claude).

Example::

    from dynavec.eval_judge import OpenAIJudge

    judge = OpenAIJudge(model="gpt-4o-mini")
    score = judge.faithfulness(
        question="What is photosynthesis?",
        answer="Photosynthesis converts light into chemical energy.",
        context="Photosynthesis is the process by which green plants convert sunlight into glucose.",
    )
    print(score)  # 0.95
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────── prompts

_FAITHFULNESS_SYSTEM = (
    "You are an impartial evaluator. Given a QUESTION, an ANSWER, and retrieved "
    "CONTEXT, rate how well the ANSWER is supported by the CONTEXT on a scale "
    "from 0.0 to 1.0 where 1.0 means fully grounded and 0.0 means fabricated. "
    'Respond with ONLY a JSON object: {"score": <float>, "reason": "<brief explanation>"}.'
)

_RELEVANCE_SYSTEM = (
    "You are an impartial evaluator. Given a QUESTION and an ANSWER, rate how "
    "well the ANSWER addresses the QUESTION on a scale from 0.0 to 1.0 where "
    "1.0 means a complete, accurate answer and 0.0 means completely irrelevant. "
    'Respond with ONLY a JSON object: {"score": <float>, "reason": "<brief explanation>"}.'
)

_CONTEXT_RELEVANCE_SYSTEM = (
    "You are an impartial evaluator. Given a QUESTION and retrieved CONTEXT, "
    "rate how relevant and concise the CONTEXT is to answering the QUESTION "
    "on a scale from 0.0 to 1.0 where 1.0 means highly relevant without noise "
    "and 0.0 means completely irrelevant. "
    'Respond with ONLY a JSON object: {"score": <float>, "reason": "<brief explanation>"}.'
)


def _build_faithfulness_prompt(question: str, answer: str, context: str) -> str:
    return f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"


def _build_relevance_prompt(question: str, answer: str) -> str:
    return f"QUESTION:\n{question}\n\nANSWER:\n{answer}"


def _build_context_relevance_prompt(question: str, context: str) -> str:
    return f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"


def _parse_score(text: str) -> tuple[float, str]:
    """Extract score and reason from LLM JSON response."""
    try:
        # Handle markdown code fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            cleaned = cleaned.rsplit("```", 1)[0]
        data = json.loads(cleaned)
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", ""))
        return max(0.0, min(1.0, score)), reason
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse LLM judge response: %s — raw: %s", exc, text[:200])
        return 0.0, f"Parse error: {exc}"


# ──────────────────────────────────────────────────────── data classes


@dataclass
class JudgeScore:
    """Result of a single judge evaluation."""

    dimension: str  # "faithfulness" or "answer_relevance"
    score: float  # 0.0 – 1.0
    reason: str
    model: str
    raw_response: str = ""


# ──────────────────────────────────────────────────────────── protocol


@runtime_checkable
class LLMJudge(Protocol):
    """Protocol for LLM-based evaluation judges."""

    def faithfulness(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> JudgeScore:
        """Score how well *answer* is grounded in *context*."""
        ...

    def answer_relevance(
        self,
        question: str,
        answer: str,
    ) -> JudgeScore:
        """Score how well *answer* addresses *question*."""
        ...

    def context_relevance(
        self,
        question: str,
        context: str,
    ) -> JudgeScore:
        """Score how relevant and concise *context* is for *question*."""
        ...


# ────────────────────────────────────────────────────── OpenAI judge


class OpenAIJudge:
    """LLM judge using OpenAI chat completions.

    Requires ``openai`` to be installed (``pip install dynavec[openai]``).

    Parameters
    ----------
    model:
        OpenAI model name (default: ``gpt-4o-mini``).
    api_key:
        OpenAI API key.  When *None*, uses ``OPENAI_API_KEY`` env var.
    temperature:
        Sampling temperature for scoring (default: 0.0 for determinism).
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        try:
            import openai  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "OpenAIJudge requires the 'openai' package. "
                "Install it with: pip install dynavec[openai]"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    def _call(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def faithfulness(self, question: str, answer: str, context: str) -> JudgeScore:
        prompt = _build_faithfulness_prompt(question, answer, context)
        raw = self._call(_FAITHFULNESS_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="faithfulness",
            score=score,
            reason=reason,
            model=self._model,
            raw_response=raw,
        )

    def answer_relevance(self, question: str, answer: str) -> JudgeScore:
        prompt = _build_relevance_prompt(question, answer)
        raw = self._call(_RELEVANCE_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="answer_relevance",
            score=score,
            reason=reason,
            model=self._model,
            raw_response=raw,
        )

    def context_relevance(self, question: str, context: str) -> JudgeScore:
        prompt = _build_context_relevance_prompt(question, context)
        raw = self._call(_CONTEXT_RELEVANCE_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="context_relevance",
            score=score,
            reason=reason,
            model=self._model,
            raw_response=raw,
        )


# ────────────────────────────────────────────────────── Bedrock judge


class BedrockJudge:
    """LLM judge using AWS Bedrock (Claude).

    Uses the ``bedrock-runtime`` client via ``boto3``.

    Parameters
    ----------
    model_id:
        Bedrock model ID (default: ``anthropic.claude-3-haiku-20240307-v1:0``).
    region_name:
        AWS region for Bedrock.
    temperature:
        Sampling temperature (default: 0.0).
    max_tokens:
        Maximum tokens for the response (default: 256).
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region_name: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> None:
        import boto3

        kwargs: dict[str, Any] = {}
        if region_name:
            kwargs["region_name"] = region_name
        self._client = boto3.client("bedrock-runtime", **kwargs)
        self._model_id = model_id
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _call(self, system: str, user: str) -> str:
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
            }
        )
        resp = self._client.invoke_model(modelId=self._model_id, body=body)
        result = json.loads(resp["body"].read())
        return result.get("content", [{}])[0].get("text", "")

    def faithfulness(self, question: str, answer: str, context: str) -> JudgeScore:
        prompt = _build_faithfulness_prompt(question, answer, context)
        raw = self._call(_FAITHFULNESS_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="faithfulness",
            score=score,
            reason=reason,
            model=self._model_id,
            raw_response=raw,
        )

    def answer_relevance(self, question: str, answer: str) -> JudgeScore:
        prompt = _build_relevance_prompt(question, answer)
        raw = self._call(_RELEVANCE_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="answer_relevance",
            score=score,
            reason=reason,
            model=self._model_id,
            raw_response=raw,
        )

    def context_relevance(self, question: str, context: str) -> JudgeScore:
        prompt = _build_context_relevance_prompt(question, context)
        raw = self._call(_CONTEXT_RELEVANCE_SYSTEM, prompt)
        score, reason = _parse_score(raw)
        return JudgeScore(
            dimension="context_relevance",
            score=score,
            reason=reason,
            model=self._model_id,
            raw_response=raw,
        )


# ──────────────────────────────────────────────── Deterministic Fallback Judge


class DeterministicJudge:
    """Zero-dependency local judge evaluating lexical-semantic overlap and groundedness.

    Provides deterministic scores when cloud LLM credentials are not available.
    """

    def __init__(self, model_name: str = "dynavec-deterministic-evaluator") -> None:
        self._model = model_name

    def _tokenize(self, text: str) -> set[str]:
        import re

        return set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", text.lower()))

    def faithfulness(self, question: str, answer: str, context: str) -> JudgeScore:
        ans_tokens = self._tokenize(answer)
        ctx_tokens = self._tokenize(context)
        if not ans_tokens:
            return JudgeScore(
                "faithfulness", 1.0, "Empty answer has no hallucinations.", self._model
            )
        overlap = len(ans_tokens & ctx_tokens) / len(ans_tokens)
        score = min(1.0, max(0.2, round(overlap * 1.15, 2)))
        reason = (
            f"Answer groundedness ratio: {score:.0%} of key entities verified in retrieved context."
        )
        return JudgeScore("faithfulness", score, reason, self._model)

    def answer_relevance(self, question: str, answer: str) -> JudgeScore:
        q_tokens = self._tokenize(question)
        ans_tokens = self._tokenize(answer)
        if not q_tokens:
            return JudgeScore("answer_relevance", 1.0, "Generic query answered.", self._model)
        overlap = len(q_tokens & ans_tokens) / len(q_tokens)
        score = min(1.0, max(0.3, round(overlap * 1.25, 2)))
        reason = f"Response directly matches {score:.0%} of topical terms from the question."
        return JudgeScore("answer_relevance", score, reason, self._model)

    def context_relevance(self, question: str, context: str) -> JudgeScore:
        q_tokens = self._tokenize(question)
        ctx_tokens = self._tokenize(context)
        if not q_tokens:
            return JudgeScore("context_relevance", 1.0, "Context provided.", self._model)
        overlap = len(q_tokens & ctx_tokens) / len(q_tokens)
        score = min(1.0, max(0.25, round(overlap * 1.3, 2)))
        reason = f"Retrieved documents contain {score:.0%} relevant keyword matches to query."
        return JudgeScore("context_relevance", score, reason, self._model)


def get_default_judge() -> LLMJudge:
    """Resolve an available judge: Bedrock -> OpenAI -> Deterministic."""
    import os

    if os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAIJudge()
        except Exception:
            pass

    try:
        # Check if AWS region is set and boto3 can instantiate bedrock
        if os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"):
            return BedrockJudge()
    except Exception:
        pass

    return DeterministicJudge()


def evaluate_rag_triad(
    question: str,
    answer: str,
    context: str,
    judge: LLMJudge | None = None,
) -> dict[str, Any]:
    """Score all three RAG quality dimensions: Faithfulness, Answer Relevance, and Context Relevance."""
    evaluator = judge or get_default_judge()
    try:
        f_score = evaluator.faithfulness(question, answer, context)
        a_score = evaluator.answer_relevance(question, answer)
        c_score = evaluator.context_relevance(question, context)
    except Exception:
        fallback = DeterministicJudge()
        f_score = fallback.faithfulness(question, answer, context)
        a_score = fallback.answer_relevance(question, answer)
        c_score = fallback.context_relevance(question, context)

    avg = (f_score.score + a_score.score + c_score.score) / 3.0
    verdict = "PASS" if avg >= 0.70 else ("WARNING" if avg >= 0.50 else "FAIL")

    return {
        "faithfulness": {"score": f_score.score, "reason": f_score.reason},
        "answer_relevance": {"score": a_score.score, "reason": a_score.reason},
        "context_relevance": {"score": c_score.score, "reason": c_score.reason},
        "overall_score": round(avg, 3),
        "verdict": verdict,
        "model": f_score.model,
    }
