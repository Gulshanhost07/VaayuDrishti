
from __future__ import annotations

from datetime import UTC, datetime

from ingest.base import Adapter, http_client
from ml.geocode import City, all_cities
from shared.db import SessionLocal
from shared.logging import q, setup_logging
from shared.models import ReferenceObservation
from shared.schemas import RawPost

log = setup_logging("ingest.open_meteo")

API = "https://api.open-meteo.com/v1/forecast"
CURRENT_VARS = (
    "temperature_2m,precipitation,wind_speed_10m,relative_humidity_2m,weather_code"
)

SAMPLE_SIZE = 40

WMO_THUNDER = {95, 96, 99}
WMO_FOG = {45, 48}
WMO_SHOWERS = {80, 81, 82}
WMO_RAIN = set(range(51, 68)) | WMO_SHOWERS

HEAVY_RAIN_MM_H = 7.5
HEATWAVE_C = 40.0
STRONG_WIND_KPH = 40.0


def _major_cities() -> list[City]:
    cities = all_cities()
    priority = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad",
                "Ahmedabad", "Pune", "Jaipur", "Lucknow", "Patna", "Guwahati",
                "Kochi", "Bhubaneswar", "Chandigarh", "Srinagar", "Shimla",
                "Thiruvananthapuram", "Nagpur", "Indore"]
    ordered: list[City] = []
    seen: set[str] = set()
    by_name = {c.name: c for c in cities}
    for name in priority:
        if name in by_name:
            ordered.append(by_name[name])
            seen.add(name)
    for c in cities:
        if len(ordered) >= SAMPLE_SIZE:
            break
        if c.name not in seen:
            ordered.append(c)
            seen.add(c.name)
    return ordered[:SAMPLE_SIZE]


class OpenMeteoAdapter(Adapter):
    name = "open_meteo"
    default_interval = 900

    def __init__(self, producer) -> None:
        super().__init__(producer)
        self._cities = _major_cities()

    async def fetch(self) -> list[RawPost]:
        if not self._cities:
            return []
        params = {
            "latitude": ",".join(str(c.lat) for c in self._cities),
            "longitude": ",".join(str(c.lon) for c in self._cities),
            "current": CURRENT_VARS,
            "timezone": "IST",
        }
        async with http_client(timeout=25.0) as client:
            resp = await client.get(API, params=params)
            resp.raise_for_status()
            payload = resp.json()

        batches = payload if isinstance(payload, list) else [payload]
        now = datetime.now(UTC)
        posts: list[RawPost] = []
        observations: list[dict] = []

        for city, batch in zip(self._cities, batches, strict=False):
            cur = (batch or {}).get("current") or {}
            tval = cur.get("temperature_2m")
            if tval is None:
                continue
            try:
                temp = float(tval)
                precip = float(cur.get("precipitation", 0) or 0)
                wind = float(cur.get("wind_speed_10m", 0) or 0)
                humidity = float(cur.get("relative_humidity_2m", 0) or 0)
                code = int(cur.get("weather_code", 0) or 0)
            except (TypeError, ValueError):
                continue

            observations.append(
                {
                    "station": city.name,
                    "lat": city.lat,
                    "lon": city.lon,
                    "temp": temp,
                    "precip": precip,
                    "wind": wind,
                    "humidity": humidity,
                    "code": code,
                }
            )
            post = self._threshold_post(city, temp, precip, wind, humidity, code, now, cur)
            if post is not None:
                posts.append(post)

        await self._store_observations(observations, now)
        return posts

    @staticmethod
    def _threshold_post(
        city: City,
        temp: float,
        precip: float,
        wind: float,
        humidity: float,
        code: int,
        now: datetime,
        cur: dict,
    ) -> RawPost | None:
        category: str | None = None
        text = ""
        if precip >= HEAVY_RAIN_MM_H:
            category, text = "rainfall", (
                f"Heavy rain in {city.name}: {precip:.1f} mm/h recorded "
                f"(auto-observation, {humidity:.0f}% RH)"
            )
        elif code in WMO_THUNDER:
            category, text = "thunderstorm", (
                f"Thunderstorm ongoing over {city.name} (WMO code {code}), "
                f"wind {wind:.0f} km/h"
            )
        elif temp >= HEATWAVE_C:
            category, text = "heatwave", (
                f"Heatwave conditions in {city.name}: {temp:.1f}°C recorded"
            )
        elif code in WMO_FOG:
            category, text = "fog", f"Dense fog reported over {city.name} (visibility reduced)"
        elif wind >= STRONG_WIND_KPH and precip < 1.0:
            category, text = "strong_winds", (
                f"Strong winds in {city.name}: {wind:.0f} km/h, dry conditions"
            )
        if category is None:
            return None

        hour_key = now.strftime("%Y%m%d%H")
        return RawPost(
            source="open_meteo",
            external_id=f"om-{city.name.lower().replace(' ', '-')}-{hour_key}",
            text=text,
            source_url="https://open-meteo.com/",
            author="open-meteo",
            observed_at=now,
            hashtags=["#IMD", "#Weather", f"#{category}"],
            lat=city.lat,
            lon=city.lon,
            city_hint=city.name,
            state_hint=city.state,
            lang="en",
            raw={"current": cur, "category_hint": category, "provider": "open-meteo"},
        )

    @staticmethod
    async def _store_observations(observations: list[dict], now: datetime) -> None:
        if not observations:
            return
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            async with SessionLocal() as session:
                for obs in observations:
                    stmt = pg_insert(ReferenceObservation).values(
                        provider="open_meteo",
                        station=obs["station"],
                        lat=obs["lat"],
                        lon=obs["lon"],
                        observed_at=now,
                        temp_c=obs["temp"],
                        precip_mm=obs["precip"],
                        wind_kph=obs["wind"],
                        humidity_pct=obs["humidity"],
                        payload={"wmo_code": obs["code"]},
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["provider", "station", "observed_at"],
                        set_={
                            "temp_c": stmt.excluded.temp_c,
                            "precip_mm": stmt.excluded.precip_mm,
                            "wind_kph": stmt.excluded.wind_kph,
                            "humidity_pct": stmt.excluded.humidity_pct,
                            "payload": stmt.excluded.payload,
                        },
                    )
                    await session.execute(stmt)
                await session.commit()
            log.info(q(f"[open_meteo] stored {len(observations)} reference observations"))
        except Exception as exc:
            log.warning(q(f"[open_meteo] observation store failed: {exc}"))
