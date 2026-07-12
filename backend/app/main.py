from __future__ import annotations

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import PROJECT_ROOT, settings
from app.core.lifespan import app_lifespan
from app.routers import calligraphy as calligraphy_router
from app.routers import chat as chat_router
from app.routers import glyphs as glyphs_router
from app.routers import learning as learning_router
from app.services.rag_chain import invoke_rag


app = FastAPI(title="Mozhi API", version="0.1.0", lifespan=app_lifespan)

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


class ChatRequest(BaseModel):
    """Compatibility schema used by the existing frontend."""

    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


def fallback_answer(message: str) -> str:
    """Keep the legacy endpoint usable while the local RAG service is unavailable."""
    topic = message.strip() or "这次练习"
    return (
        "【本地测试模式】当前无法连接本地 RAG 模型或知识库。"
        f"你可以先围绕“{topic}”从章法、结构和用笔三个方面进行观察；"
        "待本地模型和知识库初始化完成后，系统会提供基于资料检索的回答。"
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mozhi backend is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def legacy_chat(request: ChatRequest) -> ChatResponse:
    """Temporary compatibility endpoint. New callers should use /api/chat."""
    question = request.message.strip()
    try:
        result = await run_in_threadpool(invoke_rag, question)
    except Exception:
        return ChatResponse(answer=fallback_answer(question))

    answer = str(result.get("answer", "")).strip()
    return ChatResponse(answer=answer or fallback_answer(question))


# Keep the upload route before the /uploads static mount; otherwise static files
# would catch POST /uploads/calligraphy before FastAPI processes the upload.
app.include_router(calligraphy_router.router)
app.include_router(chat_router.router)
app.include_router(glyphs_router.router)
app.include_router(learning_router.router)

app.mount("/uploads", StaticFiles(directory=PROJECT_ROOT / "uploads"), name="uploads")
app.mount(
    "/glyph-library",
    StaticFiles(directory=settings.glyph_library_path, check_dir=False),
    name="glyph_library",
)
