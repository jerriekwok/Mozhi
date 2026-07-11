from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Iterator, List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.services.memory import format_history, get_chat_history
from app.services.vector_store import get_retriever, get_vector_store

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_CONTEXTUAL_QUERY_MARKERS = ("他", "她", "它", "这", "那", "上述", "刚才", "前面", "前述")


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
    seen: set[tuple[str, str]] = set()

    for doc in docs:
        metadata = doc.metadata or {}
        source = _document_source(doc)
        filename = _document_filename(doc)
        chunk_index = int(metadata.get("chunk_index", 0) or 0)
        dedup_key = (source, filename)
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
    """Build a concise, teacher-like prompt for grounded calligraphy answers."""
    system_prompt = """
你是“墨智”的书法老师。你熟悉中国书法、碑帖、书家和临摹方法。请像正常聊天一样，用现代、口语化但不随便的中文回答；说人话，不要像在背资料卡、写研究报告或故意模仿古人说话。

只能依据提供的资料回答事实性问题；资料不足时，请坦率说明“现有资料不足以确认这一点”，不要补造细节。

回答要求：
- 先直接回答用户最关心的问题，通常用一两句话说清核心判断。
- 再根据问题需要补充最有价值的背景、风格观察或练习方法；不需要面面俱到。
- 使用自然段。只有确实需要比较、列步骤或给练习清单时才使用短列表。
- 避免固定的“定义/概述、详细说明、相关推荐”标题，也不要每句话都标注“资料1、资料2”。资料引用会由界面统一展示。
- 避免重复同义形容词和空泛鼓励。对初学者给出一两条可以马上练习的具体建议。
- 不用“书友安好”“笔墨洗砚”“愿与君共赏”“雅正”等文绉绉的套话；不需要寒暄时就直接回答问题。
- 默认控制在 250 到 500 个中文字符；只有用户明确要求深入展开时再写长一些。
""".strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "{chat_history}用户问题：{question}\n\n"
                "可参考资料：\n{context}\n\n"
                "请结合资料，自然地回答这个问题。",
            ),
        ]
    )


def _build_direct_answer_prompt() -> ChatPromptTemplate:
    """Prompt used when no local knowledge source is sufficiently relevant."""
    system_prompt = """
你是“墨智”，一位正常聊天、专业但不端着的书法学习助手。使用自然的现代中文，不要文言文、古风腔或过度客气的套话。
当前没有找到足够相关的本地资料，因此不要伪造资料来源，也不要把不相关的内容硬套进回答。
请根据用户问题自然回答：招呼、感谢、告别或使用帮助应简短回应；一般性书法问题可用你的通用知识说明；
对无法可靠确认的具体事实，应坦率说明不确定，不要编造细节。不要提及“检索”“知识库”或“参考资料”。
例如用户说“你好”，可以回答“你好！想了解哪方面的书法？”；不要回答“书友安好”“笔墨洗砚”等。
""".strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{chat_history}用户问题：{question}"),
        ]
    )


def _build_answer_chain():
    prompt = _build_prompt()
    llm = ChatOllama(
        model=settings.LLM_MODEL,
        temperature=0.35,
        keep_alive=settings.MODEL_KEEP_ALIVE,
        base_url=settings.OLLAMA_BASE_URL,
        client_kwargs={"trust_env": False},
        async_client_kwargs={"trust_env": False},
    )
    return prompt | llm | StrOutputParser()


def _build_direct_answer_chain():
    prompt = _build_direct_answer_prompt()
    llm = ChatOllama(
        model=settings.LLM_MODEL,
        temperature=0.35,
        keep_alive=settings.MODEL_KEEP_ALIVE,
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


def _build_direct_answer_input(question: str, chat_history: str) -> Dict[str, str]:
    formatted_history = chat_history.strip()
    if formatted_history:
        formatted_history = f"以下是对话历史：\n{formatted_history}\n\n"
    return {"question": question, "chat_history": formatted_history}


def _build_retrieval_query(question: str, session_id: str | None) -> str:
    """Expand referential follow-up questions with the last user question."""
    if not session_id or not any(marker in question for marker in _CONTEXTUAL_QUERY_MARKERS):
        return question

    for message in reversed(get_chat_history(session_id)):
        if message.get("role") == "human" and message.get("content"):
            return f"{message['content']}\n{question}"

    return question


@lru_cache(maxsize=1)
def _get_answer_chain_cached():
    return _build_answer_chain()


@lru_cache(maxsize=1)
def _get_direct_answer_chain_cached():
    return _build_direct_answer_chain()


@lru_cache(maxsize=1)
def _get_retriever_cached():
    _get_vector_store_cached()
    return get_retriever()


@lru_cache(maxsize=1)
def _get_vector_store_cached():
    return get_vector_store()


def _retrieve_docs(question: str) -> List[Document]:
    vector_store = _get_vector_store_cached()
    scored_docs = vector_store.similarity_search_with_relevance_scores(question, k=4)
    threshold = settings.RETRIEVAL_SCORE_THRESHOLD
    docs = [doc for doc, score in scored_docs if score >= threshold]
    best_score = max((score for _, score in scored_docs), default=0.0)
    logger.info(
        "[retrieval] query=%r best_score=%.3f threshold=%.3f matched=%d",
        question,
        best_score,
        threshold,
        len(docs),
    )
    return docs


def invoke_rag(question: str, session_id: str | None = None) -> dict[str, Any]:
    """
    Execute the RAG pipeline and return answer plus source citations.
    Supports multi-turn conversation via session_id.
    """
    question = str(question).strip()
    chat_history = format_history(session_id) if session_id else ""

    docs = _retrieve_docs(_build_retrieval_query(question, session_id))
    if not docs:
        answer = _get_direct_answer_chain_cached().invoke(_build_direct_answer_input(question, chat_history))
        return {"answer": str(answer).strip(), "sources": []}

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

    docs = _retrieve_docs(_build_retrieval_query(question, session_id))
    if not docs:
        yield {"type": "sources", "sources": []}
        for chunk in _get_direct_answer_chain_cached().stream(_build_direct_answer_input(question, chat_history)):
            if chunk:
                yield {"type": "chunk", "content": str(chunk)}
        yield {"type": "done"}
        return

    yield {"type": "sources", "sources": _format_sources(docs)}

    chunk_iter = _get_answer_chain_cached().stream(
        _build_rag_input({"question": question, "docs": docs, "chat_history": chat_history})
    )
    for chunk in chunk_iter:
        if chunk:
            yield {"type": "chunk", "content": str(chunk)}

    yield {"type": "done"}
