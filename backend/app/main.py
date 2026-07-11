from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.routers import chat as chat_router
from app.routers import learning as learning_router
from app.services.rag_chain import invoke_rag


app = FastAPI(title="Mozhi API", version="0.1.0")

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

app.mount("/uploads", StaticFiles(directory=PROJECT_ROOT / "uploads"), name="uploads")


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
    """Reserved endpoint; it returns stable mock data until a vision model is added."""
    if not request.uploadId and not request.imageUrl:
        raise HTTPException(status_code=400, detail="uploadId or imageUrl is required")

    style = normalize_style(request.style)
    focus = request.question or "整体章法、结构和用笔"

    return AnalyzeResponse(
        score=86,
        style=style,
        summary=f"已收到作品，当前按“{focus}”做基础分析：整体结构较稳，部分横画起收笔还可更明确。",
        analysis=AnalyzeSections(
            composition="章法基本整齐，字距略紧。可适当拉开行距并保留边缘留白。",
            structure="重心较稳，个别字中宫偏紧。建议对照原帖检查主笔伸展。",
            strokes="起笔较轻，转折处顿挫不够清晰。横画收笔和竖画力量可再加强。",
        ),
        suggestions=[
            "先练习横画起笔和收笔，每次写 20 个，重点观察顿笔是否明确。",
            f"临摹{style}时重点观察主笔伸展、转折力度和字内留白。",
            "每次练习后圈出三个结构最不稳的字，单独复写并与原帖比较。",
        ],
    )


app.include_router(chat_router.router)
app.include_router(learning_router.router)
