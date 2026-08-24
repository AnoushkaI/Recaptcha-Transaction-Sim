# 🛡️ reCAPTCHA Transaction Simulation & SOC Prevention Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31%2B-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Cryptographic%20Ledger-003B57.svg)](https://www.sqlite.org/)
[![AI-Powered](https://img.shields.io/badge/AI%20Agent-Forensics%20%26%20Rule%20Synthesis-7B2CBF.svg)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade **Security Operations Center (SOC) Fraud Detection & Prevention Platform** demonstrating an end-to-end autonomous fraud lifecycle:
**Synthetic Fraud Profile Simulation → Risk Engine Scoring → AI Forensic Agent Investigation → Multi-Layer AST Rule Synthesis → Compiler & Rule Guard Validation → Hot-Reload Prevention → SHA-256 Hash-Chained Audit Logging.**

---

## 🌟 Executive Summary & Key Highlights

Modern payment systems face complex, multi-vector bot and human fraud schemes. The **reCAPTCHA Transaction Simulation & SOC Platform** is designed to simulate, detect, analyze, and mitigate advanced transaction fraud in real time. It features a complete **closed-loop security architecture** with zero downtime rule deployment and guaranteed offline operation capabilities.

### 🛡️ End-to-End Security Lifecycle
```
 ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
 │ 1. Profile Simulation  │ ───► │ 2. Multi-Factor Scoring│ ───► │ 3. Forensic Analysis   │
 │    10 Fraud Vectors    │      │    Risk Engine         │      │    AI Risk Agent       │
 └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
                                                                              │
 ┌────────────────────────┐      ┌────────────────────────┐                   ▼
 │ 6. Immutable Ledger    │ ◄─── │ 5. Hot-Reload Rules    │ ◄─── ┌────────────────────────┐
 │    SHA-256 Hash Chain  │      │    In-Memory Engine    │      │ 4. AST Rule Synthesis  │
 └────────────────────────┘      └────────────────────────┘      │    Compiler & Guard    │
                                                                 └────────────────────────┘
```

---

## 🔥 Key Platform Capabilities

### 🎭 1. Profile-Driven Synthetic Fraud Generator
Simulates realistic transactions across **10 distinct fraud vectors**, backed by statistical distributions and behavioral heuristics:
- **Carding Botnet**: Rapid automated micro-transactions with high velocity.
- **Velocity Attack**: Spike in transaction frequency over short time windows.
- **Account Takeover (ATO)**: Abrupt device, IP, and location changes on established accounts.
- **Geo-Velocity Fraud**: Physically impossible travel distance between consecutive transactions.
- **Micro-Charge Testing**: Low-value transactions used to validate stolen credit card numbers.
- **High-Value Exfiltration**: Sudden massive transaction amounts on young accounts.
- **Behavioral Drift**: Subtle deviation from normal user purchasing baseline over time.
- **Friendly Fraud**: Chargeback abuse patterns with suspicious merchant category velocity.
- **Night-Owl Exfiltration**: High-risk off-hours international transactions.
- **Mule Account Funnel**: High-volume rapid pass-through money transfers.

### ⚡ 2. Real-Time Dynamic Rules Engine & Hot-Reload
- High-throughput in-memory evaluation engine capable of processing thousands of events per second.
- Supports both **Structured Condition Rules** (JSON threshold operators) and **Compiled Dynamic Python AST Rules**.
- Instant **Hot-Reloading**: New rules become active immediately across all worker nodes without restarting server processes or dropping active connections.

### 🛡️ 3. Multi-Layer AST Security & Semantic Rule Guard
- **AST Safety Validator**: Performs strict static analysis on AI-generated Python code, rejecting forbidden syntax trees (`import`, `exec`, `eval`, `open`, dunder attributes, infinite loops, and OS system calls).
- **Safe Dynamic Compiler**: Compiles validated AST trees into isolated executable bytecode.
- **Rule Guard**: Enforces semantic deduplication via code similarity scoring and prevents rule bloat by enforcing a 20-rule ceiling limit.

### 🤖 4. AI Forensic Agent & Autonomous Rule Synthesis
- **Forensic Investigator Agent**: Analyzes flagged transactions, breaking down anomaly vectors, risk factors, confidence scores, and recommended SOC responses.
- **Rule Synthesis Agent**: Automatically generates optimized Python AST rules directly from incident context or natural language SOC operator prompts.
- **Multi-Provider LLM Routing**: Supports cloud providers (Google Gemini 2.5, OpenAI) alongside local models.

### 🔌 5. "Kill the Internet" Offline Resilience
- Built with complete offline autonomy. When cloud APIs are unavailable or during disconnected operation ("Kill the Internet" scenario), the system seamlessly falls back to a local **Ollama** model instance (`qwen2.5-coder:3b`).
- Provides 100% feature parity locally—generating valid AST rules, running AST validation, and deploying into the live engine with zero external network connectivity.

### 🔗 6. Cryptographic Hash-Chained Audit Ledger
- Immutable event audit log backed by SQLite (`fraud_rules.db`).
- Every logged event includes a **SHA-256 block hash** that links the `previous_hash` to `current_hash`, forming a tamper-evident cryptographic chain.
- Built-in tamper detection engine instantly detects line-item modifications, deleted records, or out-of-order log entries.

### 💻 7. Interactive Security Operations Console (Streamlit UI)
Features a modern 5-tab operational dashboard for security analysts and SOC teams:
- 🎯 **Transaction Simulator & Live Stream**: Profile selection, batch generation, real-time transaction table with risk score color-coding.
- 🛡️ **Active SOC Rules Management**: Rule status toggles, priority ordering, AST rule editor, live condition builder.
- 🤖 **AI Forensic Studio & Rule Generator**: Incident explanations, AI rule synthesis preview, validator test execution, one-click deployment.
- 🔗 **Cryptographic Audit Explorer**: Block-by-block hash chain visualization, automated tamper verification, SOC lifecycle timeline.
- 📊 **Analytics & Benchmarks**: Real-time throughput metrics, risk distribution charts, profile fraud rates, local model performance benchmark runner.

---

## 🏗️ System Architecture

```
                                    +-----------------------------------+
                                    |     Streamlit Security Console    |
                                    |       (Streamlit_app.py)          |
                                    +-----------------------------------+
                                                      |
                                             REST API / WebSocket
                                                      v
                                         +---------------------------+
                                         |  backend/main.py (FastAPI)|
                                         +---------------------------+
                                                       |
         +--------------------------------------------+--------------------------------------------+
         |                                            |                                            |
         v                                            v                                            v
+------------------+                        +-------------------+                        +--------------------+
| core/simulator.py|                        | core/validator.py |                        | core/rule_guard.py |
| Synthetic Stream |                        | AST Safety Check  |                        | Cap (20) & Similarity|
+------------------+                        +-------------------+                        +--------------------+
         |                                            |                                            |
         v                                            v                                            |
+---------------------+                      +-------------------+                                 |
|core/rules_engine.py | <------------------- | core/compiler.py  | <-------------------------------+
| Live In-Memory Rules|     Hot-Reload       | Safe Compilation  |
+---------------------+                      +-------------------+
         |                                            |
         v Stream Alerts                              v Log Action
+---------------------+                      +-------------------+
|  WebSocket Stream   |                      | core/audit_log.py |
|     (/ws/alerts)    |                      | SHA-256 Hash Chain|
+---------------------+                      +-------------------+
```

---

## 📂 Project Directory Structure

```
Recaptcha-Transaction-Sim/
├── 📁 backend/                        # Core Engine & Backend Microservices
│   ├── 📁 ai/                         # AI & LLM Agent Orchestration
│   │   ├── 📁 agents/
│   │   │   ├── investigator.py        # Forensic explanation & risk analysis agent
│   │   │   └── rule_writer.py         # Python AST rule synthesis engine
│   │   ├── 📁 prompts/                # System prompts for risk & rule synthesis
│   │   ├── 📁 providers/              # LLM provider clients (Gemini, OpenAI, Ollama)
│   │   ├── llm.py                     # Provider router & fallback manager
│   │   └── orchestrator.py            # AI agent workflow coordinator
│   ├── 📁 api/
│   │   └── routes.py                  # FastAPI REST API endpoints & WebSocket handlers
│   ├── 📁 core/
│   │   ├── audit_log.py               # Cryptographic SHA-256 hash-chained logger
│   │   ├── compiler.py                # Safe dynamic bytecode compiler
│   │   ├── db.py                      # SQLite connection pool & schema manager
│   │   ├── rule_guard.py              # Rule cap & similarity deduplication engine
│   │   ├── rules_engine.py            # Live in-memory rule engine & evaluator
│   │   ├── schemas.py                 # Core Pydantic data schemas & contracts
│   │   ├── simulator.py               # Synthetic transaction profile generator
│   │   └── validator.py               # AST static safety validator
│   ├── 📁 profiles/
│   │   └── profiles.json              # Source of truth for 10 fraud profile specs
│   ├── 📁 scoring/
│   │   └── engine.py                  # Multi-factor risk scoring engine & math
│   ├── 📁 soc/
│   │   ├── rule_store.py              # Structured condition SOC rule engine
│   │   └── soc_audit.py               # SOC lifecycle event tracker
│   ├── batch_generator.py             # Bulk transaction batch generator
│   ├── config.py                      # Application environment configuration
│   └── main.py                        # FastAPI application entry point
│
├── 📁 docs/                           # Architectural guides, presentations & benchmarks
│   ├── architecture.md                # Component architecture specification
│   ├── project_architecture_presentation.md # System presentation & design slides
│   └── benchmark_results.json         # Local model throughput & latency benchmarks
├── 📁 scripts/                        # Utility & diagnostic helper scripts
├── 📁 tests/                          # Automated pytest test suite (167 tests)
│
├── 📄 Streamlit_app.py                # Security Operations Console (Dashboard UI)
├── 📄 benchmark_local.py              # Standalone local LLM benchmark harness
├── 📄 fraud_rules.db                  # SQLite database (active rules & audit chain)
├── 📄 requirements.txt                # Python project dependencies
└── 📄 README.md                       # Project documentation & user guide
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Ollama** (Optional, for offline local AI fallback): Download from [ollama.com](https://ollama.com/)

### 2. Installation & Virtual Environment Setup
```bash
# Clone the repository
git clone https://github.com/AnoushkaI/Recaptcha-Transaction-Sim.git
cd Recaptcha-Transaction-Sim

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Backend REST & WebSocket Server
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live WebSocket Stream**: `ws://localhost:8000/ws/alerts`

### 4. Launch Security Operations Console (Dashboard)
In a separate terminal window:
```bash
streamlit run Streamlit_app.py
```
Access the dashboard in your web browser at [http://localhost:8501](http://localhost:8501).

---

## 🔌 Local LLM Setup & "Kill the Internet" Demo

To test or demonstrate full offline capabilities without external API dependencies:

### 1. Install & Launch Ollama
```bash
# Start Ollama service
ollama serve

# Pull Qwen2.5-Coder 3B model (in a separate terminal)
ollama pull qwen2.5-coder:3b
```

### 2. Configure Local Provider
Create or edit `.env` in the project root:
```env
LLM_PROVIDER=local
LOCAL_LLM_MODEL=qwen2.5-coder:3b
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Run Benchmark Harness
Benchmark local model latency, throughput (tokens/sec), and AST security validator pass rate:
```bash
python benchmark_local.py
```

### 4. Offline Demonstration Steps
1. Start local Ollama service: `ollama serve`.
2. Disconnect Wi-Fi/Ethernet or set `LLM_PROVIDER=local`.
3. Open the Streamlit Console (`http://localhost:8501`) and select a flagged transaction under **AI Forensic Studio**.
4. Click **Generate AI Rule**.
5. Observe end-to-end rule synthesis, AST validation, rule guard check, dynamic compilation, and hot-reload deployment—executed entirely offline.

---

## 🧪 Testing & Quality Assurance

The project contains a comprehensive automated test suite of **167 pytest cases** covering all components:

```bash
# Run all tests
python -m pytest tests/

# Run individual test stages
python -m pytest tests/test_schemas.py        # Data Contracts & Schemas
python -m pytest tests/test_simulator.py      # Transaction Simulator & Profiles
python -m pytest tests/test_rules_engine.py   # In-Memory Rules Engine & Hot-Reload
python -m pytest tests/test_validator.py      # AST Security Validator
python -m pytest tests/test_rule_guard.py     # Semantic Rule Guard & Cap Limits
python -m pytest tests/test_compiler.py       # Safe Bytecode Compiler
python -m pytest tests/test_audit_log.py      # Cryptographic SHA-256 Audit Ledger
python -m pytest tests/test_api.py            # FastAPI REST & WebSocket Endpoints
python -m pytest tests/test_integration.py    # End-to-End System Integration
```

---

## 📡 API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/simulate` | Generate synthetic transaction stream from fraud profile |
| `GET` | `/api/rules` | Retrieve list of active security rules |
| `POST` | `/api/rules` | Validate, compile, and deploy new security rule |
| `DELETE` | `/api/rules/{rule_id}` | Deactivate or remove existing security rule |
| `POST` | `/api/investigate` | Trigger AI Forensic Agent investigation on incident |
| `POST` | `/api/generate-rule` | Synthesize new AST Python rule from incident context |
| `GET` | `/api/audit/logs` | Fetch immutable cryptographic audit log ledger |
| `GET` | `/api/audit/verify` | Verify cryptographic SHA-256 hash chain integrity |
| `WS` | `/ws/alerts` | Real-time WebSocket alert stream for flagged transactions |

---

## 📄 License & Credits

Developed as an **Enterprise SOC Fraud Prevention & Simulation Platform**.
Licensed under the [MIT License](LICENSE).