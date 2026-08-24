# 🛡️ AI-Assisted SOC Fraud Detection & Simulation Platform
## Comprehensive Technical Architecture, Implementation & Leadership Presentation Guide

---

### Executive Summary

The **AI-Assisted SOC Fraud Detection Platform** is an enterprise-grade real-time fraud mitigation and security intelligence system. It combines deterministic mathematical scoring, static Abstract Syntax Tree (AST) code validation, AI multi-agent orchestrations (Gemini 2.5 Flash / Ollama), and instant condition-based SOC rule enforcement backed by a **PostgreSQL 17** transactional data store.

---

## 1. High-Level Architecture & End-to-End Workflow

```mermaid
flowchart TD
    subgraph Data Generation & Simulation
        SIM["Transaction Simulator<br/>(backend/core/simulator.py)"]
        GEN["Batch Scenario Generator<br/>(backend/batch_generator.py)"]
    end

    subgraph Mathematical Scoring Engine
        ENG["Scoring Pipeline (Steps 1-5)<br/>(backend/scoring/engine.py)"]
        TEL["Telemetry Human Score (S1)"]
        RISK["Weighted Combined Risk Score (S5)"]
    end

    subgraph AI Multi-Agent & Rule Pipeline
        RW["AI Rule Writer Agent<br/>(backend/ai/agents/rule_writer.py)"]
        AST["AST Safety Validator<br/>(backend/core/validator.py)"]
        GUARD["Rule Guard & Embeddings<br/>(backend/core/rule_guard.py)"]
        INV["AI Forensic Investigator<br/>(backend/ai/agents/investigator.py)"]
    end

    subgraph Persistence Layer
        PG[(PostgreSQL 17 Database<br/>fraud_engine_db)]
        AUD["audit_log / soc_rules / soc_audit_log"]
    end

    subgraph Operations & SOC Dashboards
        ST["Streamlit Console<br/>(Streamlit_app.py)"]
        REACT["React Enterprise Console<br/>(frontend/src/)"]
    end

    SIM --> ENG
    GEN --> ENG
    ENG --> TEL
    TEL --> RISK
    RISK --> RW
    RW --> AST
    AST -- "Passed" --> GUARD
    GUARD --> PG
    PG --> ST
    PG --> REACT
    RISK --> INV
    INV --> ST
    INV --> REACT
```

---

## 2. Comprehensive Directory Structure & File Mapping

