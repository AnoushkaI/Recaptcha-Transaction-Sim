"""
API Routes (`api/routes.py`)

FastAPI REST endpoints for Person A scope: rule validation, guard evaluation,
deployment, revert, audit log inspection, and simulator controls.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

from backend.core.schemas import (
    Rule,
    Transaction,
    FlaggedAlert,
    CustomProfile,
    ValidationResult,
    GuardResult,
    AuditLogEntry
)
from backend.core.validator import ASTSafetyValidator
from backend.core.rule_guard import RuleGuard
from backend.core.compiler import RuleCompiler
from backend.core.rules_engine import RulesEngine
from backend.core.audit_log import AuditLogger
from backend.core.simulator import TransactionSimulator, SimulatorState
from backend.config import settings

router = APIRouter(prefix="/api", tags=["Fraud Engine"])

# Global engine singletons (injected or accessed from app state)
validator = ASTSafetyValidator()
rule_guard = RuleGuard(
    max_rules_cap=settings.MAX_RULES_CAP,
    similarity_threshold=settings.SIMILARITY_THRESHOLD
)
compiler = RuleCompiler()
rules_engine = RulesEngine()
audit_logger = AuditLogger(db_path=settings.DATABASE_PATH)
simulator = TransactionSimulator(interval_seconds=1.0)


# Request schemas
class DeployRuleRequest(BaseModel):
    name: str = Field(..., description="Rule title")
    code: str = Field(..., description="Python evaluate(tx) code")
    description: str = Field(..., description="Description of rule logic")
    command: str = Field(default="Analyst rule deployment", description="Original user prompt or command")


class RevertRuleRequest(BaseModel):
    rule_id: str = Field(..., description="Rule ID to revert")
    command: str = Field(default="Analyst rule revert", description="Reason for revert")


class SimulatorControlRequest(BaseModel):
    action: str = Field(..., description="Action: 'play', 'pause', or 'stop'")


class DeployResponse(BaseModel):
    success: bool
    rule: Optional[Rule] = None
    validation: ValidationResult
    guard: Optional[GuardResult] = None
    message: str


@router.post("/rules/validate", response_model=ValidationResult)
def validate_rule_code(request: DeployRuleRequest):
    """Run AST Safety Validator on rule Python source code without deploying."""
    return validator.validate(request.code)


@router.post("/rules/deploy", response_model=DeployResponse)
def deploy_rule(request: DeployRuleRequest):
    """
    Full rule deployment pipeline:
    1. AST Safety Validation
    2. Rule Guard (cap + duplicate check)
    3. Compilation & Hot-reload into live engine
    4. SHA-256 Hash-chained audit logging in SQLite
    """
    # 1. AST Validation
    val_res = validator.validate(request.code)
    if not val_res.valid:
        return DeployResponse(
            success=False,
            validation=val_res,
            message=f"AST Safety Validation failed: {val_res.error}"
        )

    rule_id = f"rule_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    proposed_rule = Rule(
        id=rule_id,
        name=request.name,
        code=request.code,
        description=request.description,
        created_at=timestamp,
        status="active",
        created_by_command=request.command
    )

    # 2. Rule Guard Evaluation
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

    # 3. Compile & Hot-reload
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

    # 4. Audit Log
    audit_logger.log_deploy_rule(proposed_rule, command=request.command)

    return DeployResponse(
        success=True,
        rule=proposed_rule,
        validation=val_res,
        guard=guard_res,
        message=f"Rule '{proposed_rule.id}' deployed and hot-reloaded successfully."
    )


@router.post("/rules/revert")
def revert_rule(request: RevertRuleRequest):
    """
    Reverts an active rule: unregisters from live engine and logs revert action.
    """
    rule_id = request.rule_id
    unregistered = rules_engine.unregister_rule(rule_id)
    audit_entry = audit_logger.log_revert_rule(rule_id=rule_id, command=request.command)

    if not audit_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found in database."
        )

    return {
        "success": True,
        "rule_id": rule_id,
        "message": f"Rule '{rule_id}' successfully reverted."
    }


@router.get("/rules", response_model=List[Rule])
def get_active_rules():
    """Get all currently active rules."""
    return rules_engine.get_active_rules()


@router.get("/audit-log")
def get_audit_log(rule_id: Optional[str] = None):
    """Get complete audit log history and hash chain integrity state."""
    logs = audit_logger.get_audit_logs(rule_id=rule_id)
    is_valid, tampered_id = audit_logger.verify_hash_chain_integrity()
    return {
        "integrity_valid": is_valid,
        "tampered_row_id": tampered_id,
        "entries": logs
    }


@router.post("/simulator/control")
def control_simulator(request: SimulatorControlRequest):
    """Play / Pause / Stop synthetic transaction simulator."""
    act = request.action.lower()
    if act == "play":
        simulator.play()
    elif act == "pause":
        simulator.pause()
    elif act == "stop":
        simulator.stop()
    else:
        raise HTTPException(status_code=400, detail="Action must be 'play', 'pause', or 'stop'")

    return {"status": simulator.state.value}


@router.post("/simulator/profile")
def set_simulator_profile(profile: CustomProfile):
    """Inject a custom profile bias into simulator."""
    simulator.set_profile(profile)
    return {"message": f"Simulator profile '{profile.name}' applied successfully."}


@router.get("/simulator/status")
def get_simulator_status():
    """Get current simulator state and active profile."""
    return {
        "state": simulator.state.value,
        "profile": simulator.profile
    }
