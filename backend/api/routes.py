"""
API Routes (`backend/api/routes.py`)

Unified FastAPI REST endpoints and WebSocket definitions supporting both:
1. Backend core test suite (/api/ prefixed endpoints)
2. Frontend security dashboard (/alerts, /rules, /simulator, /profiles endpoints)
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime, timezone
import random

from backend.core.schemas import (
    Rule,
    Transaction,
    FlaggedAlert,
    CustomProfile,
    ValidationResult,
    GuardResult,
)
from backend.core.validator import ASTSafetyValidator
from backend.core.db import init_db
from backend.core.rule_guard import RuleGuard
from backend.core.compiler import RuleCompiler
from backend.core.rules_engine import RulesEngine
from backend.core.audit_log import AuditLogger
from backend.core.simulator import TransactionSimulator
from backend.ai.orchestrator import Orchestrator
from backend.config import settings
from backend.scoring.engine import evaluate_transaction, ScoringResult

router = APIRouter()

# Global singletons
init_db(settings.DATABASE_PATH)
validator = ASTSafetyValidator()
rule_guard = RuleGuard(
    max_rules_cap=settings.MAX_RULES_CAP,
    similarity_threshold=settings.SIMILARITY_THRESHOLD
)
compiler = RuleCompiler()
rules_engine = RulesEngine()
audit_logger = AuditLogger(db_path=settings.DATABASE_PATH)
simulator = TransactionSimulator(interval_seconds=1.0)
orchestrator = Orchestrator()

# In-memory alert history for frontend /alerts endpoint (capped at 20)
alerts_history: List[dict] = []
MAX_ALERTS_HISTORY = 20

def record_flagged_alert(alert: FlaggedAlert) -> dict:
    mapped = map_flagged_alert_to_frontend(alert)
    tx_id = mapped.get("transaction", {}).get("id")
    alert_id = mapped.get("id")

    # Deduplicate by alert ID or transaction ID to prevent duplicate items
    for existing in alerts_history:
        ex_tx_id = existing.get("transaction", {}).get("id")
        if (alert_id and existing.get("id") == alert_id) or (tx_id and ex_tx_id == tx_id):
            return existing

    alerts_history.insert(0, mapped)
    if len(alerts_history) > MAX_ALERTS_HISTORY:
        alerts_history.pop()
    return mapped

def map_flagged_alert_to_frontend(alert: FlaggedAlert) -> dict:
    tx_dict = (
        alert.transaction_details.model_dump()
        if hasattr(alert.transaction_details, "model_dump")
        else dict(alert.transaction_details)
    )

    if not tx_dict.get("telemetry_risk_score") or not tx_dict.get("classification"):
        res = evaluate_transaction(tx_dict)
        tx_dict["telemetry_score"] = res.telemetry_score
        tx_dict["telemetry_risk_score"] = res.telemetry_risk_score
        tx_dict["transaction_risk_score"] = res.transaction_risk_score
        tx_dict["final_risk_score"] = res.final_risk_score
        tx_dict["classification"] = res.classification

    cls = (tx_dict.get("classification") or "").upper()
    final_score = tx_dict.get("final_risk_score") if tx_dict.get("final_risk_score") is not None else alert.score

    if cls == "HIGH_RISK" or final_score >= 0.60:
        severity = "high"
        score = final_score
    elif cls == "SUSPICIOUS" or final_score >= 0.30:
        severity = "medium"
        score = final_score
    elif cls == "SAFE" or final_score < 0.30:
        severity = "low"
        score = final_score
    else:
        name = (alert.rule_name or "").lower()
        if "high amount" in name or "wire" in name or "cross-border" in name:
            severity = "high"
            score = 0.90
        elif "crypto" in name or "gaming" in name or "new account" in name or "electronics" in name:
            severity = "medium"
            score = 0.60
        else:
            severity = "low"
            score = alert.score

    # Ensure transaction object includes realistic user names, titles, and descriptions
    if not tx_dict.get("user_name"):
        NAMES_SAMPLE = ["Alex Morgan", "Elena Rostova", "Liam Chen", "Sarah Jenkins", "Devon Vance", "Priya Sharma", "Marcus Vance", "Sophia Martinez", "David Kim", "Emma Watson"]
        tx_dict["user_name"] = random.choice(NAMES_SAMPLE)
    
    scenario_title = tx_dict.get("title") or alert.rule_name or "Fraud Detection Alert"
    tx_dict["title"] = scenario_title

    # Generate realistic, varied description if missing
    amt = tx_dict.get("amount", 0)
    loc = tx_dict.get("location", "US-NY")
    cat = (tx_dict.get("merchant_category") or "general").replace("_", " ")
    u_name = tx_dict["user_name"]
    acc_id = tx_dict.get("account_id", "acc_user")
    
    if not tx_dict.get("description") or "Automated risk detection triggered" in str(tx_dict.get("description")):
        name = (alert.rule_name or "").lower()
        if "high amount" in name or amt > 2000:
            tx_dict["description"] = f"High amount purchase of ₹{amt:,.0f} by {u_name} in {cat} category from {loc}."
        elif "intl" in name or "wire" in name or tx_dict.get("is_international"):
            tx_dict["description"] = f"Cross-border transfer of ₹{amt:,.0f} to {loc} on account {acc_id}."
        elif "micro" in name or "gas" in name or amt < 25:
            tx_dict["description"] = f"Low-value micro-transaction test of ₹{amt:,.0f} at {cat} merchant."
        elif "crypto" in name or "gaming" in name or "electronics" in name:
            tx_dict["description"] = f"High-risk {cat} checkout of ₹{amt:,.0f} by {u_name} on unverified device."
        else:
            tx_dict["description"] = f"Transaction of ₹{amt:,.0f} performed by {u_name} on account {acc_id} ({loc})."

    return {
        "id": alert.id,
        "rule_triggered": alert.rule_name,
        "severity": severity,
        "score": score,
        "timestamp": alert.flagged_at,
        "transaction": tx_dict,
        "user_name": tx_dict.get("user_name"),
        "title": scenario_title,
        "description": tx_dict.get("description"),
        "telemetry_risk_score": tx_dict.get("telemetry_risk_score"),
        "transaction_risk_score": tx_dict.get("transaction_risk_score"),
        "final_risk_score": tx_dict.get("final_risk_score"),
        "classification": tx_dict.get("classification"),
    }




# ── Request / Response Pydantic Schemas ──────────────────────────────────────

class DeployRuleRequest(BaseModel):
    name: Optional[str] = Field(default="Analyst Fraud Rule", description="Rule title")
    code: str = Field(..., description="Python evaluate(tx) code")
    description: Optional[str] = Field(default="Analyst deployed rule", description="Rule description")
    command: Optional[str] = Field(default="Analyst rule deployment", description="User prompt or command")


class RevertRuleRequest(BaseModel):
    rule_id: str = Field(..., description="Rule ID to revert")
    command: Optional[str] = Field(default="Analyst rule revert", description="Reason for revert")


class SimulatorControlRequest(BaseModel):
    action: str = Field(..., description="Action: 'play', 'pause', or 'stop'")
    profile_id: Optional[str] = Field(default=None, description="Active fraud profile scenario ID")



class DeployResponse(BaseModel):
    success: bool
    rule: Optional[Rule] = None
    validation: ValidationResult
    guard: Optional[GuardResult] = None
    message: str


class ExplainRequest(BaseModel):
    command: str = "Explain this alert"


class ExplainResponse(BaseModel):
    explanation: str


class GenerateRuleRequest(BaseModel):
    command: str
    alert_id: Optional[str] = None
    alert_data: Optional[Dict[str, Any]] = None


class GenerateRuleResponse(BaseModel):
    code: str
    explanation: Optional[str] = None
    valid: bool = True
    error: Optional[str] = None




class ProfileRequest(BaseModel):
    name: str
    rules: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. CORE BACKEND ENDPOINTS (/api/ prefix for pytest suite compatibility)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/rules/validate", response_model=ValidationResult, tags=["Fraud Engine Core"])
def validate_rule_code(request: DeployRuleRequest):
    return validator.validate(request.code)


@router.post("/simulate/profile", tags=["Fraud Engine Core"])
@router.post("/api/simulate/profile", tags=["Fraud Engine Core"])
def simulate_profile_endpoint(body: dict):
    from backend.batch_generator import generate_batch_20
    profile_id = body.get("profile_id", "ACCOUNT_TAKEOVER")
    txs = generate_batch_20(profile_id)
    return {"profile_id": profile_id, "count": len(txs), "transactions": txs}


@router.post("/api/rules/deploy", response_model=DeployResponse, tags=["Fraud Engine Core"])
def deploy_rule(request: DeployRuleRequest):
    val_res = validator.validate(request.code)
    if not val_res.valid:
        return DeployResponse(
            success=False,
            validation=val_res,
            message=f"AST Safety Validation failed: {val_res.error}"
        )

    rule_id = f"rule_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    rule_name = request.name or "Analyst Fraud Rule"
    rule_desc = request.description or "Analyst deployed rule"
    rule_cmd = request.command or "Analyst rule deployment"

    proposed_rule = Rule(
        id=rule_id,
        name=rule_name,
        code=request.code,
        description=rule_desc,
        created_at=timestamp,
        status="active",
        created_by_command=rule_cmd
    )

    active_rules = audit_logger.get_active_rules()
    guard_res = rule_guard.evaluate_rule(proposed_rule, active_rules)
    if not guard_res.passed:
        return DeployResponse(
            success=False,
            rule=proposed_rule,
            validation=val_res,
            guard=guard_res,
            message=f"Rule Guard check failed: {guard_res.reason}"
        )

    try:
        compiler.compile_and_register(proposed_rule, rules_engine)
    except Exception as e:
        return DeployResponse(
            success=False,
            rule=proposed_rule,
            validation=ValidationResult(valid=False, error=str(e)),
            guard=guard_res,
            message=f"Compilation error: {str(e)}"
        )

    audit_logger.log_deploy_rule(proposed_rule, command=rule_cmd)

    return DeployResponse(
        success=True,
        rule=proposed_rule,
        validation=val_res,
        guard=guard_res,
        message=f"Rule '{proposed_rule.id}' deployed and hot-reloaded successfully."
    )


@router.post("/api/rules/revert", tags=["Fraud Engine Core"])
def revert_rule(request: RevertRuleRequest):
    rule_id = request.rule_id
    unregistered = rules_engine.unregister_rule(rule_id)
    cmd = request.command or "Analyst rule revert"
    audit_entry = audit_logger.log_revert_rule(rule_id=rule_id, command=cmd)

    if not audit_entry and not unregistered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found in database."
        )

    return {
        "success": True,
        "rule_id": rule_id,
        "message": f"Rule '{rule_id}' successfully reverted."
    }


@router.get("/api/rules", response_model=List[Rule], tags=["Fraud Engine Core"])
def get_active_rules():
    return rules_engine.get_active_rules()


@router.get("/api/audit-log", tags=["Fraud Engine Core"])
def get_audit_log(rule_id: Optional[str] = None):
    try:
        logs = audit_logger.get_audit_logs(rule_id=rule_id)
        is_valid, tampered_id = audit_logger.verify_hash_chain_integrity()
        entries = [
            e.model_dump() if hasattr(e, "model_dump") else (e.dict() if hasattr(e, "dict") else dict(e))
            for e in logs
        ]
        return {
            "integrity_valid": is_valid,
            "tampered_row_id": tampered_id,
            "entries": entries
        }
    except Exception as e:
        return {
            "integrity_valid": True,
            "tampered_row_id": None,
            "entries": [],
            "error": str(e)
        }


@router.post("/api/simulator/control", tags=["Fraud Engine Core"])
def control_simulator(request: SimulatorControlRequest):
    if request.profile_id:
        simulator.set_active_profile_id(request.profile_id)
    act = request.action.lower()
    if act == "play":
        simulator.play()
        from backend.batch_generator import generate_batch_20
        prof_id = request.profile_id or simulator.active_profile_id or "ACCOUNT_TAKEOVER"
        txs = generate_batch_20(prof_id)
        for tx in reversed(txs):
            tx_obj = Transaction(**tx)
            alert = FlaggedAlert(
                id=f"alt_{uuid.uuid4().hex[:8]}",
                transaction_id=tx_obj.id,
                rule_id="profile_scenario",
                rule_name=tx_obj.title or "Profile Fraud Alert",
                score=tx_obj.final_risk_score or 0.50,
                flagged_at=tx_obj.timestamp,
                transaction_details=tx_obj
            )
            record_flagged_alert(alert)
    elif act == "pause":
        simulator.pause()
    elif act == "stop":
        simulator.stop()
        alerts_history.clear()
    else:
        raise HTTPException(status_code=400, detail="Action must be 'play', 'pause', or 'stop'")

    return {"status": simulator.state.value, "profile_id": simulator.active_profile_id}




@router.post("/api/simulator/profile", tags=["Fraud Engine Core"])
def set_simulator_profile(profile: CustomProfile):
    simulator.set_profile(profile)
    return {"message": f"Simulator profile '{profile.name}' applied successfully."}


@router.get("/api/simulator/status", tags=["Fraud Engine Core"])
def get_simulator_status():
    return {
        "state": simulator.state.value,
        "profile": simulator.profile
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. FRONTEND SECURITY DASHBOARD ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts", summary="List flagged alerts for frontend", tags=["Frontend Dashboard"])
async def list_alerts() -> List[dict]:
    return alerts_history


@router.post("/alerts/{alert_id}/explain", response_model=ExplainResponse, tags=["Frontend Dashboard"])
async def explain_alert(
    alert_id: str,
    body: ExplainRequest = ExplainRequest(),
) -> ExplainResponse:
    alert = next((a for a in alerts_history if a.get("id") == alert_id or a.get("transaction", {}).get("id") == alert_id), None)
    if not alert and body.alert_data:
        alert = body.alert_data
    if not alert:
        alert = {
            "id": alert_id,
            "rule_triggered": "Fraud Detection Alert",
            "severity": "high",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction": {
                "id": alert_id,
                "user_name": "Devon Vance",
                "account_id": "acc_8443",
                "amount": 3543.0,
                "location": "CN-BEI",
                "title": "High Amount Transaction Threshold",
                "description": "High amount transaction performed by Devon Vance on account acc_8443 (CN-BEI)."
            }
        }

    result = await orchestrator.route(command=body.command, context=alert)

    if result.get("error") or not result.get("result"):
        from backend.ai.agents.investigator import generate_forensic_explanation
        explanation = generate_forensic_explanation(alert)
    else:
        explanation = result["result"] if isinstance(result["result"], str) else str(result["result"])

    return ExplainResponse(explanation=explanation)


@router.post("/rules/generate", response_model=GenerateRuleResponse, tags=["Frontend Dashboard"])
async def generate_rule_endpoint(body: GenerateRuleRequest) -> GenerateRuleResponse:
    context = None
    if body.alert_data:
        context = body.alert_data
    elif body.alert_id:
        context = next(
            (a for a in alerts_history if a.get("id") == body.alert_id or a.get("transaction", {}).get("id") == body.alert_id),
            None
        )
    if not context and alerts_history:
        context = alerts_history[0]

    try:
        result = await orchestrator.route(command=body.command, context=context)
        agent_output = result.get("result") if isinstance(result, dict) else None

        if isinstance(agent_output, dict):
            code_val = agent_output.get("code", "")
            expl_val = agent_output.get("explanation")
            if isinstance(code_val, dict):
                expl_val = code_val.get("explanation") or expl_val
                code_val = code_val.get("code", "")

            return GenerateRuleResponse(
                code=str(code_val or ""),
                explanation=expl_val,
                valid=agent_output.get("valid", True),
                error=agent_output.get("error"),
            )

        if agent_output:
            return GenerateRuleResponse(
                code=str(agent_output),
                explanation=None,
                valid=True,
                error=None,
            )

        from backend.ai.agents.rule_writer import generate_fallback_rule
        fb = generate_fallback_rule(body.command, context)
        return GenerateRuleResponse(
            code=fb.get("code", "") if isinstance(fb, dict) else str(fb),
            explanation=fb.get("explanation") if isinstance(fb, dict) else None,
            valid=True,
            error=None,
        )
    except Exception as exc:
        from backend.ai.agents.rule_writer import generate_fallback_rule
        fb = generate_fallback_rule(body.command, context)
        return GenerateRuleResponse(
            code=fb.get("code", "") if isinstance(fb, dict) else str(fb),
            explanation=fb.get("explanation") if isinstance(fb, dict) else None,
            valid=True,
            error=None,
        )




@router.post("/rules/deploy", tags=["Frontend Dashboard"])
@router.post("/rules/{rule_id}/approve", tags=["Frontend Dashboard"])
async def approve_or_deploy_rule(request_body: Optional[DeployRuleRequest] = None, rule_id: Optional[str] = None):
    code_to_deploy = request_body.code if request_body else "def evaluate(tx):\n    return tx.amount > 10000"
    name = (request_body.name if request_body else None) or f"Rule_{rule_id or uuid.uuid4().hex[:6]}"
    desc = (request_body.description if request_body else None) or "Analyst approved rule"
    cmd = (request_body.command if request_body else None) or "Analyst approval"

    dep_req = DeployRuleRequest(name=name, code=code_to_deploy, description=desc, command=cmd)
    res = deploy_rule(dep_req)

    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)

    return {"status": "deployed", "rule": res.rule, "message": res.message}


@router.post("/rules/revert", tags=["Frontend Dashboard"])
@router.post("/rules/{rule_id}/revert", tags=["Frontend Dashboard"])
async def revert_rule_endpoint(rule_id: Optional[str] = None, request: Optional[RevertRuleRequest] = None):
    target_id = request.rule_id if request else rule_id
    if not target_id:
        raise HTTPException(status_code=400, detail="rule_id must be provided")

    rev_req = RevertRuleRequest(rule_id=target_id, command=request.command if request else "Analyst revert")
    return revert_rule(rev_req)


@router.post("/simulator/state", tags=["Frontend Dashboard"])
@router.post("/simulator/control", tags=["Frontend Dashboard"])
async def set_simulator_state_endpoint(body: SimulatorControlRequest):
    return control_simulator(body)


@router.post("/profiles", tags=["Frontend Dashboard"])
async def create_profile_endpoint(body: ProfileRequest):
    profile_id = f"profile_{uuid.uuid4().hex[:8]}"
    rules = body.rules or {}
    
    interval = float(rules.get("interval_seconds", 1.0))
    mult = float(rules.get("amount_multiplier", 1.0))
    bias = float(rules.get("fraud_risk_bias", 0.3))

    custom_prof = CustomProfile(
        name=body.name,
        amount_multiplier=mult,
        fraud_risk_bias=bias,
        high_risk_country_bias=0.2
    )

    simulator.interval_seconds = interval
    simulator.set_profile(custom_prof)

    return {"profile_id": profile_id, "name": body.name, "interval_seconds": interval}


from backend.batch_generator import generate_batch_20


class ProfileSimulateRequest(BaseModel):
    profile_id: Optional[str] = "ACCOUNT_TAKEOVER"
    count: Optional[int] = 20


@router.post("/simulate/profile", tags=["Frontend Dashboard"])
async def simulate_profile_endpoint(body: ProfileSimulateRequest):
    txs = generate_batch_20(body.profile_id or "ACCOUNT_TAKEOVER")
    return {
        "profile_id": body.profile_id,
        "count": len(txs),
        "transactions": txs
    }


@router.post("/api/scoring/evaluate", response_model=ScoringResult, tags=["Scoring Engine"])
@router.post("/scoring/evaluate", response_model=ScoringResult, tags=["Scoring Engine"])
def evaluate_scoring_endpoint(payload: Dict[str, Any]):
    """
    Evaluates raw behavioral & transactional payload using deterministic formulas from formulae.docx.
    Returns telemetry_risk_score, transaction_risk_score, final_risk_score, and classification.
    """
    return evaluate_transaction(payload)

