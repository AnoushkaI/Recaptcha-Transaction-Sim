"""
Transaction Simulator (`core/simulator.py`)

Generates semi-realistic synthetic transaction stream with Play/Pause/Stop control,
profile-driven behavioral and transactional metrics, and automatic deterministic
scoring pipeline integration (backend/scoring/engine.py).
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from backend.core.schemas import Transaction, CustomProfile
from backend.scoring.engine import evaluate_transaction


class SimulatorState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


# Real-world realistic defaults for generation
LOCATIONS = [
    "US-NY", "US-CA", "US-TX", "GB-LON", "DE-BER",
    "FR-PAR", "JP-TYO", "RU-MOS", "BR-SAO", "CN-BEI"
]

HIGH_RISK_LOCATIONS = ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"]

MERCHANT_CATEGORIES = [
    "groceries", "gas_station", "electronics", "crypto",
    "gift_cards", "digital_goods", "fashion", "utilities", "travel", "gaming", "wire_transfer"
]


class TransactionSimulator:
    def __init__(self, interval_seconds: float = 1.0, profile_library_path: Optional[str] = None):
        self.interval_seconds: float = interval_seconds
        self.state: SimulatorState = SimulatorState.STOPPED
        self.profile: CustomProfile = CustomProfile()
        self._listeners: List[Callable[[Transaction], None]] = []
        self._async_listeners: List[Callable[[Transaction], Any]] = []
        self._task: Optional[asyncio.Task] = None
        self._counter: int = 1000
        self.loaded_profiles: List[Dict[str, Any]] = []

        # Load profile definitions library if available
        lib_path = Path(profile_library_path or "backend/profiles/profiles.json")
        if lib_path.exists():
            try:
                with open(lib_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.loaded_profiles = data.get("profiles", [])
            except Exception:
                self.loaded_profiles = []

    def add_listener(self, callback: Callable[[Transaction], None]) -> None:
        """Register a synchronous listener callback for generated transactions."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def add_async_listener(self, callback: Callable[[Transaction], Any]) -> None:
        """Register an async listener callback for generated transactions."""
        if callback not in self._async_listeners:
            self._async_listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
        if callback in self._async_listeners:
            self._async_listeners.remove(callback)

    def set_profile(self, profile: CustomProfile) -> None:
        """Inject a custom profile to bias generation distribution."""
        self.profile = profile

    def play(self) -> None:
        """Start or resume transaction generation."""
        if self.state == SimulatorState.PAUSED:
            self.state = SimulatorState.RUNNING
        elif self.state == SimulatorState.STOPPED:
            self.state = SimulatorState.RUNNING
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._run_loop())
            except RuntimeError:
                pass

    def pause(self) -> None:
        """Pause transaction generation without resetting state."""
        if self.state == SimulatorState.RUNNING:
            self.state = SimulatorState.PAUSED

    def stop(self) -> None:
        """Stop transaction generation and cancel background task."""
        self.state = SimulatorState.STOPPED
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def start_async(self) -> None:
        """Start simulator loop asynchronously."""
        self.state = SimulatorState.RUNNING
        await self._run_loop()

    def generate_single_transaction(self) -> Transaction:
        """Generate a single profile-driven transaction with calculated telemetry and risk scores."""
        self._counter += 1
        tx_id = f"tx_{self._counter}_{uuid.uuid4().hex[:6]}"
        account_id = f"acc_{random.randint(1000, 9999)}"
        device_id = f"dev_{random.randint(1000, 9999)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # If profile definitions are loaded from backend/profiles/profiles.json, pick one
        if self.loaded_profiles and random.random() > self.profile.high_risk_location_bias:
            prof = random.choice(self.loaded_profiles)
            beh = prof.get("behavioral", {})
            trx = prof.get("transactional", {})

            def sample_range(r_dict: Dict[str, Any], default_min: float, default_max: float) -> float:
                if not r_dict:
                    return random.uniform(default_min, default_max)
                mn = float(r_dict.get("minimum", default_min))
                mx = float(r_dict.get("maximum", default_max))
                return random.uniform(mn, mx)

            typing_speed_cpm = round(sample_range(beh.get("typing_speed_cpm"), 150, 300), 1)
            typing_error_rate = round(sample_range(beh.get("typing_error_rate"), 0.01, 0.1), 4)
            mouse_movement_quality = round(sample_range(beh.get("mouse_movement_quality"), 0.7, 0.98), 4)
            scroll_behavior = round(sample_range(beh.get("scroll_behavior"), 0.6, 0.95), 4)
            device_reputation = round(sample_range(beh.get("device_reputation"), 0.7, 1.0), 4)
            ip_reputation = round(sample_range(beh.get("ip_reputation"), 0.7, 1.0), 4)
            automation_prob = round(sample_range(beh.get("automation_probability"), 0.01, 0.1), 4)
            vpn_prob = round(sample_range(beh.get("vpn_probability"), 0.0, 0.05), 4)
            tor_prob = round(sample_range(beh.get("tor_probability"), 0.0, 0.02), 4)

            tx_freq_per_day = round(sample_range(trx.get("transaction_frequency_per_day"), 1, 10), 1)
            avg_amount = round(sample_range(trx.get("average_transaction_amount_usd"), 50, 500), 2)
            amount = round(sample_range(trx.get("transaction_amount_usd"), 10, 1000), 2)
            account_age_days = int(sample_range(trx.get("account_age_days"), 30, 1000))
            previous_transactions = int(sample_range(trx.get("previous_transactions"), 5, 200))

            mc_list = trx.get("merchant_categories") or MERCHANT_CATEGORIES
            merchant_category = random.choice(mc_list)

            known_device_prob = round(sample_range(trx.get("known_device_probability"), 0.7, 1.0), 4)
            unfamiliar_recipient_prob = round(sample_range(trx.get("unfamiliar_recipient_probability"), 0.0, 0.2), 4)
            password_changed_prob = round(sample_range(trx.get("password_changed_recently_probability"), 0.0, 0.1), 4)
            refund_attempts = int(sample_range(trx.get("refund_attempts"), 0, 1))

            location = random.choice(LOCATIONS)
            is_international = location not in ["US-NY", "US-CA", "US-TX"]
        else:
            # Custom Profile / Default Fallback Generation
            if random.random() < self.profile.new_account_bias:
                account_age_days = random.randint(1, 10)
                previous_transactions = random.randint(1, 5)
            else:
                account_age_days = random.randint(30, 1000)
                previous_transactions = random.randint(10, 150)

            if random.random() < self.profile.high_risk_location_bias:
                location = random.choice(HIGH_RISK_LOCATIONS)
                is_international = True
                vpn_prob = round(random.uniform(0.5, 0.95), 4)
                tor_prob = round(random.uniform(0.1, 0.8), 4)
                automation_prob = round(random.uniform(0.4, 0.9), 4)
                ip_reputation = round(random.uniform(0.1, 0.4), 4)
                mouse_movement_quality = round(random.uniform(0.1, 0.4), 4)
            else:
                location = random.choice(LOCATIONS)
                is_international = location not in ["US-NY", "US-CA", "US-TX"]
                vpn_prob = round(random.uniform(0.01, 0.1), 4)
                tor_prob = round(random.uniform(0.0, 0.02), 4)
                automation_prob = round(random.uniform(0.01, 0.15), 4)
                ip_reputation = round(random.uniform(0.7, 0.98), 4)
                mouse_movement_quality = round(random.uniform(0.6, 0.95), 4)

            amount_min = self.profile.amount_min if self.profile.amount_min is not None else 10.0
            amount_max = self.profile.amount_max if self.profile.amount_max is not None else 2500.0
            if amount_min > amount_max:
                amount_min, amount_max = amount_max, amount_min
            amount = round(random.uniform(amount_min, amount_max), 2)
            avg_amount = round(random.uniform(50.0, 500.0), 2)

            if self.profile.merchant_category_filter:
                merchant_category = random.choice(self.profile.merchant_category_filter)
            else:
                merchant_category = random.choice(MERCHANT_CATEGORIES)

            typing_speed_cpm = round(random.uniform(140.0, 320.0), 1)
            typing_error_rate = round(random.uniform(0.01, 0.15), 4)
            scroll_behavior = round(random.uniform(0.5, 0.95), 4)
            device_reputation = round(random.uniform(0.6, 0.98), 4)
            tx_freq_per_day = round(random.uniform(1.0, 15.0), 1)
            known_device_prob = 0.2 if is_international else 0.95
            unfamiliar_recipient_prob = 0.8 if is_international else 0.05
            password_changed_prob = round(random.uniform(0.0, 0.2), 4)
            refund_attempts = random.choice([0, 0, 0, 1, 2])

        # Create raw transaction instance
        tx_data = {
            "id": tx_id,
            "account_id": account_id,
            "amount": amount,
            "location": location,
            "timestamp": timestamp,
            "account_age_days": account_age_days,
            "merchant_category": merchant_category,
            "device_id": device_id,
            "is_international": is_international,
            "mouse_movement_quality": mouse_movement_quality,
            "typing_speed_cpm": typing_speed_cpm,
            "typing_error_rate": typing_error_rate,
            "scroll_behavior": scroll_behavior,
            "device_reputation": device_reputation,
            "ip_reputation": ip_reputation,
            "automation_probability": automation_prob,
            "vpn_probability": vpn_prob,
            "tor_probability": tor_prob,
            "average_amount": avg_amount,
            "previous_transactions": previous_transactions,
            "known_device_probability": known_device_prob,
            "transaction_frequency_per_day": tx_freq_per_day,
            "unfamiliar_recipient_probability": unfamiliar_recipient_prob,
            "password_changed_recently_probability": password_changed_prob,
            "refund_attempts": refund_attempts,
        }

        # Run scoring engine pipeline (formulae.docx Steps 1-5)
        scoring_result = evaluate_transaction(tx_data)

        # Attach scoring outputs
        tx_data["telemetry_score"] = scoring_result.telemetry_score
        tx_data["telemetry_risk_score"] = scoring_result.telemetry_risk_score
        tx_data["transaction_risk_score"] = scoring_result.transaction_risk_score
        tx_data["final_risk_score"] = scoring_result.final_risk_score
        tx_data["classification"] = scoring_result.classification

        return Transaction(**tx_data)

    async def _run_loop(self) -> None:
        """Internal loop executing periodic generation when state is RUNNING."""
        while self.state != SimulatorState.STOPPED:
            if self.state == SimulatorState.RUNNING:
                tx = self.generate_single_transaction()
                await self._emit_transaction(tx)
            await asyncio.sleep(self.interval_seconds)

    async def _emit_transaction(self, tx: Transaction) -> None:
        """Emit generated transaction to all registered sync and async listeners."""
        for listener in self._listeners:
            try:
                listener(tx)
            except Exception:
                pass

        for async_listener in self._async_listeners:
            try:
                res = async_listener(tx)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass
