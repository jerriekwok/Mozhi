from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as main  # noqa: E402
from app.routers import chat as chat_router  # noqa: E402
from app.routers import calligraphy as calligraphy_router  # noqa: E402
from app.services import memory  # noqa: E402
from app.services.vision_analysis import VisionAnalysisError  # noqa: E402


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
    monkeypatch.setattr(chat_router, "add_message", lambda session_id, *args, **kwargs: session_id)

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
    monkeypatch.setattr(chat_router, "add_message", lambda session_id, *args, **kwargs: session_id)

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
    monkeypatch.setattr(chat_router, "add_message", lambda session_id, *args, **kwargs: session_id)

    response = TestClient(main.app).post(
        "/api/chat/stream",
        json={"question": "Stream test", "session_id": "stream-session"},
    )

    assert response.status_code == 200
    assert "event: sources" in response.text
    assert '"content": "First "' in response.text
    assert '"content": "answer."' in response.text
    assert "event: done" in response.text


def test_calligraphy_analysis_uses_local_vision_model(tmp_path, monkeypatch) -> None:
    upload_id = "calligraphy_0123456789abcdef"
    image_path = tmp_path / f"{upload_id}.jpg"
    image_path.write_bytes(b"not-used-by-the-mock")
    monkeypatch.setattr(calligraphy_router, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(
        calligraphy_router,
        "analyze_calligraphy_image",
        lambda path, question, style: {
            "score": 72,
            "style": "楷书",
            "summary": "整体能看出楷书的基本结构，但横画收笔不够稳定。",
            "analysis": {
                "composition": "行距略紧。",
                "structure": "部分字中宫偏紧。",
                "strokes": "横画收笔需要更明确。",
            },
            "suggestions": ["先单独练横画收笔。"],
        },
    )

    response = TestClient(main.app).post(
        "/calligraphy/analyze",
        json={"uploadId": upload_id, "question": "重点看横画", "style": "kaishu"},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 72
    assert response.json()["analysis"]["strokes"] == "横画收笔需要更明确。"


def test_calligraphy_upload_endpoint_is_not_shadowed_by_static_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(calligraphy_router, "UPLOAD_ROOT", tmp_path)
    response = TestClient(main.app).post(
        "/uploads/calligraphy",
        data={"purpose": "analysis"},
        files={"file": ("practice.png", b"image-data", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["uploadId"].startswith("calligraphy_")


def test_calligraphy_analysis_reports_unavailable_vision_model(tmp_path, monkeypatch) -> None:
    upload_id = "calligraphy_0123456789abcdef"
    (tmp_path / f"{upload_id}.png").write_bytes(b"not-used-by-the-mock")
    monkeypatch.setattr(calligraphy_router, "UPLOAD_ROOT", tmp_path)

    def fail(*args, **kwargs):
        raise VisionAnalysisError("Vision model is unavailable")

    monkeypatch.setattr(calligraphy_router, "analyze_calligraphy_image", fail)

    response = TestClient(main.app).post("/calligraphy/analyze", json={"uploadId": upload_id})

    assert response.status_code == 503
    assert response.json()["detail"] == "Vision model is unavailable"


def test_calligraphy_analysis_can_stream_model_output(tmp_path, monkeypatch) -> None:
    upload_id = "calligraphy_0123456789abcdef"
    (tmp_path / f"{upload_id}.webp").write_bytes(b"not-used-by-the-mock")
    monkeypatch.setattr(calligraphy_router, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(memory, "_CHAT_DB_PATH", tmp_path / "mozhi.sqlite3")
    monkeypatch.setattr(
        calligraphy_router,
        "stream_calligraphy_image",
        lambda path, question, style: iter(("整体结构比较稳定。", "建议重点练横画收笔。")),
    )

    response = TestClient(main.app).post(
        "/calligraphy/analyze/stream",
        json={"uploadId": upload_id, "sessionId": "image-stream-session"},
    )

    assert response.status_code == 200
    assert "event: chunk" in response.text
    assert "整体结构比较稳定。" in response.text
    assert "event: done" in response.text
    saved = memory.get_chat_session("image-stream-session")
    assert saved is not None
    assert saved["messages"][0]["image_url"] == f"/uploads/calligraphy/{upload_id}.webp"
    assert saved["messages"][1]["content"] == "整体结构比较稳定。建议重点练横画收笔。"
