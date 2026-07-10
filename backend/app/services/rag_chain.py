from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Iterable, Iterator, List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.services.memory import format_history
from app.services.vector_store import get_retriever, get_vector_store

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def _snippet(text: str, limit: int = 180) -> str:
    cleaned = _normalize_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def _document_source(doc: Document) -> str:
    metadata = doc.metadata or {}
    source = metadata.get("source") or metadata.get("filename") or "unknown"
    return str(source)


def _document_filename(doc: Document) -> str:
    metadata = doc.metadata or {}
    return str(metadata.get("filename") or metadata.get("source") or "unknown")


def _format_heading_path(metadata: dict[str, Any]) -> str:
    heading_path = metadata.get("heading_path")
    if isinstance(heading_path, list) and heading_path:
        return " > ".join(str(item) for item in heading_path if item)

    chapter_title = metadata.get("chapter_title")
    if chapter_title:
        return str(chapter_title)

    title = metadata.get("title")
    if title:
        return str(title)

    return ""


def _format_context_documents(docs: List[Document]) -> str:
    if not docs:
        return "未检索到相关资料。"

    blocks: List[str] = []
    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        source = _document_source(doc)
        filename = _document_filename(doc)
        heading_path = _format_heading_path(metadata)
        chunk_index = metadata.get("chunk_index", index - 1)
        content = _normalize_text(doc.page_content)

        block_lines = [
            f"[资料{index}]",
            f"source: {source}",
            f"filename: {filename}",
            f"chunk_index: {chunk_index}",
        ]
        if heading_path:
            block_lines.append(f"chapter: {heading_path}")
        block_lines.append(f"text: {content}")
        blocks.append("\n".join(block_lines))

    return "\n\n".join(blocks)


def _format_sources(docs: List[Document]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()

    for doc in docs:
        metadata = doc.metadata or {}
        source = _document_source(doc)
        filename = _document_filename(doc)
        chunk_index = int(metadata.get("chunk_index", 0) or 0)
        dedup_key = (source, filename, chunk_index)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        sources.append(
            {
                "source": source,
                "filename": filename,
                "chunk_index": chunk_index,
                "chapter_title": metadata.get("chapter_title"),
                "heading_path": metadata.get("heading_path"),
                "snippet": _snippet(doc.page_content),
            }
        )

    return sources


def _build_prompt() -> ChatPromptTemplate:
    system_prompt = (
        "你是一位精通中国书法的学者，擅长解答书法相关问题，尤其熟悉楷书、行书、草书、隶书、篆书、碑帖、笔法、"
        "结字、章法、临摹、鉴赏与书法史。"
        "\n\n"
        "你必须严格基于提供的上下文回答问题，不得引入未给出的事实或个人臆测。"
        "如果上下文不足以支撑回答，请直接输出：根据现有资料无法回答。"
        "\n\n"
        "回答要求："
        "\n1. 使用中文回答。"
        "\n2. 结构必须按以下顺序输出：定义/概述 -> 详细说明 -> 相关推荐。"
        "\n3. 结合上下文中的来源信息，尽量在回答中自然提及相关资料来源。"
        "\n4. 若问题包含多个子问题，请逐一回应，但仍保持上述结构。"
        "\n5. 推荐给出的建议应尽量贴合书法学习、创作、临摹、鉴赏或理论研读场景。"
        "\n6. 若上下文信息不足，除固定短语外不要编造补充内容。"
    )

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "{chat_history}"
                "问题：{question}\n\n"
                "可用上下文：\n{context}\n\n"
                "请按照要求输出答案。",
            ),
        ]
    )


def _build_answer_chain():
    prompt = _build_prompt()
    llm = ChatOllama(
        model=settings.LLM_MODEL,
        temperature=0.7,
        base_url=settings.OLLAMA_BASE_URL,
        client_kwargs={"trust_env": False},
        async_client_kwargs={"trust_env": False},
    )
    return prompt | llm | StrOutputParser()


def _build_rag_input(payload: Dict[str, Any]) -> Dict[str, str]:
    question = str(payload.get("question", "")).strip()
    docs = payload.get("docs") or []
    if not isinstance(docs, list):
        docs = list(docs)

    chat_history = str(payload.get("chat_history", "")).strip()
    if chat_history:
        chat_history = f"以下是对话历史：\n{chat_history}\n\n"

    return {
        "question": question,
        "context": _format_context_documents(docs),
        "chat_history": chat_history,
    }


@lru_cache(maxsize=1)
def _get_answer_chain_cached():
    return _build_answer_chain()


@lru_cache(maxsize=1)
def _get_retriever_cached():
    _get_vector_store_cached()
    return get_retriever()


@lru_cache(maxsize=1)
def _get_vector_store_cached():
    return get_vector_store()


@lru_cache(maxsize=1)
def get_rag_chain():
    """Return an executable LCEL RAG chain for question -> retrieval -> generation."""
    retriever = _get_retriever_cached()
    answer_chain = _get_answer_chain_cached()

    return (
        RunnableParallel(question=RunnablePassthrough(), docs=retriever)
        | RunnableLambda(_build_rag_input)
        | answer_chain
    )


def _retrieve_docs(question: str) -> List[Document]:
    retriever = _get_retriever_cached()
    docs = retriever.invoke(question)
    if isinstance(docs, list):
        return docs
    return list(docs)


def invoke_rag(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Execute the RAG pipeline and return answer plus source citations.
    Supports multi-turn conversation via session_id.
    """
    question = str(question).strip()
    chat_history = format_history(session_id) if session_id else ""

    docs = _retrieve_docs(question)
    if not docs:
        return {
            "answer": "根据现有资料无法回答",
            "sources": [],
        }

    answer = _get_answer_chain_cached().invoke(
        _build_rag_input({"question": question, "docs": docs, "chat_history": chat_history})
    )

    return {
        "answer": answer,
        "sources": _format_sources(docs),
    }


def stream_rag(question: str, session_id: str | None = None) -> Iterator[dict[str, Any]]:
    """
    Stream answer chunks for SSE while also emitting source references.
    Supports multi-turn conversation via session_id.
    """
    question = str(question).strip()
    chat_history = format_history(session_id) if session_id else ""

    docs = _retrieve_docs(question)
    yield {"type": "sources", "sources": _format_sources(docs)}

    if not docs:
        yield {"type": "chunk", "content": "根据现有资料无法回答"}
        yield {"type": "done"}
        return

    chunk_iter = _get_answer_chain_cached().stream(
        _build_rag_input({"question": question, "docs": docs, "chat_history": chat_history})
    )
    for chunk in chunk_iter:
        if chunk:
            yield {"type": "chunk", "content": str(chunk)}

    yield {"type": "done"}
