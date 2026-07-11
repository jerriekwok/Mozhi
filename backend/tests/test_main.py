from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as main  # noqa: E402
from app.routers import chat as chat_router  # noqa: E402


def test_health_endpoint() -> None:
    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_legacy_chat_endpoint_delegates_to_rag(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "invoke_rag",
        lambda question: {"answer": f"RAG response: {question}", "sources": []},
    )

    response = TestClient(main.app).post("/chat", json={"message": "What is Yan style?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "RAG response: What is Yan style?"}


def test_rag_chat_endpoint_remains_available(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_router,
        "invoke_rag",
        lambda question, session_id=None: {"answer": question, "sources": []},
    )

    response = TestClient(main.app).post(
        "/api/chat",
        json={"question": "Test question", "session_id": "test-session"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Test question"
    assert response.json()["session_id"] == "test-session"


def test_rag_chat_returns_deduplicated_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_router,
        "invoke_rag",
        lambda question, session_id=None: {
            "answer": "Answer from the knowledge base.",
            "sources": [
                {
                    "filename": "yan-zhenqing.md",
                    "source": "calligraphers/yan-zhenqing.md",
                    "chapter_title": "Yan Zhenqing",
                    "snippet": "Yan Zhenqing was a Tang-dynasty calligrapher.",
                },
                {
                    "filename": "yan-zhenqing.md",
                    "source": "calligraphers/yan-zhenqing.md",
                    "chapter_title": "Yan Zhenqing",
                    "snippet": "This duplicate chunk should not be returned twice.",
                },
            ],
        },
    )

    response = TestClient(main.app).post(
        "/api/chat",
        json={"question": "Tell me about Yan Zhenqing", "session_id": "sources-session"},
    )

    assert response.status_code == 200
    assert response.json()["sources"] == [
        {
            "title": "Yan Zhenqing",
            "content": "Yan Zhenqing was a Tang-dynasty calligrapher.",
            "file": "yan-zhenqing.md",
        }
    ]


def test_rag_chat_rejects_whitespace_question() -> None:
    response = TestClient(main.app).post("/api/chat", json={"question": "   "})

    assert response.status_code == 422


def test_rag_stream_emits_sources_chunks_and_completion(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_router,
        "stream_rag",
        lambda question, session_id=None: iter(
            (
                {
                    "type": "sources",
                    "sources": [
                        {
                            "filename": "source.md",
                            "source": "source.md",
                            "chapter_title": "Source",
                            "snippet": "Source excerpt.",
                        }
                    ],
                },
                {"type": "chunk", "content": "First "},
                {"type": "chunk", "content": "answer."},
                {"type": "done"},
            )
        ),
    )

    response = TestClient(main.app).post(
        "/api/chat/stream",
        json={"question": "Stream test", "session_id": "stream-session"},
    )

    assert response.status_code == 200
    assert "event: sources" in response.text
    assert '"content": "First "' in response.text
    assert '"content": "answer."' in response.text
    assert "event: done" in response.text
