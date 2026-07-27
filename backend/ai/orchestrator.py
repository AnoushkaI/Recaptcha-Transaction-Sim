"""
backend/ai/orchestrator.py
───────────────────────────
LangGraph-based Orchestrator — pure routing, zero LLM cost.

State machine:
  START
    └── classify_command()   ← pure keyword heuristic, no model call
          ├── "explain_alert"  → run_investigator() → END
          └── "generate_rule"  → run_rule_writer()  → END

The orchestrator itself never calls any LLM.
It only reads the command string, decides a route, and calls the correct agent.

Step labels (match spec section 2 and commit messages):
  Step 3 → Step 4 : explain_alert path
  Step 5 → Step 6 : generate_rule path
"""

from __future__ import annotations

from typing import Any, Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END

from backend.ai.agents.investigator import InvestigatorAgent
from backend.ai.agents.rule_writer import RuleWriterAgent
from backend.ai.providers.factory import get_provider

# ── Command type constants (used in comments, logs, API responses) ────────────
COMMAND_EXPLAIN = "explain_alert"
COMMAND_GENERATE = "generate_rule"


# ─────────────────────────────────────────────────────────────────────────────
# State schema — the dict that flows between graph nodes
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorState(TypedDict):
    command: str                  # raw analyst instruction
    context: dict | None          # alert/transaction data (may be None)
    command_type: str             # COMMAND_EXPLAIN or COMMAND_GENERATE (set by classify node)
    result: Any                   # agent output (set by the chosen agent node)
    error: str | None             # error message if anything goes wrong


# ─────────────────────────────────────────────────────────────────────────────
# Node functions — each runs one step in the state machine
# ─────────────────────────────────────────────────────────────────────────────

def classify_command(state: OrchestratorState) -> OrchestratorState:
    """Node 1: Pure keyword classification — no model call, zero token cost.

    Reads the command string and sets state["command_type"].
    Defaults to COMMAND_EXPLAIN when ambiguous (safer — won't accidentally
    auto-deploy a rule without human intent).
    """
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


def run_investigator(state: OrchestratorState) -> OrchestratorState:
    """Node 2a: Step 3 → Step 4 — call InvestigatorAgent, get forensic explanation.

    Phase 2: agent is still a stub (returns placeholder).
    Phase 3: real system prompt + single Gemini call.
    """
    try:
        provider = get_provider(role="investigator")
        agent = InvestigatorAgent(provider=provider)
        result = agent.explain(state["context"] or {})
        return {**state, "result": result, "error": None}
    except Exception as exc:
        return {
            **state,
            "result": None,
            "error": f"InvestigatorAgent failed: {type(exc).__name__}: {exc}",
        }


def run_rule_writer(state: OrchestratorState) -> OrchestratorState:
    """Node 2b: Step 5 → Step 6 — call RuleWriterAgent, get Python rule code.

    Phase 2: agent is still a stub.
    Phase 3: real prompt + self-correcting retry loop (max 3 attempts).
    """
    try:
        provider = get_provider(role="rule_writer")
        agent = RuleWriterAgent(provider=provider)
        result = agent.generate_rule(
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


# ─────────────────────────────────────────────────────────────────────────────
# Graph assembly
# ─────────────────────────────────────────────────────────────────────────────

def _build_graph() -> Any:
    """Compile the LangGraph state machine."""
    builder = StateGraph(OrchestratorState)

    # Nodes
    builder.add_node("classify_command", classify_command)
    builder.add_node("run_investigator", run_investigator)
    builder.add_node("run_rule_writer", run_rule_writer)

    # Edges
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


# Singleton — compiled once at import time
_graph = _build_graph()


# ─────────────────────────────────────────────────────────────────────────────
# Public API — used by api/routes.py
# ─────────────────────────────────────────────────────────────────────────────

class Orchestrator:
    """Thin wrapper around the compiled LangGraph for use in routes.py."""

    def route(self, command: str, context: dict | None = None) -> dict:
        """Run the state machine and return the result.

        Args:
            command: Natural-language instruction from the analyst.
            context: Optional alert/transaction dict.

        Returns:
            {
                "command_type": str,     # "explain_alert" or "generate_rule"
                "result":       any,     # agent output
                "error":        str|None # error message if something failed
            }
        """
        initial_state: OrchestratorState = {
            "command": command,
            "context": context,
            "command_type": "",
            "result": None,
            "error": None,
        }

        final_state = _graph.invoke(initial_state)

        return {
            "command_type": final_state["command_type"],
            "result": final_state["result"],
            "error": final_state.get("error"),
        }
