from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import PROJECT_ROOT, settings  # noqa: E402
from app.services.document_loader import discover_knowledge_base_files  # noqa: E402


def test_all_configured_knowledge_base_files_are_discovered() -> None:
    expected_files = {
        file_path.resolve()
        for source_root in settings.knowledge_base_paths
        for file_path in source_root.rglob("*.md")
    }

    discovered_files = {file_path for file_path, _ in discover_knowledge_base_files()}

    assert settings.chroma_persist_path == PROJECT_ROOT / "data" / "chroma_db"
    assert discovered_files == expected_files
    assert len(discovered_files) >= 17
