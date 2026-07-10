from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """RAG 应用全局配置，支持通过环境变量覆盖默认值。"""

    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # Chroma 向量数据库配置
    CHROMA_PERSIST_PATH: str = "./data/chroma_db"

    # 知识库目录
    KNOWLEDGE_BASE_DIR: str = "data/knowledge"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局单例
settings = Settings()
