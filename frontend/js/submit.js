document.getElementById("geo").addEventListener("click", () => {
  if (!navigator.geolocation) {
    toast("Geolocation not supported by this browser", true);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      document.getElementById("lat").value = pos.coords.latitude.toFixed(4);
      document.getElementById("lon").value = pos.coords.longitude.toFixed(4);
      toast("Location captured");
    },
    (err) => toast("Location denied: " + err.message, true)
  );
});

document.getElementById("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = document.getElementById("send");
  btn.disabled = true;
  try {
    const file = document.getElementById("file").files[0];
    const fields = {
      text: document.getElementById("text").value.trim(),
      city: document.getElementById("city").value.trim() || null,
      state: document.getElementById("state").value.trim() || null,
      lat: document.getElementById("lat").value ? Number(document.getElementById("lat").value) : null,
      lon: document.getElementById("lon").value ? Number(document.getElementById("lon").value) : null,
      event_category: document.getElementById("event_category").value || null,
    };

    let res;
    if (file) {
      const fd = new FormData();
      Object.entries(fields).forEach(([k, v]) => {
        if (v != null) fd.append(k, v);
      });
      fd.append("file", file);
      res = await api("/citizen/reports", { method: "POST", headers: {}, body: fd });
    } else {
      res = await api("/citizen/reports", { method: "POST", body: JSON.stringify(fields) });
    }
    if (!res.ok) {
      let detail;
      try {
        const b = await res.json();
        detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
      } catch (e) {
        detail = "HTTP " + res.status;
      }
      throw new Error(detail);
    }
    const data = await res.json();
    document.getElementById("done").style.display = "block";
    document.getElementById("token").textContent = data.token;
    document.getElementById("tracklink").href = "#";
    document.getElementById("tracklink").dataset.token = data.token;
    document.getElementById("tracktoken").value = data.token;
    toast("Report submitted - token issued");
    document.getElementById("form").reset();
    document.getElementById("trackout").innerHTML = "";
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("tracklink").addEventListener("click", (ev) => {
  ev.preventDefault();
  document.getElementById("tracktoken").value = ev.target.dataset.token || "";
  document.getElementById("trackform").dispatchEvent(new Event("submit"));
});

document.getElementById("trackform").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const token = document.getElementById("tracktoken").value.trim();
  const out = document.getElementById("trackout");
  out.innerHTML = '<div class="muted">Checking...</div>';
  try {
    const t = await apiJson("/reports/track/" + encodeURIComponent(token));
    out.innerHTML =
      '<div class="card"><div class="detail-grid">' +
      '<div><div class="k">Status</div><div class="v">' + statusBadge(t.verification_status) + "</div></div>" +
      '<div><div class="k">Event</div><div class="v">' + categoryBadge(t.event_category) + "</div></div>" +
      '<div><div class="k">Observed</div><div class="v">' + esc(fmtTime(t.observed_at)) + "</div></div>" +
      '<div><div class="k">Location</div><div class="v">' + esc([t.city, t.state].filter(Boolean).join(", ") || "-") + "</div></div>" +
      '<div><div class="k">Report id</div><div class="v mono"><a href="report.html?id=' + t.id + '">' + esc(t.id) + "</a></div></div>" +
      '<div><div class="k">Reviewer note</div><div class="v">' + esc(t.verification_note || "-") + "</div></div>" +
      "</div></div>";
  } catch (e) {
    out.innerHTML = '<div class="card"><div class="empty">' + esc(e.message) + "</div></div>";
  }
});
