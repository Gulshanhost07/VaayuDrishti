const state = { page: 1, pageSize: 25, pages: 1 };

function currentFilters() {
  const f = {};
  ["date_from", "date_to", "category", "state", "status", "source"].forEach((k) => {
    const v = document.getElementById("f-" + k).value;
    if (v) f[k === "status" ? "verification_status" : k] = v;
  });
  return f;
}

function filterQuery() {
  return Object.entries(currentFilters())
    .map(([k, v]) => k + "=" + encodeURIComponent(v))
    .join("&");
}

async function loadSummary() {
  try {
    const s = await apiJson("/analytics/summary");
    document.getElementById("kpi-total").textContent = s.total_reports.toLocaleString();
    document.getElementById("kpi-sub-total").textContent = s.pending.toLocaleString() + " pending / " + s.disputed + " disputed";
    document.getElementById("kpi-verified").textContent = s.verified_pct + "%";
    document.getElementById("kpi-sub-verified").textContent = s.verified.toLocaleString() + " verified reports";
    document.getElementById("kpi-24h").textContent = s.reports_last_24h.toLocaleString();
    document.getElementById("kpi-1h").textContent = s.reports_last_hour.toLocaleString();
    document.getElementById("kpi-states").textContent = s.states_covered + " states covered";
    document.getElementById("kpi-cred").textContent = s.avg_credibility.toFixed(3);
    document.getElementById("kpi-sources").textContent = s.sources_enabled + " sources enabled";
  } catch (e) {
    toast("summary failed: " + e.message, true);
  }
}

async function loadFilterOptions() {
  try {
    const f = await apiJson("/analytics/filters");
    const catSel = document.getElementById("f-category");
    f.categories.forEach((c) => catSel.add(new Option(c, c)));
    const stSel = document.getElementById("f-state");
    f.states.forEach((s) => stSel.add(new Option(s, s)));
    const soSel = document.getElementById("f-source");
    f.sources.forEach((s) => soSel.add(new Option(s, s)));
  } catch (e) {
  }
}

async function loadReports() {
  const body = document.getElementById("rep-body");
  const q = filterQuery();
  const url = "/reports?page=" + state.page + "&page_size=" + state.pageSize + (q ? "&" + q : "");
  try {
    const data = await apiJson(url);
    state.pages = data.meta.pages || 1;
    document.getElementById("pageinfo").textContent = "page " + data.meta.page + " / " + Math.max(state.pages, 1) + " (" + data.meta.total + " reports)";
    document.getElementById("rep-count").textContent = data.meta.total + " matching";
    if (!data.items.length) {
      body.innerHTML = '<tr><td colspan="8" class="empty">No reports match the current filters.</td></tr>';
      return;
    }
    body.innerHTML = data.items
      .map((r) => {
        const loc = [r.city, r.state].filter(Boolean).join(", ") || "-";
        const txt = r.text || "";
        return (
          '<tr>' +
          "<td>" + esc(fmtTime(r.observed_at)) + "</td>" +
          "<td>" + esc(loc) + "</td>" +
          "<td>" + categoryBadge(r.event_category) + "</td>" +
          "<td>" + severityBadge(r.severity) + "</td>" +
          "<td>" + credBadge(r.credibility_score) + "</td>" +
          "<td>" + statusBadge(r.verification_status) + "</td>" +
          "<td>" + esc(r.source) + "</td>" +
          '<td class="text"><a href="report.html?id=' + r.id + '" title="' + esc(txt) + '">' + esc(txt) + "</a></td>" +
          "</tr>"
        );
      })
      .join("");
  } catch (e) {
    body.innerHTML = '<tr><td colspan="8" class="empty">Error: ' + esc(e.message) + "</td></tr>";
  }
}

function renderBars(elId, rows, colorFn) {
  const el = document.getElementById(elId);
  if (!rows || !rows.length) {
    el.innerHTML = '<div class="empty">No data</div>';
    return;
  }
  const max = Math.max(...rows.map((r) => r.value));
  el.innerHTML = rows
    .map((r) => {
      const pct = max ? Math.round((r.value / max) * 100) : 0;
      return (
        '<div class="barrow"><span title="' + esc(r.label) + '">' + esc(r.label) + "</span>" +
        '<span class="track"><span class="fill" style="width:' + pct + "%;background:" + colorFn(r) + '"></span></span>' +
        '<span class="num">' + (r.display || r.value) + "</span></div>"
      );
    })
    .join("");
}

