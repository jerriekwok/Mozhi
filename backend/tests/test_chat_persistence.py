from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as main  # noqa: E402
from app.services import memory  # noqa: E402


def test_chat_records_are_saved_and_exposed_by_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(memory, "_CHAT_DB_PATH", tmp_path / "mozhi.sqlite3")

    session_id = "saved-session"
    memory.add_message(session_id, "human", "颜真卿的楷书有哪些特点？")
    memory.add_message(
        session_id,
        "ai",
        "颜体以宽博雄浑、横细竖粗见长。",
        [{"title": "颜真卿", "content": "颜体特点", "file": "yan.md"}],
    )

    client = TestClient(main.app)
    summaries = client.get("/api/chat/sessions")
    detail = client.get(f"/api/chat/sessions/{session_id}")

    assert summaries.status_code == 200
    assert summaries.json()[0]["id"] == session_id
    assert summaries.json()[0]["title"] == "颜真卿的楷书有哪些特点？"
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == ["human", "ai"]
    assert detail.json()["messages"][1]["sources"][0]["file"] == "yan.md"


def test_unknown_saved_conversation_returns_not_found(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(memory, "_CHAT_DB_PATH", tmp_path / "mozhi.sqlite3")

    response = TestClient(main.app).get("/api/chat/sessions/missing")

    assert response.status_code == 404


def test_saved_conversation_can_be_deleted(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(memory, "_CHAT_DB_PATH", tmp_path / "mozhi.sqlite3")
    memory.add_message("delete-me", "human", "这条对话可以删除")
    client = TestClient(main.app)

    response = client.delete("/api/chat/sessions/delete-me")

    assert response.status_code == 204
    assert client.get("/api/chat/sessions/delete-me").status_code == 404
    assert client.get("/api/chat/sessions").json() == []
