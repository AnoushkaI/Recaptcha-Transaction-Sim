from backend.ai.providers.factory import get_provider
from backend.ai.orchestrator import Orchestrator, _graph

print("Factory import: OK")
print("Orchestrator graph compiled: OK")

orch = Orchestrator()

# Test explain routing
r1 = orch.route(
    "explain this alert",
    context={
        "id": "alert_001",
        "transaction": {},
        "rule_triggered": "velocity_check",
        "severity": "high",
        "timestamp": "2026-07-26T10:15:02Z",
    },
)
assert r1["command_type"] == "explain_alert", f"Expected explain_alert, got {r1['command_type']}"
print(f"explain route -> command_type: {r1['command_type']}  (result: {str(r1['result'])[:60]})")

# Test generate routing
r2 = orch.route("generate a rule to detect large transactions", context=None)
assert r2["command_type"] == "generate_rule", f"Expected generate_rule, got {r2['command_type']}"
print(f"generate route -> command_type: {r2['command_type']}")

# Test provider factory
inv_provider = get_provider(role="investigator")
rw_provider = get_provider(role="rule_writer")
print(f"investigator provider: {inv_provider}")
print(f"rule_writer provider:  {rw_provider}")

print("")
print("Phase 2 — All checks passed.")