async function loadCharts() {
  try {
    const cat = await apiJson("/analytics/by-category");
    renderBars(
      "ch-category",
      cat.categories.map((c) => ({ label: c.category, value: c.count, trend: c.trend, display: c.count.toLocaleString() + (c.trend ? " (" + (c.trend > 0 ? "+" : "") + c.trend + ")" : "") })),
      (r) => CATEGORY_COLORS[r.label] || "#64748b"
    );
  } catch (e) {}
  try {
    const st = await apiJson("/analytics/by-state?limit=10");
    renderBars(
      "ch-state",
      st.states.map((s) => ({ label: s.state, value: s.count, display: s.count.toLocaleString() })),
      () => "#1d5bb8"
    );
  } catch (e) {}
  try {
    const so = await apiJson("/analytics/by-source");
    renderBars(
      "ch-source",
      so.sources.map((s) => ({ label: s.source, value: s.count, display: s.share_pct + "%" })),
      (r) => (CATEGORY_COLORS[r.label] || "#0d9488")
    );
  } catch (e) {}
  try {
    const tg = await apiJson("/analytics/hashtags?limit=10");
    renderBars(
      "ch-tags",
      tg.hashtags.map((t) => ({ label: "#" + t.tag, value: t.count, display: String(t.count) })),
      () => "#7c3aed"
    );
  } catch (e) {}
}

async function loadTimeseries() {
  const canvas = document.getElementById("ts");
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth || 600;
  const H = 180;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  let points = [];
  try {
    const q = filterQuery();
    const data = await apiJson("/analytics/timeseries?bucket=hour" + (q ? "&" + q : ""));
    const byBucket = {};
    data.points.forEach((p) => {
      byBucket[p.bucket] = (byBucket[p.bucket] || 0) + p.count;
    });
    points = Object.entries(byBucket).map(([b, n]) => ({ t: new Date(b).getTime(), n }));
    points.sort((a, b) => a.t - b.t);
  } catch (e) {
    ctx.fillStyle = "#64748b";
    ctx.fillText("chart unavailable: " + e.message, 12, 24);
    return;
  }
  if (points.length < 2) {
    ctx.fillStyle = "#64748b";
    ctx.fillText("not enough data yet", 12, 24);
    return;
  }
  const pad = { l: 40, r: 8, t: 12, b: 22 };
  const max = Math.max(...points.map((p) => p.n)) || 1;
  const x = (i) => pad.l + (i / (points.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - v / max) * (H - pad.t - pad.b);

  ctx.strokeStyle = "#e2e8f0";
  ctx.fillStyle = "#64748b";
  ctx.font = "10px system-ui";
  for (let g = 0; g <= 4; g++) {
    const v = (max * g) / 4;
    ctx.beginPath();
    ctx.moveTo(pad.l, y(v));
    ctx.lineTo(W - pad.r, y(v));
    ctx.stroke();
    ctx.fillText(String(Math.round(v)), 6, y(v) + 3);
  }

  ctx.beginPath();
  points.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.n)) : ctx.moveTo(x(i), y(p.n))));
  ctx.strokeStyle = "#1d5bb8";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.lineTo(x(points.length - 1), H - pad.b);
  ctx.lineTo(x(0), H - pad.b);
  ctx.closePath();
  ctx.fillStyle = "rgba(29,91,184,0.12)";
  ctx.fill();

  ctx.fillStyle = "#64748b";
  const first = new Date(points[0].t);
  const last = new Date(points[points.length - 1].t);
  ctx.fillText(first.toLocaleDateString(), pad.l, H - 6);
  const label = last.toLocaleDateString();
  ctx.fillText(label, W - pad.r - ctx.measureText(label).width, H - 6);
}

const IN = { minLon: 68, maxLon: 98, minLat: 6, maxLat: 38 };
let mapPoints = [];

function lonToX(lon, W) { return ((lon - IN.minLon) / (IN.maxLon - IN.minLon)) * (W - 20) + 10; }
function latToY(lat, H) { return (1 - (lat - IN.minLat) / (IN.maxLat - IN.minLat)) * (H - 20) + 10; }

