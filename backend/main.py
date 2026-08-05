"""
Main FastAPI Server & WebSocket Streamer (`backend/main.py`)

Entry point for the Fraud Detection Rule Engine & AI Security Dashboard.
Provides real-time alert streaming over WebSockets (/ws/alerts and /alerts/stream).
"""
import uuid
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.profiles.library import ProfileLibraryRepository
from backend.core.db import init_db
from backend.core.schemas import Transaction, FlaggedAlert
from backend.api.routes import (
    router as api_router,
    simulator,
    rules_engine,
    audit_logger,
    compiler,
    record_flagged_alert,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for the frontend dashboard."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        payload = json.dumps(message)
        disconnected = set()

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Fraud Rule Engine backend...")

    # Load the independently-authored profile definitions before simulation can run.
    # If the JSON library was removed, this performs one validated LLM generation
    # and persists the result before the simulator is available.
    profile_library = await ProfileLibraryRepository(
        settings.PROFILE_LIBRARY_PATH
    ).load_or_generate()
    logger.info("Validated profile library ready: %d profiles", len(profile_library.profiles))

    # 1. Initialize SQLite Database
    init_db(settings.DATABASE_PATH)

    # 2. Load & compile active startup rules
    active_rules = audit_logger.get_active_rules()
    if not active_rules:
        logger.info("No active rules found in database. Seeding default initial rules...")
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        from backend.core.schemas import Rule
        default_rules = [
            Rule(
                id="rule_high_amount",
                name="High Amount Transaction Threshold",
                code="def evaluate(tx):\n    return tx.amount > 2000.0",
                description="Flag transactions exceeding $2,000 threshold",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_intl_wire",
                name="International Wire Transfer Risk",
                code="def evaluate(tx):\n    return tx.is_international and tx.merchant_category == 'wire_transfer'",
                description="Flag cross-border wire transfer operations",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_new_account",
                name="New Account High Value Activity",
                code="def evaluate(tx):\n    return tx.account_age_days < 7 and tx.amount > 500.0",
                description="Flag high-value transactions on accounts newer than 7 days",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_crypto_gaming",
                name="Crypto & Gaming Merchant Anomaly",
                code="def evaluate(tx):\n    return tx.merchant_category in ['crypto', 'gaming']",
                description="Flag high-risk merchant category transactions",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_micro_test",
                name="Low Value Micro-Transaction Test",
                code="def evaluate(tx):\n    return tx.amount < 15.0 and tx.is_international",
                description="Flag low-value cross-border testing attempts",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_electronics_spike",
                name="Electronics E-Commerce Spike",
                code="def evaluate(tx):\n    return tx.merchant_category == 'electronics' and tx.amount > 800.0",
                description="Flag large electronics purchases",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            ),
            Rule(
                id="rule_gas_station_test",
                name="Gas Station Card Testing",
                code="def evaluate(tx):\n    return tx.merchant_category == 'gas_station' and tx.amount < 25.0",
                description="Flag small gas station testing transactions",
                created_at=now,
                status="active",
                created_by_command="Default initial rule"
            )
        ]
        for r in default_rules:
            audit_logger.log_deploy_rule(r, command="Default initial rule")
        active_rules = audit_logger.get_active_rules()

    logger.info(f"Loaded {len(active_rules)} active rules from database.")
    for rule in active_rules:
        try:
            compiler.compile_and_register(rule, rules_engine)
        except Exception as e:
            logger.error(f"Failed to compile startup rule '{rule.id}': {e}")

    # 3. Hook simulator emission to rules_engine and WebSocket broadcast
    async def handle_simulated_tx(tx: Transaction):
        tx_data = tx.model_dump()
        await ws_manager.broadcast({
            "type": "transaction",
            "data": tx_data
        })
        triggered_alerts = rules_engine.score_transaction(tx)

        # Record alert ONLY for HIGH_RISK transactions
        if not triggered_alerts and (getattr(tx, "classification", "") == "HIGH_RISK" or (tx.final_risk_score or 0.0) >= 0.60):
            alert = FlaggedAlert(
                id=f"alt_{uuid.uuid4().hex[:8]}",
                transaction_id=tx.id,
                rule_id="profile_scenario",
                rule_name=tx.title or "Profile Fraud Alert",
                score=tx.final_risk_score or 0.50,
                flagged_at=tx.timestamp,
                transaction_details=tx
            )
            mapped_alert = record_flagged_alert(alert)
            await ws_manager.broadcast(mapped_alert)



    async def handle_flagged_alert(alert: FlaggedAlert):
        mapped_alert = record_flagged_alert(alert)

        # Broadcast flagged alert event to WebSocket for both formats
        await ws_manager.broadcast({
            "type": "flagged_alert",
            "data": alert.model_dump()
        })
        await ws_manager.broadcast(mapped_alert)

    simulator.add_async_listener(handle_simulated_tx)
    rules_engine.add_async_alert_listener(handle_flagged_alert)

    logger.info("Engine startup complete. Real-time rules engine is online.")

    yield

    simulator.stop()
    logger.info("Engine shutdown clean.")


app = FastAPI(
    title="AI-Assisted Fraud Detection Engine",
    description="Integrated Real-Time Rules Engine, AST Validator, and AI Orchestrator",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Fraud Detection Engine",
        "provider": settings.LLM_PROVIDER,
        "active_rules_count": len(rules_engine.get_active_rules())
    }


@app.websocket("/ws/alerts")
@app.websocket("/alerts/stream")
async def websocket_alerts(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
