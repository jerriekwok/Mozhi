from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool

from app.schemas.common import Source
from app.services.memory import add_message, delete_chat_session, get_chat_session, list_chat_sessions
from app.services.rag_chain import invoke_rag, stream_rag
from app.services.source_mapper import map_raw_sources


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    session_id: str | None = Field(default=None, description="Conversation identifier")


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    session_id: str


class SavedMessage(BaseModel):
    id: int
    role: str
    content: str
    sources: list[Source] = Field(default_factory=list)
    image_url: str | None = None
    created_at: int


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    created_at: int
    updated_at: int


class ChatSessionDetail(ChatSessionSummary):
    messages: list[SavedMessage] = Field(default_factory=list)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _require_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="question must not be blank")
    return normalized


@router.get("/sessions", response_model=list[ChatSessionSummary])
async def get_sessions() -> list[dict[str, Any]]:
    """Return saved conversations in the order displayed by the chat sidebar."""
    return await run_in_threadpool(list_chat_sessions)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(session_id: str) -> dict[str, Any]:
    """Return one saved conversation and all of its messages."""
    session = await run_in_threadpool(get_chat_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str) -> None:
    """Permanently delete one locally saved conversation."""
    deleted = await run_in_threadpool(delete_chat_session, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


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
    sources = map_raw_sources(result.get("sources") or [])

    # Save only after generation so the current question is not duplicated in its own prompt.
    add_message(session_id, "human", question)
    add_message(session_id, "ai", answer, [source.model_dump() for source in sources])

    return ChatResponse(answer=answer, sources=sources, session_id=session_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """Stream RAG response chunks as Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())
    question = _require_question(request.question)
    logger.info("[chat/stream] session=%s ip=%s", session_id, _client_ip(http_request))

    async def event_generator() -> AsyncIterator[str]:
        full_answer = ""
        question_saved = False
        mapped_sources: list[Source] = []

        try:
            # The local model is exposed as a synchronous generator.  Advance it
            # in a worker thread so history requests can run during generation.
            async for event in iterate_in_threadpool(stream_rag(question, session_id=session_id)):
                event_type = event.get("type", "chunk")
                if event_type == "sources":
                    mapped_sources = map_raw_sources(event.get("sources") or [])
                    payload = {"sources": [item.model_dump() for item in mapped_sources]}
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
                    add_message(
                        session_id,
                        "ai",
                        full_answer,
                        [source.model_dump() for source in mapped_sources],
                    )
                    yield f"event: done\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("[chat/stream] RAG stream failed: session=%s", session_id)
            if not question_saved:
                add_message(session_id, "human", question)
            if full_answer:
                add_message(
                    session_id,
                    "ai",
                    full_answer,
                    [source.model_dump() for source in mapped_sources],
                )
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
