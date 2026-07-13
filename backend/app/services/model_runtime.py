import httpx
import logging
from functools import lru_cache

from ollama import Client

from app.core.config import settings


logger = logging.getLogger(__name__)


class ModelRuntimeError(RuntimeError):
    """Raised when the local Ollama runtime cannot be prepared."""


@lru_cache(maxsize=1)
def get_ollama_client() -> Client:
    """Return one shared Ollama client for the process."""
    # 显式禁用代理，避免 Windows 或系统代理环境导致本地请求 502
    # kwargs 会透传给 httpx.Client，所以 proxy=None 可直接生效
    return Client(host=settings.OLLAMA_BASE_URL, proxy=None, timeout=300.0)


def preload_models() -> None:
    """Keep the shared generation model warm when the API starts."""
    try:
        get_ollama_client().generate(
            model=settings.VISION_MODEL,
            prompt="",
            keep_alive=settings.MODEL_KEEP_ALIVE,
        )
    except Exception as exc:
        raise ModelRuntimeError("Vision model could not be preloaded") from exc


def unload_models() -> None:
    """Release the local generation and embedding models when the API stops."""
    client = get_ollama_client()
    try:
        client.generate(model=settings.VISION_MODEL, prompt="", keep_alive=0)
    except Exception as exc:
        logger.warning("[model] Could not unload generation model: %s", exc)

    try:
        client.embed(model=settings.EMBEDDING_MODEL, input="", keep_alive=0)
    except Exception as exc:
        logger.warning("[model] Could not unload embedding model: %s", exc)
