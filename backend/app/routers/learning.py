from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.routers.chat import Source, _map_raw_sources
from app.services.rag_chain import invoke_rag


router = APIRouter(prefix="/api/learning", tags=["learning"])


class LearningPlanRequest(BaseModel):
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    style: Literal["kaishu", "xingshu", "caoshu", "lishu", "zhuanshu"] = "kaishu"
    daily_minutes: int = Field(default=30, ge=10, le=180)
    goal: str = Field(default="", max_length=120)


class LearningPlanResponse(BaseModel):
    plan: str
    sources: list[Source] = Field(default_factory=list)


LEVEL_LABELS = {
    "beginner": "零基础或初学者",
    "intermediate": "有一定基础的学习者",
    "advanced": "进阶学习者",
}
STYLE_LABELS = {
    "kaishu": "楷书",
    "xingshu": "行书",
    "caoshu": "草书",
    "lishu": "隶书",
    "zhuanshu": "篆书",
}


def _build_plan_question(request: LearningPlanRequest) -> str:
    level = LEVEL_LABELS[request.level]
    style = STYLE_LABELS[request.style]
    goal = request.goal.strip() or "建立扎实的临摹和创作基础"
    return (
        f"请为一位{level}制定{style}学习推荐。"
        f"用户每天可练习 {request.daily_minutes} 分钟，目标是：{goal}。\n"
        "请直接给出一份可执行的建议，包含：学习顺序、推荐碑帖与书法家、每阶段的观察重点，"
        "以及适合该练习时间的一条日常练习方法。内容务必基于已检索到的书法资料，"
        "不要虚构资料中没有的碑帖或人物。"
    )


@router.post("/plan", response_model=LearningPlanResponse)
async def create_learning_plan(request: LearningPlanRequest) -> LearningPlanResponse:
    try:
        result: dict[str, Any] = await run_in_threadpool(invoke_rag, _build_plan_question(request))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Learning recommendation service is temporarily unavailable") from exc

    plan = str(result.get("answer") or "").strip()
    if not plan:
        plan = "根据现有资料，暂时无法生成学习推荐。"

    return LearningPlanResponse(
        plan=plan,
        sources=_map_raw_sources(result.get("sources") or []),
    )
