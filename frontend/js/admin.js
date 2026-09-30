const $ = (id) => document.getElementById(id);

function loggedIn() {
  return !!localStorage.getItem("vaayu_access");
}

function showConsole() {
  $("loginpane").style.display = "none";
  $("console").style.display = "block";
  $("who").textContent = (localStorage.getItem("vaayu_email") || "") + " (" + (localStorage.getItem("vaayu_role") || "?") + ")";
  loadQueue();
  loadPipeline();
  loadSources();
  loadAudit();
}

$("loginform").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("loginerr").textContent = "";
  try {
    const res = await fetch(V1 + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("email").value.trim(), password: $("password").value }),
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(typeof b.detail === "string" ? b.detail : "HTTP " + res.status);
    }
    const data = await res.json();
    localStorage.setItem("vaayu_access", data.access_token);
    localStorage.setItem("vaayu_refresh", data.refresh_token);
    localStorage.setItem("vaayu_role", data.role);
    localStorage.setItem("vaayu_email", $("email").value.trim());
    showConsole();
    toast("Signed in as " + data.role);
  } catch (e) {
    $("loginerr").textContent = e.message;
  }
});

$("logout").addEventListener("click", () => {
  ["vaayu_access", "vaayu_refresh", "vaayu_role", "vaayu_email"].forEach((k) => localStorage.removeItem(k));
  location.reload();
});

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tabpane").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  });
});

const qState = { page: 1, pages: 1 };
const selected = new Set();

function updateSelectedLabel() {
  $("q-selected").textContent = selected.size + " selected";
}

async function loadQueue() {
  const status = $("q-status").value;
  const category = $("q-category").value;
  let url = "/admin/reports?page=" + qState.page + "&page_size=25";
  if (status) url += "&verification_status=" + encodeURIComponent(status);
  if (category) url += "&category=" + encodeURIComponent(category);
  selected.clear();
  updateSelectedLabel();
  const body = $("q-body");
  try {
    const data = await apiJson(url);
    qState.pages = data.meta.pages || 1;
    $("q-pageinfo").textContent = "page " + data.meta.page + " / " + Math.max(qState.pages, 1) + " (" + data.meta.total + ")";
    if (!data.items.length) {
      body.innerHTML = '<tr><td colspan="9" class="empty">Queue is empty.</td></tr>';
      return;
    }
    body.innerHTML = data.items
      .map((r) => {
        const loc = [r.city, r.state].filter(Boolean).join(", ") || "-";
        return (
          '<tr data-id="' + r.id + '">' +
          '<td><input type="checkbox" class="q-check" value="' + r.id + '" /></td>' +
          "<td>" + esc(fmtTime(r.observed_at)) + "</td>" +
          "<td>" + esc(loc) + "</td>" +
          "<td>" + categoryBadge(r.event_category) + "</td>" +
          "<td>" + credBadge(r.credibility_score) + "</td>" +
          "<td>" + statusBadge(r.verification_status) + "</td>" +
          "<td>" + esc(r.source) + "</td>" +
          '<td class="text"><a href="report.html?id=' + r.id + '" target="_blank" title="' + esc(r.text) + '">' + esc(r.text) + "</a></td>" +
          '<td class="row">' +
          '<button class="btn green sm" data-act="verified" data-id="' + r.id + '">V</button>' +
          '<button class="btn red sm" data-act="rejected" data-id="' + r.id + '">R</button>' +
          '<button class="btn amber sm" data-act="disputed" data-id="' + r.id + '">D</button>' +
          "</td></tr>"
        );
      })
      .join("");
    body.querySelectorAll(".q-check").forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked) selected.add(cb.value);
        else selected.delete(cb.value);
        updateSelectedLabel();
      });
    });
    body.querySelectorAll("button[data-act]").forEach((btn) => {
      btn.addEventListener("click", () => setVerification(btn.dataset.id, btn.dataset.act));
    });
  } catch (e) {
    body.innerHTML = '<tr><td colspan="9" class="empty">Error: ' + esc(e.message) + "</td></tr>";
  }
}

