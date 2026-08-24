import { useState, useEffect } from 'react';
import './AuditTrailModal.css';

export default function AuditTrailModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('audit'); // 'audit' | 'rules'
  const [rules, setRules] = useState([]);
  const [auditLog, setAuditLog] = useState({ entries: [], integrity_valid: true, tampered_row_id: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [rulesRes, auditRes] = await Promise.all([
          fetch('http://localhost:8000/api/rules').then(r => r.json()),
          fetch('http://localhost:8000/api/audit-log').then(r => r.json())
        ]);
        setRules(rulesRes || []);
        setAuditLog(auditRes || { entries: [], integrity_valid: true });
      } catch (err) {
        console.error('Failed to fetch audit log or rules:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card audit-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <div className="modal-title">📜 Rules Engine & Audit Trail</div>
            <div className="modal-subtitle">
              SHA-256 Hash-Chained Audit Log & Active Rules (Cap 20)
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Tab Selector */}
        <div className="audit-tabs">
          <button
            className={`audit-tab ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            Audit Log ({auditLog.entries?.length || 0})
          </button>
          <button
            className={`audit-tab ${activeTab === 'rules' ? 'active' : ''}`}
            onClick={() => setActiveTab('rules')}
          >
            Active Rules ({rules.length}/20)
          </button>
        </div>

        {/* Content Area */}
        <div className="modal-body">
          {loading ? (
            <div className="audit-loading">Loading audit records...</div>
          ) : activeTab === 'audit' ? (
            <div>
              {/* Integrity status bar */}
              <div className={`integrity-bar ${auditLog.integrity_valid ? 'valid' : 'tampered'}`}>
                {auditLog.integrity_valid ? (
                  <span>✓ <strong>SHA-256 Hash Chain Integrity Verified:</strong> Audit log entries are untampered.</span>
                ) : (
                  <span>⚠️ <strong>Hash Chain Integrity Compromised!</strong> Tampering detected at row #{auditLog.tampered_row_id}</span>
                )}
              </div>

              {/* Table */}
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Timestamp</th>
                      <th>Rule ID</th>
                      <th>Action</th>
                      <th>Analyst Command</th>
                      <th>SHA-256 Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLog.entries?.map((entry) => (
                      <tr key={entry.id}>
                        <td>{entry.id}</td>
                        <td className="meta-cell">{new Date(entry.timestamp).toLocaleString()}</td>
                        <td className="meta-cell font-mono">{entry.rule_id}</td>
                        <td>
                          <span className={`status-tag ${entry.status}`}>
                            {entry.status}
                          </span>
                        </td>
                        <td className="cmd-cell">{entry.command}</td>
                        <td className="hash-cell" title={entry.hash}>{entry.hash.substring(0, 16)}...</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="rules-list-wrap">
              {rules.length === 0 ? (
                <div className="audit-loading">No active rules currently deployed.</div>
              ) : (
                rules.map((rule) => (
                  <div key={rule.id} className="rule-card">
                    <div className="rule-card-header">
                      <div>
                        <span className="rule-card-title">{rule.name}</span>
                        <span className="rule-card-id">{rule.id}</span>
                      </div>
                      <span className="rule-status-active">ACTIVE</span>
                    </div>
                    <div className="rule-card-desc">{rule.description}</div>
                    <pre className="rule-code-block">{rule.code}</pre>
                    <div className="rule-card-footer">
                      Deployed via: "{rule.created_by_command}" &bull; {new Date(rule.created_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
