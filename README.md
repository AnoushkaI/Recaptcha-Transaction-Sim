# Recaptcha Transaction Fraud Simulation & SOC Prevention Platform

Enterprise Security Operations Center (SOC) platform demonstrating the full end-to-end fraud lifecycle:
**Simulation (Profile-Driven) → Detection (Scoring) → Investigation (Forensic Agent) → Rule Deployment → Prevention (Block/Challenge) → Immutable Audit Logging.**

---

## 📂 Formatted Project Directory Structure

```
Recaptcha-Transaction-Sim/
├── 📁 backend/                        # Backend Services & Core Engine
│   ├── 📁 ai/                         # AI & LLM Agent Orchestration
│   │   ├── 📁 agents/
│   │   │   ├── investigator.py        # Forensic explanation generator
│   │   │   └── rule_writer.py         # Python AST rule synthesis engine
│   │   └── llm.py                     # LLM API client
│   ├── 📁 api/
│   │   └── routes.py                  # FastAPI REST API endpoints & route handlers
│   ├── 📁 core/
│   │   ├── audit_log.py               # Immutable cryptographic audit logger
│   │   └── db.py                      # SQLite database schema & connection pool
│   ├── 📁 profiles/
│   │   └── profiles.json              # Sole source of truth for 10 fraud profiles
│   ├── 📁 scoring/
│   │   └── engine.py                  # Risk scoring engine & math formulas
│   ├── 📁 soc/
│   │   ├── rule_store.py              # Condition-based SOC rule engine & CRUD
│   │   └── soc_audit.py               # SOC lifecycle event logger
│   ├── batch_generator.py             # Profile transaction batch generator
│   └── main.py                        # FastAPI application entry point
│
├── 📁 frontend/                       # Web UI assets & static components
├── 📁 scripts/                        # System diagnostic & setup scripts
├── 📁 tests/                          # Automated unit & integration tests
├── 📁 docs/                           # Architecture specs & API documentation
│
├── 📄 Streamlit_app.py                # SOC Security Operations Console Dashboard
├── 📄 fraud_rules.db                  # SQLite database for active rules & audit logs
├── 📄 requirements.txt                # Python project dependencies
└── 📄 README.md                       # Project architecture & user guide
```

---

## 🚀 Execution Commands

### 1. Start Backend Server
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 2. Start Security Console UI
```bash
streamlit run Streamlit_app.py
```