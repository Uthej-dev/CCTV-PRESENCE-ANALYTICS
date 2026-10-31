// Small presentational building blocks shared across pages
export const Spinner = () => <div className="spinner" role="status" aria-label="Loading" />;

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="toolbar">{children}</div>}
    </div>
  );
}

export function Card({ title, subtitle, actions, children, flush, className = "" }) {
  return (
    <section className={`card ${flush ? "flush" : ""} ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, sub, live }) {
  return (
    <div className="card">
      <div className="stat-label">
        {live && <span className="live-dot" aria-hidden="true" />}
        {label}
      </div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

const STATUS_LABEL = { running: "Running", idle: "Idle", error: "Error", starting: "Starting", inactive: "Inactive" };

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABEL[status] || status}</span>;
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <div>{children}</div>
      {action}
    </div>
  );
}

export function ErrorAlert({ error }) {
  if (!error) return null;
  return <div className="alert alert-error" role="alert">{error}</div>;
}

export function Pagination({ skip, limit, total, onChange }) {
  const page = Math.floor(skip / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <div className="pagination">
      <span>
        {total === 0 ? "No results" : `${skip + 1}–${Math.min(skip + limit, total)} of ${total.toLocaleString()}`}
      </span>
      <div className="row">
        <button className="btn btn-sm" disabled={page <= 1} onClick={() => onChange(skip - limit)}>Previous</button>
        <span>Page {page} of {pages}</span>
        <button className="btn btn-sm" disabled={page >= pages} onClick={() => onChange(skip + limit)}>Next</button>
      </div>
    </div>
  );
}
