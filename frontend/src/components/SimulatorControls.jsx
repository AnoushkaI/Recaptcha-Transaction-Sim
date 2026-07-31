// frontend/src/components/SimulatorControls.jsx
// Play / Pause / Stop buttons → POST /simulator/state
// Revert Last Rule button → POST /rules/{id}/revert

import { useState } from 'react';
import { setSimulatorState, revertRule } from '../api';
import './SimulatorControls.css';

export default function SimulatorControls({ onRevert, activeProfile }) {
  const [simState, setSimState] = useState('stopped'); // stopped | running | paused
  const [loading, setLoading]   = useState(false);
  const [lastRuleId, setLastRuleId] = useState('latest');

  async function handleSim(action) {
    setLoading(true);
    try {
      const res = await setSimulatorState(action);
      if (action === 'play')  setSimState('running');
      if (action === 'pause') setSimState('paused');
      if (action === 'stop')  setSimState('stopped');
    } catch (err) {
      console.error('Simulator error:', err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRevert() {
    setLoading(true);
    try {
      await revertRule(lastRuleId);
      onRevert?.();
    } catch (err) {
      console.error('Revert error:', err.message);
    } finally {
      setLoading(false);
    }
  }

  const isRunning = simState === 'running';
  const isPaused  = simState === 'paused';
  const isStopped = simState === 'stopped';

  return (
    <div className="sim-controls">
      <div className="sim-status">
        <span className={`sim-dot ${isRunning ? 'running' : isPaused ? 'paused' : 'stopped'}`} />
        <span className="sim-label">
          Simulator: <strong>{simState}</strong>
        </span>
        {activeProfile && (
          <span style={{
            marginLeft: 12,
            padding: '2px 8px',
            background: 'var(--accent-dim)',
            border: '1px solid rgba(79,122,255,0.3)',
            borderRadius: '12px',
            fontSize: 11,
            color: 'var(--accent)',
            fontFamily: 'var(--font-mono)'
          }}>
            Profile: {activeProfile}
          </span>
        )}
      </div>

      <div className="sim-btn-group">
        {/* Play */}
        <button
          id="btn-sim-play"
          className={`btn ${isRunning ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => handleSim('play')}
          disabled={loading || isRunning}
          title="Start transaction simulator"
        >
          ▶ Play
        </button>

        {/* Pause */}
        <button
          id="btn-sim-pause"
          className={`btn ${isPaused ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => handleSim('pause')}
          disabled={loading || !isRunning}
          title="Pause transaction simulator"
        >
          ⏸ Pause
        </button>

        {/* Stop */}
        <button
          id="btn-sim-stop"
          className="btn btn-ghost"
          onClick={() => handleSim('stop')}
          disabled={loading || isStopped}
          title="Stop transaction simulator"
        >
          ⏹ Stop
        </button>
      </div>

      <div className="sim-divider" />

      {/* Revert Last Rule */}
      <button
        id="btn-revert-rule"
        className="btn btn-danger"
        onClick={handleRevert}
        disabled={loading}
        title="Revert to previous ruleset from audit log"
      >
        ↩ Revert to previous
      </button>
    </div>
  );
}