async function loadMap() {
  const canvas = document.getElementById("map");
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth || 400;
  const H = 330;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, W, H);

  let features = [];
  try {
    const q = filterQuery();
    const data = await apiJson("/geo/reports.geojson?limit=3000" + (q ? "&" + q : ""));
    features = data.features || [];
  } catch (e) {
    ctx.fillStyle = "#64748b";
    ctx.fillText("map unavailable: " + e.message, 12, 24);
    return;
  }

  ctx.strokeStyle = "#e6ebf3";
  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px system-ui";
  ctx.lineWidth = 1;
  for (let lon = 70; lon <= 98; lon += 7) {
    const x = lonToX(lon, W);
    ctx.beginPath(); ctx.moveTo(x, 8); ctx.lineTo(x, H - 8); ctx.stroke();
    ctx.fillText(lon + "E", x + 2, H - 10);
  }
  for (let lat = 8; lat <= 38; lat += 7) {
    const y = latToY(lat, H);
    ctx.beginPath(); ctx.moveTo(8, y); ctx.lineTo(W - 8, y); ctx.stroke();
    ctx.fillText(lat + "N", 10, y - 3);
  }

  mapPoints = [];
  features.forEach((f) => {
    const [lon, lat] = f.geometry.coordinates;
    if (lat == null || lon == null) return;
    const x = lonToX(lon, W);
    const yy = latToY(lat, H);
    const p = f.properties;
    ctx.beginPath();
    ctx.arc(x, yy, 4, 0, Math.PI * 2);
    ctx.fillStyle = CATEGORY_COLORS[p.event_category] || "#64748b";
    ctx.globalAlpha = p.is_duplicate ? 0.35 : 0.85;
    ctx.fill();
    ctx.globalAlpha = 1;
    mapPoints.push({ x, y: yy, id: p.id });
  });

  ctx.fillStyle = "#0d376e";
  ctx.font = "11px system-ui";
  ctx.fillText(features.length + " reports plotted", 12, 16);
}

document.getElementById("map").addEventListener("click", (ev) => {
  const canvas = ev.target;
  const rect = canvas.getBoundingClientRect();
  const mx = ev.clientX - rect.left;
  const my = ev.clientY - rect.top;
  let best = null;
  let bestD = 9;
  mapPoints.forEach((p) => {
    const d = Math.hypot(p.x - mx, p.y - my);
    if (d < bestD) { bestD = d; best = p; }
  });
  if (best) window.open("report.html?id=" + best.id, "_blank");
});

function connectWS() {
  const ticker = document.getElementById("ticker");
  const wsstate = document.getElementById("wsstate");
  let ws;
  try {
    ws = new WebSocket(wsURL());
  } catch (e) {
    ticker.innerHTML = '<div class="empty">WebSocket unavailable</div>';
    return;
  }
  ws.onopen = () => {
    wsstate.textContent = "connected";
    ticker.innerHTML = "";
  };
  ws.onclose = () => {
    wsstate.textContent = "disconnected - retrying...";
    setTimeout(connectWS, 3000);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (msg.type === "hello" || msg.type === "heartbeat") return;
    if (!msg.id) return;
    const item = document.createElement("div");
    item.className = "item fresh";
    item.innerHTML =
      "<div>" + categoryBadge(msg.event_category) + " " + esc(msg.city || msg.state || "?") + "</div>" +
      '<div class="meta">' + esc((msg.text || "").slice(0, 120)) + "</div>" +
      '<div class="meta">' + esc(msg.source) + " - " + esc(fmtTime(msg.observed_at)) + " - cred " + credBadge(msg.credibility_score) + "</div>";
    ticker.prepend(item);
    while (ticker.children.length > 40) ticker.lastChild.remove();
  };
}

function refreshAll() {
  state.page = 1;
  loadReports();
  loadMap();
  loadTimeseries();
  loadSummary();
}

document.getElementById("apply").addEventListener("click", refreshAll);
document.getElementById("reset").addEventListener("click", () => {
  ["date_from", "date_to", "category", "state", "status", "source"].forEach((k) => {
    document.getElementById("f-" + k).value = "";
  });
  refreshAll();
});
document.getElementById("prev").addEventListener("click", () => {
  if (state.page > 1) { state.page--; loadReports(); }
});
document.getElementById("next").addEventListener("click", () => {
  if (state.page < state.pages) { state.page++; loadReports(); }
});
window.addEventListener("resize", () => { loadMap(); loadTimeseries(); });

(async function init() {
  await loadFilterOptions();
  refreshAll();
  loadCharts();
  connectWS();
  setInterval(loadSummary, 60000);
  setInterval(loadCharts, 120000);
})();
