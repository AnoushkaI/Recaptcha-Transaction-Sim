// frontend/src/api.js
// Central API client — all backend calls go through here.

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

export async function approveRule(ruleId, ruleData = {}) {
  const payload = {
    name: ruleData.name || `Rule ${ruleId}`,
    code: ruleData.code || '',
    description: ruleData.description || 'AI generated fraud rule',
    command: ruleData.command || 'Analyst rule deployment',
  };

  const res = await fetch(`${BASE}/rules/deploy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `POST /rules/deploy failed: ${res.status}`);
  }
  return res.json();
}

export async function revertRule(ruleId) {
  const res = await fetch(`${BASE}/rules/revert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rule_id: ruleId, command: 'Analyst rule revert' }),
  });
  if (!res.ok) throw new Error(`POST /rules/revert failed: ${res.status}`);
  return res.json();
}

export async function setSimulatorState(action) {
  const res = await fetch(`${BASE}/simulator/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`POST /simulator/control failed: ${res.status}`);
  return res.json();
}

export async function createProfile(name, rules = null) {
  const res = await fetch(`${BASE}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, rules }),
  });
  if (!res.ok) throw new Error(`POST /profiles failed: ${res.status}`);
  return res.json();
}

export const WS_ALERTS_URL = 'ws://localhost:8000/alerts/stream';
