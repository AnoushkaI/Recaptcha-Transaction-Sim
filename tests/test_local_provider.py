"""
Comprehensive unit tests for local_provider.py and base.py.
Missing lines: base.py 29,36 (abstract methods); local_provider.py 36,55,60-62,68-70,76-97
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from backend.ai.providers.base import BaseLLMProvider
from backend.ai.providers.local_provider import LocalOllamaProvider


# --------------- base.py abstract methods ---------------

def test_base_provider_is_abstract():
    """Hits lines 29,36: BaseLLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()


def test_concrete_subclass_must_implement_all_methods():
    """Confirms all abstract methods must be implemented."""
    class PartialProvider(BaseLLMProvider):
        async def generate(self, prompt, system_prompt=None):
            return "ok"
        # Missing check_health → should raise TypeError
    with pytest.raises(TypeError):
        PartialProvider()


def test_full_concrete_subclass_works():
    class FullProvider(BaseLLMProvider):
        async def generate(self, prompt, system_prompt=None):
            return "generated"
        async def check_health(self):
            return True

    p = FullProvider()
    assert isinstance(p, BaseLLMProvider)


# --------------- LocalOllamaProvider construction ---------------

def test_local_provider_inherits_base():
    provider = LocalOllamaProvider()
    assert isinstance(provider, BaseLLMProvider)


def test_local_provider_uses_config_defaults():
    provider = LocalOllamaProvider()
    assert "localhost" in provider.base_url or "11434" in provider.base_url
    assert "qwen" in provider.model_name


def test_local_provider_custom_url_and_model():
    provider = LocalOllamaProvider(base_url="http://localhost:9999", model_name="test-model")
    assert provider.base_url == "http://localhost:9999"
    assert provider.model_name == "test-model"
    assert provider.generate_url == "http://localhost:9999/api/generate"


# --------------- health check ---------------

@pytest.mark.asyncio
async def test_health_check_success():
    """Hits lines 36+: check_health when server responds 200."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        result = await provider.check_health()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure_connection_error():
    """Hits the except block in check_health → returns False."""
    provider = LocalOllamaProvider(base_url="http://localhost:59999")
    result = await provider.check_health()
    assert result is False


@pytest.mark.asyncio
async def test_health_check_non_200_response():
    """Server reachable but returns non-200."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 503

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        result = await provider.check_health()

    assert result is False


# --------------- generate ---------------

@pytest.mark.asyncio
async def test_generate_success():
    """Hits lines 55-70: successful generate() call path."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "def evaluate(tx): return tx.amount > 100"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        result = await provider.generate("Write a fraud rule")

    assert "evaluate" in result


@pytest.mark.asyncio
async def test_generate_with_system_prompt():
    """Hits lines 60-62: system prompt is added to payload."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "def evaluate(tx): return True"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        result = await provider.generate("Write a fraud rule", system_prompt="You are an expert")

    assert result is not None


@pytest.mark.asyncio
async def test_generate_connect_error_raises_runtime():
    """Hits lines 68-70: httpx.ConnectError → RuntimeError with Ollama message."""
    provider = LocalOllamaProvider(base_url="http://localhost:59999")
    with pytest.raises(RuntimeError, match="Ollama server unavailable"):
        await provider.generate("Write a fraud rule")


@pytest.mark.asyncio
async def test_generate_other_exception_raises_runtime():
    """Hits lines 76-78: non-ConnectError exception → RuntimeError."""
    provider = LocalOllamaProvider()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        with pytest.raises(RuntimeError, match="Local LLM generation failed"):
            await provider.generate("Write a fraud rule")


# --------------- generate_with_metrics ---------------

@pytest.mark.asyncio
async def test_generate_with_metrics_success():
    """Hits lines 83-97: generate_with_metrics full happy path."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "def evaluate(tx): return tx.amount > 100",
        "eval_count": 20,
        "eval_duration": 2_000_000_000,  # 2 seconds in nanoseconds
        "total_duration": 3_000_000_000,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        result = await provider.generate_with_metrics("Write a fraud rule",
                                                       system_prompt="You are an expert")

    assert "response" in result
    assert result["eval_count"] == 20
    assert result["tokens_per_second"] == 10.0
    assert result["total_duration_sec"] == 3.0


@pytest.mark.asyncio
async def test_generate_with_metrics_zero_eval_duration():
    """Hits safety guard: eval_duration=0 → avoids division by zero."""
    provider = LocalOllamaProvider()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "def evaluate(tx): return True",
        "eval_count": 5,
        "eval_duration": 0,
        "total_duration": 1_000_000_000,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        result = await provider.generate_with_metrics("prompt")

    assert result["tokens_per_second"] >= 0
