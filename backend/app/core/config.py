from pathlib import Path

from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """RAG 应用全局配置，支持通过环境变量覆盖默认值。"""

    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5vl:7b"
    VISION_MODEL: str = "qwen2.5vl:7b"
    MODEL_KEEP_ALIVE: str = "-1m"
    EMBEDDING_MODEL: str = "bge-m3"
    RETRIEVAL_SCORE_THRESHOLD: float = 0.40

    # Chroma 向量数据库配置
    CHROMA_PERSIST_PATH: str = "data/chroma_db"

    # Comma-separated source directories, relative to the project root by default.
    KNOWLEDGE_BASE_DIRS: str = (
        "data/knowledge,"
        "data/knowledge_base/mozhi_knowledge_base"
    )

    @property
    def chroma_persist_path(self) -> Path:
        return self._resolve_project_path(self.CHROMA_PERSIST_PATH)

    @property
    def knowledge_base_paths(self) -> tuple[Path, ...]:
        paths = [
            self._resolve_project_path(item.strip())
            for item in self.KNOWLEDGE_BASE_DIRS.split(",")
            if item.strip()
        ]
        return tuple(dict.fromkeys(paths))

    @staticmethod
    def _resolve_project_path(value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局单例
settings = Settings()
