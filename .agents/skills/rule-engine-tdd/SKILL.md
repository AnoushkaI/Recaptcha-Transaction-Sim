---
name: rule-engine-tdd
description: Enforces deterministic logic for evaluating rules against transactions. Every rule must evaluate conditions strictly with exactly three possible enforcement actions.
---

# Rule Engine TDD — Deterministic Rule Evaluation

## Rule Evaluation Contract

Every rule in the SOC rule engine MUST produce exactly one of three deterministic enforcement actions:

| Action | Meaning | Behavior |
|---|---|---|
| `ALLOW` | Transaction proceeds normally | No intervention, logged as `TRANSACTION_ALLOWED` |
| `CHALLENGE` | Requires secondary verification | Triggers OTP/MFA/reCAPTCHA, logged as `CHALLENGE_TRIGGERED` |
| `BLOCK` | Transaction stopped immediately | Halted, logged as `TRANSACTION_BLOCKED` |

## Condition Evaluation Rules

1. **All conditions must be AND-evaluated**: A rule matches only when ALL its conditions are satisfied.
2. **Conditions are key-value pairs** — not Python code — to prevent injection attacks.
3. **Supported Condition Keys**:
   - `amount_gt: float` — Transaction amount exceeds threshold
   - `amount_lt: float` — Transaction amount below threshold
   - `vpn_prob_gt: float` — VPN probability exceeds threshold (0.0–1.0)
   - `automation_score_gt: float` — Automation probability exceeds threshold
   - `unknown_device: bool` — `known_device_probability < 0.5`
   - `classification: str` — Matches `HIGH_RISK`, `SUSPICIOUS`, or `SAFE`
   - `location_in: list[str]` — Location code is in the provided list
   - `tor_used: bool` — `tor_probability > 0.3`
4. **Short-circuit evaluation**: If any condition fails, skip remaining conditions immediately.
5. **No side-effects inside evaluation**: The evaluator is a pure function — it does NOT modify the transaction.

## Priority

Rules are evaluated in order of `created_at` (oldest first). The FIRST matching rule wins.

## Enforcement Action Immutability

The `final_risk_score` is computed by the scoring engine and MUST NOT be changed by rule evaluation. The rule only adds an `enforcement_action` field.
