"""
System Configuration (`backend/config.py`)

Unifies model provider selection, Gemini API configuration, Ollama/Local settings,
and Fraud Rules Engine core settings using Pydantic BaseSettings.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    # LLM & Provider Settings (supports MODEL_PROVIDER and LLM_PROVIDER)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER") or os.getenv("MODEL_PROVIDER") or "gemini"
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER") or os.getenv("LLM_PROVIDER") or "gemini"
    
    # Gemini Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_RULE_WRITER_MODEL: str = "gemini-2.5-flash"
    GEMINI_INVESTIGATOR_MODEL: str = "gemini-2.5-flash"
    GEMINI_PROFILE_BUILDER_MODEL: str = "gemini-2.5-flash"
    RULE_WRITER_MAX_RETRIES: int = 3

    # Ollama / Local Provider Settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

    # Fraud Engine Settings
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "fraud_rules.db")
    MAX_RULES_CAP: int = int(os.getenv("MAX_RULES_CAP", "20"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    PROFILE_LIBRARY_PATH: str = os.getenv(
        "PROFILE_LIBRARY_PATH", "backend/profiles/profiles.json"
    )

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Module-level alias constants for backward compatibility
MODEL_PROVIDER: str = settings.MODEL_PROVIDER.lower()
LLM_PROVIDER: str = settings.LLM_PROVIDER.lower()
GEMINI_API_KEY: str = settings.GEMINI_API_KEY
GEMINI_RULE_WRITER_MODEL: str = settings.GEMINI_RULE_WRITER_MODEL
GEMINI_INVESTIGATOR_MODEL: str = settings.GEMINI_INVESTIGATOR_MODEL
GEMINI_PROFILE_BUILDER_MODEL: str = settings.GEMINI_PROFILE_BUILDER_MODEL
OLLAMA_HOST: str = settings.OLLAMA_HOST
OLLAMA_BASE_URL: str = settings.OLLAMA_BASE_URL
OLLAMA_MODEL: str = settings.OLLAMA_MODEL
RULE_WRITER_MAX_RETRIES: int = settings.RULE_WRITER_MAX_RETRIES
