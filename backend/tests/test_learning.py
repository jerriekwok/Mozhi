from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as main  # noqa: E402
from app.routers import learning  # noqa: E402


def test_learning_plan_uses_rag_and_returns_sources(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_invoke_rag(question: str) -> dict:
        captured["question"] = question
        return {
            "answer": "Start with basic strokes, then study a regular-script copybook.",
            "sources": [
                {
                    "filename": "path.md",
                    "source": "path.md",
                    "chapter_title": "Learning path",
                    "snippet": "Practice in stages.",
                }
            ],
        }

    monkeypatch.setattr(learning, "invoke_rag", fake_invoke_rag)
    response = TestClient(main.app).post(
        "/api/learning/plan",
        json={
            "level": "beginner",
            "style": "kaishu",
            "daily_minutes": 30,
            "goal": "Build a steady foundation",
        },
    )

    assert response.status_code == 200
    assert "30" in captured["question"]
    assert response.json()["plan"].startswith("Start with basic strokes")
    assert response.json()["sources"][0]["file"] == "path.md"


def test_learning_plan_validates_daily_practice_time() -> None:
    response = TestClient(main.app).post(
        "/api/learning/plan",
        json={"level": "beginner", "style": "kaishu", "daily_minutes": 5},
    )

    assert response.status_code == 422
