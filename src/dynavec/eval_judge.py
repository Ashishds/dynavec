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
    "Respond with ONLY a JSON object: {\"score\": <float>, \"reason\": \"<brief explanation>\"}."
)

_RELEVANCE_SYSTEM = (
    "You are an impartial evaluator. Given a QUESTION and an ANSWER, rate how "
    "well the ANSWER addresses the QUESTION on a scale from 0.0 to 1.0 where "
    "1.0 means a complete, accurate answer and 0.0 means completely irrelevant. "
    "Respond with ONLY a JSON object: {\"score\": <float>, \"reason\": \"<brief explanation>\"}."
)


def _build_faithfulness_prompt(question: str, answer: str, context: str) -> str:
    return (
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"ANSWER:\n{answer}"
    )


def _build_relevance_prompt(question: str, answer: str) -> str:
    return f"QUESTION:\n{question}\n\nANSWER:\n{answer}"


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
