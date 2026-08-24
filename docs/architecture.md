# Architecture & Operations Guide - Person A: Engine & Local AI

## Overview
This component implements **Person A's half** of the AI-assisted fraud detection system: a high-performance, real-time rules engine, synthetic transaction simulator, multi-layer AST safety validator, rule guard, compiler, cryptographic hash-chained SQLite audit logger, and local LLM fallback provider (`qwen2.5-coder:3b`).

It is designed to run **100% standalone with zero AI dependency**, allowing complete isolation testing, while also serving as the execution foundation for Person B's frontend dashboard and agent orchestrator.

---

## Component Architecture

```
                                    +-----------------------------------+
                                    | Person B: React Dashboard / Agent |
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

## Data Contracts (Co-owned with Person B)

Defined in `backend/core/schemas.py`:
- `Transaction`: `id`, `account_id`, `amount`, `location`, `timestamp`, `account_age_days`, `merchant_category`, `device_id`, `is_international`
- `FlaggedAlert`: `id`, `transaction_id`, `rule_id`, `rule_name`, `score`, `flagged_at`, `transaction_details`
- `Rule`: `id`, `name`, `code`, `description`, `created_at`, `status`, `created_by_command`
- `CustomProfile`: `name`, `amount_min`, `amount_max`, `high_risk_location_bias`, `new_account_bias`
- `ValidationResult`: `valid` (bool), `error` (str | None), `line_number` (int | None)
- `GuardResult`: `passed` (bool), `reason` (str | None), `similarity_score` (float | None), `duplicate_rule_id` (str | None)

---

## Setup & Running Guide

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) (for local model fallback)

### 2. Environment & Dependency Setup
```bash
# Clone and enter project directory
cd fraud-rule-engine

# Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Local LLM Fallback (Ollama)
```bash
# Install Ollama from https://ollama.com/
# Start Ollama server
ollama serve

# In a new terminal, pull Qwen2.5-Coder 3B (Q4 quantization)
ollama pull qwen2.5-coder:3b
```

### 4. Running the Standalone Backend
```bash
# Start FastAPI server on port 8000
python -m uvicorn backend.main:app --reload --port 8000
```
- REST API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Live WebSocket Alerts Endpoint: `ws://localhost:8000/ws/alerts`

---

## Running Test Suites

Run all automated unit and standalone integration tests:
```bash
python -m pytest tests/
```

Individual test stage execution:
```bash
python -m pytest tests/test_schemas.py        # Stage 1: Data Contracts
python -m pytest tests/test_simulator.py      # Stage 2: Simulator
python -m pytest tests/test_rules_engine.py   # Stage 3: Live Engine & Hot-Reload
python -m pytest tests/test_validator.py      # Stage 4: AST Security Checks
python -m pytest tests/test_rule_guard.py     # Stage 5: Rule Guard & Semantic Check
python -m pytest tests/test_compiler.py       # Stage 6: Compiler
python -m pytest tests/test_audit_log.py      # Stage 7: Hash-Chained Audit Log
python -m pytest tests/test_integration.py    # Stage 8: Full Integration Test
```

---

## Local Model Benchmark Harness

To benchmark local model generation throughput and AST pass rate on your hardware (NVIDIA RTX 2050 GPU / 4GB VRAM):
```bash
python benchmark_local.py
```
This runs 10 fraud-rule generation prompts and records:
- Generation Latency (seconds)
- Token Throughput (tokens/sec)
- AST Security Validator pass rate
- Results saved to `docs/benchmark_results.json`.

---

## "Kill the Internet" Demo Guide

To demonstrate the resilience of the local model fallback during a presentation or viva:
1. Start local Ollama: `ollama serve`
2. Disconnect Wi-Fi / Ethernet or set `LLM_PROVIDER=local` in `.env`.
3. Trigger a rule-generation request via the agent API.
4. Observe that the system automatically falls back to `qwen2.5-coder:3b`, completes the rule generation end-to-end, passes the AST Safety Validator, passes the Rule Guard, and hot-reloads into the live engine without any internet connectivity.
