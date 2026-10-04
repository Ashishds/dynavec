"""Tests for RAG answer synthesis, inline citations, and fallback synthesizer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dynavec.rag_synthesizer import (
    ExtractiveRAGSynthesizer,
    OpenAISynthesizer,
    SynthesizedAnswer,
    _extract_citations,
    get_default_synthesizer,
)


class TestCitationExtraction:
    def test_citations_from_tags(self):
        chunks = [
            {
                "id": "doc1",
                "text": "Self-attention replaces recurrence.",
                "metadata": {"filename": "paper.pdf", "page": 1},
                "score": 0.88,
            },
            {
                "id": "doc2",
                "text": "Feed-forward network has dimension 2048.",
                "metadata": {"filename": "paper.pdf", "page": 5},
                "score": 0.75,
            },
        ]
        answer = "The model uses self-attention [1] and feed-forward networks [2]."
        citations = _extract_citations(chunks, answer)

        assert len(citations) == 2
        assert citations[0].index == 1
        assert citations[0].id == "doc1"
        assert citations[0].page == 1
        assert citations[1].index == 2
        assert citations[1].page == 5

    def test_citations_fallback_when_no_tags(self):
        chunks = [
            {"id": "doc1", "text": "Only one chunk available.", "metadata": {"page": 3}},
        ]
        answer = "This is a clean answer without explicit brackets."
        citations = _extract_citations(chunks, answer)

        assert len(citations) == 1
        assert citations[0].id == "doc1"
        assert citations[0].page == 3


class TestExtractiveSynthesizer:
    def test_synthesizes_clean_answer_with_citations(self):
        synth = ExtractiveRAGSynthesizer()
        chunks = [
            {
                "id": "transformer#p1",
                "text": "The dominant sequence models include an encoder and a decoder. The encoder maps an input sequence to representations.",
                "metadata": {"filename": "transformer.pdf", "page": 1},
                "score": 0.85,
            },
            {
                "id": "transformer#p5",
                "text": "The decoder generates an output sequence of symbols one element at a time. It employs masking for self-attention.",
                "metadata": {"filename": "transformer.pdf", "page": 5},
                "score": 0.81,
            },
        ]
        res = synth.synthesize("what is encoder and decoder in transformers?", chunks)

        assert isinstance(res, SynthesizedAnswer)
        assert "encoder" in res.text.lower()
        assert len(res.citations) >= 1
        assert res.citations[0].filename == "transformer.pdf"
        assert res.latency_ms >= 0.0

    def test_empty_chunks_returns_graceful_message(self):
        synth = ExtractiveRAGSynthesizer()
        res = synth.synthesize("non-existent query", [])
        assert "No relevant context" in res.text
        assert res.citations == []


class TestOpenAISynthesizer:
    def test_openai_synthesis_flow(self):
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Transformers use an encoder to encode representations and a decoder to generate tokens [1]."
        mock_client.chat.completions.create.return_value.choices = [mock_choice]

        with patch.dict("sys.modules", {"openai": mock_openai}):
            synth = OpenAISynthesizer(api_key="sk-fake")
            chunks = [
                {
                    "id": "doc-1",
                    "text": "Encoder and decoder architecture.",
                    "metadata": {"page": 2},
                    "score": 0.9,
                },
            ]
            res = synth.synthesize("explain encoder and decoder", chunks)

            assert "Transformers use an encoder" in res.text
            assert len(res.citations) == 1
            assert res.citations[0].page == 2
            assert "openai" in res.model


def test_get_default_synthesizer():
    synth = get_default_synthesizer()
    assert synth is not None
