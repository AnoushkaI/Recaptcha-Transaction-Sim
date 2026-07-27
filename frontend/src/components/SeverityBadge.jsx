// frontend/src/components/SeverityBadge.jsx
// Reusable severity badge — used by AlertRow and ChatPanel

export default function SeverityBadge({ severity }) {
  const cls = {
    high:   'badge badge-high',
    medium: 'badge badge-medium',
    low:    'badge badge-low',
  }[severity] ?? 'badge badge-low';

  return (
    <span className={cls}>
      <span className="badge-dot" />
      {severity}
    </span>
  );
}
