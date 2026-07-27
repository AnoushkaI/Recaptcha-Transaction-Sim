"""
Unit tests for Local Model Fallback Provider (`ai/providers/local_provider.py`).
"""

import pytest
import httpx
from backend.ai.providers.base import BaseLLMProvider
from backend.ai.providers.local_provider import LocalOllamaProvider


def test_provider_subclass():
    provider = LocalOllamaProvider(base_url="http://localhost:11434")
    assert isinstance(provider, BaseLLMProvider)


@pytest.mark.asyncio
async def test_ollama_health_check_offline():
    # Point to unused port to simulate offline server
    provider = LocalOllamaProvider(base_url="http://localhost:59999")
    is_healthy = await provider.check_health()
    assert is_healthy is False


@pytest.mark.asyncio
async def test_local_provider_offline_error():
    provider = LocalOllamaProvider(base_url="http://localhost:59999")
    with pytest.raises(RuntimeError, match="Ollama server unavailable"):
        await provider.generate(prompt="Write a fraud rule")
