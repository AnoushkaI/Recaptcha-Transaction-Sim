"""
Comprehensive API & main.py endpoint tests targeting maximum coverage.
Each test uses unique rule names/codes to avoid cross-test duplicate detection.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# --------------- health & status ---------------

def test_health_check():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "service" in data
    assert "active_rules_count" in data


def test_get_active_rules_empty():
    res = client.get("/api/rules")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# --------------- validate endpoint ---------------

def test_validate_valid_rule():
    res = client.post("/api/rules/validate", json={
        "name": "Valid Rule",
        "code": "def evaluate(tx):\n    return tx.amount > 100",
        "description": "Test valid rule",
        "command": "Test"
    })
    assert res.status_code == 200
    assert res.json()["valid"] is True


def test_validate_invalid_rule_import():
    res = client.post("/api/rules/validate", json={
        "name": "Invalid Rule",
        "code": "import os\ndef evaluate(tx): return True",
        "description": "Malicious",
        "command": "Test"
    })
    assert res.status_code == 200
    assert res.json()["valid"] is False
    assert "Disallowed import" in res.json()["error"]


# --------------- deploy endpoint ---------------

def test_deploy_valid_rule_success():
    res = client.post("/api/rules/deploy", json={
        "name": "Deploy Test A unique 1",
        "code": "def evaluate(tx):\n    return tx.amount > 9000 and tx.account_age_days < 3",
        "description": "Deploy test unique rule 1",
        "command": "Deploy unique rule 1"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["rule"]["id"].startswith("rule_")


def test_deploy_valid_rule_second_unique():
    """Different enough rule to avoid duplicate detection."""
    res = client.post("/api/rules/deploy", json={
        "name": "Deploy Test B unique 2",
        "code": "def evaluate(tx):\n    return tx.location == 'DEL-LKO' and tx.merchant_category == 'wire_transfer'",
        "description": "Flag KP wire transfers specifically",
        "command": "Deploy KP wire transfer check unique"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True


def test_deploy_ast_invalid_rule_fails():
    res = client.post("/api/rules/deploy", json={
        "name": "Malicious Deploy",
        "code": "import subprocess\ndef evaluate(tx): return True",
        "description": "AST failure test",
        "command": "Malicious"
    })
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "AST Safety Validation failed" in res.json()["message"]


# --------------- revert endpoint ---------------

def test_deploy_then_revert_success():
    # Deploy unique rule
    deploy_res = client.post("/api/rules/deploy", json={
        "name": "Rule To Revert Unique XYZ",
        "code": "def evaluate(tx):\n    return tx.device_id == 'dev_9999' and tx.amount > 999",
        "description": "Unique device rule for revert test",
        "command": "Deploy device rule for revert"
    })
    assert deploy_res.json()["success"] is True
    rule_id = deploy_res.json()["rule"]["id"]

    revert_res = client.post("/api/rules/revert", json={
        "rule_id": rule_id,
        "command": "Revert via API test"
    })
    assert revert_res.status_code == 200
    assert revert_res.json()["success"] is True
    assert revert_res.json()["rule_id"] == rule_id


def test_revert_nonexistent_rule_404():
    res = client.post("/api/rules/revert", json={
        "rule_id": "rule_does_not_exist_abc123",
        "command": "Revert non-existent"
    })
    assert res.status_code == 404


# --------------- audit log endpoint ---------------

def test_get_audit_log_all():
    res = client.get("/api/audit-log")
    assert res.status_code == 200
    data = res.json()
    assert "integrity_valid" in data
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_get_audit_log_filtered_by_rule_id():
    res = client.get("/api/audit-log?rule_id=nonexistent_rule")
    assert res.status_code == 200
    assert res.json()["entries"] == []


# --------------- simulator endpoints ---------------

def test_simulator_play():
    res = client.post("/api/simulator/control", json={"action": "play"})
    assert res.status_code == 200
    assert res.json()["status"] == "running"


def test_simulator_pause():
    client.post("/api/simulator/control", json={"action": "play"})
    res = client.post("/api/simulator/control", json={"action": "pause"})
    assert res.status_code == 200
    assert res.json()["status"] == "paused"


def test_simulator_stop():
    res = client.post("/api/simulator/control", json={"action": "stop"})
    assert res.status_code == 200
    assert res.json()["status"] == "stopped"


def test_simulator_invalid_action():
    res = client.post("/api/simulator/control", json={"action": "explode"})
    assert res.status_code == 400


def test_simulator_set_profile():
    res = client.post("/api/simulator/profile", json={
        "name": "api_high_risk",
        "amount_min": 5000.0,
        "amount_max": 10000.0,
        "high_risk_location_bias": 1.0,
        "new_account_bias": 0.8
    })
    assert res.status_code == 200
    assert "applied successfully" in res.json()["message"]


def test_simulator_status():
    res = client.get("/api/simulator/status")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "profile" in data


# --------------- websocket endpoint ---------------

def test_websocket_connects_and_stays_open():
    with client.websocket_connect("/ws/alerts") as ws:
        ws.send_text("ping")
        # Just verify connection is established — no crash
