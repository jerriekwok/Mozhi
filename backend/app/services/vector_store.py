import logging
from typing import Optional

from langchain_chroma import Chroma

from app.core.config import settings
from app.services.ollama_embeddings_compat import OllamaEmbeddingsCompat

logger = logging.getLogger(__name__)

# 全局缓存实例，避免重复初始化
_vector_store_instance: Optional[Chroma] = None


def _get_embedding_model() -> OllamaEmbeddingsCompat:
    """返回 Ollama 嵌入模型实例。"""
    logger.info(
        "Initializing OllamaEmbeddings: model=%s, base_url=%s",
        settings.EMBEDDING_MODEL,
        settings.OLLAMA_BASE_URL,
    )
    return OllamaEmbeddingsCompat(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def get_vector_store() -> Chroma:
    """获取或初始化 Chroma 向量存储实例（单例）。

    Returns:
        Chroma 向量存储实例，绑定到 calligraphy_knowledge collection。

    Raises:
        RuntimeError: 当 Chroma 初始化失败且无法恢复时抛出。
    """
    global _vector_store_instance

    if _vector_store_instance is not None:
        return _vector_store_instance

    try:
        embeddings = _get_embedding_model()

        logger.info(
            "Initializing Chroma vector store: persist_path=%s, collection=%s",
            settings.CHROMA_PERSIST_PATH,
            "calligraphy_knowledge",
        )

        vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_PATH,
            collection_name="calligraphy_knowledge",
            embedding_function=embeddings,
        )

        _vector_store_instance = vector_store
        logger.info("Chroma vector store initialized successfully.")
        return vector_store

    except Exception as exc:
        logger.exception("Failed to initialize Chroma vector store: %s", exc)
        raise RuntimeError(f"Chroma vector store initialization failed: {exc}") from exc


def get_retriever(k: int = 4):
    """返回基于向量存储的检索器。

    Args:
        k: 默认返回最相似的 k 条结果。

    Returns:
        Chroma 检索器实例。

    Raises:
        RuntimeError: 当向量存储未初始化时抛出。
    """
    vector_store = get_vector_store()
    logger.info("Creating retriever with k=%d", k)
    return vector_store.as_retriever(search_kwargs={"k": k})


def delete_collection() -> None:
    """删除当前 collection，用于重建知识库。

    注意：此操作会清空所有已存储的向量数据，且不可恢复。
    """
    global _vector_store_instance

    try:
        vector_store = get_vector_store()
        logger.warning("Deleting collection: calligraphy_knowledge")
        vector_store.delete_collection()
        _vector_store_instance = None
        logger.info("Collection deleted successfully.")
    except Exception as exc:
        logger.exception("Failed to delete collection: %s", exc)
        raise RuntimeError(f"Failed to delete collection: {exc}") from exc
