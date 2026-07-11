import json
import logging
import urllib.request
from typing import List

from langchain_core.embeddings import Embeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingsCompat(Embeddings):
    """兼容 Ollama 的 Embedding 实现，使用 urllib 替代 httpx 避免 502 错误。"""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")
        logger.info("OllamaEmbeddingsCompat initialized: model=%s, base_url=%s", model, base_url)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """调用 Ollama /api/embed 接口获取 embeddings。"""
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["embeddings"]
        except urllib.error.HTTPError as e:
            logger.error("Ollama embed API HTTP error: %s, body: %s", e.code, e.read().decode())
            raise
        except Exception as e:
            logger.error("Ollama embed API error: %s", e)
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]
