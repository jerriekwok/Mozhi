from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool

from app.core.config import PROJECT_ROOT
from app.services.memory import add_message
from app.services.vision_analysis import VisionAnalysisError, analyze_calligraphy_image, stream_calligraphy_image


logger = logging.getLogger(__name__)
router = APIRouter(tags=["calligraphy"])

UPLOAD_ROOT = PROJECT_ROOT / "uploads" / "calligraphy"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
UPLOAD_ID_PATTERN = re.compile(r"calligraphy_[0-9a-f]{16}")
DEFAULT_IMAGE_QUESTION = "请分析这张书法图片。"


class UploadResponse(BaseModel):
    uploadId: str
    filename: str
    contentType: str
    size: int
    imageUrl: str


class AnalyzeRequest(BaseModel):
    uploadId: str | None = None
    imageUrl: str | None = None
    mode: str = "full"
    userLevel: str = "beginner"
    style: str | None = None
    question: str | None = None
    sessionId: str | None = None


class AnalyzeSections(BaseModel):
    composition: str
    structure: str
    strokes: str


class AnalyzeResponse(BaseModel):
    score: int
    style: str
    summary: str
    analysis: AnalyzeSections
    suggestions: list[str]


def normalize_style(style: str | None) -> str:
    style_map = {
        "kaishu": "楷书",
        "xingshu": "行书",
        "caoshu": "草书",
        "lishu": "隶书",
        "zhuanshu": "篆书",
    }
    if not style:
        return "楷书"
    return style_map.get(style.lower(), style)


def resolve_uploaded_image(upload_id: str | None, image_url: str | None) -> Path:
    """Resolve an analysis image while keeping requests inside the upload directory."""
    if upload_id:
        if not UPLOAD_ID_PATTERN.fullmatch(upload_id):
            raise HTTPException(status_code=400, detail="Invalid uploadId")
        for extension in ALLOWED_IMAGE_TYPES.values():
            candidate = UPLOAD_ROOT / f"{upload_id}{extension}"
            if candidate.is_file():
                return candidate
        raise HTTPException(status_code=404, detail="Uploaded image was not found")

    prefix = "/uploads/calligraphy/"
    if not image_url or not image_url.startswith(prefix):
        raise HTTPException(status_code=400, detail="imageUrl must point to an uploaded calligraphy image")
    filename = Path(image_url[len(prefix):]).name
    if filename != image_url[len(prefix):] or Path(filename).suffix.lower() not in ALLOWED_IMAGE_TYPES.values():
        raise HTTPException(status_code=400, detail="Invalid imageUrl")
    candidate = UPLOAD_ROOT / filename
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Uploaded image was not found")
    return candidate


@router.post("/uploads/calligraphy", response_model=UploadResponse)
async def upload_calligraphy_image(
    file: UploadFile = File(...),
    purpose: str = Form("analysis"),
) -> UploadResponse:
    if purpose != "analysis":
        raise HTTPException(status_code=400, detail="purpose must be analysis")

    content_type = file.content_type or ""
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")

    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Uploaded image must be 8MB or smaller")

    upload_id = f"calligraphy_{uuid4().hex[:16]}"
    stored_name = f"{upload_id}{extension}"
    (UPLOAD_ROOT / stored_name).write_bytes(content)

    return UploadResponse(
        uploadId=upload_id,
        filename=file.filename or stored_name,
        contentType=content_type,
        size=size,
        imageUrl=f"/uploads/calligraphy/{stored_name}",
    )


@router.post("/calligraphy/analyze", response_model=AnalyzeResponse)
async def analyze_calligraphy(request: AnalyzeRequest) -> AnalyzeResponse:
    if not request.uploadId and not request.imageUrl:
        raise HTTPException(status_code=400, detail="uploadId or imageUrl is required")

    image_path = resolve_uploaded_image(request.uploadId, request.imageUrl)
    try:
        result = await run_in_threadpool(
            analyze_calligraphy_image,
            image_path,
            request.question,
            normalize_style(request.style) if request.style else None,
        )
    except VisionAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AnalyzeResponse(
        score=result["score"],
        style=result["style"],
        summary=result["summary"],
        analysis=AnalyzeSections(**result["analysis"]),
        suggestions=result["suggestions"],
    )


@router.post("/calligraphy/analyze/stream")
async def stream_calligraphy_analysis(request: AnalyzeRequest) -> StreamingResponse:
    if not request.uploadId and not request.imageUrl:
        raise HTTPException(status_code=400, detail="uploadId or imageUrl is required")

    image_path = resolve_uploaded_image(request.uploadId, request.imageUrl)
    style_hint = normalize_style(request.style) if request.style else None
    session_id = request.sessionId or str(uuid4())
    question = (request.question or DEFAULT_IMAGE_QUESTION).strip() or DEFAULT_IMAGE_QUESTION
    image_url = request.imageUrl or f"/uploads/calligraphy/{image_path.name}"

    async def event_generator():
        full_answer = ""
        try:
            # Keep synchronous vision-model inference off the event loop, so
            # the rest of the app stays responsive while the image is analyzed.
            async for chunk in iterate_in_threadpool(stream_calligraphy_image(image_path, question, style_hint)):
                full_answer += chunk
                yield f"event: chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            saved_answer = full_answer.strip() or "图片分析完成，但没有返回具体内容。"
            await run_in_threadpool(add_message, session_id, "human", question, None, image_url)
            await run_in_threadpool(add_message, session_id, "ai", saved_answer)
            yield f"event: done\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"
        except VisionAnalysisError as exc:
            logger.warning("[vision] Stream failed: %s", exc)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
