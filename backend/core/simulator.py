"""
Transaction Simulator (`core/simulator.py`)

Generates semi-realistic synthetic transaction stream with Play/Pause/Stop control
and Custom Profile injection for fraud scenario testing.
"""

import asyncio
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional, List, Dict, Any

from backend.core.schemas import Transaction, CustomProfile


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
    "luxury_goods", "travel", "gaming", "wire_transfer"
]


class TransactionSimulator:
    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds: float = interval_seconds
        self.state: SimulatorState = SimulatorState.STOPPED
        self.profile: CustomProfile = CustomProfile()
        self._listeners: List[Callable[[Transaction], None]] = []
        self._async_listeners: List[Callable[[Transaction], Any]] = []
        self._task: Optional[asyncio.Task] = None
        self._counter: int = 1000

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
            # Start background async loop if loop is running
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._run_loop())
            except RuntimeError:
                pass  # No running event loop yet; will run when start_async() is called

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
        """Generate a single transaction based on active custom profile biases."""
        self._counter += 1
        tx_id = f"tx_{self._counter}_{uuid.uuid4().hex[:6]}"
        account_id = f"acc_{random.randint(1000, 9999)}"

        # 1. Account age bias
        if random.random() < self.profile.new_account_bias:
            account_age_days = random.randint(1, 10)
        else:
            account_age_days = random.randint(1, 1000)

        # 2. Location bias
        if random.random() < self.profile.high_risk_location_bias:
            location = random.choice(HIGH_RISK_LOCATIONS)
            is_international = True
        else:
            location = random.choice(LOCATIONS)
            is_international = location not in ["US-NY", "US-CA", "US-TX"]

        # 3. Amount bias
        amount_min = self.profile.amount_min if self.profile.amount_min is not None else 10.0
        amount_max = self.profile.amount_max if self.profile.amount_max is not None else 2500.0
        if amount_min > amount_max:
            amount_min, amount_max = amount_max, amount_min
        amount = round(random.uniform(amount_min, amount_max), 2)

        # 4. Category selection
        if self.profile.merchant_category_filter:
            category = random.choice(self.profile.merchant_category_filter)
        else:
            category = random.choice(MERCHANT_CATEGORIES)

        device_id = f"dev_{random.randint(1000, 9999)}"
        timestamp = datetime.now(timezone.utc).isoformat()

        tx = Transaction(
            id=tx_id,
            account_id=account_id,
            amount=amount,
            location=location,
            timestamp=timestamp,
            account_age_days=account_age_days,
            merchant_category=category,
            device_id=device_id,
            is_international=is_international
        )
        return tx

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
            except Exception as e:
                pass

        for async_listener in self._async_listeners:
            try:
                res = async_listener(tx)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                pass
