"""
Main FastAPI Server & WebSocket Streamer (`main.py`)

Entry point for the Fraud Detection Rule Engine backend.
Provides real-time alert streaming over WebSocket `/ws/alerts`.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.core.db import init_db
from backend.core.schemas import Transaction, FlaggedAlert
from backend.core.compiler import RuleCompiler
from backend.api.routes import (
    router as api_router,
    simulator,
    rules_engine,
    audit_logger,
    compiler
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for Person B's frontend dashboard."""

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
        """Broadcast event to all connected WebSocket clients."""
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
    """
    Application startup and shutdown hooks.
    """
    logger.info("Initializing Fraud Rule Engine backend...")

    # 1. Initialize DB tables
    init_db(settings.DATABASE_PATH)

    # 2. Load and hot-reload active rules from SQLite at startup
    active_rules = audit_logger.get_active_rules()
    logger.info(f"Loaded {len(active_rules)} active rules from database.")
    for rule in active_rules:
        try:
            compiler.compile_and_register(rule, rules_engine)
        except Exception as e:
            logger.error(f"Failed to compile startup rule '{rule.id}': {e}")

    # 3. Hook simulator emission to rules_engine and WebSocket broadcast
    async def handle_simulated_tx(tx: Transaction):
        # Broadcast transaction event to WebSocket
        await ws_manager.broadcast({
            "type": "transaction",
            "data": tx.model_dump()
        })
        # Score transaction against active rules in-memory
        rules_engine.score_transaction(tx)

    async def handle_flagged_alert(alert: FlaggedAlert):
        # Broadcast flagged alert event to WebSocket
        await ws_manager.broadcast({
            "type": "flagged_alert",
            "data": alert.model_dump()
        })

    simulator.add_async_listener(handle_simulated_tx)
    rules_engine.add_async_alert_listener(handle_flagged_alert)

    logger.info("Engine startup complete. Real-time rules engine is online.")

    yield

    # Shutdown
    simulator.stop()
    logger.info("Engine shutdown clean.")


app = FastAPI(
    title="AI-Assisted Fraud Detection Engine",
    description="Person A Scope: Real-Time Rules Engine, AST Validator, Local LLM Provider",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware to allow cross-origin calls from Person B's frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
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
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for Person B's frontend to receive live transactions and flagged alerts.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive optional client messages/pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
