from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.documents import Document


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import rag_chain  # noqa: E402


class FakeVectorStore:
    def __init__(self, scored_docs: list[tuple[Document, float]]) -> None:
        self.scored_docs = scored_docs

    def similarity_search_with_relevance_scores(self, question: str, k: int):
        assert k == 4
        return self.scored_docs


class FakeDirectAnswerChain:
    def invoke(self, payload: dict[str, str]) -> str:
        assert payload["question"] == "你好"
        return "你好，我是墨智。"

    def stream(self, payload: dict[str, str]):
        assert payload["question"] == "你好"
        yield "你好，"
        yield "我是墨智。"


def test_low_similarity_results_are_not_used_as_sources(monkeypatch) -> None:
    low_score_doc = Document(page_content="无关资料", metadata={"filename": "unrelated.md"})
    monkeypatch.setattr(rag_chain, "_get_vector_store_cached", lambda: FakeVectorStore([(low_score_doc, 0.30)]))
    monkeypatch.setattr(rag_chain.settings, "RETRIEVAL_SCORE_THRESHOLD", 0.40)

    assert rag_chain._retrieve_docs("你好") == []


def test_high_similarity_results_continue_to_use_rag(monkeypatch) -> None:
    matching_doc = Document(page_content="颜真卿资料", metadata={"filename": "yan.md"})
    monkeypatch.setattr(rag_chain, "_get_vector_store_cached", lambda: FakeVectorStore([(matching_doc, 0.60)]))
    monkeypatch.setattr(rag_chain.settings, "RETRIEVAL_SCORE_THRESHOLD", 0.40)

    assert rag_chain._retrieve_docs("颜真卿的书法有什么特点") == [matching_doc]


def test_low_similarity_uses_direct_llm_without_sources(monkeypatch) -> None:
    monkeypatch.setattr(rag_chain, "_retrieve_docs", lambda question: [])
    monkeypatch.setattr(rag_chain, "_get_direct_answer_chain_cached", lambda: FakeDirectAnswerChain())

    result = rag_chain.invoke_rag("你好")

    assert result == {"answer": "你好，我是墨智。", "sources": []}


def test_streamed_low_similarity_answer_has_no_sources(monkeypatch) -> None:
    monkeypatch.setattr(rag_chain, "_retrieve_docs", lambda question: [])
    monkeypatch.setattr(rag_chain, "_get_direct_answer_chain_cached", lambda: FakeDirectAnswerChain())

    events = list(rag_chain.stream_rag("你好"))

    assert events == [
        {"type": "sources", "sources": []},
        {"type": "chunk", "content": "你好，"},
        {"type": "chunk", "content": "我是墨智。"},
        {"type": "done"},
    ]
