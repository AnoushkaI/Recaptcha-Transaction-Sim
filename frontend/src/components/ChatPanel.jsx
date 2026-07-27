// frontend/src/components/ChatPanel.jsx
// AI Investigator Chat Panel
// Step 3 → Step 4: explain alert
// Step 5 → Step 6: generate rule with code diff + Approve/Reject

import { useState, useRef, useEffect } from 'react';
import { explainAlert, generateRule, approveRule } from '../api';
import SeverityBadge from './SeverityBadge';
import './ChatPanel.css';

// ── Code diff renderer ──────────────────────────────────────────────────────
function CodeDiffView({ code, filename = 'rule.py' }) {
  if (!code) return null;
  const lines = code.split('\n');
  return (
    <div className="diff-container">
      <div className="diff-header">
        <span style={{ color: 'var(--success)', fontSize: 13 }}>+</span>
        <span>{filename}</span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>new rule</span>
      </div>
      <div className="diff-body">
        <div className="diff-line header-line">
          <span className="diff-line-num">@@</span>
          <span className="diff-line-content">@@ -0,0 +1,{lines.length} @@</span>
        </div>
        {lines.map((line, i) => (
          <div key={i} className="diff-line add">
            <span className="diff-line-num">{i + 1}</span>
            <span className="diff-line-content">{line || '\u00a0'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Transaction chip ────────────────────────────────────────────────────────
function TxnChips({ txn }) {
  if (!txn) return null;
  const chips = [
    ['₹' + Number(txn.amount).toLocaleString('en-IN')],
    [txn.location],
    [txn.account_id],
  ];
  return chips.map(([v], i) => (
    <span key={i} className="txn-chip">{v}</span>
  ));
}

// ── Main component ──────────────────────────────────────────────────────────
export default function ChatPanel({ alert, onRuleDeployed }) {
  const [messages, setMessages]     = useState([]);
  const [command, setCommand]       = useState('');
  const [loading, setLoading]       = useState(false);
  const [pendingRule, setPendingRule] = useState(null); // { code, ruleId }
  const feedRef = useRef(null);

  // Clear chat when alert changes
  useEffect(() => {
    setMessages([]);
    setPendingRule(null);
    setCommand('');
  }, [alert?.id]);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, loading]);

  if (!alert) {
    return (
      <div className="chat-root">
        <div className="chat-empty">
          <div className="chat-empty-icon">🔍</div>
          <div className="chat-empty-title">No alert selected</div>
          <div className="chat-empty-sub">Click an alert in the console to investigate</div>
        </div>
      </div>
    );
  }

  // ── Send a command ─────────────────────────────────────────────────────────
  async function handleSend(cmd) {
    const text = (cmd || command).trim();
    if (!text || loading) return;
    setCommand('');
    setMessages(m => [...m, { type: 'user', text }]);
    setLoading(true);

    const isGenerate = /generate|create|write|add|build|make|rule|detect|flag/i.test(text);

    try {
      if (isGenerate) {
        const result = await generateRule(text, alert.id);
        const ruleId = `rule_${Date.now()}`;
        setPendingRule({ code: result.code, ruleId, valid: result.valid, attempts: result.attempts });
        setMessages(m => [...m, {
          type: 'rule',
          code: result.code,
          valid: result.valid,
          error: result.error,
          attempts: result.attempts,
          ruleId,
        }]);
      } else {
        const result = await explainAlert(alert.id, text);
        setMessages(m => [...m, { type: 'explain', text: result.explanation }]);
      }
    } catch (err) {
      setMessages(m => [...m, { type: 'error', text: err.message }]);
    } finally {
      setLoading(false);
    }
  }

  // ── Approve / reject handlers ──────────────────────────────────────────────
  async function handleApprove(ruleId) {
    try {
      await approveRule(ruleId);
      setMessages(m => [...m, { type: 'system', text: `Rule ${ruleId} deployed successfully.` }]);
      setPendingRule(null);
      onRuleDeployed?.();
    } catch (err) {
      setMessages(m => [...m, { type: 'error', text: err.message }]);
    }
  }

  function handleReject() {
    setPendingRule(null);
    setMessages(m => [...m, { type: 'system', text: 'Rule rejected — not deployed.' }]);
  }

  return (
    <div className="chat-root">
      {/* Alert context bar */}
      <div className="chat-context-bar">
        <div className="chat-context-id">{alert.id} &bull; {new Date(alert.timestamp).toLocaleString()}</div>
        <div className="chat-context-rule">{alert.rule_triggered}</div>
        <div className="chat-context-row">
          <SeverityBadge severity={alert.severity} />
          <TxnChips txn={alert.transaction} />
        </div>
      </div>

      {/* Message feed */}
      <div className="chat-feed" ref={feedRef}>
        {messages.length === 0 && !loading && (
          <div className="msg-system">Ask the AI to explain this alert or generate a detection rule.</div>
        )}

        {messages.map((msg, i) => {
          if (msg.type === 'user') return (
            <div key={i} style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <div style={{
                background: 'var(--accent-dim)', border: '1px solid rgba(79,122,255,0.25)',
                borderRadius: 'var(--radius-md)', padding: '8px 12px',
                fontSize: 13, maxWidth: '80%', color: 'var(--text-primary)',
                animation: 'fadeSlideIn 0.2s ease',
              }}>{msg.text}</div>
            </div>
          );

          if (msg.type === 'explain') return (
            <div key={i} className="msg-explain">
              <div className="msg-explain-label">AI Forensic Analysis</div>
              <div className="msg-explain-text">{msg.text}</div>
            </div>
          );

          if (msg.type === 'rule') return (
            <div key={i} className="msg-rule">
              <div className="msg-rule-label">
                Generated Detection Rule
                {msg.attempts > 1 && (
                  <span className="retry-badge">⟳ {msg.attempts} attempts</span>
                )}
              </div>
              <CodeDiffView code={msg.code} />
              {!msg.valid && msg.error && (
                <div className="msg-error" style={{ marginTop: 8 }}>
                  Validation failed: {msg.error}
                </div>
              )}
              {msg.valid && (
                <div className="rule-actions">
                  <button
                    id={`btn-deploy-${msg.ruleId}`}
                    className="btn btn-success"
                    onClick={() => handleApprove(msg.ruleId)}
                  >
                    ✓ Deploy rule
                  </button>
                  <button
                    id={`btn-reject-${msg.ruleId}`}
                    className="btn btn-ghost"
                    onClick={handleReject}
                  >
                    ✕ Reject
                  </button>
                </div>
              )}
            </div>
          );

          if (msg.type === 'system') return (
            <div key={i} className="msg-system">{msg.text}</div>
          );

          if (msg.type === 'error') return (
            <div key={i} className="msg-error">{msg.text}</div>
          );

          return null;
        })}

        {loading && (
          <div className="thinking">
            <span className="spinner" />
            AI is thinking...
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="chat-input-bar">
        <div className="chat-input-row">
          <input
            id="chat-command-input"
            className="input"
            placeholder="Explain this alert… or Generate a rule for…"
            value={command}
            onChange={e => setCommand(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button
            id="btn-send-command"
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={loading || !command.trim()}
          >
            Send
          </button>
        </div>
        <div className="chat-quick-actions">
          <button className="quick-btn" onClick={() => handleSend('Explain this alert')}>Explain this</button>
          <button className="quick-btn" onClick={() => handleSend('Generate a rule to detect this pattern')}>Generate rule</button>
          <button className="quick-btn" onClick={() => handleSend('Why was this flagged?')}>Why flagged?</button>
          <button className="quick-btn" onClick={() => handleSend('Flag similar transactions in future')}>Flag similar</button>
        </div>
      </div>
    </div>
  );
}
