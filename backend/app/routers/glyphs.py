from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.glyph_library import GlyphLibrary, GlyphLibraryError


router = APIRouter(prefix="/api/glyphs", tags=["glyphs"])


class GlyphCandidate(BaseModel):
    source: str
    artist: str
    style: str
    copybook: str
    filename: str
    image_url: str


class GlyphCharacterResult(BaseModel):
    character: str
    candidates: list[GlyphCandidate] = Field(default_factory=list)


class GlyphSearchResponse(BaseModel):
    text: str
    source: str | None
    characters: list[GlyphCharacterResult]
    missing_characters: list[str]


@lru_cache(maxsize=1)
def get_glyph_library() -> GlyphLibrary:
    return GlyphLibrary(settings.glyph_library_path)


@router.get("/search", response_model=GlyphSearchResponse)
def search_glyphs(
    text: str = Query(..., min_length=1, max_length=10),
    source: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=12, ge=1, le=30),
) -> GlyphSearchResponse:
    normalized_text = "".join(character for character in text.strip() if not character.isspace())
    if not normalized_text:
        raise HTTPException(status_code=422, detail="text must contain at least one character")

    try:
        characters = get_glyph_library().search(normalized_text, source=source, limit=limit)
    except GlyphLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    missing = [item["character"] for item in characters if not item["candidates"]]
    return GlyphSearchResponse(
        text=normalized_text,
        source=source,
        characters=characters,
        missing_characters=missing,
    )
