from __future__ import annotations

import sys

import httpx

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"
ADMIN = {"email": "admin@vaayu.local", "password": "vaayu@123"}

results: list[tuple[str, str, str, str, str, bool]] = []


def check(
    method: str,
    path: str,
    auth: str,
    resp: httpx.Response,
    expected: set[int],
) -> None:
    ok = resp.status_code in expected
    exp = "/".join(str(e) for e in sorted(expected))
    results.append((method, auth, path, str(resp.status_code), exp, ok))
    return None


def main() -> int:
    public = httpx.Client(base_url=BASE, timeout=30)

    bad = public.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrong-pass"})
    check("POST", "/auth/login", "public", bad, {401})

    login_ok = public.post(f"{API}/auth/login", json=ADMIN)
    check("POST", "/auth/login", "public", login_ok, {200})
    tokens = login_ok.json()
    access = tokens.get("access_token", "")
    headers = {"Authorization": f"Bearer {access}"}
    client = httpx.Client(base_url=BASE, timeout=30, headers=headers)

    if "refresh_token" in tokens:
        ref = public.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        check("POST", "/auth/refresh", "public", ref, {200})
        ref_bad = public.post(f"{API}/auth/refresh", json={"refresh_token": "bogus-token-0123456789"})
        check("POST", "/auth/refresh (bad)", "public", ref_bad, {401})
    else:
        ref = public.post(f"{API}/auth/refresh", json={"refresh_token": "bogus-token-0123456789"})
        check("POST", "/auth/refresh", "public", ref, {401, 422})

    me = client.get(f"{API}/auth/me")
    check("GET", "/auth/me", "bearer", me, {200})
    unauth = public.get(f"{API}/auth/me")
    check("GET", "/auth/me", "no-auth", unauth, {401})

    h = public.get(f"{API}/health", params={"deep": "true"})
    check("GET", "/health?deep=true", "public", h, {200})
    h2 = public.get(f"{BASE}/health")
    check("GET", "/health (root)", "public", h2, {200})

    rep = public.get(f"{API}/reports", params={"page_size": 5})
    check("GET", "/reports", "public", rep, {200})
    items = rep.json().get("items", []) if rep.status_code == 200 else []
    total = rep.json().get("meta", {}).get("total", 0) if rep.status_code == 200 else 0

    bad_sort = public.get(f"{API}/reports", params={"sort": "nope"})
    check("GET", "/reports (422)", "public", bad_sort, {422})

    first_id = items[0]["id"] if items else ""
    one = public.get(f"{API}/reports/{first_id}") if first_id else None
    if one is not None:
        check("GET", "/reports/{id}", "public", one, {200})

    missing = public.get(f"{API}/reports/00000000-0000-0000-0000-000000000000")
    check("GET", "/reports/{id} (404)", "public", missing, {404})

    s = public.get(f"{API}/reports/search", params={"q": "rain", "page_size": 5})
    check("GET", "/reports/search", "public", s, {200})
    s_bad = public.get(f"{API}/reports/search", params={"q": ""})
    check("GET", "/reports/search (422)", "public", s_bad, {422})

    g = public.get(
        f"{API}/geo/reports.geojson",
        params={"bbox": "68.0,6.0,98.0,38.0", "limit": 500},
    )
    check("GET", "/geo/reports.geojson (bbox)", "public", g, {200})
    g2 = public.get(f"{API}/geo/reports.geojson", params={"lat": 28.6, "lon": 77.2, "radius_km": 50})
    check("GET", "/geo/reports.geojson (radius)", "public", g2, {200})
    g_bad = public.get(f"{API}/geo/reports.geojson", params={"bbox": "1,2"})
    check("GET", "/geo/reports.geojson (422)", "public", g_bad, {422})

    t = public.get(f"{API}/reports/track/not-a-real-token")
    check("GET", "/reports/track/{token} (404)", "public", t, {404})

    media_report, media_key = "", ""
    for pg in (1, 2, 3, 4):
        page = public.get(f"{API}/reports", params={"page": pg, "page_size": 100})
        if page.status_code != 200:
            break
        for it in page.json().get("items", []):
            if it.get("media"):
                media_report, media_key = it["id"], it["media"][0]["key"]
                break
        if media_report:
            break
    if media_report:
        m = public.get(f"{API}/reports/{media_report}/media/{media_key}")
        check("GET", "/reports/{id}/media/{key}", "public", m, {200})
    else:
        m = public.get(f"{API}/reports/{first_id}/media/none.jpg")
        check("GET", "/reports/{id}/media/{key} (404)", "public", m, {404})

    analytics: dict[str, dict[str, str | int]] = {
        "summary": {"hours": 24},
        "timeseries": {"hours": 48, "bucket": "hour"},
        "by-state": {"hours": 24},
        "by-category": {"hours": 24},
        "by-source": {"hours": 24},
        "hashtags": {"limit": 10},
        "filters": {},
    }
    for name, params in analytics.items():
        r = public.get(f"{API}/analytics/{name}", params=params)
        check("GET", f"/analytics/{name}", "public", r, {200})

    bad_bucket = public.get(f"{API}/analytics/timeseries", params={"bucket": "nonsense"})
    check("GET", "/analytics/timeseries (422)", "public", bad_bucket, {422})

    sub = public.post(
        f"{API}/citizen/reports",
        json={
            "text": "API smoke: street flooding reported under the flyover after heavy rain",
            "city": "Kolkata",
            "state": "West Bengal",
            "event_category": "flooding",
        },
    )
    check("POST", "/citizen/reports", "public", sub, {201})
    token = sub.json().get("token", "") if sub.status_code == 201 else ""
    if token:
        tr = public.get(f"{API}/reports/track/{token}")
        check("GET", "/reports/track/{token}", "public", tr, {200})
    bad_sub = public.post(f"{API}/citizen/reports", json={"text": "short"})
    check("POST", "/citizen/reports (422)", "public", bad_sub, {422})

    for path in (
        "/admin/pipeline",
        "/admin/reports",
        "/admin/audit",
        "/admin/sources",
        "/admin/ingest-runs",
        "/admin/export",
    ):
        r = public.get(f"{API}{path}")
        check("GET", path, "no-auth", r, {401})

    pipe = client.get(f"{API}/admin/pipeline")
    check("GET", "/admin/pipeline", "bearer", pipe, {200})

    areps = client.get(f"{API}/admin/reports", params={"page_size": 5, "verification_status": "pending"})
    check("GET", "/admin/reports", "bearer", areps, {200})

    audit = client.get(f"{API}/admin/audit", params={"limit": 5})
    check("GET", "/admin/audit", "bearer", audit, {200})

    runs = client.get(f"{API}/admin/ingest-runs", params={"limit": 5})
    check("GET", "/admin/ingest-runs", "bearer", runs, {200})

    sources = client.get(f"{API}/admin/sources")
    check("GET", "/admin/sources", "bearer", sources, {200})
    src_list = sources.json().get("sources", []) if sources.status_code == 200 else []
    src_names = [s["name"] for s in src_list]
    if src_names:
        cur = next(s for s in src_list if s["name"] == src_names[0])
        p = client.patch(
            f"{API}/admin/sources/{src_names[0]}",
            json={"enabled": bool(cur.get("enabled", True))},
        )
        check("PATCH", "/admin/sources/{name} (same value)", "bearer", p, {200})

    exp = client.get(f"{API}/admin/export", params={"limit": 10})
    check("GET", "/admin/export (CSV)", "bearer", exp, {200})

    target = ""
    pend = client.get(f"{API}/admin/reports", params={"page_size": 1, "verification_status": "pending"})
    if pend.status_code == 200 and pend.json().get("items"):
        target = pend.json()["items"][0]["id"]
    if target:
        v = client.patch(
            f"{API}/admin/reports/{target}/verification",
            json={"status": "pending", "note": None},
        )
        check("PATCH", "/admin/reports/{id}/verification", "bearer", v, {200})
    bad_v = client.patch(f"{API}/admin/reports/{target}/verification", json={"status": "banana"})
    check("PATCH", ".../verification (422)", "bearer", bad_v, {422})

    bulk_bad = client.post(f"{API}/admin/reports/bulk-verification", json={"ids": [], "status": "verified"})
    check("POST", "/admin/reports/bulk-verification (422)", "bearer", bulk_bad, {422})
    missing_id = client.post(
        f"{API}/admin/reports/bulk-verification",
        json={"ids": ["00000000-0000-0000-0000-000000000000"], "status": "verified"},
    )
    check("POST", "/admin/reports/bulk-verification (missing)", "bearer", missing_id, {200})

    bad_patch = client.patch(f"{API}/admin/sources/does-not-exist", json={"enabled": True})
    check("PATCH", "/admin/sources/{bad} (404)", "bearer", bad_patch, {404})

    rl_codes: set[int] = set()
    for _ in range(16):
        r = public.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrong"})
        rl_codes.add(r.status_code)
        if r.status_code == 429:
            break
    check(
        "POST",
        "/auth/login (rate-limit)",
        "public",
        httpx.Response(429 if 429 in rl_codes else 200),
        {429},
    )

    width = max(len(r[2]) for r in results)
    print(f"{'METHOD':7} {'AUTH':8} {'PATH':<{width}} {'GOT':>5} {'WANT':>8}  ok")
    print("-" * (width + 34))
    fails = 0
    for method, auth_kind, path, got, want, ok in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"{method:7} {auth_kind:8} {path:<{width}} {got:>5} {want:>8}  {mark}")
    print("-" * (width + 34))
    print(f"{len(results) - fails}/{len(results)} checks passed; reports total={total}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
