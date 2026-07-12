from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.main as main  # noqa: E402
from app.routers import glyphs  # noqa: E402
from app.services.glyph_library import GlyphLibrary  # noqa: E402


def create_library(tmp_path: Path) -> GlyphLibrary:
    source = "颜真卿 多宝塔碑 楷书"
    (tmp_path / source / "永").mkdir(parents=True)
    (tmp_path / source / "永" / "001.gif").write_bytes(b"gif")
    (tmp_path / "index.json").write_text(
        json.dumps({"永": {source: ["001.gif"]}, "缺": {}}),
        encoding="utf-8",
    )
    return GlyphLibrary(tmp_path)


def test_glyph_library_returns_existing_images_and_metadata(tmp_path) -> None:
    library = create_library(tmp_path)

    result = library.search("永缺", source="颜真卿 多宝塔碑 楷书")

    assert result[0]["character"] == "永"
    assert result[0]["candidates"][0]["artist"] == "颜真卿"
    assert result[0]["candidates"][0]["copybook"] == "多宝塔碑"
    assert result[0]["candidates"][0]["image_url"].endswith("/001.gif")
    assert result[1] == {"character": "缺", "candidates": []}


def test_glyph_search_endpoint_reports_missing_characters(tmp_path, monkeypatch) -> None:
    library = create_library(tmp_path)
    monkeypatch.setattr(glyphs, "get_glyph_library", lambda: library)

    response = TestClient(main.app).get(
        "/api/glyphs/search",
        params={"text": "永缺", "source": "颜真卿 多宝塔碑 楷书"},
    )

    assert response.status_code == 200
    assert response.json()["missing_characters"] == ["缺"]
    assert len(response.json()["characters"][0]["candidates"]) == 1
