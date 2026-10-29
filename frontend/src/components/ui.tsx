import type { ReactNode } from "react";

export function StatTile({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export function Card({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="subtitle">{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export interface TooltipRow {
  name: string;
  value: string;
  color?: string;
  dashed?: boolean;
}

export function TooltipBox({ title, rows }: { title: string; rows: TooltipRow[] }) {
  return (
    <div className="tooltip">
      <div className="title">{title}</div>
      {rows.map((r) => (
        <div className="row" key={r.name}>
          {r.color && <span className={`key-line${r.dashed ? " dashed" : ""}`} style={{ borderColor: r.color }} />}
          <strong>{r.value}</strong>
          <span className="name">{r.name}</span>
        </div>
      ))}
    </div>
  );
}

/** A collapsible plain table so every charted value is reachable without hovering. */
export function TableView({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  return (
    <details className="table-view">
      <summary>Show data table</summary>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function Status({ error, children }: { error?: boolean; children: ReactNode }) {
  return <div className={`status${error ? " error" : ""}`} role={error ? "alert" : "status"}>{children}</div>;
}
