
from __future__ import annotations

import os
from datetime import UTC, datetime

from ingest.base import Adapter, http_client
from ml.geocode import find_city_by_name, nearest_city
from shared.config import settings
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("ingest.imd")

BASE = os.environ.get("IMD_API_BASE", "https://api.imd.gov.in")

WARNING_CODES = {
    "2": "rainfall",
    "16": "rainfall",
    "17": "flooding",
    "4": "thunderstorm",
    "5": "thunderstorm",
    "6": "dust_storm",
    "7": "dust_storm",
    "8": "strong_winds",
    "9": "heatwave",
    "10": "heatwave",
    "15": "fog",
}
WARNING_TEXT = {
    "2": "Heavy rain warning", "16": "Very heavy rain warning",
    "17": "Extremely heavy rain warning (flooding likely)",
    "4": "Thunderstorm & lightning warning", "5": "Hailstorm warning",
    "6": "Dust storm warning", "7": "Dust-raising winds warning",
    "8": "Strong surface winds warning", "9": "Heat wave warning",
    "10": "Hot day warning", "15": "Dense fog warning",
}
COLOR_SEVERITY = {"1": "red", "2": "orange", "3": "yellow", "4": "green"}

WMO_THUNDER = {95, 96, 99, 91, 92, 97}
WMO_FOG = {10, 11, 12, 28, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49}
WMO_DUST = {6, 7, 8, 9, 30, 31, 32, 33, 34, 35}
WMO_RAIN = set(range(60, 70)) | set(range(80, 83)) | {14, 15, 16, 20, 21, 25}
HEAVY_RAIN_24H_MM = 64.5
HEATWAVE_C = 40.0
STRONG_WIND_KPH = 40.0


class IMDAdapter(Adapter):
    name = "imd"
    default_interval = 600

    async def fetch(self) -> list[RawPost]:
        if not settings.imd_api_key:
            log.warning(
                q("[imd] IMD_API_KEY not set - skipping cycle "
                  "(register free key at https://api.imd.gov.in)")
            )
            return []
        posts: list[RawPost] = []
        posts += await self._district_warnings()
        posts += await self._current_weather()
        return posts

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": settings.imd_api_key, "User-Agent": "VaayuDrishti/1.0"}

    async def _get(self, client, path: str, params: dict | None = None):
        resp = await client.get(f"{BASE}{path}", params=params or {}, headers=self._headers())
        if resp.status_code == 401:
            raise PermissionError("IMD API key rejected (401)")
        resp.raise_for_status()
        return resp.json()

    async def _district_warnings(self) -> list[RawPost]:
        try:
            async with http_client(timeout=25.0) as client:
                data = await self._get(client, "/api/v1/districtwarning")
        except PermissionError:
            raise
        except Exception as exc:
            log.warning(q(f"[imd] districtwarning failed: {exc}"))
            return []

        rows = data if isinstance(data, list) else (data or {}).get("data") or []
        now = datetime.now(UTC)
        posts: list[RawPost] = []
        today = now.strftime("%Y-%m-%d")
        for row in rows:
            district = str(row.get("District") or "").strip()
            if not district:
                continue
            for day_key in ("Day_1", "Day_2", "Day_3", "Day_4", "Day_5"):
                codes = str(row.get(day_key) or "").strip()
                if not codes or codes == "0":
                    continue
                color = str(
                    row.get(f"Day{day_key[-1]}_Color")
                    or row.get(f"Day{day_key[-1]}_color")
                    or ""
                )
                matched = [c.strip() for c in codes.split(",") if c.strip() in WARNING_CODES]
                if not matched:
                    continue
                categories = {WARNING_CODES[c] for c in matched}
                category = (
                    "flooding" if "flooding" in categories else sorted(categories)[0]
                )
                labels = ", ".join(WARNING_TEXT.get(c, c) for c in matched)
                text = f"IMD {labels} for {district} district ({day_key.replace('_', ' ')})"
                city = find_city_by_name(district) or nearest_city(
                    float(row.get("Latitude") or 0) or 22.0,
                    float(row.get("Longitude") or 0) or 79.0,
                )
                external_id = f"dw-{district.lower().replace(' ', '-')}-{day_key}-{row.get('Date', today)}"
                posts.append(
                    RawPost(
                        source="imd",
                        external_id=external_id,
                        text=text,
                        source_url="https://mausam.imd.gov.in/",
                        author="IMD",
                        observed_at=now,
                        hashtags=["#IMD", "#IMDAlert"] + [f"#{c}" for c in matched],
                        lat=city.lat if city else None,
                        lon=city.lon if city else None,
                        city_hint=city.name if city else district,
                        state_hint=city.state if city else None,
                        lang="en",
                        raw={
                            "warning_codes": matched,
                            "color": color,
                            "category_hint": category,
                            "row": row,
                        },
                    )
                )
        return posts

    async def _current_weather(self) -> list[RawPost]:
        try:
            async with http_client(timeout=30.0) as client:
                data = await self._get(client, "/api/v1/current_wx")
        except PermissionError:
            raise
        except Exception as exc:
            log.warning(q(f"[imd] current_wx failed: {exc}"))
            return []

        rows = data if isinstance(data, list) else (data or {}).get("data") or []
        now = datetime.now(UTC)
        posts: list[RawPost] = []
        for row in rows:
            station = str(row.get("Station") or row.get("Station_Name") or "").strip()
            if not station:
                continue
            try:
                temp = float(row.get("Temperature") or 0)
                wind = float(row.get("Wind Speed") or 0)
                rain24 = float(row.get("Last 24 hrs Rainfall") or 0)
                code = int(row.get("Weather Code") or 0)
            except (TypeError, ValueError):
                continue

            category: str | None = None
            text = ""
            if rain24 >= HEAVY_RAIN_24H_MM:
                category, text = "rainfall", (
                    f"IMD station {station}: {rain24:.1f} mm rainfall in last 24 hrs"
                )
            elif code in WMO_THUNDER:
                category, text = "thunderstorm", f"IMD nowcast: thunderstorm at {station}"
            elif temp >= HEATWAVE_C:
                category, text = "heatwave", f"IMD station {station}: {temp:.1f}°C - heat wave"
            elif code in WMO_DUST:
                category, text = "dust_storm", f"IMD nowcast: dust storm conditions at {station}"
            elif code in WMO_FOG:
                category, text = "fog", f"IMD nowcast: fog at {station}"
            elif wind >= STRONG_WIND_KPH:
                category, text = "strong_winds", f"IMD station {station}: wind {wind:.0f} km/h"
            if category is None:
                continue

            city = find_city_by_name(station) or nearest_city(
                float(row.get("Latitude") or 0) or 22.0,
                float(row.get("Longitude") or 0) or 79.0,
            )
            hour_key = now.strftime("%Y%m%d%H")
            posts.append(
                RawPost(
                    source="imd",
                    external_id=f"cw-{station.lower().replace(' ', '-')}-{hour_key}",
                    text=text,
                    source_url="https://mausam.imd.gov.in/",
                    author="IMD",
                    observed_at=now,
                    hashtags=["#IMD", "#Weather", f"#{category}"],
                    lat=float(row.get("Latitude")) if row.get("Latitude") else (city.lat if city else None),
                    lon=float(row.get("Longitude")) if row.get("Longitude") else (city.lon if city else None),
                    city_hint=city.name if city else station,
                    state_hint=city.state if city else None,
                    lang="en",
                    raw={"category_hint": category, "row": row},
                )
            )
        return posts
