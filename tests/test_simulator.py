"""
Comprehensive unit tests for simulator.py targeting 100% line coverage.
Missing lines from previous run: 55-56, 59-62, 77, 90-91, 95-96, 122, 149-153, 160-161, 164-169
"""

import asyncio
import pytest
from backend.core.schemas import Transaction, CustomProfile
from backend.core.simulator import TransactionSimulator, SimulatorState


# --------------- helpers ---------------

def make_tx_collector():
    collected = []
    def cb(tx):
        collected.append(tx)
    return cb, collected


# --------------- basic state tests ---------------

def test_initial_state():
    sim = TransactionSimulator(interval_seconds=0.1)
    assert sim.state == SimulatorState.STOPPED


def test_play_from_stopped():
    sim = TransactionSimulator()
    sim.play()
    assert sim.state == SimulatorState.RUNNING


def test_play_while_running_is_noop():
    sim = TransactionSimulator()
    sim.play()
    sim.play()  # duplicate play — should stay RUNNING
    assert sim.state == SimulatorState.RUNNING


def test_play_from_paused_resumes():
    sim = TransactionSimulator()
    sim.play()
    sim.pause()
    assert sim.state == SimulatorState.PAUSED
    sim.play()  # resume from PAUSED → hits the if-branch on line 70-71
    assert sim.state == SimulatorState.RUNNING


def test_pause_while_running():
    sim = TransactionSimulator()
    sim.play()
    sim.pause()
    assert sim.state == SimulatorState.PAUSED


def test_pause_while_stopped_is_noop():
    sim = TransactionSimulator()
    sim.pause()  # not RUNNING, so guard on line 83 prevents state change
    assert sim.state == SimulatorState.STOPPED


def test_stop_from_running():
    sim = TransactionSimulator()
    sim.play()
    sim.stop()
    assert sim.state == SimulatorState.STOPPED


def test_stop_while_already_stopped():
    sim = TransactionSimulator()
    sim.stop()  # _task is None, so the if-branch on 89 is skipped
    assert sim.state == SimulatorState.STOPPED


# --------------- listener registration ---------------

def test_add_listener_deduplication():
    sim = TransactionSimulator()
    cb, _ = make_tx_collector()
    sim.add_listener(cb)
    sim.add_listener(cb)  # duplicate — should not add twice (line 50 guard)
    assert sim._listeners.count(cb) == 1


def test_add_async_listener_deduplication():
    sim = TransactionSimulator()
    async def acb(tx): pass
    sim.add_async_listener(acb)
    sim.add_async_listener(acb)  # duplicate guard on line 55-56
    assert sim._async_listeners.count(acb) == 1


def test_remove_sync_listener():
    sim = TransactionSimulator()
    cb, _ = make_tx_collector()
    sim.add_listener(cb)
    sim.remove_listener(cb)  # hits line 59-60
    assert cb not in sim._listeners


def test_remove_async_listener():
    sim = TransactionSimulator()
    async def acb(tx): pass
    sim.add_async_listener(acb)
    sim.remove_listener(acb)  # hits line 61-62
    assert acb not in sim._async_listeners


def test_remove_nonexistent_listener_is_safe():
    sim = TransactionSimulator()
    cb, _ = make_tx_collector()
    sim.remove_listener(cb)  # should not raise


# --------------- transaction generation ---------------

def test_generate_single_transaction():
    sim = TransactionSimulator()
    tx = sim.generate_single_transaction()
    assert isinstance(tx, Transaction)
    assert tx.id.startswith("tx_")
    assert tx.amount >= 10.0
    assert tx.account_age_days >= 1


