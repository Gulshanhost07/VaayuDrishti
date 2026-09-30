const id = qs("id");
const root = document.getElementById("content");

function field(k, v) {
  return '<div><div class="k">' + k + '</div><div class="v">' + (v == null || v === "" ? "-" : v) + "</div></div>";
}

function esc2(v) {
  return esc(v);
}

async function load() {
  if (!id) {
    root.innerHTML = '<div class="card"><div class="empty">No report id given. <a href="index.html">Go back</a>.</div></div>';
    return;
  }
  let r;
  try {
    r = await apiJson("/reports/" + encodeURIComponent(id));
  } catch (e) {
    root.innerHTML = '<div class="card"><div class="empty">Could not load report: ' + esc(e.message) + ' <a href="index.html">Go back</a></div></div>';
    return;
  }

  document.title = "Report " + (r.city || "") + " - VaayuDrishti";

  const media = (r.media || [])
    .map((m) => {
      const url = V1 + "/reports/" + r.id + "/media/" + m.key;
      return '<a href="' + esc(url) + '" target="_blank"><img src="' + esc(url) + '" alt="report media" loading="lazy" /></a>';
    })
    .join("");

  const loc = [r.city, r.district, r.state].filter(Boolean).join(", ");

  root.innerHTML =
    '<div class="card">' +
      '<div class="row spread" style="margin-bottom:10px">' +
        "<div>" + categoryBadge(r.event_category) + " " + severityBadge(r.severity) +
        " " + statusBadge(r.verification_status) + " " + credBadge(r.credibility_score) + "</div>" +
        '<span class="muted mono">' + esc2(r.id) + "</span>" +
      "</div>" +
      '<p style="font-size:15.5px;line-height:1.5;margin:6px 0 12px">' + esc2(r.text) + "</p>" +
      (r.source_url ? '<p><a href="' + esc2(r.source_url) + '" target="_blank" rel="noopener">Original source &#8599;</a></p>' : "") +
      (media ? '<div class="gallery">' + media + "</div>" : "") +
    "</div>" +

    '<div class="grid2">' +
      '<div class="card"><h2>Details</h2><div class="detail-grid">' +
        field("Observed at", esc2(fmtTime(r.observed_at))) +
        field("Ingested at", esc2(fmtTime(r.ingested_at))) +
        field("Location", esc2(loc || "Unknown")) +
        field("Coordinates", r.lat != null ? r.lat.toFixed(4) + ", " + r.lon.toFixed(4) : "-") +
        field("Source", esc2(r.source)) +
        field("Author", esc2(r.author)) +
        field("Language", esc2(r.lang)) +
        field("Hashtags", (r.hashtags || []).map((h) => "#" + esc2(h)).join(" ") || "-") +
        field("Credibility", credBadge(r.credibility_score)) +
        field("Classifier confidence", r.confidence != null ? Number(r.confidence).toFixed(3) : "-") +
        field("Duplicate", r.is_duplicate ? "yes" + (r.duplicate_of ? " of " + esc2(r.duplicate_of) : "") : "no") +
        field("Verification note", esc2(r.verification_note)) +
      "</div></div>" +

      '<div class="card"><h2>ML evidence</h2>' +
        (r.plausibility
          ? '<p class="hint">Weather plausibility cross-check</p><pre class="json">' + esc2(JSON.stringify(r.plausibility, null, 2)) + "</pre>"
          : '<p class="muted">No plausibility data for this report.</p>') +
        (r.credibility_features
          ? '<p class="hint" style="margin-top:10px">Credibility feature contributions</p><pre class="json">' + esc2(JSON.stringify(r.credibility_features, null, 2)) + "</pre>"
          : "") +
        (r.raw
          ? '<p class="hint" style="margin-top:10px">Raw payload</p><pre class="json">' + esc2(JSON.stringify(r.raw, null, 2)).slice(0, 4000) + "</pre>"
          : "") +
      "</div>" +
    "</div>";
}

load();
