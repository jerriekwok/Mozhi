from typing import Any

from app.schemas.common import Source


def map_raw_sources(raw_sources: list[dict[str, Any]]) -> list[Source]:
    """Convert RAG metadata into the stable source shape returned by the API."""
    mapped: list[Source] = []
    seen_files: set[str] = set()

    for source in raw_sources:
        filename = str(source.get("filename") or source.get("source") or "")
        if filename and filename in seen_files:
            continue
        seen_files.add(filename)

        heading = source.get("heading_path")
        title = str(source.get("chapter_title") or "")
        if not title and isinstance(heading, list):
            title = " > ".join(str(item) for item in heading if item)
        if not title:
            title = str(heading or source.get("source") or filename)

        mapped.append(
            Source(
                title=title,
                content=str(source.get("snippet") or ""),
                file=filename,
            )
        )

    return mapped
