"""
LLM Client & Provider Module for AI Agent Orchestration.
Interfaces with LLM providers for forensic investigation and rule synthesis.
"""
from typing import Dict, Any, Optional
from backend.ai.orchestrator import orchestrator


def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Send a prompt to the LLM provider and return response text."""
    try:
        res = orchestrator.query(prompt=prompt, system_prompt=system_prompt)
        return str(res)
    except Exception as e:
        return f"LLM client call failed: {e}"
