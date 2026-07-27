// frontend/src/api.js
// Central API client — all backend calls go through here.
// Phase 4: calls FastAPI backend on port 8000.
// Phase 5: same URLs, backend now hits real teammate data.

const BASE = 'http://localhost:8000';

export async function fetchAlerts() {
  const res = await fetch(`${BASE}/alerts`);
  if (!res.ok) throw new Error(`GET /alerts failed: ${res.status}`);
  return res.json();
}

export async function explainAlert(alertId, command = 'explain this') {
  const res = await fetch(`${BASE}/alerts/${alertId}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `POST /alerts/${alertId}/explain failed: ${res.status}`);
  }
  return res.json(); // { explanation: string }
}

export async function generateRule(command, alertId = null) {
  const res = await fetch(`${BASE}/rules/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, alert_id: alertId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `POST /rules/generate failed: ${res.status}`);
  }
  return res.json(); // { code, valid, error }
}

export async function approveRule(ruleId) {
  const res = await fetch(`${BASE}/rules/${ruleId}/approve`, { method: 'POST' });
  if (!res.ok) throw new Error(`POST /rules/${ruleId}/approve failed: ${res.status}`);
  return res.json(); // { status: "deployed" }
}

export async function revertRule(ruleId) {
  const res = await fetch(`${BASE}/rules/${ruleId}/revert`, { method: 'POST' });
  if (!res.ok) throw new Error(`POST /rules/${ruleId}/revert failed: ${res.status}`);
  return res.json(); // { status: "reverted" }
}

export async function setSimulatorState(action) {
  const res = await fetch(`${BASE}/simulator/state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`POST /simulator/state failed: ${res.status}`);
  return res.json(); // { is_running: bool }
}

export async function createProfile(name, rules = null) {
  const res = await fetch(`${BASE}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, rules }),
  });
  if (!res.ok) throw new Error(`POST /profiles failed: ${res.status}`);
  return res.json(); // { profile_id: string }
}

// WebSocket URL for live alert stream
export const WS_ALERTS_URL = 'ws://localhost:8000/alerts/stream';
