from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


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
    #定义系统提示
    system_prompt = (
        "你是一位中国书法大师与教学专家，精通楷书、行书、草书、隶书、篆书等各种书体。"
        "你的回答应当专业、细致、有文化底蕴，能够帮助书法学习者提升技艺。"
        "回答请使用中文，语气亲切但专业。"
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
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="AI 服务未启动，请检查 Ollama 是否运行")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 响应超时，请稍后重试")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI 服务返回错误：{e.response.status_code}")
    except Exception:
        raise HTTPException(status_code=500, detail="服务器内部错误")

    return ChatResponse(answer=data.get("response", "").strip())
