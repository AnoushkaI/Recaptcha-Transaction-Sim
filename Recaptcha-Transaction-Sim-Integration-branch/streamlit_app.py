"""
streamlit_app.py — AI Fraud Rule Engine Dashboard
Streamlit replacement for the React/Vite frontend.
Connects to FastAPI backend at http://localhost:8000.

Run:
    streamlit run streamlit_app.py
"""

import time
import requests
import streamlit as st
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
MAX_ALERTS = 20
REFRESH_INTERVAL_MS = 3000  # ms — live alert polling


# ─── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fraud Rule Engine — AI Security Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─── Global CSS injection ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0a0c10 !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
section[data-testid="stSidebar"] { display: none; }

/* ── Main content padding ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Dashboard header ── */
.dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 28px;
    background: #111318;
    border-bottom: 1px solid #1e2433;
    position: sticky;
    top: 0;
    z-index: 100;
}
.dash-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.3px;
}
.dash-logo .logo-icon {
    font-size: 22px;
    filter: drop-shadow(0 0 8px rgba(79,122,255,0.6));
}
.dash-divider { width: 1px; height: 20px; background: #2a3142; margin: 0 12px; }
.dash-subtitle {
    font-size: 11px;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.live-badge {
    padding: 3px 10px;
    background: #0d1421;
    border: 1px solid #1e2433;
    border-radius: 6px;
    font-size: 10px;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Controls bar ── */
.controls-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 28px;
    background: #0d1117;
    border-bottom: 1px solid #1e2433;
}
.sim-state-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    background: #111318;
    border: 1px solid #1e2433;
    border-radius: 20px;
    font-size: 12px;
    color: #94a3b8;
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: #374151; display: inline-block; }
.dot.running { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.6); animation: pulse 1.5s infinite; }
.dot.paused  { background: #f59e0b; box-shadow: 0 0 6px rgba(245,158,11,0.5); }
.dot.stopped { background: #374151; }

/* ── Panel containers ── */
.panel-box {
    background: #111318;
    border: 1px solid #1e2433;
    border-radius: 12px;
    overflow: hidden;
    height: 100%;
}
.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #0d1117;
    border-bottom: 1px solid #1e2433;
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ── Alert rows ── */
.alert-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid #1a1f2e;
    cursor: pointer;
    transition: background 0.15s;
    border-radius: 0;
}
.alert-row:hover { background: #161b27; }
.alert-row.selected { background: #131c35; border-left: 3px solid #4f7aff; }
.alert-rule { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.alert-meta { font-size: 10px; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
.alert-amount { font-size: 13px; font-weight: 700; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }

/* ── Severity badges ── */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge.high   { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
.badge.medium { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.badge.low    { background: rgba(34,197,94,0.15);  color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }

/* ── Stats metrics ── */
.stat-card {
    text-align: center;
    padding: 10px 16px;
    background: #111318;
    border: 1px solid #1e2433;
    border-radius: 8px;
}
.stat-value { font-size: 22px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.stat-value.high   { color: #ef4444; }
.stat-value.medium { color: #f59e0b; }
.stat-value.success { color: #22c55e; }
.stat-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

/* ── Chat messages ── */
.msg-context-bar {
    padding: 10px 14px;
    background: #0d1117;
    border-bottom: 1px solid #1e2433;
    font-size: 11px;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
}
.msg-context-id { font-weight: 600; color: #94a3b8; }
.msg-context-rule { color: #4f7aff; margin-top: 2px; font-size: 12px; }

.msg-user {
    background: rgba(79,122,255,0.12);
    border: 1px solid rgba(79,122,255,0.25);
    border-radius: 10px 10px 2px 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: #e2e8f0;
    margin: 6px 0;
    margin-left: auto;
    max-width: 80%;
    width: fit-content;
    float: right;
    clear: both;
}
.msg-explain {
    background: #131a2e;
    border: 1px solid #1e2d50;
    border-radius: 2px 10px 10px 10px;
    padding: 12px 14px;
    margin: 6px 0;
    clear: both;
}
.msg-explain-label {
    font-size: 10px;
    font-weight: 700;
    color: #4f7aff;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.msg-explain-text { font-size: 13px; color: #cbd5e1; line-height: 1.6; }
.msg-rule {
    background: #0f1a12;
    border: 1px solid #1e3a24;
    border-radius: 2px 10px 10px 10px;
    padding: 12px 14px;
    margin: 6px 0;
    clear: both;
}
.msg-rule-label {
    font-size: 10px;
    font-weight: 700;
    color: #22c55e;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
}
.msg-system {
    text-align: center;
    font-size: 11px;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
    padding: 8px;
    clear: both;
}
.msg-error {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    color: #ef4444;
    clear: both;
}

/* ── Code diff view ── */
.diff-container {
    border: 1px solid #1e3a24;
    border-radius: 8px;
    overflow: hidden;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    margin-top: 8px;
}
.diff-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: #0d1f11;
    border-bottom: 1px solid #1e3a24;
    font-size: 11px;
    color: #94a3b8;
}
.diff-body { background: #080f0a; max-height: 250px; overflow-y: auto; }
.diff-line { display: flex; gap: 8px; padding: 1px 12px; }
.diff-line.add { background: rgba(34,197,94,0.07); color: #86efac; }
.diff-line-num { min-width: 24px; color: #374151; text-align: right; user-select: none; }

/* ── Retry badge ── */
.retry-badge {
    margin-left: 8px;
    padding: 1px 6px;
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 4px;
    font-size: 9px;
    color: #f59e0b;
}

/* ── Streamlit widget overrides ── */
.stButton > button {
    background: #111318 !important;
    color: #e2e8f0 !important;
    border: 1px solid #2a3142 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #161b27 !important;
    border-color: #4f7aff !important;
    color: #e2e8f0 !important;
}
button[kind="primary"] {
    background: #2d4ecc !important;
    border-color: #4f7aff !important;
    color: #fff !important;
}
button[kind="primary"]:hover {
    background: #3b5fe0 !important;
}

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stNumberInput"] input {
    background: #0d1117 !important;
    border-color: #1e2433 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #4f7aff !important;
    box-shadow: 0 0 0 2px rgba(79,122,255,0.2) !important;
}

.stExpander {
    background: #111318 !important;
    border: 1px solid #1e2433 !important;
    border-radius: 10px !important;
}
.stExpander summary {
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

.stMetric {
    background: #111318 !important;
    border: 1px solid #1e2433 !important;
    border-radius: 10px !important;
    padding: 12px !important;
}
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-size: 26px !important; }

[data-testid="stChatInput"] textarea {
    background: #0d1117 !important;
    border-color: #1e2433 !important;
    color: #e2e8f0 !important;
}
[data-testid="stChatMessage"] {
    background: transparent !important;
}

.stAlert { border-radius: 8px !important; }

.stSlider [data-baseweb="slider"] { padding: 0 !important; }

/* ── WS status dot animation ── */
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(34,197,94,0.4); }
    70%  { box-shadow: 0 0 0 5px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
}

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0c10; }
::-webkit-scrollbar-thumb { background: #2a3142; border-radius: 4px; }

/* ── Dividers ── */
hr { border-color: #1e2433 !important; }

/* ── Dataframe / table overrides ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialisation ─────────────────────────────────────────────
def init_state():
    defaults = {
        "alerts": [],
        "selected_alert": None,
        "chat_messages": [],          # list of dicts: {role, content, type, ...}
        "pending_rule": None,         # {code, ruleId, command, valid}
        "sim_state": "stopped",       # stopped | running | paused
        "rule_deployed_count": 0,
        "active_profile": "Standard Simulation",
        "last_refresh": 0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── API helpers ──────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs):
    """Thin wrapper around requests; returns (data, error_str)."""
    try:
        r = requests.request(method, f"{BASE_URL}{path}", timeout=8, **kwargs)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend offline — start uvicorn first"
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


def fetch_alerts():
    data, err = api("GET", "/alerts")
    return data or [], err


def explain_alert(alert_id: str, command: str):
    data, err = api("POST", f"/alerts/{alert_id}/explain",
                    json={"command": command})
    return data, err


def generate_rule(command: str, alert_id: str):
    data, err = api("POST", "/rules/generate",
                    json={"command": command, "alert_id": alert_id})
    return data, err


def deploy_rule(rule_name: str, code: str, description: str, command: str):
    data, err = api("POST", "/rules/deploy",
                    json={"name": rule_name, "code": code,
                          "description": description, "command": command})
    return data, err


def revert_rule():
    data, err = api("POST", "/rules/revert",
                    json={"rule_id": "latest", "command": "Analyst rule revert"})
    return data, err


def set_simulator_state(action: str):
    data, err = api("POST", "/simulator/control", json={"action": action})
    return data, err


def create_profile(name: str, rules: dict):
    data, err = api("POST", "/profiles", json={"name": name, "rules": rules})
    return data, err


def fetch_rules():
    data, err = api("GET", "/api/rules")
    return data or [], err


def fetch_audit_log():
    data, err = api("GET", "/api/audit-log")
    return data or {"entries": [], "integrity_valid": True}, err


# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_inr(amount):
    try:
        return f"₹{float(amount):,.0f}"
    except Exception:
        return str(amount)


def fmt_time(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        return str(ts)


def severity_badge(sev: str) -> str:
    colors = {
        "high":   ("#ef4444", "rgba(239,68,68,0.15)",   "rgba(239,68,68,0.3)"),
        "medium": ("#f59e0b", "rgba(245,158,11,0.15)",  "rgba(245,158,11,0.3)"),
        "low":    ("#22c55e", "rgba(34,197,94,0.15)",   "rgba(34,197,94,0.3)"),
    }
    c, bg, border = colors.get(sev, ("#94a3b8", "rgba(148,163,184,0.1)", "rgba(148,163,184,0.2)"))
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'font-size:10px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;'
        f'color:{c};background:{bg};border:1px solid {border};">{sev}</span>'
    )


def code_diff_html(code: str) -> str:
    lines = code.split("\n")
    rows = ""
    for i, line in enumerate(lines, 1):
        escaped = (line
                   .replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace(" ", "&nbsp;")
                   or "&nbsp;")
        rows += (
            f'<div class="diff-line add">'
            f'<span class="diff-line-num">{i}</span>'
            f'<span class="diff-line-content">+&nbsp;{escaped}</span>'
            f'</div>'
        )
    return f"""
    <div class="diff-container">
      <div class="diff-header">
        <span style="color:#22c55e">+</span>
        <span>rule.py</span>
        <span style="margin-left:auto;color:#64748b;font-size:10px">new rule · {len(lines)} lines</span>
      </div>
      <div class="diff-body">
        <div class="diff-line" style="color:#374151;padding:2px 12px">
          <span class="diff-line-num">@@</span>
          <span>&nbsp;@@ -0,0 +1,{len(lines)} @@</span>
        </div>
        {rows}
      </div>
    </div>
    """


# ─── Auto-refresh ─────────────────────────────────────────────────────────────
# Uses a simple time-based check so the page reruns at most every 3s
_now = time.time()
if _now - st.session_state.last_refresh > (REFRESH_INTERVAL_MS / 1000):
    fresh_alerts, _ = fetch_alerts()
    if fresh_alerts:
        st.session_state.alerts = fresh_alerts[:MAX_ALERTS]
    st.session_state.last_refresh = _now


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── HEADER ──────────────────────────────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<div class="dash-header">
  <div class="dash-logo">
    <span class="logo-icon">🛡</span>
    Fraud Rule Engine
    <div class="dash-divider"></div>
    <span class="dash-subtitle">AI Security Console</span>
  </div>
  <div class="live-badge">Live Backend Engine</div>
</div>
""", unsafe_allow_html=True)


# ─── Profile Options ─────────────────────────────────────────────────────────
PROFILE_IDS = [
    "REGULAR_CUSTOMER",
    "GIFT_CARD_FRAUD",
    "CARD_TESTING",
    "ACCOUNT_TAKEOVER",
    "CREDENTIAL_STUFFING",
    "REFUND_FRAUD",
    "SYNTHETIC_IDENTITY_FRAUD",
    "MONEY_MULE_TRANSFER",
    "AUTHORIZED_PUSH_PAYMENT_SCAM",
    "VPN_HIGH_RISK_TRAVELER",
]

def simulate_profile(profile_id: str, count: int = 20):
    data, err = api("POST", "/simulate/profile", json={"profile_id": profile_id, "count": count})
    return data, err


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── SIMULATOR CONTROLS BAR ──────────────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div style="padding: 12px 28px 6px 28px;">', unsafe_allow_html=True)

sim_state = st.session_state.sim_state
dot_cls = "running" if sim_state == "running" else ("paused" if sim_state == "paused" else "stopped")

st.markdown(f"""
<div class="controls-bar" style="padding:0;margin-bottom:6px;">
  <div class="sim-state-pill">
    <span class="dot {dot_cls}"></span>
    Simulator: <strong style="color:#e2e8f0;margin-left:4px;">{sim_state}</strong>
  </div>
</div>
""", unsafe_allow_html=True)

sim_cols = st.columns([2.5, 1.2, 1, 1, 1])

with sim_cols[0]:
    selected_prof = st.selectbox(
        "Select Active Fraud Profile (Source of Truth):",
        options=PROFILE_IDS,
        index=PROFILE_IDS.index(st.session_state.get("selected_profile_id", "ACCOUNT_TAKEOVER"))
        if st.session_state.get("selected_profile_id") in PROFILE_IDS else 3,
        key="profile_select_box"
    )
    if selected_prof != st.session_state.get("selected_profile_id"):
        st.session_state.selected_profile_id = selected_prof
        # Automatically trigger profile batch simulation
        res, err = simulate_profile(selected_prof, count=20)
        if not err and res:
            st.session_state.profile_transactions = res.get("transactions", [])
            fresh, _ = fetch_alerts()
            if fresh:
                st.session_state.alerts = fresh[:MAX_ALERTS]
            st.toast(f"Generated 20 synthetic transactions for profile: {selected_prof}", icon="🎯")
            st.rerun()

with sim_cols[1]:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("🎲 Generate Batch (20)", key="btn_gen_batch", use_container_width=True):
        prof_to_run = st.session_state.get("selected_profile_id", "ACCOUNT_TAKEOVER")
        res, err = simulate_profile(prof_to_run, count=20)
        if err:
            st.toast(f"Error: {err}", icon="❌")
        else:
            st.session_state.profile_transactions = res.get("transactions", [])
            fresh, _ = fetch_alerts()
            if fresh:
                st.session_state.alerts = fresh[:MAX_ALERTS]
            st.toast(f"Generated 20 synthetic transactions for {prof_to_run}", icon="⚡")
            st.rerun()

with sim_cols[2]:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    play_disabled = (sim_state == "running")
    if st.button("▶  Play", disabled=play_disabled, key="btn_play", use_container_width=True):
        _, err = set_simulator_state("play")
        if err:
            st.toast(f"Error: {err}", icon="❌")
        else:
            st.session_state.sim_state = "running"
            st.rerun()

with sim_cols[3]:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    pause_disabled = (sim_state != "running")
    if st.button("⏸  Pause", disabled=pause_disabled, key="btn_pause", use_container_width=True):
        _, err = set_simulator_state("pause")
        if err:
            st.toast(f"Error: {err}", icon="❌")
        else:
            st.session_state.sim_state = "paused"
            st.rerun()

with sim_cols[4]:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    stop_disabled = (sim_state == "stopped")
    if st.button("⏹  Stop", disabled=stop_disabled, key="btn_stop", use_container_width=True):
        _, err = set_simulator_state("stop")
        if err:
            st.toast(f"Error: {err}", icon="❌")
        else:
            st.session_state.sim_state = "stopped"
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("---")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── MAIN TWO-COLUMN LAYOUT ──────────────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
left_col, right_col = st.columns([1, 1], gap="medium")

alerts = st.session_state.alerts
profile_txs = st.session_state.get("profile_transactions", [])

# Combine alerts and profile transactions into a unified list
feed_items = []
for alt in alerts:
    feed_items.append({
        "id": alt.get("id"),
        "rule_triggered": alt.get("rule_triggered"),
        "severity": alt.get("severity", "high"),
        "timestamp": alt.get("timestamp"),
        "transaction": alt.get("transaction", {}),
        "telemetry_risk_score": alt.get("telemetry_risk_score"),
        "transaction_risk_score": alt.get("transaction_risk_score"),
        "final_risk_score": alt.get("final_risk_score"),
        "classification": alt.get("classification"),
    })

for ptx in profile_txs:
    if not any(f["transaction"].get("id") == ptx.get("id") for f in feed_items):
        feed_items.append({
            "id": ptx.get("id") or ptx.get("transaction_id"),
            "rule_triggered": ptx.get("title") or "Synthetic Profile Transaction",
            "severity": "high" if ptx.get("classification") == "HIGH_RISK" else ("medium" if ptx.get("classification") == "SUSPICIOUS" else "low"),
            "timestamp": ptx.get("timestamp"),
            "transaction": ptx,
            "telemetry_risk_score": ptx.get("telemetry_risk_score"),
            "transaction_risk_score": ptx.get("transaction_risk_score"),
            "final_risk_score": ptx.get("final_risk_score"),
            "classification": ptx.get("classification"),
        })

sev_order = {"high": 0, "medium": 1, "low": 2}
sorted_items = sorted(feed_items, key=lambda a: sev_order.get(a.get("severity", ""), 9))

high_count = sum(1 for a in sorted_items if a.get("classification") == "HIGH_RISK" or a.get("severity") == "high")
med_count  = sum(1 for a in sorted_items if a.get("classification") == "SUSPICIOUS" or a.get("severity") == "medium")


# ──────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — Live Security Console
# ──────────────────────────────────────────────────────────────────────────────
with left_col:
    hdr_l, refresh_btn = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            '<div class="panel-header" style="border-radius:8px 8px 0 0;">🔴&nbsp;Live Security Console'
            f'<span style="margin-left:auto;font-size:11px;color:#64748b;">{len(sorted_items)} item{"s" if len(sorted_items)!=1 else ""}</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with refresh_btn:
        if st.button("↻ Refresh", key="btn_refresh", use_container_width=True):
            fresh, _ = fetch_alerts()
            if fresh:
                st.session_state.alerts = fresh[:MAX_ALERTS]
            st.rerun()

    # Alert / Transaction list
    if not sorted_items:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#64748b;">
          <div style="font-size:40px;margin-bottom:12px;">&#128737;</div>
          <div style="font-size:14px;font-weight:600;color:#94a3b8;">No transactions yet</div>
          <div style="font-size:11px;margin-top:6px;">Select a profile from the dropdown or click Generate Batch</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        selected_id = (st.session_state.selected_alert or {}).get("id", "")
        for item in sorted_items[:25]:
            aid = item.get("id", "")
            txn = item.get("transaction", {})
            sev = item.get("severity", "low")
            is_selected = aid == selected_id

            t_risk = item.get("telemetry_risk_score") or txn.get("telemetry_risk_score", 0.5)
            tx_risk = item.get("transaction_risk_score") or txn.get("transaction_risk_score", 0.5)
            f_risk = item.get("final_risk_score") or txn.get("final_risk_score", 0.5)
            cls_name = item.get("classification") or txn.get("classification", "HIGH_RISK" if f_risk >= 0.6 else "SUSPICIOUS" if f_risk >= 0.3 else "SAFE")
            
            # High risk visual flagging
            is_high_risk = cls_name == "HIGH_RISK"
            border_left = "4px solid #ef4444" if is_high_risk else ("3px solid #4f7aff" if is_selected else "3px solid transparent")
            bg = "rgba(239, 68, 68, 0.08)" if is_high_risk else ("#131c35" if is_selected else "#111318")

            cls_color = "#ef4444" if is_high_risk else ("#f59e0b" if cls_name == "SUSPICIOUS" else "#22c55e")
            cls_bg = "rgba(239,68,68,0.15)" if is_high_risk else ("rgba(245,158,11,0.15)" if cls_name == "SUSPICIOUS" else "rgba(34,197,94,0.15)")

            user_display = str(txn.get("user_name") or "Synthetic User")
            title_display = str(txn.get("title") or item.get("rule_triggered") or "Transaction Scenario")
            acc_id_display = str(txn.get("account_id") or "—")
            loc_display = str(txn.get("location") or "—")
            time_display = fmt_time(item.get("timestamp") or "")
            amt_display = fmt_inr(txn.get("amount") or 0)
            description = str(txn.get("description") or f"Transaction performed by {user_display} on account {acc_id_display}.")

            st.markdown(f"""
            <div style="
              background:{bg};
              border-bottom:1px solid #1a1f2e;
              border-left:{border_left};
              padding:12px 14px;
              border-radius:4px;
              margin-bottom:6px;
            ">
              <div style="display:flex;align-items:flex-start;justify-content:space-between;">
                <div style="flex:1;min-width:0;">
                  <div style="font-size:14px;font-weight:700;color:#f1f5f9;">{title_display}</div>
                  <div style="font-size:12px;font-weight:600;color:#38bdf8;margin-top:2px;">
                    &#128104; {user_display} &bull; <span style="color:#94a3b8;font-family:'JetBrains Mono',monospace;">{acc_id_display}</span> &bull; {loc_display} &bull; {time_display}
                  </div>
                  <div style="font-size:11px;color:#cbd5e1;margin-top:4px;line-height:1.4;background:rgba(255,255,255,0.03);padding:6px;border-radius:4px;">
                    {description}
                  </div>
                  <div style="display:flex;gap:6px;margin-top:6px;font-size:11px;flex-wrap:wrap;color:#94a3b8;">
                    <span style="padding:1px 6px;background:#1e293b;border-radius:3px;border:1px solid rgba(255,255,255,0.1);">
                      &#128225; Telemetry Risk: <strong style="color:#e2e8f0">{float(t_risk):.2f}</strong>
                    </span>
                    <span style="padding:1px 6px;background:#1e293b;border-radius:3px;border:1px solid rgba(255,255,255,0.1);">
                      &#128179; Tx Risk: <strong style="color:#e2e8f0">{float(tx_risk):.2f}</strong>
                    </span>
                    <span style="padding:1px 6px;background:#1e293b;border-radius:3px;border:1px solid rgba(255,255,255,0.1);">
                      &#127919; Final Risk: <strong style="color:#e2e8f0">{float(f_risk):.2f}</strong>
                    </span>
                  </div>
                </div>
                <div style="text-align:right;flex-shrink:0;margin-left:12px;">
                  <div class="alert-amount">{amt_display}</div>
                  <div style="margin-top:6px;display:flex;gap:4px;justify-content:flex-end;align-items:center;">
                    <span style="padding:2px 8px;border-radius:4px;font-size:10px;font-weight:800;color:{cls_color};background:{cls_bg};border:1px solid {cls_color};">{cls_name}</span>
                    {severity_badge(sev)}
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(
                f"Investigate →" if not is_selected else "✓ Selected",
                key=f"sel_{aid}",
                use_container_width=True,
            ):
                st.session_state.selected_alert = item
                st.session_state.chat_messages = []
                st.session_state.pending_rule = None
                st.rerun()

    # Stats bar
    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total", len(alerts), help="Maximum 20 alerts shown")
    with s2:
        st.metric("🔴 High", high_count)
    with s3:
        st.metric("🟡 Medium", med_count)
    with s4:
        st.metric("✅ Deployed", st.session_state.rule_deployed_count)


# ──────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — AI Investigator Chat Panel
# ──────────────────────────────────────────────────────────────────────────────
with right_col:
    selected = st.session_state.selected_alert

    panel_subtitle = ""
    if selected:
        panel_subtitle = f'<span style="font-size:10px;color:#64748b;font-family:\'JetBrains Mono\',monospace;margin-left:auto;">{selected.get("id","")}</span>'

    st.markdown(
        f'<div class="panel-header" style="border-radius:8px 8px 0 0;">🤖&nbsp;AI Investigator{panel_subtitle}</div>',
        unsafe_allow_html=True,
    )

    if not selected:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;color:#64748b;">
          <div style="font-size:40px;margin-bottom:14px;">🔍</div>
          <div style="font-size:15px;font-weight:600;color:#94a3b8;margin-bottom:6px;">No alert selected</div>
          <div style="font-size:12px;">Click <strong style="color:#4f7aff">Investigate →</strong> on any alert in the console</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        txn = selected.get("transaction", {})
        sev = selected.get("severity", "low")

        # Alert context bar
        ts_str = ""
        try:
            ts_str = datetime.fromisoformat(
                str(selected.get("timestamp", "")).replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts_str = str(selected.get("timestamp", ""))

        st.markdown(f"""
        <div class="msg-context-bar">
          <div class="msg-context-id">{selected.get("id","—")} · {ts_str}</div>
          <div class="msg-context-rule">{selected.get("rule_triggered","—")}</div>
          <div style="margin-top:6px;display:flex;gap:8px;align-items:center;">
            {severity_badge(sev)}
            <span style="background:#1e2433;border-radius:4px;padding:2px 8px;font-size:11px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">{fmt_inr(txn.get("amount",0))}</span>
            <span style="background:#1e2433;border-radius:4px;padding:2px 8px;font-size:11px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">{txn.get("location","—")}</span>
            <span style="background:#1e2433;border-radius:4px;padding:2px 8px;font-size:11px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">{txn.get("account_id","—")}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Message feed ──────────────────────────────────────────────────────
        feed_container = st.container(height=380)
        with feed_container:
            messages = st.session_state.chat_messages
            if not messages:
                st.markdown(
                    '<div class="msg-system">Ask the AI to explain this alert or generate a detection rule.</div>',
                    unsafe_allow_html=True,
                )

            for msg in messages:
                mtype = msg.get("type", "system")

                if mtype == "user":
                    st.markdown(
                        f'<div class="msg-user">{msg["text"]}</div><div style="clear:both"></div>',
                        unsafe_allow_html=True,
                    )

                elif mtype == "explain":
                    st.markdown(f"""
                    <div class="msg-explain">
                      <div class="msg-explain-label">AI Forensic Analysis</div>
                      <div class="msg-explain-text">{msg["text"]}</div>
                    </div>
                    """, unsafe_allow_html=True)

                elif mtype == "rule":
                    retry_html = ""
                    if msg.get("attempts", 1) > 1:
                        retry_html = f'<span class="retry-badge">⟳ {msg["attempts"]} attempts</span>'

                    st.markdown(f"""
                    <div class="msg-rule">
                      <div class="msg-rule-label">Generated Detection Rule {retry_html}</div>
                      {code_diff_html(msg.get("code", ""))}
                    </div>
                    """, unsafe_allow_html=True)

                    if not msg.get("valid") and msg.get("error"):
                        st.error(f"Validation failed: {msg['error']}")

                    if msg.get("valid"):
                        rule_key = msg.get("ruleId", "unknown")
                        btn_c1, btn_c2 = st.columns([1, 1])
                        with btn_c1:
                            if st.button(
                                "✓ Deploy rule",
                                key=f"deploy_{rule_key}",
                                type="primary",
                                use_container_width=True,
                            ):
                                rdata, err = deploy_rule(
                                    # pyrefly: ignore [unexpected-keyword]
                                    name=f"Rule for Alert {selected.get('id','')}",
                                    code=msg.get("code", ""),
                                    description=f"Fraud detection rule via: {msg.get('command','analyst')}",
                                    command=msg.get("command", "analyst command"),
                                )
                                if err:
                                    st.session_state.chat_messages.append(
                                        {"type": "error", "text": f"Deploy failed: {err}"}
                                    )
                                else:
                                    st.session_state.chat_messages.append(
                                        {"type": "system", "text": f"✅ Rule {rule_key} deployed successfully."}
                                    )
                                    st.session_state.pending_rule = None
                                    st.session_state.rule_deployed_count += 1
                                    st.rerun()

                        with btn_c2:
                            if st.button(
                                "✕ Reject",
                                key=f"reject_{rule_key}",
                                use_container_width=True,
                            ):
                                st.session_state.chat_messages.append(
                                    {"type": "system", "text": "Rule rejected — not deployed."}
                                )
                                st.session_state.pending_rule = None
                                st.rerun()

                elif mtype == "system":
                    st.markdown(
                        f'<div class="msg-system">{msg["text"]}</div>',
                        unsafe_allow_html=True,
                    )

                elif mtype == "error":
                    st.markdown(
                        f'<div class="msg-error">{msg["text"]}</div>',
                        unsafe_allow_html=True,
                    )

        # ── Quick action buttons ───────────────────────────────────────────────
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        qa1, qa2, qa3, qa4 = st.columns(4)
        quick_cmds = [
            (qa1, "Explain this", "Explain this alert"),
            (qa2, "Generate rule", "Generate a rule to detect this pattern"),
            (qa3, "Why flagged?", "Why was this flagged?"),
            (qa4, "Flag similar", "Flag similar transactions in future"),
        ]

        def _handle_send(cmd_text: str):
            """Process a chat command and update session state."""
            alert_id = selected.get("id", "")
            st.session_state.chat_messages.append({"type": "user", "text": cmd_text})

            is_generate = any(kw in cmd_text.lower() for kw in
                              ["generate", "create", "write", "add", "build",
                               "make", "rule", "detect", "flag"])

            if is_generate:
                result, err = generate_rule(cmd_text, alert_id)
                if err:
                    st.session_state.chat_messages.append({"type": "error", "text": err})
                else:
                    rule_id = f"rule_{int(time.time()*1000)}"
                    msg = {
                        "type": "rule",
                        "code": result.get("code", ""),
                        "valid": result.get("valid", False),
                        "error": result.get("error"),
                        "attempts": result.get("attempts", 1),
                        "command": cmd_text,
                        "ruleId": rule_id,
                    }
                    st.session_state.chat_messages.append(msg)
                    if result.get("valid"):
                        st.session_state.pending_rule = msg
            else:
                result, err = explain_alert(alert_id, cmd_text)
                if err:
                    st.session_state.chat_messages.append({"type": "error", "text": err})
                else:
                    st.session_state.chat_messages.append(
                        {"type": "explain", "text": result.get("explanation", "")}
                    )

        for col, label, cmd in quick_cmds:
            with col:
                if st.button(label, key=f"qb_{label}", use_container_width=True):
                    _handle_send(cmd)
                    st.rerun()

        # ── Chat input ────────────────────────────────────────────────────────
        prompt = st.chat_input(
            "Explain this alert… or Generate a rule for…",
            key="chat_input",
        )
        if prompt:
            _handle_send(prompt)
            st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── RULES & AUDIT LOG EXPANDER ──────────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
with st.expander("📜  Rules Engine & Audit Trail", expanded=False):
    audit_tab, rules_tab = st.tabs(["🔐 Audit Log", "⚙️ Active Rules"])

    with audit_tab:
        audit_data, audit_err = fetch_audit_log()
        if audit_err:
            st.error(f"Failed to load audit log: {audit_err}")
        else:
            integrity_valid = audit_data.get("integrity_valid", True)
            tampered_id = audit_data.get("tampered_row_id")
            entries = audit_data.get("entries", [])

            if integrity_valid:
                st.markdown("""
                <div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);
                  border-radius:8px;padding:10px 14px;font-size:12px;color:#22c55e;margin-bottom:12px;">
                  ✓ <strong>SHA-256 Hash Chain Integrity Verified</strong> — Audit log entries are untampered.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
                  border-radius:8px;padding:10px 14px;font-size:12px;color:#ef4444;margin-bottom:12px;">
                  ⚠️ <strong>Hash Chain Integrity Compromised!</strong> — Tampering detected at row #{tampered_id}
                </div>
                """, unsafe_allow_html=True)

            if not entries:
                st.info("No audit entries yet.")
            else:
                import pandas as pd
                df = pd.DataFrame([{
                    "#":         e.get("id"),
                    "Timestamp": e.get("timestamp", "")[:19].replace("T", " "),
                    "Rule ID":   e.get("rule_id", ""),
                    "Action":    e.get("status", ""),
                    "Command":   e.get("command", ""),
                    "SHA-256":   e.get("hash", "")[:16] + "…",
                } for e in entries])
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "#":         st.column_config.NumberColumn(width="small"),
                        "Timestamp": st.column_config.TextColumn(width="medium"),
                        "Rule ID":   st.column_config.TextColumn(width="medium"),
                        "Action":    st.column_config.TextColumn(width="small"),
                        "Command":   st.column_config.TextColumn(width="large"),
                        "SHA-256":   st.column_config.TextColumn(width="medium"),
                    },
                )

    with rules_tab:
        rules_data, rules_err = fetch_rules()
        if rules_err:
            st.error(f"Failed to load rules: {rules_err}")
        elif not rules_data:
            st.info("No active rules currently deployed.")
        else:
            st.markdown(
                f'<div style="font-size:11px;color:#64748b;margin-bottom:12px;">'
                f'{len(rules_data)}/20 rules active</div>',
                unsafe_allow_html=True,
            )
            for rule in rules_data:
                with st.container():
                    r1, r2 = st.columns([4, 1])
                    with r1:
                        st.markdown(f"""
                        <div style="font-size:13px;font-weight:600;color:#e2e8f0;">{rule.get("name","—")}</div>
                        <div style="font-size:10px;color:#64748b;font-family:'JetBrains Mono',monospace;margin-top:2px;">{rule.get("id","")}</div>
                        <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{rule.get("description","")}</div>
                        """, unsafe_allow_html=True)
                    with r2:
                        st.markdown(
                            '<span style="background:rgba(34,197,94,0.15);color:#22c55e;'
                            'border:1px solid rgba(34,197,94,0.3);border-radius:4px;'
                            'padding:2px 8px;font-size:10px;font-weight:700;">ACTIVE</span>',
                            unsafe_allow_html=True,
                        )
                    st.code(rule.get("code", ""), language="python")
                    dep_ts = ""
                    try:
                        dep_ts = datetime.fromisoformat(
                            str(rule.get("created_at", "")).replace("Z", "+00:00")
                        ).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        dep_ts = rule.get("created_at", "")
                    st.markdown(
                        f'<div style="font-size:10px;color:#64748b;margin-bottom:4px;">'
                        f'Deployed via: "{rule.get("created_by_command","")}" · {dep_ts}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div style="border-bottom:1px solid #1e2433;margin:8px 0;"></div>', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── CUSTOM PROFILE BUILDER EXPANDER ─────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.expander("➕  Custom Simulator Profile", expanded=False):
    st.markdown(
        '<div style="font-size:12px;color:#64748b;margin-bottom:16px;">'
        'Define a transaction pattern for the simulator to generate.</div>',
        unsafe_allow_html=True,
    )

    with st.form("profile_builder_form", clear_on_submit=True):
        p_name = st.text_input(
            "Profile name *",
            placeholder="e.g. High-value foreign transactions",
            key="pf_name",
        )

        pc1, pc2 = st.columns(2)
        with pc1:
            p_min = st.number_input("Min amount (₹)", min_value=0, value=0, key="pf_min")
        with pc2:
            p_max = st.number_input("Max amount (₹)", min_value=0, value=999999, key="pf_max")

        p_location = st.selectbox(
            "Transaction location",
            options=["any", "new_device", "foreign_ip", "atm", "online"],
            key="pf_location",
        )

        p_rate = st.slider(
            "Transactions per minute",
            min_value=1, max_value=30, value=5, key="pf_rate",
        )

        pf_submit = st.form_submit_button("✨ Create Profile", type="primary", use_container_width=True)

    if pf_submit:
        if not p_name.strip():
            st.error("Profile name is required.")
        else:
            rules_payload = {
                "amount_range": [float(p_min), float(p_max)],
                "location": None if p_location == "any" else p_location,
                "txn_per_minute": int(p_rate),
            }
            result, err = create_profile(p_name.strip(), rules_payload)
            if err:
                st.error(f"Failed to create profile: {err}")
            else:
                st.session_state.active_profile = p_name.strip()
                st.success(f"✓ Profile created: `{result.get('profile_id', 'unknown')}`")
                st.info("The simulator will use this profile on next start.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ─── AUTO-RERUN for live feed polling ────────────────────────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Only auto-rerun when the simulator is running (no need to poll when idle)
if st.session_state.sim_state == "running":
    time.sleep(3)
    st.rerun()
