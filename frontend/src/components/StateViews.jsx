/** Shared async page states: loading / error / empty. Never blank screens;
 * errors keep the backend request_id for diagnostics. */
export function StatusLine({ children }) {
  return (
    <p className="status-line" role="status" aria-live="polite">
      {children}
    </p>
  );
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  const message = error?.message || "Something went wrong.";
  return (
    <div className="error-box" role="alert">
      <strong>{message}</strong>
      {error.requestId ? (
        <small>
          Request ID: <code>{error.requestId}</code>
        </small>
      ) : null}
      {onRetry ? (
        <button type="button" className="retry-button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      {children}
    </div>
  );
}
