from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any
from urllib.parse import quote


class GlyphLibraryError(RuntimeError):
    """Raised when the local glyph library is unavailable or malformed."""


class GlyphLibrary:
    """Read-only query layer for the bundled calligraphy-community index."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path

    @cached_property
    def index(self) -> dict[str, dict[str, list[str]]]:
        index_path = self.root_path / "index.json"
        if not index_path.is_file():
            raise GlyphLibraryError(f"Glyph library index was not found: {index_path}")
        try:
            raw_data = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GlyphLibraryError("Glyph library index could not be read") from exc
        if not isinstance(raw_data, dict):
            raise GlyphLibraryError("Glyph library index has an invalid format")
        return raw_data

    def search(self, text: str, source: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
        return [self._search_character(character, source, limit) for character in text if not character.isspace()]

    def _search_character(self, character: str, source: str | None, limit: int) -> dict[str, Any]:
        source_map = self.index.get(character, {})
        if not isinstance(source_map, dict):
            source_map = {}

        selected_sources = {source: source_map.get(source, [])} if source else source_map
        candidates: list[dict[str, str]] = []
        for source_name, filenames in selected_sources.items():
            if not isinstance(source_name, str) or not isinstance(filenames, list):
                continue
            metadata = parse_source_name(source_name)
            for filename in filenames:
                if not isinstance(filename, str):
                    continue
                image_path = self.root_path / source_name / character / filename
                if not image_path.is_file():
                    continue
                candidates.append(
                    {
                        "source": source_name,
                        "artist": metadata["artist"],
                        "style": metadata["style"],
                        "copybook": metadata["copybook"],
                        "filename": filename,
                        "image_url": f"/glyph-library/{quote(source_name)}/{quote(character)}/{quote(filename)}",
                    }
                )
                if len(candidates) >= limit:
                    break
            if len(candidates) >= limit:
                break

        return {"character": character, "candidates": candidates}


def parse_source_name(source_name: str) -> dict[str, str]:
    """Split labels such as '顏真卿 多寶塔碑 楷書' for display and filtering."""
    parts = source_name.split()
    if len(parts) < 2:
        return {"artist": source_name, "copybook": "", "style": ""}
    return {
        "artist": parts[0],
        "copybook": " ".join(parts[1:-1]),
        "style": parts[-1],
    }
