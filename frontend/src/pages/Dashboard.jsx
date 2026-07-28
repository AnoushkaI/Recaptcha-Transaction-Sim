// frontend/src/pages/Dashboard.jsx
// Main dashboard page — assembles components, live feed, rules audit log, custom profiles

import { useState, useEffect } from 'react';
import LiveSecurityConsole from '../components/LiveSecurityConsole';
import ChatPanel from '../components/ChatPanel';
import SimulatorControls from '../components/SimulatorControls';
import ProfileBuilderModal from '../components/ProfileBuilderModal';
import AuditTrailModal from '../components/AuditTrailModal';
import { fetchAlerts } from '../api';
import './Dashboard.css';

export default function Dashboard() {
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [activeProfile, setActiveProfile] = useState('Standard Simulation');
  const [alerts, setAlerts] = useState([]);
  const [ruleDeployedCount, setRuleDeployedCount] = useState(0);

  // Fetch initial alerts
  useEffect(() => {
    fetchAlerts().then(setAlerts).catch(() => {});
  }, [ruleDeployedCount]);

  const highCount = alerts.filter(a => a.severity === 'high').length;
  const medCount = alerts.filter(a => a.severity === 'medium').length;

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
            id="btn-open-audit-trail"
            className="btn btn-ghost"
            onClick={() => setShowAuditModal(true)}
            title="Inspect active rules engine & SHA-256 audit trail"
          >
            📜 Rules & Audit Log
          </button>
          <button
            id="btn-open-profile-builder"
            className="btn btn-primary"
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
            Live Backend Engine
          </div>
        </div>
      </header>

      {/* ── Simulator controls + active profile badge + revert ────── */}
      <div className="controls-bar">
        <SimulatorControls
          activeProfile={activeProfile}
          onRevert={() => {
            setSelectedAlert(null);
            setRuleDeployedCount(c => c + 1);
          }}
        />
      </div>

      {/* ── Two-column main layout ────────────────────────────────── */}
      <div className="main-layout">
        {/* Left column — Live Security Console */}
        <div className="left-col">
          <div className="panel-header">
            <span className="panel-title">Live Security Console (Cap 20)</span>
          </div>
          <div className="col-panel">
            <LiveSecurityConsole
              selectedAlert={selectedAlert}
              onAlertSelect={handleAlertSelect}
              onAlertsChange={setAlerts}
              activeProfile={activeProfile}
            />
          </div>

          {/* Stats bar */}
          <div className="stats-bar">
            <div className="stat-item">
              <div className="stat-value">{alerts.length}</div>
              <div className="stat-label">Total (Max 20)</div>
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
          onCreated={(id, name) => {
            setActiveProfile(name || 'Custom Profile Applied');
            setShowProfileModal(false);
          }}
        />
      )}

      {/* ── Rules & Audit Trail modal ────────────────────────────── */}
      {showAuditModal && (
        <AuditTrailModal
          onClose={() => setShowAuditModal(false)}
        />
      )}
    </div>
  );
}
