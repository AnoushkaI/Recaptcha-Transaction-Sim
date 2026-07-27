"""
backend/config.py
─────────────────
Central configuration switch for the AI engine.

MODEL_PROVIDER env var selects the active model path:
  "gemini"  → GeminiProvider (default, cloud)
  "local"   → LocalProvider  (fallback, Ollama, built by teammate)

All model names are pinned here so they can be changed in one place.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
load_dotenv()


# ── Provider switch ───────────────────────────────────────────────────────────
MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "gemini").lower()

VALID_PROVIDERS = ("gemini", "local")
if MODEL_PROVIDER not in VALID_PROVIDERS:
    raise ValueError(
        f"Invalid MODEL_PROVIDER='{MODEL_PROVIDER}'. "
        f"Must be one of: {VALID_PROVIDERS}"
    )


# ── Gemini model names (do not rename — shared contract) ─────────────────────
GEMINI_RULE_WRITER_MODEL = "gemini-2.5-flash"   # Step 6: rule generation (Pro requires paid tier)
GEMINI_INVESTIGATOR_MODEL = "gemini-2.5-flash"  # Step 4: forensic explanation (flash-lite deprecated for new API keys)


# ── Gemini API key ────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

if MODEL_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env file (see .env.example)."
    )


# ── Ollama / Local settings (teammate's provider reads these) ─────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")


# ── Retry / generation limits ─────────────────────────────────────────────────
RULE_WRITER_MAX_RETRIES: int = 3   # caps self-correction loop in rule_writer.py