```
Recaptcha-Transaction-Sim-Integration-branch/
├── backend/
│   ├── ai/
│   │   ├── agents/
│   │   │   ├── investigator.py     # AI Forensic Investigation Agent (Generates SOC Incident Reports)
│   │   │   └── rule_writer.py      # Self-correcting AI Rule Writer Agent with AST Retry Loop
│   │   ├── prompts/
│   │   │   ├── investigator_prompts.py # Prompts for Threat & Risk Analysis
│   │   │   └── rule_writer_prompts.py  # System Prompts & Allowed Transaction Field Specs
│   │   ├── providers/
│   │   │   ├── base.py             # Abstract Base Provider Interface
│   │   │   ├── factory.py          # LLM Provider Factory (Gemini vs Local Ollama)
│   │   │   ├── gemini_provider.py  # Google Gemini 2.5 Flash Integration
│   │   │   └── local_provider.py   # Ollama / qwen2.5-coder Local Provider
│   │   ├── llm.py                  # LLM Client Wrappers
│   │   └── orchestrator.py         # AI Orchestrator combining Analysis & Rule Generation
│   ├── api/
│   │   └── routes.py               # FastAPI REST Endpoints & Live Simulator Router
│   ├── core/
│   │   ├── audit_log.py            # PostgreSQL Active Rules Audit Logger
│   │   ├── compiler.py             # Dynamic Python Bytecode Rule Compiler
│   │   ├── db.py                   # PostgreSQL Connection Pool & Schema Manager
│   │   ├── rules_engine.py         # Rules Engine Evaluator Execution Loop
│   │   ├── rule_guard.py           # Deduplication & SentenceTransformer Vector Embeddings
│   │   ├── schemas.py              # Pydantic Core Data Schemas (Transaction, Rule, Profile)
│   │   ├── simulator.py            # Real-time Stream Simulator (Indian Regional City Pairs)
│   │   └── validator.py            # Layered Static AST Safety & Dry-Run Validator
│   ├── profiles/
│   │   ├── builder.py              # Custom Fraud Profile Generator
│   │   └── profiles.json           # Behavioral & Transactional Profile Library
│   ├── scoring/
│   │   └── engine.py               # Deterministic 5-Step Mathematical Risk Pipeline
│   ├── soc/
│   │   ├── rule_store.py           # Condition-Based SOC Prevention Store & Hit Counter
│   │   └── soc_audit.py            # PostgreSQL SOC Event Tracker
│   ├── batch_generator.py          # Scenario Batch Generator (ACCOUNT_TAKEOVER, GIFT_CARD)
│   ├── config.py                   # Unified Settings (Pydantic BaseSettings, CORS)
│   └── main.py                     # FastAPI Application Entrypoint & Lifespan Handler
├── docs/
│   ├── architecture.md             # High-level System Architecture Document
│   └── project_architecture_presentation.md # Detailed Presentation & Leadership Guide
├── frontend/                       # Enterprise React (Vite) Security Console
├── scripts/
│   ├── check_pg_tables.py          # PostgreSQL Verification & Audit Utility
│   ├── create_pg_db.py             # Database Initialization Utility
│   └── generate_profiles.py        # Behavioral Profile Generator
├── tests/                          # 167 Comprehensive Pytest Unit & Integration Tests
├── Streamlit_app.py                # Interactive Streamlit SOC Prevention Platform
├── .env                            # Environment Configuration (PostgreSQL, Gemini API Key)
└── requirements.txt                # Python Production Dependencies
```

---

## 3. Deep Dive into System Components & Implementation

### A. Real-Time Transaction Stream Simulator (`backend/core/simulator.py`)
- **Purpose**: Generates high-throughput synthetic payment streams with configurable behavioral and transactional telemetry.
- **Indian Regional City Pairs**: Uses Indian inter-city origin-destination location codes for realistic domestic routing:
  - **Standard Cities**: `MUM-DEL`, `DEL-BLR`, `BLR-HYD`, `HYD-MAA`, `MAA-CCU`, `CCU-PNQ`, `MUM-PNQ`, `BLR-AMD`, `DEL-JAI`.
  - **High-Risk Fraud Corridors**: `DEL-LKO` (Lucknow), `MUM-JMT` (Jamtara), `DEL-NUH` (Nuh), `BLR-PAT` (Patna), `HYD-RNC` (Ranchi).

### B. Mathematical Risk Scoring Engine (`backend/scoring/engine.py`)
Implemented according to the 5-step deterministic scoring formula:

1. **Step 1: Telemetry Human Score ($S_1$)**:
   Calculates human interaction quality from biometric signals (mouse curve smoothness, typing CPM speed, error rates, scroll behavior).
   $$S_1 = 0.35 \times \text{mouse\_quality} + 0.25 \times \text{typing\_speed\_norm} + 0.20 \times (1 - \text{typing\_error\_rate}) + 0.20 \times \text{scroll\_behavior}$$
2. **Step 2: Telemetry Risk Score ($S_2$)**:
   Calculates behavioral threat score.
   $$S_2 = 1.0 - S_1$$
3. **Step 3: Financial & Transaction Risk ($S_3$)**:
   Evaluates device trust, IP threat feeds, velocity spikes, and network proxy usage (VPN/TOR).
4. **Step 4: Combined Raw Risk Score ($S_4$)**:
   Weights behavioral and financial risk scores:
   $$S_4 = 0.40 \times S_2 + 0.60 \times S_3$$
5. **Step 5: Classification & Final Risk Score ($S_5$)**:
   Classifies transactions into risk tiers:
   - **`SAFE`**: Score $< 0.30$
   - **`SUSPICIOUS`**: $0.30 \le \text{Score} < 0.60$
   - **`HIGH_RISK`**: Score $\ge 0.60$

