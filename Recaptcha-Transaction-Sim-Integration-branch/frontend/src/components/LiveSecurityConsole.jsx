// frontend/src/components/LiveSecurityConsole.jsx
// Step 2 / Step 3: Shows live flagged alerts. WebSocket feed + REST fallback.

import { useEffect, useRef, useState } from 'react';
import { fetchAlerts, WS_ALERTS_URL } from '../api';
import SeverityBadge from './SeverityBadge';
import './LiveSecurityConsole.css';

function formatAmount(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(amount);
}

function formatTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return ts; }
}

export default function LiveSecurityConsole({ selectedAlert, onAlertSelect, onAlertsChange, activeProfile }) {
  const [alerts, setAlerts] = useState([]);
  const [wsStatus, setWsStatus] = useState('connecting'); // connecting | live | disconnected
  const [newIds, setNewIds] = useState(new Set());
  const wsRef = useRef(null);

  // REST load for initial alert list
  useEffect(() => {
    fetchAlerts()
      .then(data => setAlerts(data))
      .catch(() => setAlerts([]));
  }, []);

  // Sync alerts up to parent for live stats bar calculation
  useEffect(() => {
    onAlertsChange?.(alerts);
  }, [alerts, onAlertsChange]);

  // WebSocket for live stream
  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_ALERTS_URL);
      wsRef.current = ws;

      ws.onopen = () => setWsStatus('live');
      ws.onerror = () => setWsStatus('disconnected');
      ws.onclose = () => {
        setWsStatus('disconnected');
        setTimeout(connect, 5000); // auto-reconnect
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          const alert = data.type === 'flagged_alert' && data.data ? data.data : data;
          if (alert && alert.id && alert.transaction && alert.rule_triggered) {
            setAlerts(prev => {
              if (prev.some(a => a.id === alert.id)) return prev;
              setNewIds(ids => new Set([...ids, alert.id]));
              setTimeout(() => setNewIds(ids => { const n = new Set(ids); n.delete(alert.id); return n; }), 800);
              return [alert, ...prev].slice(0, 20);
            });
          }
        } catch (_) {}
      };
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  const sevOrder = { high: 0, medium: 1, low: 2 };
  const sorted = [...alerts].sort((a, b) =>
    (sevOrder[a.severity] ?? 9) - (sevOrder[b.severity] ?? 9)
  );

  return (
    <div className="console-root">
      {/* Status bar */}
      <div className="console-status-bar">
        <span className={`status-dot ${wsStatus === 'live' ? 'live' : ''}`} />
        {wsStatus === 'live'
          ? 'Live feed active'
          : wsStatus === 'connecting'
          ? 'Connecting...'
          : 'Feed disconnected — reconnecting'}

        {activeProfile && (
          <span style={{
            marginLeft: 10,
            padding: '2px 8px',
            background: 'var(--accent-dim)',
            border: '1px solid rgba(79,122,255,0.3)',
            borderRadius: '10px',
            fontSize: 10,
            color: 'var(--accent)',
            fontFamily: 'var(--font-mono)'
          }}>
            Profile: {activeProfile}
          </span>
        )}

        <span style={{ marginLeft: 'auto' }}>{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Alert list */}
      <div className="alert-list">
        {sorted.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🛡️</div>
            <div>No alerts yet</div>
            <div style={{ fontSize: 10 }}>Waiting for live feed...</div>
          </div>
        ) : (
          sorted.map(alert => (
            <div
              key={alert.id}
              id={`alert-row-${alert.id}`}
              className={[
                'alert-row',
                selectedAlert?.id === alert.id ? 'selected' : '',
                newIds.has(alert.id) ? 'new-alert' : '',
              ].join(' ')}
              onClick={() => onAlertSelect(alert)}
            >
              <div className="alert-row-left">
                <div className="alert-rule">{alert.rule_triggered}</div>
                <div className="alert-meta">
                  {alert.transaction?.account_id} &bull; {alert.transaction?.location} &bull; {formatTime(alert.timestamp)}
                </div>
              </div>
              <div className="alert-row-right">
                <span className="alert-amount">{formatAmount(alert.transaction?.amount ?? 0)}</span>
                <SeverityBadge severity={alert.severity} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
