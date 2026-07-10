from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="Mozhi API", version="0.1.0")

# CORS - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama 配置
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
USE_MODEL = os.getenv("MOZHI_USE_MODEL", "1") != "0"
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
    message: str


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
    """
    本地开发兜底回复：用于没有安装/启动 Ollama 或模型时测试前端链路。
    """
    topic = message.strip() or "这次练习"
    return (
        "【本地测试模式】当前未连接本地大模型，我先用内置书法老师回复帮你完成前端测试。\n\n"
        f"简要判断：关于“{topic}”，可以先把它当作一次书法学习诊断来处理，不急着追求写得多，先看问题是否集中。\n\n"
        "具体分析：\n"
        "1. 章法：先看整幅的行距、字距和留白，好的章法要有呼吸感，不能挤成一片。\n"
        "2. 结构：单字重心要稳，中宫不要过紧，左右、上下的伸展要有主次。\n"
        "3. 用笔：起笔、行笔、收笔要交代清楚，转折处要能看出提按和顿挫。\n\n"
        "练习建议：先选 3 到 5 个最不稳的字慢写三遍，再对照原帖检查横画角度、竖画力度和转折位置。"
        "如果是在临帖，建议每次只抓一个目标，例如今天只修正横画起收笔，效果会更明显。"
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
async def chat(request: ChatRequest):
    """
    对接 Ollama 本地大模型，实现 AI 书法问答。
    """
    if not USE_MODEL:
        return ChatResponse(answer=fallback_answer(request.message))

    # 定义系统提示
    system_prompt = (
        "你是“墨智”的书法老师，精通楷书、行书、草书、隶书、篆书，以及颜真卿、柳公权、欧阳询、王羲之等经典书家与碑帖。"
        "请始终使用中文回答，语气亲切、专业、具体，避免空泛鼓励。"
        "回答时先判断用户问题类型：如果是作品点评，重点按章法、结构、用笔、改进练习组织；"
        "如果是临帖或技法问题，说明观察方法、常见错误和当天可执行练习；"
        "如果是书家、碑帖或书体知识，补充风格特征、学习价值和临摹要点。"
        "默认输出结构为：简要判断、具体分析、练习建议。"
        "练习建议要可执行，尽量包含练习对象、练习次数或观察重点。"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": request.message,
        "system": system_prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()#检查状态码
            data = response.json()
    except Exception:
        return ChatResponse(answer=fallback_answer(request.message))

    answer = data.get("response", "").strip()
    return ChatResponse(answer=answer or fallback_answer(request.message))


@app.post("/uploads/calligraphy", response_model=UploadResponse)
async def upload_calligraphy_image(
    file: UploadFile = File(...),
    purpose: str = Form("analysis"),
):
    """
    上传书法作品图片，供后续作品分析接口使用。
    """
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
    stored_path = UPLOAD_ROOT / stored_name
    stored_path.write_bytes(content)

    return UploadResponse(
        uploadId=upload_id,
        filename=file.filename or stored_name,
        contentType=content_type,
        size=size,
        imageUrl=f"/uploads/calligraphy/{stored_name}",
    )


@app.post("/calligraphy/analyze", response_model=AnalyzeResponse)
async def analyze_calligraphy(request: AnalyzeRequest):
    """
    书法作品分析预留接口。当前返回稳定模拟数据，后续可接 OCR / OpenCV / 视觉模型。
    """
    if not request.uploadId and not request.imageUrl:
        raise HTTPException(status_code=400, detail="uploadId or imageUrl is required")

    style = normalize_style(request.style)
    focus = request.question or "整体章法、结构和用笔"

    return AnalyzeResponse(
        score=86,
        style=style,
        summary=f"已收到作品，当前按“{focus}”做基础分析：整体结构较稳，部分横画起收笔还可以更明确。",
        analysis=AnalyzeSections(
            composition="章法基本整齐，字距略紧。后续可以通过拉开行距和保留边缘留白，让作品更有呼吸感。",
            structure="重心较稳定，个别字中宫偏紧。建议对照原帖检查主笔伸展，避免所有笔画都收在字心。",
            strokes="起笔较轻，转折处顿挫不够清楚。横画收笔和竖画力量可以再加强。",
        ),
        suggestions=[
            "先做横画起笔和收笔的慢速练习，每次写 20 个，重点看顿笔是否明确。",
            f"临摹{style}时重点观察主笔伸展、转折力度和字内留白。",
            "每次练习后圈出三个结构最不稳的字单独复写，再与原帖重叠比较重心。",
        ],
    )
