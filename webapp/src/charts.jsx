import React, { useEffect, useRef } from "react";
import { CATEGORY_COLORS } from "./api.js";

export function Timeseries({ points }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const W = canvas.clientWidth || 600;
      const H = 180;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      const ctx = canvas.getContext("2d");
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, W, H);

      if (points.length < 2) {
        ctx.fillStyle = "#5b6b7f";
        ctx.font = "12px system-ui";
        ctx.fillText("not enough data yet", 12, 28);
        return;
      }
      const pad = { l: 42, r: 10, t: 12, b: 24 };
      const max = Math.max(...points.map((p) => p.n)) || 1;
      const x = (i) => pad.l + (i / (points.length - 1)) * (W - pad.l - pad.r);
      const y = (v) => pad.t + (1 - v / max) * (H - pad.t - pad.b);

      ctx.strokeStyle = "#e3eaf4";
      ctx.fillStyle = "#7c8aa0";
      ctx.font = "10px system-ui";
      for (let g = 0; g <= 4; g++) {
        const v = (max * g) / 4;
        ctx.beginPath();
        ctx.moveTo(pad.l, y(v));
        ctx.lineTo(W - pad.r, y(v));
        ctx.stroke();
        ctx.fillText(String(Math.round(v)), 6, y(v) + 3);
      }

      const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
      grad.addColorStop(0, "rgba(29,91,184,0.28)");
      grad.addColorStop(1, "rgba(29,91,184,0.02)");

      ctx.beginPath();
      points.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.n)) : ctx.moveTo(x(i), y(p.n))));
      ctx.lineTo(x(points.length - 1), H - pad.b);
      ctx.lineTo(x(0), H - pad.b);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.beginPath();
      points.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.n)) : ctx.moveTo(x(i), y(p.n))));
      ctx.strokeStyle = "#1d5bb8";
      ctx.lineWidth = 2;
      ctx.stroke();

      points.forEach((p, i) => {
        ctx.beginPath();
        ctx.arc(x(i), y(p.n), 2.5, 0, Math.PI * 2);
        ctx.fillStyle = "#0d376e";
        ctx.fill();
      });

      ctx.fillStyle = "#7c8aa0";
      const first = new Date(points[0].t);
      const last = new Date(points[points.length - 1].t);
      ctx.fillText(first.toLocaleDateString(), pad.l, H - 7);
      const label = last.toLocaleDateString();
      ctx.fillText(label, W - pad.r - ctx.measureText(label).width, H - 7);
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [points]);

  return <canvas ref={ref} className="chart-canvas" height="180" />;
}

const IN = { minLon: 68, maxLon: 98, minLat: 6, maxLat: 38 };

function lonToX(lon, W) {
  return ((lon - IN.minLon) / (IN.maxLon - IN.minLon)) * (W - 20) + 10;
}
function latToY(lat, H) {
  return (1 - (lat - IN.minLat) / (IN.maxLat - IN.minLat)) * (H - 20) + 10;
}

export function IndiaMap({ features, onPick }) {
  const ref = useRef(null);
  const pointsRef = useRef([]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const W = canvas.clientWidth || 400;
      const H = 330;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      const ctx = canvas.getContext("2d");
      ctx.scale(dpr, dpr);

      const bg = ctx.createLinearGradient(0, 0, 0, H);
      bg.addColorStop(0, "#f2f7fd");
      bg.addColorStop(1, "#eaf1fa");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      ctx.strokeStyle = "#dde7f3";
      ctx.fillStyle = "#93a3b8";
      ctx.font = "10px system-ui";
      ctx.lineWidth = 1;
      for (let lon = 70; lon <= 98; lon += 7) {
        const x = lonToX(lon, W);
        ctx.beginPath();
        ctx.moveTo(x, 8);
        ctx.lineTo(x, H - 8);
        ctx.stroke();
        ctx.fillText(lon + "E", x + 2, H - 10);
      }
      for (let lat = 8; lat <= 38; lat += 7) {
        const y = latToY(lat, H);
        ctx.beginPath();
        ctx.moveTo(8, y);
        ctx.lineTo(W - 8, y);
        ctx.stroke();
        ctx.fillText(lat + "N", 10, y - 3);
      }

      const pts = [];
      features.forEach((f) => {
        const [lon, lat] = f.geometry.coordinates;
        if (lat == null || lon == null) return;
        const x = lonToX(lon, W);
        const y = latToY(lat, H);
        const p = f.properties;
        ctx.beginPath();
        ctx.arc(x, y, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = CATEGORY_COLORS[p.event_category] || "#64748b";
        ctx.globalAlpha = p.is_duplicate ? 0.3 : 0.88;
        ctx.fill();
        ctx.globalAlpha = 1;
        pts.push({ x, y, id: p.id });
      });
      pointsRef.current = pts;

      ctx.fillStyle = "#0d376e";
      ctx.font = "600 11px system-ui";
      ctx.fillText(features.length + " reports plotted", 12, 18);
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [features]);

  const handleClick = (ev) => {
    const canvas = ref.current;
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    let best = null;
    let bestD = 10;
    pointsRef.current.forEach((p) => {
      const d = Math.hypot(p.x - mx, p.y - my);
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    });
    if (best && onPick) onPick(best.id);
  };

  return <canvas ref={ref} className="map-canvas" height="330" onClick={handleClick} />;
}

export function BarList({ rows, empty = "No data" }) {
  if (!rows || !rows.length) return <div className="empty">{empty}</div>;
  const value = (r) => Number(r.value) || 0;
  const max = Math.max(...rows.map(value), 1);
  return (
    <div className="barlist">
      {rows.map((r, i) => {
        const pct = Math.round((value(r) / max) * 100);
        const label = String(r.label ?? "-");
        return (
          <div className="barrow" key={label + "-" + i}>
            <span className="barlabel" title={label}>{label}</span>
            <span className="track">
              <span className="fill" style={{ width: pct + "%", background: r.color }} />
            </span>
            <span className="barnum">{r.display != null ? r.display : value(r)}</span>
          </div>
        );
      })}
    </div>
  );
}
