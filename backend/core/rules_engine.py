"""
Live Rules Engine (`core/rules_engine.py`)

Evaluates synthetic transactions against active rules in-memory. Emits FlaggedAlerts
over WebSocket callback immediately. Supports mid-run hot-reloading and ruleset revert.
"""

import logging
import asyncio
from typing import Dict, List, Callable, Optional, Tuple, Any
from datetime import datetime, timezone
import uuid

from backend.core.schemas import Transaction, FlaggedAlert, Rule

logger = logging.getLogger(__name__)


class RulesEngine:
    def __init__(self):
        # Maps rule_id -> (Rule metadata object, compiled executable function)
        self._active_rules: Dict[str, Tuple[Rule, Callable[[Transaction], bool]]] = {}
        self._alert_listeners: List[Callable[[FlaggedAlert], None]] = []
        self._async_alert_listeners: List[Callable[[FlaggedAlert], Any]] = []

    def add_alert_listener(self, callback: Callable[[FlaggedAlert], None]) -> None:
        """Register a sync listener for generated alerts."""
        if callback not in self._alert_listeners:
            self._alert_listeners.append(callback)

    def add_async_alert_listener(self, callback: Callable[[FlaggedAlert], Any]) -> None:
        """Register an async listener for generated alerts (e.g. WebSocket manager)."""
        if callback not in self._async_alert_listeners:
            self._async_alert_listeners.append(callback)

    def remove_alert_listener(self, callback: Callable) -> None:
        if callback in self._alert_listeners:
            self._alert_listeners.remove(callback)
        if callback in self._async_alert_listeners:
            self._async_alert_listeners.remove(callback)

    def register_rule(self, rule: Rule, rule_func: Callable[[Transaction], bool]) -> None:
        """
        Hot-reload registration: Add or update an active rule in memory immediately.
        No process restart required.
        """
        self._active_rules[rule.id] = (rule, rule_func)
        logger.info(f"Registered/Hot-reloaded active rule: {rule.id} ({rule.name})")

    def unregister_rule(self, rule_id: str) -> Optional[Rule]:
        """Remove a rule from active in-memory evaluation."""
        if rule_id in self._active_rules:
            rule, _ = self._active_rules.pop(rule_id)
            logger.info(f"Unregistered active rule: {rule_id}")
            return rule
        return None

    def get_active_rules(self) -> List[Rule]:
        """Returns all currently active rules."""
        return [rule for rule, _ in self._active_rules.values()]

    def get_active_rule_ids(self) -> List[str]:
        """Returns IDs of all currently active rules."""
        return list(self._active_rules.keys())

    def clear_rules(self) -> None:
        """Clear all active in-memory rules."""
        self._active_rules.clear()

    def revert_ruleset(self, new_rules: List[Tuple[Rule, Callable[[Transaction], bool]]]) -> None:
        """
        Revert active ruleset to a specific historic snapshot.
        Replaces current active dictionary atomically.
        """
        new_active = {}
        for rule, func in new_rules:
            new_active[rule.id] = (rule, func)
        self._active_rules = new_active
        logger.info(f"Reverted active ruleset. Active rule count is now {len(self._active_rules)}")

    def score_transaction(self, tx: Transaction) -> List[FlaggedAlert]:
        """
        Evaluates a transaction against all active rules synchronously.
        Returns a list of generated FlaggedAlert objects.
        """
        alerts: List[FlaggedAlert] = []
        for rule_id, (rule, rule_func) in list(self._active_rules.items()):
            try:
                # Execute compiled rule
                is_triggered = rule_func(tx)
                if is_triggered:
                    alert_id = f"alt_{uuid.uuid4().hex[:8]}"
                    timestamp = datetime.now(timezone.utc).isoformat()
                    alert = FlaggedAlert(
                        id=alert_id,
                        transaction_id=tx.id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        score=1.0,
                        flagged_at=timestamp,
                        transaction_details=tx
                    )
                    alerts.append(alert)
                    self._emit_alert_sync(alert)
            except Exception as e:
                logger.error(f"Error executing rule {rule_id} on tx {tx.id}: {str(e)}")

        return alerts

    def _emit_alert_sync(self, alert: FlaggedAlert) -> None:
        """Emit alert to synchronous listeners immediately."""
        for listener in self._alert_listeners:
            try:
                listener(alert)
            except Exception as e:
                logger.error(f"Error in sync alert listener: {e}")

        # Also schedule emission to async listeners if event loop running
        try:
            loop = asyncio.get_running_loop()
            for async_listener in self._async_alert_listeners:
                res = async_listener(alert)
                if asyncio.iscoroutine(res):
                    loop.create_task(res)
        except RuntimeError:
            pass  # No running event loop
