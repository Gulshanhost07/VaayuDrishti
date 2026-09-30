import React, { useEffect, useState } from "react";
import { Layout, Card, Spinner, toast, CategoryBadge, StatusBadge, SeverityBadge, CredBadge } from "../ui.jsx";
import { apiJson, V1, fmtTime, qs, CATEGORY_LABELS } from "../api.js";

function Detail({ label, value }) {
  return (
    <div className="detail">
      <div className="detail-label">{label}</div>
      <div className="detail-value">{value == null || value === "" ? "-" : String(value)}</div>
    </div>
  );
}

export default function Report() {
  const id = qs("id");
  const [report, setReport] = useState(undefined);

  useEffect(() => {
    if (!id) {
      setReport(null);
      return;
    }
    apiJson("/reports/" + encodeURIComponent(id))
      .then(setReport)
      .catch((e) => {
        setReport(null);
        toast("failed to load report: " + e.message, true);
      });
  }, [id]);

  if (!id) {
    return (
      <Layout>
        <Card title="Report not found">
          <div className="empty">No report id in the URL. Open a report from the dashboard.</div>
          <a className="btn primary" href="index.html">Back to dashboard</a>
        </Card>
      </Layout>
    );
  }

  if (report === undefined) {
    return (
      <Layout>
        <Spinner />
      </Layout>
    );
  }

  if (report === null) {
    return (
      <Layout>
        <Card title="Report unavailable">
          <div className="empty">This report could not be loaded. It may have been removed.</div>
          <a className="btn primary" href="index.html">Back to dashboard</a>
        </Card>
      </Layout>
    );
  }

  const media = report.media || [];
  const sourceUrl = report.source_url || (report.source === "mastodon" ? report.url : "");
  const plaus = report.plausibility || {};

  return (
    <Layout>
      <div className="report-head">
        <div className="report-badges">
          <CategoryBadge value={report.event_category} />
          <StatusBadge value={report.verification_status} />
          <SeverityBadge value={report.severity} />
          <CredBadge value={report.confidence} />
        </div>
        <h1>{CATEGORY_LABELS[report.event_category] || report.event_category || "Report"}</h1>
        <div className="report-sub">
          {report.city || ""} {report.district && report.district !== report.city ? "· " + report.district : ""} {report.state ? "· " + report.state : ""} · observed {fmtTime(report.observed_at)}
        </div>
      </div>

      <div className="grid-2">
        <Card title="Report">
          <p className="report-text">{report.text || "No description provided."}</p>
          {sourceUrl && (
            <a className="btn ghost sm" href={sourceUrl} target="_blank" rel="noreferrer">Open original source</a>
          )}
          <div className="details">
            <Detail label="Report ID" value={report.id} />
            <Detail label="Source" value={report.source} />
            <Detail label="Latitude" value={report.lat} />
            <Detail label="Longitude" value={report.lon} />
            <Detail label="Place" value={[report.city, report.district, report.state].filter(Boolean).join(", ")} />
            <Detail label="Observed" value={fmtTime(report.observed_at)} />
            <Detail label="Ingested" value={fmtTime(report.ingested_at)} />
            <Detail label="Language" value={report.lang} />
            <Detail label="Duplicate" value={report.is_duplicate ? "yes" + (report.duplicate_of ? " of " + report.duplicate_of : "") : "no"} />
            <Detail label="Verification note" value={report.verification_note} />
          </div>
        </Card>

        <div className="stack">
          {media.length > 0 && (
            <Card title="Media">
              <div className="media-grid">
                {media.map((m) => (
                  <img
                    key={m.key || m}
                    src={V1 + "/reports/" + encodeURIComponent(report.id) + "/media/" + encodeURIComponent(m.key || m)}
                    alt="report media"
                  />
                ))}
              </div>
            </Card>
          )}

          <Card title="Evidence">
            <div className="ml">
              <Detail label="ML confidence" value={report.confidence != null ? Number(report.confidence).toFixed(3) : null} />
              <Detail label="Credibility" value={report.credibility_score != null ? Number(report.credibility_score).toFixed(3) : null} />
              <Detail label="Plausibility" value={plaus.checked == null ? null : plaus.checked ? "checked" : plaus.reason || "unchecked"} />
              <Detail label="Model" value="weather-bert-v1" />
            </div>
            {report.credibility_features && Object.keys(report.credibility_features).length > 0 && (
              <details className="features">
                <summary>Credibility features</summary>
                <pre className="json">{JSON.stringify(report.credibility_features, null, 2)}</pre>
              </details>
            )}
          </Card>

          {report.hashtags && report.hashtags.length > 0 && (
            <Card title="Hashtags">
              <div className="report-badges">
                {report.hashtags.map((h) => <span className="tag" key={h}>{h}</span>)}
              </div>
            </Card>
          )}
        </div>
      </div>

      <Card title="Raw record (JSON)">
        <pre className="json">{JSON.stringify(report, null, 2)}</pre>
      </Card>
    </Layout>
  );
}
