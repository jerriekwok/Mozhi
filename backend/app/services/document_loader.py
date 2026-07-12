from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.services.vector_store import get_vector_store

#文档加载与索引

logger = logging.getLogger(__name__)

SEPARATORS = ["\n\n", "\n", "\u3002", "\uff0c", " ", ""]
_MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

try:
    from langchain_community.document_loaders import UnstructuredMarkdownLoader  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    UnstructuredMarkdownLoader = None


def _knowledge_base_paths() -> tuple[Path, ...]:
    return settings.knowledge_base_paths


def _discover_markdown_files(directory: str | Path) -> List[Path]:
    """Discover all Markdown files under a directory recursively."""
    path = Path(directory).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        logger.warning("Knowledge base directory does not exist: %s", path)
        return []

    files = sorted({file.resolve() for file in path.rglob("*.md") if file.is_file()})
    logger.info("Discovered %d markdown files in %s", len(files), path)
    return files


def _relative_source(file_path: Path, source_root: Path) -> str:
    try:
        return str(Path(source_root.name) / file_path.resolve().relative_to(source_root))
    except ValueError:
        return file_path.name


def discover_knowledge_base_files() -> List[tuple[Path, Path]]:
    """Discover all Markdown files from every configured knowledge-base directory."""
    discovered: List[tuple[Path, Path]] = []
    seen: set[Path] = set()

    for source_root in _knowledge_base_paths():
        for file_path in _discover_markdown_files(source_root):
            resolved = file_path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append((resolved, source_root))

    logger.info(
        "Discovered %d markdown files across %d knowledge-base directories.",
        len(discovered),
        len(_knowledge_base_paths()),
    )
    return discovered


def _detect_encoding(file_path: Path) -> str:
    try:
        import chardet
    except Exception:
        return "utf-8"

    raw = file_path.read_bytes()
    detected = chardet.detect(raw).get("encoding")
    return detected or "utf-8"


def _load_with_text_loader(file_path: Path) -> List[Document]:
    encoding = _detect_encoding(file_path)
    try:
        loader = TextLoader(
            str(file_path),
            encoding=encoding,
            autodetect_encoding=False,
        )
        return loader.load()
    except Exception as exc:
        logger.warning(
            "TextLoader failed for %s with encoding %s, retrying with UTF-8 autodetect: %s",
            file_path,
            encoding,
            exc,
        )
        loader = TextLoader(
            str(file_path),
            encoding="utf-8",
            autodetect_encoding=True,
        )
        return loader.load()


def _load_single_file(file_path: Path, source_root: Path) -> List[Document]:
    """Load one Markdown file using UnstructuredMarkdownLoader or TextLoader."""
    logger.debug("Loading markdown file: %s", file_path)

    docs: List[Document]
    if UnstructuredMarkdownLoader is not None:
        try:
            docs = UnstructuredMarkdownLoader(str(file_path)).load()
        except Exception as exc:
            logger.warning("UnstructuredMarkdownLoader failed for %s: %s", file_path, exc)
            docs = _load_with_text_loader(file_path)
    else:
        docs = _load_with_text_loader(file_path)

    relative_source = _relative_source(file_path, source_root)
    filename = file_path.name
    title = _extract_document_title(docs)

    for doc in docs:
        doc.metadata = dict(doc.metadata or {})
        doc.metadata.setdefault("source", relative_source)
        doc.metadata.setdefault("filename", filename)
        if title:
            doc.metadata.setdefault("title", title)

    return docs


def _extract_document_title(docs: Iterable[Document]) -> Optional[str]:
    for doc in docs:
        title = _extract_heading(doc.page_content)
        if title:
            return title
    return None


def _extract_heading(text: str) -> Optional[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _MARKDOWN_HEADING_PATTERN.match(stripped)
        if match:
            return match.group(2).strip()
        break
    return None


def _heading_path(text: str) -> List[str]:
    headings: List[str] = []
    for line in text.splitlines():
        match = _MARKDOWN_HEADING_PATTERN.match(line.strip())
        if match:
            headings.append(match.group(2).strip())
    return headings


#文本切块
def _split_documents(docs: List[Document]) -> List[Document]:
    """Split documents with RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_documents(docs)
    for index, chunk in enumerate(chunks):
        chunk.metadata = dict(chunk.metadata or {})
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_id"] = f"{chunk.metadata.get('source', 'unknown')}::{index}"

        headings = _heading_path(chunk.page_content)
        if headings:
            chunk.metadata.setdefault("chapter_title", headings[0])
            chunk.metadata.setdefault("heading_path", headings)

        if "title" not in chunk.metadata:
            derived_title = _extract_heading(chunk.page_content)
            if derived_title:
                chunk.metadata["title"] = derived_title

    logger.info("Split %d documents into %d chunks", len(docs), len(chunks))
    return chunks


def load_and_index_documents() -> int:
    """Load Markdown files from the knowledge base directory and index them."""
    source_files = discover_knowledge_base_files()

    if not source_files:
        logger.warning(
            "No markdown files found in configured directories %s, nothing to index.",
            _knowledge_base_paths(),
        )
        return 0

    all_docs: List[Document] = []
    for file_path, source_root in source_files:
        try:
            all_docs.extend(_load_single_file(file_path, source_root))
        except Exception as exc:
            logger.exception("Failed to load %s: %s", file_path, exc)

    if not all_docs:
        logger.warning("All files failed to load, nothing to index.")
        return 0

    chunks = _split_documents(all_docs)
    if not chunks:
        logger.warning("No chunks produced after splitting.")
        return 0

    try:
        vector_store = get_vector_store()
        logger.info("Adding %d chunks to Chroma collection...", len(chunks))
        vector_store.add_documents(
            chunks,
            ids=[str(chunk.metadata["chunk_id"]) for chunk in chunks],
        )
        logger.info("Successfully indexed %d chunks.", len(chunks))
        return len(chunks)
    except Exception as exc:
        logger.exception("Failed to add documents to vector store: %s", exc)
        raise RuntimeError(f"Failed to index documents: {exc}") from exc


def check_documents_count() -> int:
    """Return the number of documents already stored in the Chroma collection."""
    try:
        vector_store = get_vector_store()
        count = vector_store._collection.count()
        logger.info("Current document count in collection: %d", count)
        return count
    except Exception as exc:
        logger.warning("Unable to check document count: %s", exc)
        return 0
