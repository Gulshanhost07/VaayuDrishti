const API_BASE = location.port === "8000" ? "" : "http://localhost:8000";
const V1 = API_BASE + "/api/v1";

const CATEGORY_COLORS = {
  rainfall: "#3b82f6",
  thunderstorm: "#8b5cf6",
  flooding: "#06b6d4",
  heatwave: "#ef4444",
  fog: "#94a3b8",
  dust_storm: "#f59e0b",
  strong_winds: "#10b981",
  other: "#64748b",
};

const SEVERITY_COLORS = {
  extreme: "#dc2626",
  severe: "#f97316",
  moderate: "#eab308",
  mild: "#3b82f6",
  unknown: "#94a3b8",
};

function statusColor(s) {
  return { verified: "#16a34a", rejected: "#dc2626", disputed: "#f59e0b", pending: "#64748b" }[s] || "#64748b";
}

function authHeaders() {
  const t = localStorage.getItem("vaayu_access");
  return t ? { Authorization: "Bearer " + t } : {};
}

async function tryRefresh() {
  const rt = localStorage.getItem("vaayu_refresh");
  if (!rt) return false;
  try {
    const res = await fetch(V1 + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem("vaayu_access", data.access_token);
    localStorage.setItem("vaayu_refresh", data.refresh_token);
    localStorage.setItem("vaayu_role", data.role);
    return true;
  } catch (e) {
    return false;
  }
}

async function api(path, opts = {}) {
  opts.headers = Object.assign({ "Content-Type": "application/json" }, authHeaders(), opts.headers || {});
  let res = await fetch(V1 + path, opts);
  if (res.status === 401 && localStorage.getItem("vaayu_refresh") && !opts._retried) {
    if (await tryRefresh()) {
      const retry = Object.assign({}, opts, { _retried: true });
      retry.headers = Object.assign({ "Content-Type": "application/json" }, authHeaders(), opts.headers || {});
      res = await fetch(V1 + path, retry);
    }
  }
  return res;
}

async function apiJson(path, opts = {}) {
  const res = await api(path, opts);
  if (!res.ok) {
    let detail;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (e) {
      detail = "HTTP " + res.status;
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function wsURL() {
  const host = location.port === "8000" ? location.host : "localhost:8000";
  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  return proto + host + "/api/v1/live/stream";
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function fmtTime(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch (e) {
    return iso;
  }
}

function badge(text, color) {
  return '<span class="badge" style="background:' + color + '">' + esc(text) + "</span>";
}

function categoryBadge(cat) {
  return badge(cat || "other", CATEGORY_COLORS[cat] || CATEGORY_COLORS.other);
}

function statusBadge(st) {
  return badge(st || "pending", statusColor(st));
}

function severityBadge(sev) {
  return badge(sev || "unknown", SEVERITY_COLORS[sev] || SEVERITY_COLORS.unknown);
}

function credBadge(score) {
  if (score == null) return "-";
  const s = Number(score);
  const color = s >= 0.7 ? "#16a34a" : s >= 0.4 ? "#f59e0b" : "#dc2626";
  return '<span class="badge" style="background:' + color + '">' + s.toFixed(2) + "</span>";
}

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

function toast(msg, isErr) {
  const el = document.createElement("div");
  el.className = "toast" + (isErr ? " err" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
