import React, { useEffect, useState } from "react";
import { Layout, Card, Spinner, toast, CategoryBadge, StatusBadge } from "../ui.jsx";
import { api, apiJson, V1, fmtTime, CATEGORY_LABELS } from "../api.js";

const TABS = ["Queue", "Pipeline", "Sources", "Audit", "Export"];

function Login({ onDone }) {
  const [email, setEmail] = useState("admin@vaayu.local");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (ev) => {
    ev.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(V1 + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("invalid credentials");
      const data = await res.json();
      localStorage.setItem("vaayu_access", data.access_token);
      localStorage.setItem("vaayu_refresh", data.refresh_token);
      localStorage.setItem("vaayu_role", data.role);
      localStorage.setItem("vaayu_email", data.email || email);
      toast("signed in as " + (data.email || email));
      onDone();
    } catch (e) {
      toast(e.message, true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <Card className="login-card" title="Admin console">
        <p className="muted">Restricted to IMD / MoES operators. Actions are written to the audit log.</p>
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span>Email</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="vaayu@123" />
          </label>
          <button className="btn primary big" disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
        </form>
      </Card>
    </div>
  );
}

const QUEUE_INITIAL = { verification_status: "pending", category: "", state: "", source: "", date_from: "", date_to: "" };

function Queue() {
  const [rows, setRows] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sel, setSel] = useState({});
  const [f, setF] = useState(QUEUE_INITIAL);
  const [applied, setApplied] = useState(QUEUE_INITIAL);

  useEffect(() => {
    (async () => {
      try {
        const p = new URLSearchParams({ page: String(page), page_size: "25" });
        Object.entries(applied).forEach(([k, v]) => v && p.set(k, v));
        const data = await apiJson("/admin/reports?" + p.toString());
        setRows(data.items || []);
        setTotal(data.meta?.total || 0);
        setSel({});
      } catch (e) {
        setRows([]);
        toast(e.message, true);
      }
    })();
  }, [page, applied]);

  const setFld = (k) => (ev) => setF((x) => ({ ...x, [k]: ev.target.value }));

  const act = async (ids, status) => {
    if (!ids.length) return;
    try {
      const out = await apiJson("/admin/reports/bulk-verification", {
        method: "POST",
        body: JSON.stringify({ ids, status }),
      });
      toast((out.updated ?? ids.length) + " report(s) → " + status);
      setRows((xs) => (xs || []).filter((r) => !ids.includes(r.id)));
      setTotal((t) => Math.max(0, t - ids.length));
      setSel({});
    } catch (e) {
      toast(e.message, true);
    }
  };

  const selected = Object.keys(sel).filter((k) => sel[k]);
  const totalPages = Math.max(1, Math.ceil(total / 25));

  return (
    <div className="stack">
      <div className="filters compact">
        <select value={f.verification_status} onChange={setFld("verification_status")}>
          <option value="pending">pending</option>
          <option value="verified">verified</option>
          <option value="rejected">rejected</option>
          <option value="disputed">disputed</option>
        </select>
        <select value={f.category} onChange={setFld("category")}>
          <option value="">any category</option>
          {Object.keys(CATEGORY_LABELS).map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
        </select>
        <input placeholder="state" value={f.state} onChange={setFld("state")} />
        <input placeholder="source" value={f.source} onChange={setFld("source")} />
        <input type="date" value={f.date_from} onChange={setFld("date_from")} />
        <input type="date" value={f.date_to} onChange={setFld("date_to")} />
        <button className="btn primary sm" onClick={() => { setPage(1); setApplied({ ...f }); }}>Apply</button>
        <button className="btn ghost sm" onClick={() => { setF(QUEUE_INITIAL); setPage(1); setApplied({ ...QUEUE_INITIAL }); }}>Reset</button>
      </div>

      <div className="bulkbar">
        <span className="muted">{selected.length} selected</span>
        <button className="btn sm green" disabled={!selected.length} onClick={() => act(selected, "verified")}>Verify</button>
        <button className="btn sm red" disabled={!selected.length} onClick={() => act(selected, "rejected")}>Reject</button>
        <button className="btn sm amber" disabled={!selected.length} onClick={() => act(selected, "disputed")}>Dispute</button>
      </div>

      {!rows ? <Spinner /> : rows.length === 0 ? <div className="empty">Queue is empty</div> : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th><input type="checkbox" checked={selected.length === rows.length && rows.length > 0} onChange={(e) => setSel(e.target.checked ? Object.fromEntries(rows.map((r) => [r.id, true])) : {})} /></th>
                <th>Time</th><th>Category</th><th>Place</th><th>Status</th><th>Source</th><th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td><input type="checkbox" checked={!!sel[r.id]} onChange={(e) => setSel((s) => ({ ...s, [r.id]: e.target.checked }))} /></td>
                  <td className="nowrap">{fmtTime(r.observed_at || r.created_at)}</td>
                  <td><CategoryBadge value={r.event_category} /></td>
                  <td className="cell-city">{r.city || r.state || "-"}</td>
                  <td><StatusBadge value={r.verification_status} /></td>
                  <td>{r.source}</td>
                  <td className="nowrap actions">
                    <button className="btn sm green" onClick={() => act([r.id], "verified")}>V</button>
                    <button className="btn sm red" onClick={() => act([r.id], "rejected")}>R</button>
                    <button className="btn sm amber" onClick={() => act([r.id], "disputed")}>D</button>
                    <a className="btn sm ghost" href={"report.html?id=" + encodeURIComponent(r.id)}>open</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pager">
        <button className="btn sm ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
        <span className="muted">page {page} / {totalPages} · {total} reports</span>
        <button className="btn sm ghost" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}

function Pipeline() {
  const [data, setData] = useState(null);

  const load = async () => {
    try {
      setData(await apiJson("/admin/pipeline"));
    } catch (e) {
      toast(e.message, true);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (!data) return <Spinner />;

  const counters = data.counters || {};
  const kafka = data.kafka || {};
  const lag = kafka.lag || {};
  const runs = data.recent_runs || [];

  return (
    <div className="stack">
      <div className="kpi-grid">
        {Object.entries(counters).slice(0, 6).map(([k, v]) => (
          <div className="kpi" key={k}>
            <span className="kpi-dot" style={{ background: "#1d5bb8" }} />
            <div className="kpi-body">
              <div className="kpi-value">{Number(v).toLocaleString()}</div>
              <div className="kpi-label">{k.replace(/_/g, " ")}</div>
            </div>
          </div>
        ))}
        <div className="kpi">
          <span className="kpi-dot" style={{ background: kafka.available ? "#16a34a" : "#dc2626" }} />
          <div className="kpi-body">
            <div className="kpi-value">{kafka.available ? Number(kafka.sum ?? 0).toLocaleString() : "n/a"}</div>
            <div className="kpi-label">consumer lag</div>
          </div>
        </div>
      </div>

      <Card title="Consumer lag">
        {!kafka.available ? (
          <div className="empty">kafka unavailable{data.kafka?.error ? ": " + data.kafka.error : ""}</div>
        ) : Object.keys(lag).length === 0 ? (
          <div className="empty">all consumer groups at zero lag</div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Consumer group</th><th>Lag</th></tr></thead>
              <tbody>
                {Object.entries(lag).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td><span className="badge" style={{ background: Number(v) > 1000 ? "#dc2626" : "#16a34a" }}>{String(v)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Recent ingest runs">
        {runs.length === 0 ? <div className="empty">no runs yet</div> : (
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Source</th><th>Status</th><th>Fetched</th><th>Published</th><th>Errors</th><th>Started</th></tr></thead>
              <tbody>
                {runs.map((r, i) => (
                  <tr key={i}>
                    <td>{r.source}</td>
                    <td><span className="badge" style={{ background: ["succeeded", "success", "ok"].includes(r.status) ? "#16a34a" : ["failed", "error"].includes(r.status) ? "#dc2626" : r.status === "running" ? "#1d5bb8" : "#f59e0b" }}>{r.status}</span></td>
                    <td>{r.fetched ?? 0}</td>
                    <td>{r.published ?? 0}</td>
                    <td>{r.errors ?? 0}</td>
                    <td className="nowrap">{fmtTime(r.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function Sources() {
  const [rows, setRows] = useState(null);
  const [edit, setEdit] = useState(null);

  const load = async () => {
    try {
      const data = await apiJson("/admin/sources");
      setRows(Array.isArray(data) ? data : data.sources || data.items || []);
    } catch (e) {
      setRows([]);
      toast(e.message, true);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (name, patch) => {
    try {
      await apiJson("/admin/sources/" + encodeURIComponent(name), {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      toast(name + " updated");
      setEdit(null);
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  if (!rows) return <Spinner />;

  return (
    <Card title="Ingest sources">
      {rows.length === 0 ? <div className="empty">no sources registered</div> : (
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Name</th><th>Enabled</th><th>Interval</th><th>Updated</th><th></th></tr></thead>
            <tbody>
              {rows.map((s) => {
                const name = s.name || s.source;
                const isEdit = !!edit && edit.name === name;
                return (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>
                      <input
                        type="checkbox"
                        checked={isEdit ? !!edit._enabled : !!s.enabled}
                        onChange={(e) => {
                          const on = e.target.checked;
                          setEdit((prev) =>
                            prev && prev.name === name
                              ? { ...prev, _enabled: on }
                              : { name, _enabled: on, interval: s.interval_seconds ?? s.interval ?? 300 }
                          );
                        }}
                      />
                    </td>
                    <td>
                      {isEdit ? (
                        <input
                          className="inline-input"
                          type="number"
                          min="30"
                          value={edit.interval}
                          onChange={(e) => setEdit({ ...edit, interval: Number(e.target.value) })}
                        />
                      ) : (s.interval_seconds ?? s.interval ?? "-") + "s"}
                    </td>
                    <td>{fmtTime(s.updated_at)}</td>
                    <td className="nowrap actions">
                      {isEdit ? (
                        <>
                          <button className="btn sm green" onClick={() => save(name, { enabled: edit._enabled, interval_seconds: Number(edit.interval) })}>Save</button>
                          <button className="btn sm ghost" onClick={() => setEdit(null)}>Cancel</button>
                        </>
                      ) : (
                        <button className="btn sm ghost" onClick={() => setEdit({ name, _enabled: !!s.enabled, interval: s.interval_seconds ?? s.interval ?? 300 })}>Edit</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Audit() {
  const [rows, setRows] = useState(null);
  const [action, setAction] = useState("");

  const load = async () => {
    try {
      const data = await apiJson("/admin/audit?limit=100" + (action ? "&action=" + encodeURIComponent(action) : ""));
      setRows(Array.isArray(data) ? data : data.entries || data.items || []);
    } catch (e) {
      setRows([]);
      toast(e.message, true);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (!rows) return <Spinner />;

  return (
    <Card title="Audit log">
      <div className="filters compact">
        <input placeholder="action filter, e.g. verification.update" value={action} onChange={(e) => setAction(e.target.value)} />
        <button className="btn primary sm" onClick={load}>Load</button>
      </div>
      {rows.length === 0 ? <div className="empty">no audit entries</div> : (
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="nowrap">{fmtTime(r.created_at || r.at)}</td>
                  <td>{r.user_id || r.actor || "-"}</td>
                  <td><code>{r.action}</code></td>
                  <td className="cell-city">{[r.entity, r.entity_id].filter(Boolean).join(" · ") || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ExportPanel() {
  const [format, setFormat] = useState("csv");
  const [limit, setLimit] = useState(1000);

  const run = async () => {
    try {
      const res = await api("/admin/export?format=" + format + "&limit=" + limit);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "vaayudrishti-export." + format;
      a.click();
      URL.revokeObjectURL(a.href);
      toast("export downloaded");
    } catch (e) {
      toast("export failed: " + e.message, true);
    }
  };

  return (
    <Card title="Export">
      <p className="muted">Download report data for offline analysis, briefings or IMD archives.</p>
      <div className="filters compact">
        <select value={format} onChange={(e) => setFormat(e.target.value)}>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
        </select>
        <input type="number" value={limit} min="10" max="100000" onChange={(e) => setLimit(Number(e.target.value))} />
        <button className="btn primary sm" onClick={run}>Download</button>
      </div>
    </Card>
  );
}

function Console() {
  const initial = (location.hash || "").replace("#", "").toLowerCase();
  const [tab, setTab] = useState(() => TABS.find((t) => t.toLowerCase() === initial) || "Queue");
  const switchTab = (t) => {
    setTab(t);
    history.replaceState(null, "", "#" + t.toLowerCase());
  };
  const logout = () => {
    ["vaayu_access", "vaayu_refresh", "vaayu_role", "vaayu_email"].forEach((k) => localStorage.removeItem(k));
    location.reload();
  };

  return (
    <div className="stack">
      <div className="console-head">
        <div>
          <h1>Admin console</h1>
          <div className="muted">signed in as {localStorage.getItem("vaayu_email") || "operator"} · {localStorage.getItem("vaayu_role")}</div>
        </div>
        <button className="btn ghost" onClick={logout}>Sign out</button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => switchTab(t)}>{t}</button>
        ))}
      </div>

      {tab === "Queue" && <Queue />}
      {tab === "Pipeline" && <Pipeline />}
      {tab === "Sources" && <Sources />}
      {tab === "Audit" && <Audit />}
      {tab === "Export" && <ExportPanel />}
    </div>
  );
}

export default function Admin() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem("vaayu_access"));

  useEffect(() => {
    if (!authed) return;
    api("/auth/me")
      .then((res) => {
        if (res.status === 401 || res.status === 403) setAuthed(false);
      })
      .catch(() => {});
  }, []);

  return <Layout>{authed ? <Console /> : <Login onDone={() => setAuthed(true)} />}</Layout>;
}
