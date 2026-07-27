"""
System Configuration (`config.py`)

# CONTRACT: Confirm with Person B - LLM_PROVIDER key switch name is shared contract.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # CONTRACT: co-owned with Person B for AI switch
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")  # 'gemini' | 'local'
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

    # Engine Settings
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "fraud_rules.db")
    MAX_RULES_CAP: int = int(os.getenv("MAX_RULES_CAP", "20"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
