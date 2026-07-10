from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.memory import add_message
from app.services.rag_chain import invoke_rag, stream_rag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class Source(BaseModel):
    title: str = Field(default="", description="来源标题或章节名")
    content: str = Field(default="", description="内容摘要片段")
    file: str = Field(default="", description="来源文件名")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    session_id: str | None = Field(default=None, description="会话 ID，为空时后端生成")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="完整回答")
    sources: list[Source] = Field(default_factory=list, description="引用来源列表")
    session_id: str = Field(..., description="会话 ID")


def _map_raw_sources(raw_sources: list[dict[str, Any]]) -> list[Source]:
    """将 rag_chain 返回的原始 source 字典映射为 Source 模型。"""
    mapped: list[Source] = []
    for s in raw_sources:
        # 优先使用 chapter_title / heading_path 作为 title
        title = s.get("chapter_title") or ""
        if not title:
            heading = s.get("heading_path")
            if isinstance(heading, list):
                title = " > ".join(str(h) for h in heading if h)
            else:
                title = str(heading or "")
        if not title:
            title = s.get("source") or ""

        snippet = s.get("snippet") or ""
        filename = s.get("filename") or s.get("source") or ""

        mapped.append(Source(title=title, content=snippet, file=filename))
    return mapped


def _client_ip(req: Request) -> str:
    client = req.client
    if client is None:
        return "unknown"
    return client.host or "unknown"


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """
    非流式 RAG 问答接口，返回完整回答与引用来源。
    支持多轮对话：通过 session_id 识别会话，自动保存对话历史。
    """
    session_id = request.session_id or str(uuid.uuid4())
    question = request.question.strip()
    client_ip = _client_ip(req)

    logger.info("[chat] session=%s ip=%s question=%s", session_id, client_ip, question)

    # 保存用户问题到历史
    add_message(session_id, "human", question)

    try:
        result = invoke_rag(question, session_id=session_id)
    except Exception as exc:
        logger.exception("[chat] RAG invoke failed: session=%s", session_id)
        raise HTTPException(status_code=500, detail=f"RAG 调用失败：{exc}") from exc

    sources = _map_raw_sources(result.get("sources", []))
    answer = result.get("answer", "")

    # 保存 AI 回答到历史
    add_message(session_id, "ai", answer)

    logger.info("[chat] session=%s answer_len=%d sources_count=%d", session_id, len(answer), len(sources))

    return ChatResponse(answer=answer, sources=sources, session_id=session_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request) -> StreamingResponse:
    """
    流式 RAG 问答接口，使用 SSE（Server-Sent Events）输出。
    支持多轮对话：通过 session_id 识别会话，自动保存对话历史。

    SSE 事件格式：
    - event: sources\n  data: {"sources": [...]}\n\n
    - event: chunk\n   data: {"content": "..."}\n\n
    - event: done\n    data: {"session_id": "..."}\n\n
    """
    session_id = request.session_id or str(uuid.uuid4())
    question = request.question.strip()
    client_ip = _client_ip(req)

    logger.info("[chat/stream] session=%s ip=%s question=%s", session_id, client_ip, question)

    # 保存用户问题到历史
    add_message(session_id, "human", question)

    async def _event_generator() -> AsyncIterator[str]:
        full_answer = ""
        try:
            for event in stream_rag(question, session_id=session_id):
                event_type = event.get("type", "chunk")
                if event_type == "sources":
                    sources = _map_raw_sources(event.get("sources", []))
                    payload = {"sources": [s.model_dump() for s in sources]}
                    yield f"event: sources\ndata: {__import__('json').dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "chunk":
                    content = event.get("content", "")
                    full_answer += content
                    payload = {"content": content}
                    yield f"event: chunk\ndata: {__import__('json').dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "done":
                    # 保存完整回答到历史
                    add_message(session_id, "ai", full_answer)
                    yield f"event: done\ndata: {{\"session_id\": \"{session_id}\"}}\n\n"
                else:
                    # 未知类型透传
                    yield f"event: {event_type}\ndata: {__import__('json').dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("[chat/stream] RAG stream failed: session=%s", session_id)
            # 异常时也尝试保存已收到的部分回答
            if full_answer:
                add_message(session_id, "ai", full_answer)
            payload = {"error": f"流式输出异常：{exc}"}
            yield f"event: error\ndata: {__import__('json').dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )
