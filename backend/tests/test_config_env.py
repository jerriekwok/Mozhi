import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.config as config_module


def test_settings_loads_dotenv_from_project_root(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[2]
    backend_dir = project_root / "backend"

    monkeypatch.chdir(backend_dir)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("VISION_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("MODEL_KEEP_ALIVE", raising=False)

    reloaded = importlib.reload(config_module)

    assert reloaded.settings.OLLAMA_BASE_URL == "http://127.0.0.1:11434"
    assert reloaded.settings.VISION_MODEL == "qwen2.5vl:3b"
