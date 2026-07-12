from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from ollama import ResponseError

from app.core.config import settings
from app.services.model_runtime import get_ollama_client


logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class VisionAnalysisError(RuntimeError):
    """Raised when the local vision model cannot produce a usable analysis."""


def _strip_code_fence(content: str) -> str:
    return _CODE_FENCE_RE.sub("", content.strip()).strip()


def _as_text(value: Any, field: str, fallback: str | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        if fallback:
            return fallback
        raise VisionAnalysisError(f"Vision model returned an empty {field}")
    return text


def _normalise_result(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise VisionAnalysisError("Vision model did not return a JSON object")

    raw_analysis = payload.get("analysis")
    if not isinstance(raw_analysis, dict):
        raise VisionAnalysisError("Vision model response is missing analysis details")

    try:
        score = int(float(payload.get("score")))
    except (TypeError, ValueError) as exc:
        raise VisionAnalysisError("Vision model returned an invalid score") from exc

    raw_suggestions = payload.get("suggestions")
    if not isinstance(raw_suggestions, list):
        raise VisionAnalysisError("Vision model response is missing suggestions")
    suggestions = [str(item).strip() for item in raw_suggestions if str(item).strip()][:4]

    score = max(0, min(score, 100))
    cannot_analyse = score == 0
    unavailable_note = "图片中没有足够清晰的书法内容，无法做这一项分析。"

    return {
        "score": score,
        "style": _as_text(payload.get("style"), "style"),
        "summary": _as_text(payload.get("summary"), "summary"),
        "analysis": {
            "composition": _as_text(
                raw_analysis.get("composition"), "composition analysis", unavailable_note if cannot_analyse else None
            ),
            "structure": _as_text(
                raw_analysis.get("structure"), "structure analysis", unavailable_note if cannot_analyse else None
            ),
            "strokes": _as_text(
                raw_analysis.get("strokes"), "stroke analysis", unavailable_note if cannot_analyse else None
            ),
        },
        "suggestions": suggestions or (["请上传一张正面、清晰、完整的书法作品图片后再试。"] if cannot_analyse else []),
    }


def analyze_calligraphy_image(
    image_path: Path,
    question: str | None = None,
    style_hint: str | None = None,
) -> dict[str, Any]:
    """Ask the configured Ollama vision model for a grounded image critique."""
    if not image_path.is_file():
        raise VisionAnalysisError("Uploaded image file was not found")

    focus = (question or "整体章法、结构和用笔").strip()
    style = (style_hint or "未指定").strip()
    system_prompt = """
你是书法作品分析助手。请只根据图片中实际看得见的内容给出判断，不要假装看清了模糊、裁切或遮挡的部分。
用正常、直接的现代中文，不要古风腔，也不要客套话。评分只是帮助练习的相对参考，不代表权威鉴定。
如果图片不清晰、不是书法作品，或无法判断书体，请明确说明；此时 score 可以为 0，style 写“无法判断”。

必须只输出一个 JSON 对象，不能有 Markdown、解释文字或代码块，格式如下：
{
  "score": 0,
  "style": "识别到的书体，或无法判断",
  "summary": "先直接说整体观察和最需要改的地方",
  "analysis": {
    "composition": "章法、行距、字距或留白的观察",
    "structure": "结体、重心、主笔和空间关系的观察",
    "strokes": "起收笔、转折、轻重和线条质量的观察"
  },
  "suggestions": ["一条可以立刻练的建议", "第二条建议", "第三条建议"]
}
""".strip()
    user_prompt = (
        f"用户希望重点看：{focus}\n"
        f"用户选择的书体：{style}\n"
        "请分析这张上传的书法图片。"
    )

    try:
        client = get_ollama_client()
        response = client.chat(
            model=settings.VISION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt, "images": [str(image_path)]},
            ],
            format="json",
            options={"temperature": 0.2},
            keep_alive=settings.MODEL_KEEP_ALIVE,
        )
        content = response.message.content
    except ResponseError as exc:
        logger.warning("[vision] Ollama rejected image analysis: %s", exc)
        raise VisionAnalysisError("Vision model is unavailable") from exc
    except Exception as exc:
        logger.exception("[vision] Image analysis request failed")
        raise VisionAnalysisError("Vision model request failed") from exc

    try:
        return _normalise_result(json.loads(_strip_code_fence(content)))
    except json.JSONDecodeError as exc:
        logger.warning("[vision] Model returned non-JSON content: %s", content[:500])
        raise VisionAnalysisError("Vision model returned an invalid result") from exc


def stream_calligraphy_image(
    image_path: Path,
    question: str | None = None,
    style_hint: str | None = None,
):
    """Yield a plain-language critique as the local vision model generates it."""
    if not image_path.is_file():
        raise VisionAnalysisError("Uploaded image file was not found")

    focus = (question or "整体章法、结构和用笔").strip()
    style = (style_hint or "未指定").strip()
    system_prompt = """
你是书法作品分析助手。请只根据图片里实际看得见的内容作判断；看不清、裁切或遮挡的部分要直接说明，不要猜。
用正常、直接的现代中文，不要古风腔和客套话。不要假装是权威评分。
请按下面顺序写成简短自然的文字：整体判断、章法、结构、用笔、接下来怎么练。
如果图片不是书法作品或不够清晰，请直接说无法分析，并说明用户应怎样重新拍摄或上传。
不要使用 Markdown 表格，不要输出 JSON。
""".strip()
    user_prompt = (
        f"用户希望重点看：{focus}\n"
        f"用户选择的书体：{style}\n"
        "请分析这张上传的书法图片。"
    )

    try:
        client = get_ollama_client()
        response = client.chat(
            model=settings.VISION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt, "images": [str(image_path)]},
            ],
            stream=True,
            options={"temperature": 0.25},
            keep_alive=settings.MODEL_KEEP_ALIVE,
        )
        for part in response:
            content = part.message.content
            if content:
                yield content
    except ResponseError as exc:
        logger.warning("[vision] Ollama rejected streamed image analysis: %s", exc)
        raise VisionAnalysisError("Vision model is unavailable") from exc
    except Exception as exc:
        logger.exception("[vision] Streamed image analysis request failed")
        raise VisionAnalysisError("Vision model request failed") from exc
