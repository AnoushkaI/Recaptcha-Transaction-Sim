"""
Unit tests for core transaction simulator.
"""

import pytest
import asyncio
from backend.core.schemas import Transaction, CustomProfile
from backend.core.simulator import TransactionSimulator, SimulatorState


def test_simulator_initial_state():
    sim = TransactionSimulator(interval_seconds=0.1)
    assert sim.state == SimulatorState.STOPPED


def test_simulator_play_pause_stop():
    sim = TransactionSimulator(interval_seconds=0.1)
    
    sim.play()
    assert sim.state == SimulatorState.RUNNING

    sim.pause()
    assert sim.state == SimulatorState.PAUSED

    sim.play()
    assert sim.state == SimulatorState.RUNNING

    sim.stop()
    assert sim.state == SimulatorState.STOPPED


def test_single_transaction_generation():
    sim = TransactionSimulator()
    tx = sim.generate_single_transaction()

    assert isinstance(tx, Transaction)
    assert tx.id.startswith("tx_")
    assert tx.account_id.startswith("acc_")
    assert tx.amount >= 10.0
    assert tx.account_age_days >= 1


def test_custom_profile_injection():
    sim = TransactionSimulator()
    
    profile = CustomProfile(
        name="high_risk_test",
        amount_min=5000.0,
        amount_max=10000.0,
        high_risk_location_bias=1.0,
        new_account_bias=1.0,
        merchant_category_filter=["crypto"]
    )
    sim.set_profile(profile)

    for _ in range(10):
        tx = sim.generate_single_transaction()
        assert tx.amount >= 5000.0
        assert tx.amount <= 10000.0
        assert tx.account_age_days <= 10
        assert tx.merchant_category == "crypto"
        assert tx.location in ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"]


@pytest.mark.asyncio
async def test_simulator_listener_emission():
    sim = TransactionSimulator(interval_seconds=0.05)
    received_txs = []

    def sync_listener(tx: Transaction):
        received_txs.append(tx)

    sim.add_listener(sync_listener)
    
    # Generate 3 transactions manually
    for _ in range(3):
        tx = sim.generate_single_transaction()
        await sim._emit_transaction(tx)

    assert len(received_txs) == 3
    assert received_txs[0].id.startswith("tx_")

    # Test remove listener
    sim.remove_listener(sync_listener)
    assert sync_listener not in sim._listeners


def test_simulator_amount_swap_and_state():
    sim = TransactionSimulator()
    profile = CustomProfile(amount_min=5000.0, amount_max=1000.0)  # Min > Max
    sim.set_profile(profile)

    tx = sim.generate_single_transaction()
    assert 1000.0 <= tx.amount <= 5000.0

    # Redundant state calls
    sim.pause()
    assert sim.state == SimulatorState.STOPPED
    sim.play()
    assert sim.state == SimulatorState.RUNNING
    sim.play()  # Duplicate play call while RUNNING
    assert sim.state == SimulatorState.RUNNING
    sim.pause()
    assert sim.state == SimulatorState.PAUSED
    sim.pause()  # Duplicate pause while PAUSED
    assert sim.state == SimulatorState.PAUSED
    sim.stop()
    assert sim.state == SimulatorState.STOPPED
    sim.stop()  # Duplicate stop while STOPPED
    assert sim.state == SimulatorState.STOPPED


@pytest.mark.asyncio
async def test_simulator_async_run_loop():
    sim = TransactionSimulator(interval_seconds=0.01)
    received = []

    def cb(tx: Transaction):
        received.append(tx)

    sim.add_listener(cb)
    sim.play()
    await asyncio.sleep(0.05)
    sim.stop()
    assert len(received) > 0

