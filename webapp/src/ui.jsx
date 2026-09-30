import React, { useEffect, useState } from "react";
import { CATEGORY_COLORS, SEVERITY_COLORS, statusColor } from "./api.js";
import moesLogo from "./assets/moes_logo.jpg";
import imdLogo from "./assets/imd_logo_a.webp";

export function toast(msg, isErr = false) {
  window.dispatchEvent(new CustomEvent("vaayu-toast", { detail: { msg, isErr } }));
}

export function ToastHost() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    let seq = 0;
    const onToast = (ev) => {
      const id = ++seq;
      setItems((xs) => [...xs, { id, ...ev.detail }]);
      setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 4000);
    };
    window.addEventListener("vaayu-toast", onToast);
    return () => window.removeEventListener("vaayu-toast", onToast);
  }, []);
  return (
    <div className="toasts">
      {items.map((t) => (
        <div key={t.id} className={"toast" + (t.isErr ? " err" : "")}>{t.msg}</div>
      ))}
    </div>
  );
}

export function Badge({ children, color }) {
  return (
    <span className="badge" style={{ background: color || "#64748b" }}>{children}</span>
  );
}

export function CategoryBadge({ value }) {
  return <Badge color={CATEGORY_COLORS[value] || CATEGORY_COLORS.other}>{value || "other"}</Badge>;
}

export function StatusBadge({ value }) {
  return <Badge color={statusColor(value)}>{value || "pending"}</Badge>;
}

export function SeverityBadge({ value }) {
  return <Badge color={SEVERITY_COLORS[value] || SEVERITY_COLORS.unknown}>{value || "unknown"}</Badge>;
}

export function CredBadge({ value }) {
  if (value == null) return <span className="muted">-</span>;
  const s = Number(value);
  const color = s >= 0.7 ? "#16a34a" : s >= 0.4 ? "#f59e0b" : "#dc2626";
  return <Badge color={color}>{s.toFixed(2)}</Badge>;
}

const NAV = [
  { href: "index.html", label: "Dashboard", match: ["index", "/"] },
  { href: "submit.html", label: "Submit report", match: ["submit"] },
  { href: "admin.html", label: "Admin", match: ["admin"] },
];

export function Layout({ children }) {
  const path = location.pathname;
  const active = (m) => m.some((x) => path.endsWith(x) || path === x);
  return (
    <div className="app">
      <div className="tricolor" />
      <header className="site-header">
        <div className="wrap header-inner">
          <a className="brand" href="index.html">
            <img className="brand-logo" src={moesLogo} alt="Ministry of Earth Sciences" />
            <span className="brand-text">
              <strong>VaayuDrishti</strong>
              <small>National Weather Big Data Analytics Platform</small>
            </span>
          </a>
          <nav className="nav">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className={active(n.match) ? "active" : ""}>{n.label}</a>
            ))}
          </nav>
        </div>
      </header>
      <main className="wrap page">{children}</main>
      <footer className="site-footer">
        <div className="wrap footer-inner">
          <div className="footer-brand">
            <img className="footer-logo" src={imdLogo} alt="India Meteorological Department" />
            <div>
              <div className="footer-title">India Meteorological Department</div>
              <div className="footer-sub">Ministry of Earth Sciences, Government of India</div>
            </div>
          </div>
          <div className="footer-meta">
            <span>Problem statement SIH26069</span>
            <span className="dot">·</span>
            <span>Team TechnCrew · 148709</span>
            <span className="dot">·</span>
            <a href="https://github.com/Gulshanhost07/VaayuDrishti" target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </div>
      </footer>
      <ToastHost />
    </div>
  );
}

export function Card({ title, extra, children, className = "" }) {
  return (
    <section className={"card " + className}>
      {(title || extra) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {extra && <div className="card-extra">{extra}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Spinner() {
  return <div className="empty">Loading...</div>;
}