---

### C. Self-Correcting AI Rule Writer Agent (`backend/ai/agents/rule_writer.py`)
- **Multi-Provider Architecture**: Supports **Google Gemini 2.5 Flash** (Primary) with automatic failover to local **Ollama `qwen2.5-coder`**.
- **Self-Correction Retry Loop**:
  If the generated Python code violates AST safety rules (e.g. invalid attribute, prohibited loop, forbidden import), the validator's exact line error is fed back to the LLM to self-correct up to **3 automated retries**.

```
[LLM Code Generation] ──> [AST Safety Validator] ──> Passed?
         ▲                           │ No
         └──── [Retry with Error] ───┘
```

---

### D. Layered Static AST Safety Validator (`backend/core/validator.py`)
Ensures no malicious, blocking, or non-deterministic code reaches production:
1. **Syntax Check**: Verifies AST compilation via `ast.parse()`.
2. **Forbidden Node Inspection**: Rejects `Import`, `ImportFrom`, `For`, `While`, `Try`/`Except`, `ClassDef`, `Lambda`, and async nodes.
3. **Schema Attribute Whitelisting**: Guarantees attribute accesses (`tx.<field>`) only target predefined properties on `Transaction`.
4. **Sandboxed Dry-Run Execution**: Executes the compiled function against test payloads in a restricted scope containing only `SAFE_BUILTINS` (`abs`, `min`, `max`, `round`, `int`, `float`, `str`, `bool`).

---

### E. Governance & Similarity Guard (`backend/core/rule_guard.py`)
- **Semantic Vector Embeddings**: Utilizes `sentence-transformers` (`all-MiniLM-L6-v2`) to generate vector representations of active rules.
- **Cosine Similarity Verification**: Prevents duplicate or contradictory rules by rejecting candidate rules with $\ge 85\%$ cosine similarity (`SIMILARITY_THRESHOLD = 0.85`).
- **Rule Cap Control**: Enforces maximum active rules limit (`MAX_RULES_CAP = 20`).

---

### F. Condition-Based SOC Prevention Store (`backend/soc/rule_store.py`)
- **One-Click Deployments**: Allows SOC analysts to deploy instant key-value condition rules (`amount_gt`, `location_in`, `vpn_prob_gt`, `automation_score_gt`, `known_device_lt`).
- **Short-Circuit Evaluation**: Rules evaluate in order of creation (`ORDER BY created_at ASC`). The first matching rule blocks the transaction and increments `hit_count`.
- **PostgreSQL JSONB Integration**: Stores conditions cleanly in native PostgreSQL JSONB columns.

---

### G. Production PostgreSQL Database Architecture (`backend/core/db.py`)
- **Database Engine**: **PostgreSQL 17** (`postgresql://postgres:...@localhost:5432/fraud_engine_db`).
- **Database Tables**:
  - `audit_log`: Deployed Python code rules and deployment history.
  - `soc_rules`: Active/Inactive SOC prevention rules with hit counters.
  - `soc_audit_log`: Live audit tracker recording every triggered SOC enforcement event.

---

## 4. Verification & Testing Suite

The repository includes **167 automated unit and integration tests** (`tests/`) covering:
- **API Routes**: Endpoint validations, error codes, and responses (`test_api.py`).
- **Audit Logging**: PostgreSQL transaction isolation and active rule selection (`test_audit_log.py`).
- **AST Validator**: Security checks, import blocking, and dry-run sandboxing (`test_validator.py`).
- **Scoring Pipeline**: Formula verification across telemetry and financial steps (`test_scoring_engine.py`).
- **Rule Guard**: Semantic vector similarity and deduplication thresholds (`test_rule_guard.py`).
- **Simulator**: Stream throughput and Indian regional location generation (`test_simulator.py`).

---

## 5. How to Run the Platform

### Start Backend API Server (FastAPI):
```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Start Streamlit Security Console:
```powershell
streamlit run Streamlit_app.py
```

### Start React Enterprise Dashboard:
```powershell
cd frontend
npm run dev
```

### Run Test Suite:
```powershell
python -m pytest tests/
```
