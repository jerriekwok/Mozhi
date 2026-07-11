from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import settings
from app.routers import chat as chat_router
from app.routers import learning as learning_router
from app.services.rag_chain import invoke_rag
from app.services.vision_analysis import (
    VisionAnalysisError,
    analyze_calligraphy_image,
    preload_vision_model,
    stream_calligraphy_image,
    unload_vision_model,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Keep the shared Qwen model warm for both chat and image analysis."""
    try:
        await run_in_threadpool(preload_vision_model)
        logger.info("[model] Preloaded %s", settings.VISION_MODEL)
    except VisionAnalysisError as exc:
        logger.warning("[model] Preload skipped: %s", exc)

    try:
        yield
    finally:
        await run_in_threadpool(unload_vision_model)


app = FastAPI(title="Mozhi API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = PROJECT_ROOT / "uploads" / "calligraphy"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
UPLOAD_ID_PATTERN = re.compile(r"calligraphy_[0-9a-f]{16}")

class ChatRequest(BaseModel):
    """Compatibility schema used by the existing frontend."""

    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


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


def fallback_answer(message: str) -> str:
    """Keep the frontend usable while the local RAG service is unavailable."""
    topic = message.strip() or "这次练习"
    return (
        "【本地测试模式】当前无法连接本地 RAG 模型或知识库。"
        f"你可以先围绕“{topic}”从章法、结构和用笔三个方面进行观察；"
        "待本地模型和知识库初始化完成后，系统会提供基于资料检索的回答。"
    )


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
    filename = Path(image_url[len(prefix) :]).name
    if filename != image_url[len(prefix) :] or Path(filename).suffix.lower() not in ALLOWED_IMAGE_TYPES.values():
        raise HTTPException(status_code=400, detail="Invalid imageUrl")
    candidate = UPLOAD_ROOT / filename
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Uploaded image was not found")
    return candidate


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mozhi backend is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Frontend-compatible entry point that delegates to the RAG pipeline."""
    question = request.message.strip()
    try:
        result = await run_in_threadpool(invoke_rag, question)
    except Exception:
        return ChatResponse(answer=fallback_answer(question))

    answer = str(result.get("answer", "")).strip()
    return ChatResponse(answer=answer or fallback_answer(question))


@app.post("/uploads/calligraphy", response_model=UploadResponse)
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
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
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


@app.post("/calligraphy/analyze", response_model=AnalyzeResponse)
async def analyze_calligraphy(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze an uploaded calligraphy image using the local vision model."""
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


@app.post("/calligraphy/analyze/stream")
async def stream_calligraphy_analysis(request: AnalyzeRequest) -> StreamingResponse:
    """Stream a vision-model critique of an uploaded calligraphy image."""
    if not request.uploadId and not request.imageUrl:
        raise HTTPException(status_code=400, detail="uploadId or imageUrl is required")

    image_path = resolve_uploaded_image(request.uploadId, request.imageUrl)
    style_hint = normalize_style(request.style) if request.style else None

    async def event_generator():
        try:
            for chunk in stream_calligraphy_image(image_path, request.question, style_hint):
                yield f"event: chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"
        except VisionAnalysisError as exc:
            logger.warning("[vision] Stream failed: %s", exc)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# Register this after the upload endpoint. Otherwise the static-file mount
# catches POST /uploads/calligraphy before FastAPI can process the upload.
app.mount("/uploads", StaticFiles(directory=PROJECT_ROOT / "uploads"), name="uploads")


app.include_router(chat_router.router)
app.include_router(learning_router.router)
