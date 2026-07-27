"""
backend/api/routes.py
──────────────────────
MY additive routes only.

DO NOT edit teammate's routes here — this file is exclusively for the AI engine
and control-plane endpoints listed in spec section 4.

Mounted on the shared FastAPI app in main.py with prefix="/".
WebSocket /alerts/stream streams mock alerts in Phase 1-4 → real alerts in Phase 5.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.ai.orchestrator import Orchestrator

router = APIRouter()

# ── Mock data source (Phases 1-4 — swapped for real DB in Phase 5) ───────────
MOCK_DB_PATH = Path(__file__).parent.parent.parent / "mocks" / "db.json"


def _load_mock_alerts() -> list[dict]:
    """Load alerts from the json-server mock database."""
    try:
        return json.loads(MOCK_DB_PATH.read_text(encoding="utf-8")).get("alerts", [])
    except FileNotFoundError:
        return []


# ── Singleton orchestrator — compiled LangGraph, wired to factory providers ───
_orchestrator = Orchestrator()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request/response models
# ─────────────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    command: str = "explain this"


class ExplainResponse(BaseModel):
    explanation: str


class GenerateRuleRequest(BaseModel):
    command: str
    alert_id: str | None = None


class GenerateRuleResponse(BaseModel):
    code: str
    valid: bool
    error: str | None = None


class ApproveResponse(BaseModel):
    status: str


class RevertResponse(BaseModel):
    status: str


class SimulatorStateRequest(BaseModel):
    action: str  # "play" | "pause" | "stop"


class SimulatorStateResponse(BaseModel):
    is_running: bool


class ProfileRequest(BaseModel):
    name: str
    rules: dict | None = None


class ProfileResponse(BaseModel):
    profile_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: GET /alerts  — list flagged alerts
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts", summary="List flagged alerts")
async def list_alerts() -> list[dict]:
    """Return all flagged alerts.

    Phase 1-4: reads from mocks/db.json.
    Phase 5: delegates to teammate's Real-Time Rules Engine.
    """
    return _load_mock_alerts()


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: WS /alerts/stream  — live alert feed
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/alerts/stream")
async def alerts_stream(websocket: WebSocket):
    """WebSocket that streams flagged alerts to the Live Security Console.

    Phase 1-4: replays mock alerts from db.json with a 2s delay between each.
    Phase 5: bridges to teammate's real-time simulator output.
    """
    await websocket.accept()
    alerts = _load_mock_alerts()
    try:
        for alert in alerts:
            await websocket.send_json(alert)
            await asyncio.sleep(2)  # 2-second cadence for mock streaming
        # After all mocks sent, keep connection alive
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: POST /alerts/{id}/explain  — forensic explanation
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/alerts/{alert_id}/explain", response_model=ExplainResponse)
async def explain_alert(
    alert_id: str,
    body: ExplainRequest = ExplainRequest(),
) -> ExplainResponse:
    """Step 3 → Step 4: Analyst clicks a flagged alert → gets explanation.

    Routes command through Orchestrator (LangGraph) → InvestigatorAgent.
    Phase 2: InvestigatorAgent is still a stub — real prompts in Phase 3.
    """
    alerts = _load_mock_alerts()
    alert = next((a for a in alerts if a["id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    result = _orchestrator.route(command=body.command, context=alert)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    explanation = result["result"] if isinstance(result["result"], str) else str(result["result"])
    return ExplainResponse(explanation=explanation)


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: POST /rules/generate  — generate a Python detection rule
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/rules/generate", response_model=GenerateRuleResponse)
async def generate_rule(body: GenerateRuleRequest) -> GenerateRuleResponse:
    """Step 5 → Step 6: Analyst command → Orchestrator → RuleWriterAgent.

    Phase 2: RuleWriterAgent is still a stub — real retry loop in Phase 3.
    """
    alerts = _load_mock_alerts()
    context = (
        next((a for a in alerts if a["id"] == body.alert_id), None)
        if body.alert_id
        else None
    )

    result = _orchestrator.route(command=body.command, context=context)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    agent_output = result["result"]
    if isinstance(agent_output, dict):
        return GenerateRuleResponse(
            code=agent_output.get("code", ""),
            valid=agent_output.get("valid", False),
            error=agent_output.get("error"),
        )
    return GenerateRuleResponse(
        code=str(agent_output),
        valid=False,
        error="Unexpected agent output format",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 6b: POST /rules/{id}/approve  — analyst approves a generated rule
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/rules/{rule_id}/approve", response_model=ApproveResponse)
async def approve_rule(rule_id: str) -> ApproveResponse:
    """Step 6b: Human approval → Dynamic Rule Compiler (teammate's side).

    Phase 2 MOCK — replace with teammate's Rule Compiler call in Phase 5.
    """
    return ApproveResponse(status="deployed")


# ─────────────────────────────────────────────────────────────────────────────
# Revert: POST /rules/{id}/revert  — pull prior ruleset from Audit Log
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/rules/{rule_id}/revert", response_model=RevertResponse)
async def revert_rule(rule_id: str) -> RevertResponse:
    """Revert Last Rule → Rule Audit Log (teammate's side).

    Phase 2 MOCK — replace with teammate's Audit Log call in Phase 5.
    """
    return RevertResponse(status="reverted")


# ─────────────────────────────────────────────────────────────────────────────
# Play/Pause/Stop: POST /simulator/state
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/simulator/state", response_model=SimulatorStateResponse)
async def set_simulator_state(body: SimulatorStateRequest) -> SimulatorStateResponse:
    """Play / Pause / Stop buttons → Simulator State (teammate's side).

    Phase 2 MOCK — replace with teammate's Simulator State call in Phase 5.
    """
    is_running = body.action == "play"
    return SimulatorStateResponse(is_running=is_running)


# ─────────────────────────────────────────────────────────────────────────────
# Custom Profile Builder: POST /profiles
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/profiles", response_model=ProfileResponse)
async def create_profile(body: ProfileRequest) -> ProfileResponse:
    """Custom Profile Builder Modal → Custom Profile Storage (teammate's side).

    Phase 2 MOCK — replace with teammate's storage call in Phase 5.
    """
    profile_id = f"profile_{uuid.uuid4().hex[:8]}"
    return ProfileResponse(profile_id=profile_id)
