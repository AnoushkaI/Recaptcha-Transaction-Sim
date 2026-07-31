"""
Local Model Fallback Provider (`ai/providers/local_provider.py`)

Integrates with local Ollama runtime running `qwen2.5-coder:3b` (Q4 quantization)
on Person A's RTX 2050 GPU. Provides high-speed offline rule-generation capability.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from backend.ai.providers.base import BaseLLMProvider
from backend.config import settings

logger = logging.getLogger(__name__)


class LocalOllamaProvider(BaseLLMProvider):
    """
    Ollama integration provider for qwen2.5-coder:3b.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model_name: str = settings.OLLAMA_MODEL
    ):
        self.base_url: str = base_url.rstrip("/")
        self.model_name: str = model_name
        self.generate_url: str = f"{self.base_url}/api/generate"

    async def check_health(self) -> bool:
        """Verify Ollama runtime server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed at {self.base_url}: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate completion using local qwen2.5-coder:3b via Ollama.
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic code generation
                "top_p": 0.9,
                "num_predict": max_tokens,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(self.generate_url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama server unavailable at {self.base_url}. "
                f"Please ensure Ollama is installed and running (`ollama serve`)."
            )
        except Exception as e:
            logger.error(f"Error calling local Ollama model '{self.model_name}': {e}")
            raise RuntimeError(f"Local LLM generation failed: {str(e)}")

    async def generate_with_metrics(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Extended generation method returning timing and token throughput metrics for benchmarking.
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.generate_url, json=payload)
            response.raise_for_status()
            data = response.json()

            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 1)
            eval_duration_sec = eval_duration_ns / 1e9 if eval_duration_ns > 0 else 0.001
            tps = round(eval_count / eval_duration_sec, 2) if eval_duration_sec > 0 else 0.0

            return {
                "response": data.get("response", "").strip(),
                "eval_count": eval_count,
                "eval_duration_sec": round(eval_duration_sec, 3),
                "tokens_per_second": tps,
                "total_duration_sec": round(data.get("total_duration", 0) / 1e9, 3)
            }
