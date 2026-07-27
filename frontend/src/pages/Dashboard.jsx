// frontend/src/pages/Dashboard.jsx
// Main dashboard page — assembles all 5 components

import { useState, useEffect } from 'react';
import LiveSecurityConsole from '../components/LiveSecurityConsole';
import ChatPanel from '../components/ChatPanel';
import SimulatorControls from '../components/SimulatorControls';
import ProfileBuilderModal from '../components/ProfileBuilderModal';
import { fetchAlerts } from '../api';
import './Dashboard.css';

export default function Dashboard() {
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [ruleDeployedCount, setRuleDeployedCount] = useState(0);

  // For stats bar
  useEffect(() => {
    fetchAlerts().then(setAlerts).catch(() => {});
  }, []);

  const highCount   = alerts.filter(a => a.severity === 'high').length;
  const medCount    = alerts.filter(a => a.severity === 'medium').length;

  function handleAlertSelect(alert) {
    setSelectedAlert(alert);
  }

  function handleRuleDeployed() {
    setRuleDeployedCount(c => c + 1);
  }

  return (
    <div className="dashboard">
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="header">
        <div className="header-left">
          <div className="header-logo">
            <div className="header-logo-icon">🛡</div>
            Fraud Rule Engine
          </div>
          <div className="header-divider" />
          <div className="header-subtitle">AI Security Console</div>
        </div>
        <div className="header-right">
          <button
            id="btn-open-profile-builder"
            className="btn btn-ghost"
            onClick={() => setShowProfileModal(true)}
          >
            + Custom profile
          </button>
          <div style={{
            padding: '4px 10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: 11,
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}>
            Phase 4 — Mock Backend
          </div>
        </div>
      </header>

      {/* ── Simulator controls + revert ──────────────────────────── */}
      <div className="controls-bar">
        <SimulatorControls onRevert={() => setSelectedAlert(null)} />
      </div>

      {/* ── Two-column main layout ────────────────────────────────── */}
      <div className="main-layout">
        {/* Left column — Live Security Console */}
        <div className="left-col">
          <div className="panel-header">
            <span className="panel-title">Live Security Console</span>
          </div>
          <div className="col-panel">
            <LiveSecurityConsole
              selectedAlert={selectedAlert}
              onAlertSelect={handleAlertSelect}
            />
          </div>

          {/* Stats bar */}
          <div className="stats-bar">
            <div className="stat-item">
              <div className="stat-value">{alerts.length}</div>
              <div className="stat-label">Total alerts</div>
            </div>
            <div className="stat-item">
              <div className="stat-value high">{highCount}</div>
              <div className="stat-label">High</div>
            </div>
            <div className="stat-item">
              <div className="stat-value medium">{medCount}</div>
              <div className="stat-label">Medium</div>
            </div>
            <div className="stat-item">
              <div className="stat-value" style={{ color: 'var(--success)' }}>{ruleDeployedCount}</div>
              <div className="stat-label">Deployed</div>
            </div>
          </div>
        </div>

        {/* Right column — AI Investigator Chat Panel */}
        <div className="right-col">
          <div className="panel-header">
            <span className="panel-title">AI Investigator</span>
            {selectedAlert && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {selectedAlert.id}
              </span>
            )}
          </div>
          <div className="col-panel">
            <ChatPanel
              alert={selectedAlert}
              onRuleDeployed={handleRuleDeployed}
            />
          </div>
        </div>
      </div>

      {/* ── Profile builder modal ─────────────────────────────────── */}
      {showProfileModal && (
        <ProfileBuilderModal
          onClose={() => setShowProfileModal(false)}
          onCreated={(id) => {
            console.log('Profile created:', id);
            setShowProfileModal(false);
          }}
        />
      )}
    </div>
  );
}
