// frontend/src/components/ProfileBuilderModal.jsx
// Custom Profile Builder Modal → POST /profiles

import { useState } from 'react';
import { createProfile } from '../api';
import './ProfileBuilderModal.css';

const LOCATION_OPTIONS = ['new_device', 'foreign_ip', 'atm', 'online', 'any'];

export default function ProfileBuilderModal({ onClose, onCreated }) {
  const [name, setName]             = useState('');
  const [minAmount, setMinAmount]   = useState('');
  const [maxAmount, setMaxAmount]   = useState('');
  const [location, setLocation]     = useState('any');
  const [txnRate, setTxnRate]       = useState('5');
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [created, setCreated]       = useState(null);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) { setError('Profile name is required.'); return; }
    setError('');
    setLoading(true);
    try {
      const rules = {
        amount_range: [
          minAmount ? parseFloat(minAmount) : 0,
          maxAmount ? parseFloat(maxAmount) : 999999,
        ],
        location: location === 'any' ? null : location,
        txn_per_minute: parseInt(txnRate, 10) || 5,
      };
      const res = await createProfile(name.trim(), rules);
      setCreated(res.profile_id);
      onCreated?.(res.profile_id, name.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal profile-modal">
        {!created ? (
          <>
            <div className="modal-title">Custom Simulator Profile</div>
            <div className="modal-subtitle">
              Define a transaction pattern for the simulator to generate.
            </div>

            <form onSubmit={handleCreate} className="profile-form">
              <div className="field">
                <label className="field-label">Profile name</label>
                <input
                  id="profile-name-input"
                  className="input"
                  placeholder="e.g. High-value foreign transactions"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="field-row">
                <div className="field">
                  <label className="field-label">Min amount (₹)</label>
                  <input
                    id="profile-min-amount"
                    className="input"
                    type="number"
                    placeholder="0"
                    value={minAmount}
                    onChange={e => setMinAmount(e.target.value)}
                    min="0"
                  />
                </div>
                <div className="field">
                  <label className="field-label">Max amount (₹)</label>
                  <input
                    id="profile-max-amount"
                    className="input"
                    type="number"
                    placeholder="999,999"
                    value={maxAmount}
                    onChange={e => setMaxAmount(e.target.value)}
                    min="0"
                  />
                </div>
              </div>

              <div className="field">
                <label className="field-label">Transaction location</label>
                <select
                  id="profile-location-select"
                  className="input"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                >
                  {LOCATION_OPTIONS.map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label className="field-label">
                  Transactions per minute: <strong>{txnRate}</strong>
                </label>
                <input
                  id="profile-txn-rate"
                  type="range"
                  min="1" max="30"
                  value={txnRate}
                  onChange={e => setTxnRate(e.target.value)}
                  className="range-input"
                />
                <div className="range-labels"><span>1</span><span>30</span></div>
              </div>

              {error && <div className="profile-error">{error}</div>}

              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
                <button
                  id="btn-create-profile"
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? <><span className="spinner" /> Creating...</> : 'Create profile'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="profile-success">
            <div className="success-icon">✓</div>
            <div className="modal-title">Profile created</div>
            <div className="profile-id font-mono">{created}</div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
              The simulator will use this profile on next start.
            </p>
            <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={onClose}>
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
