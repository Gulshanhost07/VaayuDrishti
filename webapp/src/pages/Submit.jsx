import React, { useState } from "react";
import { Layout, Card, toast, CategoryBadge, StatusBadge } from "../ui.jsx";
import { V1, CATEGORY_LABELS, apiJson, fmtTime } from "../api.js";

const CATEGORIES = Object.keys(CATEGORY_LABELS);

export default function Submit() {
  const [form, setForm] = useState({
    text: "",
    city: "",
    state: "",
    latitude: "",
    longitude: "",
    event_category: "rainfall",
    severity: "moderate",
  });
  const [file, setFile] = useState(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [trackId, setTrackId] = useState("");
  const [tracked, setTracked] = useState(null);
  const [tracking, setTracking] = useState(false);

  const set = (k) => (ev) => setForm((f) => ({ ...f, [k]: ev.target.value }));

  const locate = () => {
    if (!navigator.geolocation) {
      toast("geolocation is not available in this browser", true);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setForm((f) => ({ ...f, latitude: pos.coords.latitude.toFixed(4), longitude: pos.coords.longitude.toFixed(4) })),
      () => toast("could not read your location", true)
    );
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!form.text.trim()) {
      toast("describe what you observed", true);
      return;
    }
    setSending(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => v !== "" && fd.append(k, v));
      if (file) fd.append("file", file);
      const res = await fetch(V1 + "/citizen/reports", { method: "POST", body: fd });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail) || res.status);
      }
      const data = await res.json();
      setResult(data);
      toast("report submitted");
      setForm({ text: "", city: "", state: "", latitude: "", longitude: "", event_category: "rainfall", severity: "moderate" });
      setFile(null);
    } catch (e) {
      toast("submit failed: " + e.message, true);
    } finally {
      setSending(false);
    }
  };

  const track = async (ev) => {
    ev.preventDefault();
    if (!trackId.trim()) return;
    setTracking(true);
    try {
      setTracked(await apiJson("/reports/track/" + encodeURIComponent(trackId.trim())));
    } catch (e) {
      setTracked(null);
      toast("not found: " + e.message, true);
    } finally {
      setTracking(false);
    }
  };

  return (
    <Layout>
      <div className="page-head">
        <h1>Submit a weather report</h1>
        <p className="muted">Ground truth from citizens feeds verification, ML training and the operational dashboard. No account needed.</p>
      </div>

      <div className="grid-2">
        <Card title="New report">
          <form className="form" onSubmit={submit}>
            <label className="field">
              <span>What did you observe?</span>
              <textarea rows="4" placeholder="Heavy rain since morning, waterlogging on the highway..." value={form.text} onChange={set("text")} />
            </label>
            <div className="form-row">
              <label className="field">
                <span>City / district</span>
                <input value={form.city} onChange={set("city")} placeholder="Pune" />
              </label>
              <label className="field">
                <span>State</span>
                <input value={form.state} onChange={set("state")} placeholder="Maharashtra" />
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span>Category</span>
                <select value={form.event_category} onChange={set("event_category")}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Severity</span>
                <select value={form.severity} onChange={set("severity")}>
                  <option value="mild">mild</option>
                  <option value="moderate">moderate</option>
                  <option value="severe">severe</option>
                  <option value="extreme">extreme</option>
                </select>
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span>Latitude</span>
                <input value={form.latitude} onChange={set("latitude")} placeholder="18.5204" />
              </label>
              <label className="field">
                <span>Longitude</span>
                <input value={form.longitude} onChange={set("longitude")} placeholder="73.8567" />
              </label>
            </div>
            <div className="form-actions">
              <button type="button" className="btn ghost" onClick={locate}>Use my location</button>
              <label className="btn ghost file-btn">
                {file ? file.name : "Attach photo"}
                <input type="file" accept="image/*" hidden onChange={(e) => setFile(e.target.files[0] || null)} />
              </label>
            </div>
            <button className="btn primary big" disabled={sending}>{sending ? "Submitting..." : "Submit report"}</button>
          </form>

          {result && (
            <div className="result">
              <div className="result-title">Received with status {result.status}.</div>
              <code>{result.id}</code>
              {result.token && <div className="muted tiny">tracking token {result.token}</div>}
              <a className="btn ghost sm" href={"report.html?id=" + encodeURIComponent(result.id)}>View report</a>
            </div>
          )}
        </Card>

        <Card title="Track a report">
          <form className="form inline" onSubmit={track}>
            <input value={trackId} onChange={(e) => setTrackId(e.target.value)} placeholder="tracking token from your submission" />
            <button className="btn primary" disabled={tracking}>{tracking ? "..." : "Track"}</button>
          </form>

          {tracked && (
            <div className="track-result">
              <div className="live-row">
                <CategoryBadge value={tracked.event_category} />
                <StatusBadge value={tracked.verification_status} />
              </div>
              <div className="muted tiny">
                {[tracked.city, tracked.state].filter(Boolean).join(", ")} · observed {fmtTime(tracked.observed_at)}
              </div>
              {tracked.verification_note && <div className="track-note">{tracked.verification_note}</div>}
            </div>
          )}

          <div className="how">
            <h3>How it works</h3>
            <ol>
              <li>Your observation is stored and geocoded.</li>
              <li>ML checks language, category and image evidence.</li>
              <li>IMD verification is tracked on the report page.</li>
            </ol>
          </div>
        </Card>
      </div>
    </Layout>
  );
}
