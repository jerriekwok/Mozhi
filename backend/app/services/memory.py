from __future__ import annotations

import logging
import threading
import uuid
from typing import Dict, List, Tuple

from langchain_ollama import ChatOllama

from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局内存存储，按 session_id 隔离
_memory_store: Dict[str, List[Dict[str, str]]] = {}
_lock = threading.RLock()

# 配置项
_MAX_HISTORY_TURNS = 6  # 保留最近 6 轮对话（用户 + AI = 12 条消息）
_MAX_HISTORY_CHARS = 3000  # 历史字符数上限，超过时触发压缩


def _get_session_key(session_id: str | None) -> str:
    """确保返回有效的 session_id。"""
    return session_id or str(uuid.uuid4())


def get_chat_history(session_id: str | None) -> List[Dict[str, str]]:
    """获取指定 session 的对话历史（深拷贝，防止外部修改）。"""
    key = _get_session_key(session_id)
    with _lock:
        history = _memory_store.get(key, [])
        return [dict(msg) for msg in history]


def add_message(session_id: str | None, role: str, content: str) -> str:
    """
    向指定 session 添加一条消息，返回实际使用的 session_id。

    role: "human" | "ai"
    """
    key = _get_session_key(session_id)
    with _lock:
        if key not in _memory_store:
            _memory_store[key] = []
        _memory_store[key].append({"role": role, "content": content})
        # 裁剪：保留最近 _MAX_HISTORY_TURNS 轮（每轮 = 2 条消息）
        max_messages = _MAX_HISTORY_TURNS * 2
        if len(_memory_store[key]) > max_messages:
            _memory_store[key] = _memory_store[key][-max_messages:]
    return key


def clear_history(session_id: str | None) -> str:
    """清空指定 session 的历史，返回 session_id。"""
    key = _get_session_key(session_id)
    with _lock:
        _memory_store.pop(key, None)
    return key


def format_history(session_id: str | None) -> str:
    """
    将对话历史格式化为字符串，供 Prompt 使用。
    如果历史过长，会先进行压缩（总结）。
    """
    history = get_chat_history(session_id)
    if not history:
        return ""

    lines: List[str] = []
    for msg in history:
        role_label = "用户" if msg["role"] == "human" else "助手"
        lines.append(f"{role_label}：{msg['content']}")

    text = "\n".join(lines)

    # 如果历史字符数超过阈值，进行压缩总结
    if len(text) > _MAX_HISTORY_CHARS:
        text = _compress_history(history)

    return text


def _compress_history(history: List[Dict[str, str]]) -> str:
    """
    使用 LLM 对过长的历史对话进行总结压缩，保留关键信息。
    """
    try:
        llm = ChatOllama(
            model=settings.LLM_MODEL,
            temperature=0.3,
            base_url=settings.OLLAMA_BASE_URL,
            client_kwargs={"trust_env": False},
            async_client_kwargs={"trust_env": False},
        )

        # 取最近 2 轮完整保留，其余早期对话进行总结
        recent = history[-4:]  # 最近 2 轮（4 条消息）
        earlier = history[:-4]

        summary = ""
        if earlier:
            conversation_text = "\n".join(
                f"{'用户' if m['role'] == 'human' else '助手'}：{m['content']}"
                for m in earlier
            )
            prompt = (
                "请对以下对话历史进行简洁总结，保留关键事实和背景信息，"
                "不要遗漏用户提到的具体人名、书名、概念等重要信息。"
                "总结控制在 200 字以内。\n\n"
                f"{conversation_text}\n\n"
                "总结："
            )
            try:
                summary = llm.invoke(prompt).content.strip()
            except Exception as exc:
                logger.warning("[memory] History compression failed: %s", exc)
                # 压缩失败时，直接截断早期历史
                summary = "（早期对话已省略）"

        parts: List[str] = []
        if summary:
            parts.append(f"【历史对话总结】{summary}")
        for m in recent:
            role_label = "用户" if m["role"] == "human" else "助手"
            parts.append(f"{role_label}：{m['content']}")

        return "\n".join(parts)
    except Exception as exc:
        logger.warning("[memory] _compress_history failed: %s", exc)
        # 降级：直接截断保留后半部分
        return "\n".join(
            f"{'用户' if m['role'] == 'human' else '助手'}：{m['content']}"
            for m in history[-4:]
        )