def test_custom_profile_high_risk():
    sim = TransactionSimulator()
    profile = CustomProfile(
        name="high_risk",
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
        assert tx.location in ["MUM-JMT", "DEL-NUH", "BLR-PAT", "DEL-LKO", "HYD-RNC"]


def test_amount_min_greater_than_max_is_swapped():
    """Hits line 121-122: amount_min > amount_max swap branch."""
    sim = TransactionSimulator()
    profile = CustomProfile(amount_min=5000.0, amount_max=100.0)
    sim.set_profile(profile)
    tx = sim.generate_single_transaction()
    assert 100.0 <= tx.amount <= 5000.0


def test_no_category_filter_uses_random():
    """Profile with no merchant_category_filter hits else-branch on line 129."""
    sim = TransactionSimulator()
    profile = CustomProfile(name="no_filter")
    sim.set_profile(profile)
    tx = sim.generate_single_transaction()
    assert tx.merchant_category is not None


# --------------- async emit ---------------

@pytest.mark.asyncio
async def test_emit_sync_listener():
    sim = TransactionSimulator()
    cb, collected = make_tx_collector()
    sim.add_listener(cb)
    tx = sim.generate_single_transaction()
    await sim._emit_transaction(tx)
    assert len(collected) == 1


@pytest.mark.asyncio
async def test_emit_async_listener():
    """Hits lines 163-167: async listener coroutine branch."""
    sim = TransactionSimulator()
    received = []

    async def acb(tx):
        received.append(tx)

    sim.add_async_listener(acb)
    tx = sim.generate_single_transaction()
    await sim._emit_transaction(tx)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_emit_async_listener_non_coroutine():
    """Hits line 165: async_listener returns non-coroutine (plain value)."""
    sim = TransactionSimulator()
    received = []

    def sync_returning_none(tx):
        received.append(tx)
        return None  # not a coroutine, so iscoroutine(res) is False

    sim.add_async_listener(sync_returning_none)
    tx = sim.generate_single_transaction()
    await sim._emit_transaction(tx)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_emit_sync_listener_exception_is_swallowed():
    """Hits line 160-161: sync listener exception handling."""
    sim = TransactionSimulator()

    def crashing_cb(tx):
        raise ValueError("boom")

    sim.add_listener(crashing_cb)
    tx = sim.generate_single_transaction()
    # Should not raise
    await sim._emit_transaction(tx)


@pytest.mark.asyncio
async def test_emit_async_listener_exception_is_swallowed():
    """Hits line 168-169: async listener exception handling."""
    sim = TransactionSimulator()

    async def crashing_acb(tx):
        raise ValueError("boom async")

    sim.add_async_listener(crashing_acb)
    tx = sim.generate_single_transaction()
    # Should not raise
    await sim._emit_transaction(tx)


@pytest.mark.asyncio
async def test_run_loop_generates_transactions():
    """Hits lines 147-153: the run_loop body executing in RUNNING state."""
    sim = TransactionSimulator(interval_seconds=0.01)
    collected = []
    sim.add_listener(lambda tx: collected.append(tx))

    # Simulate 3 iterations then stop
    sim.state = SimulatorState.RUNNING
    task = asyncio.create_task(sim._run_loop())
    await asyncio.sleep(0.05)
    sim.stop()
    try:
        await asyncio.wait_for(task, timeout=0.2)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    assert len(collected) > 0


@pytest.mark.asyncio
async def test_run_loop_paused_skips_generation():
    """Hits line 150: PAUSED state — loop iterates but skips generation."""
    sim = TransactionSimulator(interval_seconds=0.01)
    collected = []
    sim.add_listener(lambda tx: collected.append(tx))

    sim.state = SimulatorState.PAUSED  # Set paused directly
    task = asyncio.create_task(sim._run_loop())
    await asyncio.sleep(0.05)
    sim.stop()
    try:
        await asyncio.wait_for(task, timeout=0.2)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    assert len(collected) == 0  # PAUSED → nothing generated


@pytest.mark.asyncio
async def test_start_async():
    """Hits lines 93-96: start_async() method."""
    sim = TransactionSimulator(interval_seconds=0.01)
    collected = []
    sim.add_listener(lambda tx: collected.append(tx))

    task = asyncio.create_task(sim.start_async())
    await asyncio.sleep(0.05)
    sim.stop()
    try:
        await asyncio.wait_for(task, timeout=0.2)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    assert len(collected) > 0


@pytest.mark.asyncio
async def test_play_with_running_event_loop_creates_task():
    """Hits line 77: play() when asyncio loop IS running → creates background task."""
    sim = TransactionSimulator(interval_seconds=0.05)
    sim.play()  # inside pytest-asyncio, loop is already running
    await asyncio.sleep(0.1)
    sim.stop()
    if sim._task:
        try:
            await asyncio.wait_for(sim._task, timeout=0.2)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    assert sim.state == SimulatorState.STOPPED
