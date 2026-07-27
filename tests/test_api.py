"""
API & FastAPI Endpoint Unit Tests (`tests/test_api.py`).
Verifies 100% endpoint coverage for backend/main.py and backend/api/routes.py.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "Fraud Detection Engine"


def test_get_active_rules_endpoint():
    response = client.get("/api/rules")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_validate_rule_endpoint():
    payload = {
        "name": "API Validate Rule",
        "code": "def evaluate(tx):\n    return tx.amount > 100",
        "description": "Validation test",
        "command": "Validate"
    }
    response = client.post("/api/rules/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


def test_deploy_rule_endpoint_success():
    payload = {
        "name": "API Deploy Rule Success",
        "code": "def evaluate(tx):\n    return tx.amount > 5000 and tx.is_international",
        "description": "Deploy test rule",
        "command": "Deploy rule via API"
    }
    response = client.post("/api/rules/deploy", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rule"]["id"].startswith("rule_")


def test_deploy_rule_endpoint_ast_fail():
    payload = {
        "name": "API Deploy Rule AST Fail",
        "code": "import os\ndef evaluate(tx): os.system('whoami')",
        "description": "Invalid rule",
        "command": "Malicious code"
    }
    response = client.post("/api/rules/deploy", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Disallowed import" in data["message"]


def test_revert_rule_endpoint():
    # Deploy first
    deploy_payload = {
        "name": "To Revert Rule",
        "code": "def evaluate(tx): return tx.account_age_days < 3",
        "description": "Revert test",
        "command": "Deploy to revert"
    }
    deploy_res = client.post("/api/rules/deploy", json=deploy_payload).json()
    rule_id = deploy_res["rule"]["id"]

    # Revert
    revert_payload = {
        "rule_id": rule_id,
        "command": "Revert rule API test"
    }
    revert_res = client.post("/api/rules/revert", json=revert_payload)
    assert revert_res.status_code == 200
    assert revert_res.json()["success"] is True


def test_get_audit_log_endpoint():
    response = client.get("/api/audit-log")
    assert response.status_code == 200
    data = response.json()
    assert "integrity_valid" in data
    assert "entries" in data


def test_simulator_control_endpoint():
    action_map = {"play": "running", "pause": "paused", "stop": "stopped"}
    for act, expected_status in action_map.items():
        response = client.post("/api/simulator/control", json={"action": act})
        assert response.status_code == 200
        assert response.json()["status"] == expected_status

    # Invalid action
    response_inv = client.post("/api/simulator/control", json={"action": "invalid_action"})
    assert response_inv.status_code == 400


def test_simulator_profile_endpoint():
    profile_data = {
        "name": "api_profile_test",
        "amount_min": 1000.0,
        "amount_max": 2000.0,
        "high_risk_location_bias": 0.5,
        "new_account_bias": 0.5
    }
    response = client.post("/api/simulator/profile", json=profile_data)
    assert response.status_code == 200
    assert "applied successfully" in response.json()["message"]


def test_simulator_status_endpoint():
    response = client.get("/api/simulator/status")
    assert response.status_code == 200
    assert "state" in response.json()
    assert "profile" in response.json()


def test_websocket_alerts_endpoint():
    with client.websocket_connect("/ws/alerts") as websocket:
        websocket.send_text("ping")
