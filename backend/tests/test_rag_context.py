from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import rag_chain  # noqa: E402


def test_referential_follow_up_uses_last_user_question(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_chain,
        "get_chat_history",
        lambda session_id: [
            {"role": "human", "content": "请介绍颜真卿。"},
            {"role": "ai", "content": "颜真卿是唐代书法家。"},
        ],
    )

    query = rag_chain._build_retrieval_query("他的代表碑帖有哪些？", "test-session")

    assert query == "请介绍颜真卿。\n他的代表碑帖有哪些？"


def test_independent_question_keeps_its_original_retrieval_query(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_chain,
        "get_chat_history",
        lambda session_id: [{"role": "human", "content": "请介绍颜真卿。"}],
    )

    assert rag_chain._build_retrieval_query("什么是楷书？", "test-session") == "什么是楷书？"
