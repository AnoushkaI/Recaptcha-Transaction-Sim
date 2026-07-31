"""Constrained prompt used to author the profile definition library."""

from backend.profiles.schemas import PROFILE_IDS

PROFILE_BUILDER_SYSTEM_PROMPT = """You are a fraud-simulation configuration author.
Return only a valid JSON object. Do not use Markdown. Do not provide explanations.
You must conform exactly to the requested schema, use realistic synthetic ranges, and
never add fields. This is synthetic simulation data, not real customer data."""


def build_profile_library_prompt() -> str:
    names = ", ".join(PROFILE_IDS)
    return f"""Create exactly ten synthetic user profile definitions for a fraud-detection
transaction simulator. The exact profile_id values, each used once, are: {names}.

Return this exact JSON shape:
{{
  "schema_version": "1.0",
  "generated_by": "<model name>",
  "profiles": [
    {{
      "profile_id": "one allowed ID",
      "display_name": "string", "domain": "string", "description": "string",
      "risk_tendency": "low|medium|high",
      "identity": {{
        "age_years": {{"minimum": 18, "maximum": 80}},
        "occupations": ["string"],
        "monthly_income_usd": {{"minimum": 0, "maximum": 100000}},
        "device_types": ["string"], "browsers": ["string"],
        "preferred_payment_methods": ["string"],
        "typical_login_hour_utc": {{"minimum": 0, "maximum": 23}}
      }},
      "behavioral": {{
        "typing_speed_cpm": {{"minimum": 0, "maximum": 600}},
        "typing_error_rate": {{"minimum": 0.0, "maximum": 1.0}},
        "mouse_movement_quality": {{"minimum": 0.0, "maximum": 1.0}},
        "scroll_behavior": {{"minimum": 0.0, "maximum": 1.0}},
        "device_reputation": {{"minimum": 0.0, "maximum": 1.0}},
        "ip_reputation": {{"minimum": 0.0, "maximum": 1.0}},
        "vpn_probability": {{"minimum": 0.0, "maximum": 1.0}},
        "tor_probability": {{"minimum": 0.0, "maximum": 1.0}},
        "automation_probability": {{"minimum": 0.0, "maximum": 1.0}}
      }},
      "transactional": {{
        "transaction_frequency_per_day": {{"minimum": 0, "maximum": 1000}},
        "average_transaction_amount_usd": {{"minimum": 1, "maximum": 5000}},
        "transaction_amount_usd": {{"minimum": 1, "maximum": 5000}},
        "account_age_days": {{"minimum": 0, "maximum": 36500}},
        "previous_transactions": {{"minimum": 0, "maximum": 100000}},
        "merchant_categories": ["string"],
        "known_device_probability": {{"minimum": 0.0, "maximum": 1.0}},
        "unfamiliar_recipient_probability": {{"minimum": 0.0, "maximum": 1.0}},
        "password_changed_recently_probability": {{"minimum": 0.0, "maximum": 1.0}},
        "refund_attempts": {{"minimum": 0, "maximum": 100}},
        "counterparties_per_day": {{"minimum": 0, "maximum": 1000}}
      }}
    }}
  ]
}}

Constraints: behavioral probabilities and quality/reputation scores must be 0..1;
amounts must be 1..5000; profile descriptions must explain the scenario. Make
VPN_HIGH_RISK_TRAVELER medium risk with good telemetry and a known device; make
AUTHORIZED_PUSH_PAYMENT_SCAM potentially legitimate-looking with a high unfamiliar-recipient probability."""


def build_single_profile_prompt(profile_id: str) -> str:
    """Keep a local 3B model's response small enough to validate reliably."""
    return f"""Create ONE synthetic fraud-simulation profile. Return only one JSON object,
with no Markdown and no outer library object. Its profile_id must be exactly
\"{profile_id}\". Include every field below and no other fields.

{{
  "profile_id":"{profile_id}", "display_name":"string", "domain":"string",
  "description":"at least 20 characters", "risk_tendency":"low|medium|high",
  "identity":{{"age_years":{{"minimum":18,"maximum":80}},"occupations":["string"],
    "monthly_income_usd":{{"minimum":0,"maximum":100000}},"device_types":["string"],
    "browsers":["string"],"preferred_payment_methods":["string"],
    "typical_login_hour_utc":{{"minimum":0,"maximum":23}}}},
  "behavioral":{{"typing_speed_cpm":{{"minimum":0,"maximum":600}},
    "typing_error_rate":{{"minimum":0,"maximum":1}},"mouse_movement_quality":{{"minimum":0,"maximum":1}},
    "scroll_behavior":{{"minimum":0,"maximum":1}},"device_reputation":{{"minimum":0,"maximum":1}},
    "ip_reputation":{{"minimum":0,"maximum":1}},"vpn_probability":{{"minimum":0,"maximum":1}},
    "tor_probability":{{"minimum":0,"maximum":1}},"automation_probability":{{"minimum":0,"maximum":1}}}},
  "transactional":{{"transaction_frequency_per_day":{{"minimum":0,"maximum":1000}},
    "average_transaction_amount_usd":{{"minimum":1,"maximum":5000}},"transaction_amount_usd":{{"minimum":1,"maximum":5000}},
    "account_age_days":{{"minimum":0,"maximum":36500}},"previous_transactions":{{"minimum":0,"maximum":100000}},
    "merchant_categories":["string"],"known_device_probability":{{"minimum":0,"maximum":1}},
    "unfamiliar_recipient_probability":{{"minimum":0,"maximum":1}},
    "password_changed_recently_probability":{{"minimum":0,"maximum":1}},"refund_attempts":{{"minimum":0,"maximum":100}},
    "counterparties_per_day":{{"minimum":0,"maximum":1000}}}}
}}

Use plausible values for {profile_id}. All probability, reputation, and human-quality
ranges are 0..1. Ensure every minimum is <= its maximum. Specific guidance: card
testing and credential stuffing are highly automated; gift-card fraud uses a new
device and likely VPN; APP scams retain good telemetry and known devices; high-risk
travellers have good telemetry, known devices, travel merchants, and medium risk."""
