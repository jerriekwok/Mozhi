from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.memory import add_message
from app.services.rag_chain import invoke_rag, stream_rag


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class Source(BaseModel):
    title: str = Field(default="", description="Source title or section heading")
    content: str = Field(default="", description="Retrieved source excerpt")
    file: str = Field(default="", description="Source file name")

#数据模型验证
class ChatRequest(BaseModel):#定义聊天请求的输入数据格式
    question: str = Field(..., min_length=1, description="User question")
    session_id: str | None = Field(default=None, description="Conversation identifier")


class ChatResponse(BaseModel):#定义接口返回的数据格式
    answer: str
    sources: list[Source] = Field(default_factory=list)
    session_id: str


def _map_raw_sources(raw_sources: list[dict[str, Any]]) -> list[Source]:
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


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _require_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="question must not be blank")
    return normalized


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Return a complete RAG response with sources and conversation state."""
    session_id = request.session_id or str(uuid.uuid4())
    question = _require_question(request.question)
    logger.info("[chat] session=%s ip=%s", session_id, _client_ip(http_request))

    try:
        result = await run_in_threadpool(invoke_rag, question, session_id)
    except Exception as exc:
        logger.exception("[chat] RAG invoke failed: session=%s", session_id)
        raise HTTPException(status_code=503, detail="RAG service is temporarily unavailable") from exc

    answer = str(result.get("answer") or "").strip()
    if not answer:
        answer = "根据现有资料无法回答。"
    sources = _map_raw_sources(result.get("sources") or [])

    # Save only after generation so the current question is not duplicated in its own prompt.
    add_message(session_id, "human", question)
    add_message(session_id, "ai", answer)

    return ChatResponse(answer=answer, sources=sources, session_id=session_id)


#定义流式接口
@router.post("/stream")
async def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """Stream RAG response chunks as Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4()) #生成会话ID
    question = _require_question(request.question) #验证问题非空
    logger.info("[chat/stream] session=%s ip=%s", session_id, _client_ip(http_request))

    async def event_generator() -> AsyncIterator[str]:
        full_answer = ""
        question_saved = False

        try:
            for event in stream_rag(question, session_id=session_id):
                event_type = event.get("type", "chunk")
                if event_type == "sources":
                    payload = {"sources": [item.model_dump() for item in _map_raw_sources(event.get("sources") or [])]}
                    yield f"event: sources\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    add_message(session_id, "human", question)
                    question_saved = True
                elif event_type == "chunk":
                    content = str(event.get("content") or "")
                    full_answer += content
                    yield f"event: chunk\ndata: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                elif event_type == "done":
                    if not question_saved:
                        add_message(session_id, "human", question)
                    add_message(session_id, "ai", full_answer)
                    yield f"event: done\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("[chat/stream] RAG stream failed: session=%s", session_id)
            if not question_saved:
                add_message(session_id, "human", question)
            if full_answer:
                add_message(session_id, "ai", full_answer)
            payload = {"error": "RAG stream is temporarily unavailable"}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )
