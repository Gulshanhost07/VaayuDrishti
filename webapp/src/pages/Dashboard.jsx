import React, { useEffect, useRef, useState } from "react";
import { Layout, Card, Spinner, toast, CategoryBadge, StatusBadge, SeverityBadge, CredBadge } from "../ui.jsx";
import { apiJson, fmtTime, wsURL, CATEGORY_LABELS } from "../api.js";
import { Timeseries, IndiaMap, BarList } from "../charts.jsx";

const EMPTY_FILTERS = { q: "", event_category: "", verification_status: "", state: "", source: "", date_from: "", date_to: "" };

function Kpi({ label, value, accent }) {
  return (
    <div className="kpi">
      <span className="kpi-dot" style={{ background: accent }} />
      <div className="kpi-body">
        <div className="kpi-value">{value}</div>
        <div className="kpi-label">{label}</div>
      </div>
    </div>
  );
}

function barRows(data, listKey, color) {
  const list = Array.isArray(data) ? data : data && Array.isArray(data[listKey]) ? data[listKey] : [];
  return list
    .slice(0, 8)
    .map((r) => ({
      label: String(r.category ?? r.state ?? r.source ?? r.tag ?? "-"),
      value: Number(r.count ?? r.n ?? 0),
      display: r.share_pct != null ? Number(r.share_pct).toFixed(1) + "%" : undefined,
      color,
    }));
}

