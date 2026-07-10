#!/usr/bin/env python3
"""Standalone entry point for initializing the knowledge base index."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_loader import check_documents_count, load_and_index_documents


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _setup_logging()
    logger = logging.getLogger("init_knowledge_base")

    logger.info("Starting knowledge base initialization")

    try:
        before = check_documents_count()
        logger.info("Document count before indexing: %d", before)

        indexed = load_and_index_documents()
        after = check_documents_count()

        logger.info("Newly indexed chunks: %d", indexed)
        logger.info("Document count after indexing: %d", after)

        if indexed == 0:
            logger.warning("No documents were indexed. Please check data/knowledge/.")
            return 0

        logger.info("Knowledge base initialization completed successfully.")
        return 0
    except Exception as exc:
        logger.exception("Knowledge base initialization failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
