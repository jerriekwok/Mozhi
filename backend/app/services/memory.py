from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama

from app.core.config import settings

logger = logging.getLogger(__name__)

# Chat records are kept outside the knowledge-base index, so rebuilding the
# vector database will not erase a user's conversations.
_CHAT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "mozhi.sqlite3"
_MAX_HISTORY_TURNS = 6
_MAX_HISTORY_CHARS = 3000
_DEFAULT_TITLE = "新对话"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _get_session_key(session_id: str | None) -> str:
    return session_id or str(uuid.uuid4())


def _connect() -> sqlite3.Connection:
    _CHAT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_CHAT_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('human', 'ai')),
            content TEXT NOT NULL,
            sources_json TEXT NOT NULL DEFAULT '[]',
            image_url TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
        ON chat_messages(session_id, created_at, id);
        """
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(chat_messages)")}
    if "image_url" not in columns:
        connection.execute("ALTER TABLE chat_messages ADD COLUMN image_url TEXT")
    return connection


def _title_from_message(content: str) -> str:
    compact = " ".join(content.split())
    if not compact:
        return _DEFAULT_TITLE
    return compact[:16] + ("..." if len(compact) > 16 else "")


def _ensure_session(connection: sqlite3.Connection, session_id: str) -> None:
    now = _now_ms()
    connection.execute(
        """
        INSERT INTO chat_sessions (id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, _DEFAULT_TITLE, now, now),
    )


def _parse_sources(raw: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def get_chat_history(session_id: str | None) -> list[dict[str, str]]:
    """Return the recent context used by RAG, without creating a new session."""
    if not session_id:
        return []

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (session_id, _MAX_HISTORY_TURNS * 2),
        ).fetchall()

    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def add_message(
    session_id: str | None,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    image_url: str | None = None,
) -> str:
    """Persist one message and return the actual conversation id."""
    if role not in {"human", "ai"}:
        raise ValueError("role must be 'human' or 'ai'")

    key = _get_session_key(session_id)
    now = _now_ms()
    serialized_sources = json.dumps(sources or [], ensure_ascii=False)

    with _connect() as connection:
        _ensure_session(connection, key)
        connection.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, sources_json, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key, role, content, serialized_sources, image_url, now),
        )

        if role == "human":
            connection.execute(
                """
                UPDATE chat_sessions
                SET title = CASE WHEN title = ? THEN ? ELSE title END,
                    updated_at = ?
                WHERE id = ?
                """,
                (_DEFAULT_TITLE, _title_from_message(content), now, key),
            )
        else:
            connection.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, key),
            )
    return key


def list_chat_sessions(limit: int = 50) -> list[dict[str, Any]]:
    """List saved conversations, newest first, without loading their messages."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat_session(session_id: str) -> dict[str, Any] | None:
    """Load a saved conversation, including source references for each answer."""
    with _connect() as connection:
        session = connection.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            return None
        rows = connection.execute(
            """
            SELECT id, role, content, sources_json, image_url, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (session_id,),
        ).fetchall()

    result = dict(session)
    result["messages"] = [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "sources": _parse_sources(row["sources_json"]),
            "image_url": row["image_url"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return result


def delete_chat_session(session_id: str) -> bool:
    """Delete a saved conversation. Returns whether it existed."""
    with _connect() as connection:
        result = connection.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    return result.rowcount > 0


def format_history(session_id: str | None) -> str:
    """Format the recent chat turns for the RAG prompt."""
    history = get_chat_history(session_id)
    if not history:
        return ""

    text = "\n".join(
        f"{'用户' if message['role'] == 'human' else '助手'}：{message['content']}"
        for message in history
    )
    return _compress_history(history) if len(text) > _MAX_HISTORY_CHARS else text


def _compress_history(history: list[dict[str, str]]) -> str:
    """Use the configured LLM only when the recent context exceeds its budget."""
    try:
        llm = ChatOllama(
            model=settings.LLM_MODEL,
            temperature=0.3,
            base_url=settings.OLLAMA_BASE_URL,
            client_kwargs={"trust_env": False},
            async_client_kwargs={"trust_env": False},
        )
        recent = history[-4:]
        earlier = history[:-4]
        summary = ""
        if earlier:
            conversation_text = "\n".join(
                f"{'用户' if item['role'] == 'human' else '助手'}：{item['content']}"
                for item in earlier
            )
            try:
                summary = llm.invoke(
                    "请简洁总结以下早期对话，保留人名、作品和用户偏好等关键信息，控制在 200 字内。\n\n"
                    f"{conversation_text}"
                ).content.strip()
            except Exception as exc:
                logger.warning("[memory] History compression failed: %s", exc)

        parts = [f"【历史对话总结】{summary}"] if summary else []
        parts.extend(
            f"{'用户' if item['role'] == 'human' else '助手'}：{item['content']}"
            for item in recent
        )
        return "\n".join(parts)
    except Exception as exc:
        logger.warning("[memory] History compression failed: %s", exc)
        return "\n".join(
            f"{'用户' if item['role'] == 'human' else '助手'}：{item['content']}"
            for item in history[-4:]
        )