function tsRows(times) {
  const agg = {};
  (times?.points || []).forEach((p) => {
    const k = p.bucket || p.t;
    if (k) agg[k] = (agg[k] || 0) + Number(p.count ?? p.n ?? 0);
  });
  return Object.entries(agg)
    .sort((a, b) => (a[0] < b[0] ? -1 : 1))
    .slice(-200)
    .map(([t, n]) => ({ t, n }));
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [options, setOptions] = useState({ states: [], sources: [], categories: [] });
  const [reports, setReports] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [ts, setTs] = useState([]);
  const [features, setFeatures] = useState([]);
  const [catRows, setCatRows] = useState([]);
  const [stateRows, setStateRows] = useState([]);
  const [sourceRows, setSourceRows] = useState([]);
  const [tagRows, setTagRows] = useState([]);
  const [live, setLive] = useState([]);
  const [wsState, setWsState] = useState("connecting");
  const wsRef = useRef(null);

  const query = (extra = {}, withQ = false) => {
    const p = new URLSearchParams();
    const put = (k, v) => {
      if (!v) return;
      if (k === "q") {
        if (withQ) p.set("q", v);
        return;
      }
      p.set(k === "event_category" ? "category" : k, v);
    };
    Object.entries(applied).forEach(([k, v]) => put(k, v));
    Object.entries(extra).forEach(([k, v]) => put(k, v));
    return p.toString();
  };

  const loadSummary = async () => {
    try {
      setSummary(await apiJson("/analytics/summary?" + query()));
    } catch (e) {
      toast("summary failed: " + e.message, true);
    }
  };

  const loadReports = async () => {
    try {
      const path = applied.q && applied.q.trim() ? "/reports/search?" : "/reports?";
      const data = await apiJson(path + "page=" + page + "&page_size=25&" + query({}, true));
      setReports(data.items || []);
      setTotalPages(data.meta?.pages ?? Math.max(1, Math.ceil((data.meta?.total || 0) / 25)));
    } catch (e) {
      toast("reports failed: " + e.message, true);
      setReports([]);
    }
  };

  const loadCharts = async () => {
    try {
      const [cat, st, src, tags, times, geo] = await Promise.all([
        apiJson("/analytics/by-category?" + query()),
        apiJson("/analytics/by-state?" + query()),
        apiJson("/analytics/by-source?" + query()),
        apiJson("/analytics/hashtags?" + query()),
        apiJson("/analytics/timeseries?bucket=hour&" + query()),
        apiJson("/geo/reports.geojson?" + query()),
      ]);
        setCatRows(barRows(cat, "categories", "#1d5bb8"));
        setStateRows(barRows(st, "states", "#0d376e"));
        setSourceRows(barRows(src, "sources", "#0070c0"));
        const tagList = Array.isArray(tags?.hashtags) ? tags.hashtags : Array.isArray(tags) ? tags : [];
        setTagRows(
          tagList.slice(0, 8).map((t) => ({
            label: String(t.tag || t.hashtag || t.name || "-"),
            value: Number(t.count ?? t.n ?? 0),
            color: "#8b5cf6",
          }))
        );
        setTs(tsRows(times));
      setFeatures((geo && geo.features) || []);
    } catch (e) {
      toast("charts failed: " + e.message, true);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const f = await apiJson("/analytics/filters");
        setOptions({
          states: f.states || [],
          sources: f.sources || [],
          categories: f.categories || Object.keys(CATEGORY_LABELS),
        });
      } catch (e) {
        setOptions({ states: [], sources: [], categories: Object.keys(CATEGORY_LABELS) });
      }
    })();
  }, []);

  useEffect(() => {
    loadSummary();
    loadCharts();
  }, [applied]);

  useEffect(() => {
    loadReports();
  }, [page, applied]);

  useEffect(() => {
    const a = setInterval(loadSummary, 60000);
    const b = setInterval(loadCharts, 120000);
    return () => {
      clearInterval(a);
      clearInterval(b);
    };
  }, [applied]);

  useEffect(() => {
    let closed = false;
    let retry = 1000;
    const connect = () => {
      try {
        const ws = new WebSocket(wsURL());
        wsRef.current = ws;
        ws.onopen = () => {
          if (!closed) {
            setWsState("live");
            retry = 1000;
          }
        };
        ws.onmessage = (m) => {
          try {
            const ev = JSON.parse(m.data);
            if (!ev || ev.type === "hello" || ev.type === "heartbeat") return;
            setLive((xs) => [{ ...ev, _at: Date.now() }, ...xs].slice(0, 30));
          } catch (e) {}
        };
        ws.onclose = () => {
          if (closed) return;
          setWsState("reconnecting");
          setTimeout(connect, retry);
          retry = Math.min(retry * 2, 15000);
        };
        ws.onerror = () => ws.close();
      } catch (e) {
        setWsState("reconnecting");
        setTimeout(connect, retry);
      }
    };
    connect();
    return () => {
      closed = true;
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const applyFilters = () => {
    setPage(1);
    setApplied({ ...filters });
  };

  const resetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setPage(1);
  };

  const setF = (k) => (ev) => setFilters((f) => ({ ...f, [k]: ev.target.value }));

  const openReport = (id) => {
    location.href = "report.html?id=" + encodeURIComponent(id);
  };

  return (
    <Layout>
      <div className="hero">
        <div>
          <div className="hero-eyebrow">National Weather Big Data Analytics Platform</div>
          <h1>VaayuDrishti</h1>
          <p>Ground truth, official bulletins and ML evidence for Indian weather events, unified in one operational view.</p>
        </div>
        <div className={"ws-chip " + wsState}>
          <span className="ws-dot" />
          {wsState === "live" ? "LIVE FEED" : wsState.toUpperCase()}
        </div>
      </div>

      <div className="kpi-grid">
        <Kpi label="Total reports" value={summary ? summary.total_reports ?? 0 : "..."} accent="#1d5bb8" />
        <Kpi label="Verified" value={summary ? summary.verified ?? 0 : "..."} accent="#16a34a" />
        <Kpi label="Pending" value={summary ? summary.pending ?? 0 : "..."} accent="#f59e0b" />
        <Kpi label="States covered" value={summary ? summary.states_covered ?? 0 : "..."} accent="#8b5cf6" />
        <Kpi label="Last 24 hours" value={summary ? summary.reports_last_24h ?? 0 : "..."} accent="#06b6d4" />
      </div>

      <Card title="Filters">
        <div className="filters">
          <input placeholder="Search text..." value={filters.q} onChange={setF("q")} />
          <select value={filters.event_category} onChange={setF("event_category")}>
            <option value="">All categories</option>
            {options.categories.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>)}
          </select>
          <select value={filters.verification_status} onChange={setF("verification_status")}>
            <option value="">Any status</option>
            <option value="pending">pending</option>
            <option value="verified">verified</option>
            <option value="rejected">rejected</option>
            <option value="disputed">disputed</option>
          </select>
          <select value={filters.state} onChange={setF("state")}>
            <option value="">All states</option>
            {options.states.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={filters.source} onChange={setF("source")}>
            <option value="">All sources</option>
            {options.sources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input type="date" value={filters.date_from} onChange={setF("date_from")} />
          <input type="date" value={filters.date_to} onChange={setF("date_to")} />
          <div className="filter-actions">
            <button className="btn primary" onClick={applyFilters}>Apply</button>
            <button className="btn ghost" onClick={resetFilters}>Reset</button>
          </div>
        </div>
      </Card>

      <div className="grid-2">
        <Card title="Reports">
          {!reports ? <Spinner /> : reports.length === 0 ? <div className="empty">No reports match the current filters</div> : (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr><th>Time</th><th>Category</th><th>Place</th><th>Status</th><th>Confidence</th></tr>
                </thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} onClick={() => openReport(r.id)}>
                      <td className="nowrap">{fmtTime(r.observed_at || r.created_at)}</td>
                      <td><CategoryBadge value={r.event_category} /></td>
                      <td className="cell-city">{r.city || r.state || "-"}</td>
                      <td><StatusBadge value={r.verification_status} /></td>
                      <td><CredBadge value={r.confidence ?? r.credibility_score} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="pager">
            <button className="btn sm ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
            <span className="muted">page {page} / {totalPages}</span>
            <button className="btn sm ghost" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </Card>

        <Card title="Report volume (hourly)">
          <Timeseries points={ts} />
        </Card>
      </div>

      <div className="grid-2">
        <Card title="Geo view" className="map-card">
          <IndiaMap features={features} onPick={openReport} />
          <div className="muted tiny">Click a dot to open the report</div>
        </Card>

        <Card title="Live feed">
          <div className="live">
            {live.length === 0 && <div className="empty">Waiting for live events...</div>}
            {live.map((ev, i) => (
              <div className={"live-item" + (Date.now() - ev._at < 4000 ? " fresh" : "")} key={ev._at + "-" + i}>
                <div className="live-row">
                  <CategoryBadge value={ev.event_category || ev.category} />
                  <span className="live-time">{fmtTime(ev.observed_at || ev.ts || ev.time)}</span>
                </div>
                <div className="live-text">{ev.text || ev.summary || ev.city || JSON.stringify(ev).slice(0, 120)}</div>
                <div className="live-meta">{ev.city || ""} {ev.state ? "· " + ev.state : ""} {ev.source ? "· " + ev.source : ""}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid-3">
        <Card title="By category"><BarList rows={catRows} /></Card>
        <Card title="Top states"><BarList rows={stateRows} /></Card>
        <Card title="By source"><BarList rows={sourceRows} /></Card>
      </div>

      <Card title="Top hashtags"><BarList rows={tagRows} empty="No hashtags yet" /></Card>
    </Layout>
  );
}
