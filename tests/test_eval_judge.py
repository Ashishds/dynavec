"""Tests for LLM-as-a-judge evaluation module."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from dynavec.eval_judge import (
    BedrockJudge,
    JudgeScore,
    LLMJudge,
    OpenAIJudge,
    _build_faithfulness_prompt,
    _build_relevance_prompt,
    _parse_score,
)


class TestScoreParsing:
    def test_clean_json(self):
        text = '{"score": 0.85, "reason": "Answer is well supported."}'
        score, reason = _parse_score(text)
        assert score == 0.85
        assert reason == "Answer is well supported."

    def test_markdown_code_fence(self):
        text = '```json\n{"score": 0.95, "reason": "Excellent match."}\n```'
        score, reason = _parse_score(text)
        assert score == 0.95
        assert reason == "Excellent match."

    def test_markdown_code_fence_no_lang(self):
        text = '```\n{"score": 0.7, "reason": "Partially grounded."}\n```'
        score, reason = _parse_score(text)
        assert score == 0.7
        assert reason == "Partially grounded."

    def test_score_clamping(self):
        # Above 1.0
        score, _ = _parse_score('{"score": 1.5, "reason": "Over"}' )
        assert score == 1.0

        # Below 0.0
        score, _ = _parse_score('{"score": -0.2, "reason": "Under"}' )
        assert score == 0.0

    def test_invalid_json(self):
        score, reason = _parse_score("This is not JSON at all")
        assert score == 0.0
        assert "Parse error" in reason

    def test_missing_fields(self):
        score, reason = _parse_score('{"other": 123}')
        assert score == 0.0
        assert reason == ""


class TestPromptBuilders:
    def test_faithfulness_prompt(self):
        p = _build_faithfulness_prompt(
            question="What is X?",
            answer="X is Y.",
            context="According to docs, X is Y.",
        )
        assert "QUESTION:\nWhat is X?" in p
        assert "CONTEXT:\nAccording to docs, X is Y." in p
        assert "ANSWER:\nX is Y." in p

    def test_relevance_prompt(self):
        p = _build_relevance_prompt(
            question="What is X?",
            answer="X is Y.",
        )
        assert "QUESTION:\nWhat is X?" in p
        assert "ANSWER:\nX is Y." in p


class TestProtocolConformance:
    def test_openai_judge_implements_protocol(self):
        judge = OpenAIJudge.__new__(OpenAIJudge)
        assert isinstance(judge, LLMJudge)

    def test_bedrock_judge_implements_protocol(self):
        judge = BedrockJudge.__new__(BedrockJudge)
        assert isinstance(judge, LLMJudge)


class TestOpenAIJudge:
    def test_faithfulness(self):
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = '{"score": 0.9, "reason": "Supported by context"}'
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        with patch.dict("sys.modules", {"openai": mock_openai}):
            judge = OpenAIJudge(model="gpt-4o-mini", api_key="test-key")
            res = judge.faithfulness(
                question="What is RAG?",
                answer="Retrieval-Augmented Generation",
                context="RAG stands for Retrieval-Augmented Generation.",
            )

            assert isinstance(res, JudgeScore)
            assert res.dimension == "faithfulness"
            assert res.score == 0.9
            assert res.reason == "Supported by context"
            assert res.model == "gpt-4o-mini"

    def test_answer_relevance(self):
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = '{"score": 0.8, "reason": "Answers the question well"}'
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        with patch.dict("sys.modules", {"openai": mock_openai}):
            judge = OpenAIJudge(model="gpt-4o-mini", api_key="test-key")
            res = judge.answer_relevance(
                question="What is RAG?",
                answer="Retrieval-Augmented Generation",
            )

            assert isinstance(res, JudgeScore)
            assert res.dimension == "answer_relevance"
            assert res.score == 0.8
            assert res.reason == "Answers the question well"

    def test_missing_openai_dependency(self):
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="OpenAIJudge requires the 'openai' package"):
                OpenAIJudge()


class TestBedrockJudge:
    def test_faithfulness(self):
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        response_body = {
            "content": [{"text": '{"score": 0.92, "reason": "Directly mentioned"}'}]
        }
        mock_client.invoke_model.return_value = {
            "body": io.BytesIO(json.dumps(response_body).encode("utf-8"))
        }

        with patch("boto3.client", mock_boto3.client):
            judge = BedrockJudge(model_id="anthropic.claude-3-haiku-20240307-v1:0")
            res = judge.faithfulness(
                question="What is Titan?",
                answer="Titan is an AWS embedding model.",
                context="Amazon Titan is an embedding and text generation model family.",
            )

            assert isinstance(res, JudgeScore)
            assert res.dimension == "faithfulness"
            assert res.score == 0.92
            assert res.reason == "Directly mentioned"
            assert res.model == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_answer_relevance(self):
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        response_body = {
            "content": [{"text": '{"score": 0.88, "reason": "Relevant answer"}'}]
        }
        mock_client.invoke_model.return_value = {
            "body": io.BytesIO(json.dumps(response_body).encode("utf-8"))
        }

        with patch("boto3.client", mock_boto3.client):
            judge = BedrockJudge(
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
                region_name="us-east-1",
            )
            res = judge.answer_relevance(
                question="What is Titan?",
                answer="Titan is an AWS embedding model.",
            )

            assert isinstance(res, JudgeScore)
            assert res.dimension == "answer_relevance"
            assert res.score == 0.88
            assert res.reason == "Relevant answer"
