"""
backend/ai/orchestrator.py
───────────────────────────
LangGraph-based Orchestrator — pure routing, async node execution.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END

from backend.ai.agents.investigator import InvestigatorAgent
from backend.ai.agents.rule_writer import RuleWriterAgent
from backend.ai.providers.factory import get_provider

COMMAND_EXPLAIN = "explain_alert"
COMMAND_GENERATE = "generate_rule"


class OrchestratorState(TypedDict):
    command: str
    context: Optional[dict]
    command_type: str
    result: Any
    error: Optional[str]


def classify_command(state: OrchestratorState) -> OrchestratorState:
    """Node 1: Pure keyword classification — no model call, zero token cost."""
    command_lower = state["command"].lower()

    explain_keywords = {"explain", "why", "what", "describe", "investigate", "analyse", "analyze", "tell me"}
    generate_keywords = {"generate", "create", "write", "add", "build", "make", "rule", "detect", "flag"}

    explain_hits = sum(1 for kw in explain_keywords if kw in command_lower)
    generate_hits = sum(1 for kw in generate_keywords if kw in command_lower)

    command_type = COMMAND_GENERATE if generate_hits > explain_hits else COMMAND_EXPLAIN

    return {**state, "command_type": command_type}


def route_after_classify(
    state: OrchestratorState,
) -> Literal["run_investigator", "run_rule_writer"]:
    """Conditional edge: reads command_type and returns the next node name."""
    if state["command_type"] == COMMAND_GENERATE:
        return "run_rule_writer"
    return "run_investigator"


async def run_investigator(state: OrchestratorState) -> OrchestratorState:
    """Node 2a: Async call InvestigatorAgent, get forensic explanation."""
    try:
        provider = get_provider(role="investigator")
        agent = InvestigatorAgent(provider=provider)
        result = await agent.explain(state["context"] or {})
        return {**state, "result": result, "error": None}
    except Exception as exc:
        return {
            **state,
            "result": None,
            "error": f"InvestigatorAgent failed: {type(exc).__name__}: {exc}",
        }


async def run_rule_writer(state: OrchestratorState) -> OrchestratorState:
    """Node 2b: Async call RuleWriterAgent, get Python rule code."""
    try:
        provider = get_provider(role="rule_writer")
        agent = RuleWriterAgent(provider=provider)
        result = await agent.generate_rule(
            command=state["command"],
            context=state["context"],
        )
        return {**state, "result": result, "error": None}
    except Exception as exc:
        return {
            **state,
            "result": None,
            "error": f"RuleWriterAgent failed: {type(exc).__name__}: {exc}",
        }


def _build_graph() -> Any:
    """Compile the LangGraph state machine."""
    builder = StateGraph(OrchestratorState)

    builder.add_node("classify_command", classify_command)
    builder.add_node("run_investigator", run_investigator)
    builder.add_node("run_rule_writer", run_rule_writer)

    builder.set_entry_point("classify_command")
    builder.add_conditional_edges(
        "classify_command",
        route_after_classify,
        {
            "run_investigator": "run_investigator",
            "run_rule_writer": "run_rule_writer",
        },
    )
    builder.add_edge("run_investigator", END)
    builder.add_edge("run_rule_writer", END)

    return builder.compile()


_graph = _build_graph()


class Orchestrator:
    """Thin wrapper around compiled LangGraph for use in routes.py."""

    async def route(self, command: str, context: Optional[dict] = None) -> dict:
        """Run the state machine asynchronously and return the result."""
        initial_state: OrchestratorState = {
            "command": command,
            "context": context,
            "command_type": "",
            "result": None,
            "error": None,
        }

        final_state = await _graph.ainvoke(initial_state)

        return {
            "command_type": final_state["command_type"],
            "result": final_state["result"],
            "error": final_state.get("error"),
        }