async function setVerification(id, status) {
  try {
    await apiJson("/admin/reports/" + id + "/verification", {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    toast(id.slice(0, 8) + " -> " + status);
    loadQueue();
  } catch (e) {
    toast(e.message, true);
  }
}

async function bulkVerify(status) {
  if (!selected.size) {
    toast("Select at least one report", true);
    return;
  }
  try {
    const out = await apiJson("/admin/reports/bulk-verification", {
      method: "POST",
      body: JSON.stringify({ ids: Array.from(selected), status }),
    });
    toast("updated " + out.updated + ", missing " + out.missing.length);
    loadQueue();
  } catch (e) {
    toast(e.message, true);
  }
}

document.querySelectorAll("[data-bulk]").forEach((btn) =>
  btn.addEventListener("click", () => bulkVerify(btn.dataset.bulk))
);
$("q-all").addEventListener("change", () => {
  document.querySelectorAll(".q-check").forEach((cb) => {
    cb.checked = $("q-all").checked;
    if (cb.checked) selected.add(cb.value);
    else selected.delete(cb.value);
  });
  updateSelectedLabel();
});
$("q-load").addEventListener("click", () => { qState.page = 1; loadQueue(); });
$("q-prev").addEventListener("click", () => { if (qState.page > 1) { qState.page--; loadQueue(); } });
$("q-next").addEventListener("click", () => { if (qState.page < qState.pages) { qState.page++; loadQueue(); } });

async function loadPipeline() {
  try {
    const p = await apiJson("/admin/pipeline");
    $("p-time").textContent = "computed " + fmtTime(p.computed_at);
    const k = p.kafka || {};
    $("p-lag").innerHTML = k.available
      ? Object.entries(k.lag)
          .map(([g, n]) => '<span class="badge" style="background:' + (n === 0 ? "#16a34a" : "#f59e0b") + ';margin-right:6px">' + esc(g) + ": " + n + "</span>")
          .join("") + '<span class="muted" style="margin-left:8px">sum ' + k.sum + "</span>"
      : '<span class="badge" style="background:#dc2626">kafka unavailable (' + esc(k.error || "?") + ")</span>";

    $("p-counters").innerHTML = Object.entries(p.counters || {})
      .map(([k2, v]) => '<div><div class="k">' + esc(k2) + '</div><div class="v">' + v + "</div></div>")
      .join("") || '<span class="muted">no counters yet</span>';

    $("p-runs").innerHTML = (p.recent_runs || [])
      .map(
        (r) =>
          "<tr><td>" + esc(r.source) + "</td>" +
          "<td>" + badge(r.status, r.status === "ok" ? "#16a34a" : "#dc2626") + "</td>" +
          "<td>" + r.fetched + "</td><td>" + r.published + "</td><td>" + r.errors + "</td>" +
          "<td>" + esc(fmtTime(r.started_at)) + "</td><td>" + esc(fmtTime(r.finished_at)) + "</td></tr>"
      )
      .join("");
  } catch (e) {
    $("p-lag").textContent = "Error: " + e.message;
  }
}

async function loadSources() {
  const body = $("s-body");
  try {
    const data = await apiJson("/admin/sources");
    const rows = data.sources || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty">No sources configured.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map(
        (s) =>
          '<tr data-name="' + esc(s.name) + '">' +
          "<td class='mono'>" + esc(s.name) + "</td>" +
          '<td><input type="checkbox" class="s-en"' + (s.enabled ? " checked" : "") + " /></td>" +
          '<td><input type="number" class="s-int" value="' + s.interval_seconds + '" min="5" max="86400" style="width:90px" /></td>' +
          "<td>" + esc(fmtTime(s.updated_at)) + "</td>" +
          '<td><button class="btn sm s-save">Save</button></td></tr>'
      )
      .join("");
    body.querySelectorAll(".s-save").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr");
        try {
          await apiJson("/admin/sources/" + encodeURIComponent(tr.dataset.name), {
            method: "PATCH",
            body: JSON.stringify({
              enabled: tr.querySelector(".s-en").checked,
              interval_seconds: Number(tr.querySelector(".s-int").value),
            }),
          });
          toast(tr.dataset.name + " updated");
          loadSources();
        } catch (e) {
          toast(e.message, true);
        }
      });
    });
  } catch (e) {
    body.innerHTML = '<tr><td colspan="5" class="empty">Error: ' + esc(e.message) + "</td></tr>";
  }
}

async function loadAudit() {
  const body = $("a-body");
  let url = "/admin/audit?limit=50";
  const action = $("a-action").value.trim();
  if (action) url += "&action=" + encodeURIComponent(action);
  try {
    const data = await apiJson(url);
    const rows = data.entries || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty">No audit entries.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map((e) => {
        const det = JSON.stringify({ before: e.before, after: e.after });
        return (
          "<tr><td>" + esc(fmtTime(e.created_at)) + "</td>" +
          "<td>" + esc((e.user_id || "").slice(0, 8)) + "</td>" +
          "<td>" + esc(e.action) + "</td>" +
          "<td>" + esc(e.entity) + "</td>" +
          '<td class="mono">' + esc((e.entity_id || "").slice(0, 24)) + "</td>" +
          '<td><details><summary>view</summary><pre class="json">' + esc(JSON.stringify(JSON.parse(det), null, 2)) + "</pre></details></td></tr>"
        );
      })
      .join("");
  } catch (e) {
    body.innerHTML = '<tr><td colspan="6" class="empty">Error: ' + esc(e.message) + "</td></tr>";
  }
}
$("a-load").addEventListener("click", loadAudit);

async function download(format) {
  let url = "/admin/export?format=" + format + "&limit=" + (Number($("e-limit").value) || 1000);
  ["date_from", "date_to", "state", "category"].forEach((k) => {
    const v = $("e-" + k).value;
    if (v) url += "&" + k + "=" + encodeURIComponent(v);
  });
  const st = $("e-status").value;
  if (st) url += "&verification_status=" + st;
  try {
    const res = await api(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = format === "csv" ? "vaayu_export.csv" : "vaayu_export.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    toast("Export downloaded");
  } catch (e) {
    toast("export failed: " + e.message, true);
  }
}
$("e-csv").addEventListener("click", () => download("csv"));
$("e-json").addEventListener("click", () => download("json"));

if (loggedIn()) showConsole();
setInterval(() => {
  if (loggedIn() && $("tab-pipeline").classList.contains("active")) loadPipeline();
}, 10000);
