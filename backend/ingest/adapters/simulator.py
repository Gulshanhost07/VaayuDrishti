
from __future__ import annotations

import random
import uuid
from collections import deque
from datetime import UTC, datetime

from ingest.base import Adapter
from ml.geocode import all_cities
from shared.config import settings
from shared.schemas import RawPost

CATEGORIES = [
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_winds",
]

TEMPLATES_EN = {
    "rainfall": [
        "Heavy rain lashing {city} since morning, roads waterlogged near {area} #IMD #MumbaiRains",
        "Downpour in {city} - {amount} mm recorded today, traffic crawling #Rainfall",
        "Non-stop rain in {city}! Umbrellas useless at this point 🌧️ #Weather #IMD",
        "Rain intensity increasing in {city} area {area}, IMD had issued a warning #IMDAlert",
    ],
    "thunderstorm": [
        "Massive thunderstorm over {city} right now, lightning lighting up the sky #Thunderstorm",
        "Thunder and lightning in {city} since last hour, trees swaying badly #IMD",
        "Hailstorm warning for {city}? Saw hail pellets in {area} just now #Hailstorm",
    ],
    "flooding": [
        "Water entering ground floors in {area}, {city} after last night's rain #Flood",
        "{city} {area} is submerged - cars stuck, please avoid this route #UrbanFlood #IMD",
        "River crossing danger mark near {city}, NDRF teams being deployed #FloodAlert",
    ],
    "heatwave": [
        "Scorching heat in {city} today, feels like {temp}°C in the shade #Heatwave",
        "{city} burning at {temp}°C - heat wave conditions persist #HeatWaveAlert",
        "Unable to step out in {city}, sun is brutal this afternoon #HotWeather",
    ],
    "fog": [
        "Dense fog in {city} this morning, visibility below 50 metres on the highway #Fog",
        "Fog has swallowed {city} completely, flights running late #DenseFog #IMD",
        "Winter morning in {city}: zero visibility conditions, drive slow #ColdWave",
    ],
    "dust_storm": [
        "Dust storm approaching {city}, sky turned orange #DustStorm",
        "Strong dusty winds in {city} - visibility dropping fast #DustStormAlert",
        "Sandstorm-like conditions in {city} {area}, stay indoors #Weather",
    ],
    "strong_winds": [
        "Wind speed picking up in {city}, loose objects flying #StrongWinds #IMD",
        "Tree branches down in {area} {city} due to strong gusts #Storm",
        "Cyclone watch: rough winds battering {city} coast #CycloneAlert",
    ],
}

TEMPLATES_HI = {
    "rainfall": ["{city} में भारी बारिश, निचले इलाकों में पानी भरा #बारिश #IMD",
                 "{city} में मानसून सक्रिय, आज {amount} मिमी बारिश दर्ज #मौसम"],
    "flooding": ["{city} के {area} में बाढ़ जैसी स्थिति, लोग परेशान #बाढ़",
                 "{city} में नदी का जलस्तर बढ़ा, प्रशासन सतर्क #FloodAlert"],
    "thunderstorm": ["{city} में तेज़ आकाशीय बिजली के साथ बिजली गिरना #तूफान", ],
    "heatwave": ["{city} में लू का कहर, तापमान {temp} डिग्री #लू #Heatwave"],
    "fog": ["{city} में घना कोहरा, दृश्यता बेहद कम #कोहरा #Fog"],
    "dust_storm": ["{city} में धूल भरी आंधी, बाहर न निकलें #धूलभराआंधी"],
    "strong_winds": ["{city} में तेज़ हवाओं का दौर, पेड़ गिरने की आशंका #आंधी"],
}

AREAS = ["MG Road", "Station Road", "civil lines", "old city", "riverside", "market area",
         "ring road", "airport zone", "industrial area", "lakeside"]

FAKE_PHRASES = [
    "SHOCKING video of {city} submerged, you won't believe this",
    "1000 year rain event! {city} is going to disappear, please share widely",
    "MEDIA WON'T SHOW THIS: entire {city} underwater, forward to everyone",
    "BREAKING: {city} to see record breaking {amount} mm rain never seen before",
    "URGENT: tsunami-scale flooding heading to {city}, evacuate now!!",
]

MEDIA_POOL = [
    "https://picsum.photos/seed/{seed}/800/600",
    "https://picsum.photos/seed/{seed}/640/480",
]

_recent: deque[str] = deque(maxlen=200)
_counter = 0


class SimulatorAdapter(Adapter):
    name = "simulator"
    default_interval = 10

    async def fetch(self) -> list[RawPost]:
        global _counter
        cities = all_cities()
        if not cities:
            return []
        per_cycle = max(1, settings.simulator_rate_per_min // 6)
        posts: list[RawPost] = []
        for _ in range(per_cycle):
            posts.append(self._make_post(cities))
        return posts

    def _make_post(self, cities) -> RawPost:
        global _counter
        city = random.choice(cities)
        roll = random.random()
        category = random.choice(CATEGORIES)
        lang = (random.random() < 0.25 and "hi") or "en"

        is_duplicate = roll < 0.15 and bool(_recent)
        is_fake = (not is_duplicate) and roll >= 0.75 and roll < 0.90
        with_media = (not is_duplicate) and roll >= 0.90

        if is_duplicate:
            text = random.choice(list(_recent))
            external_id = f"sim-dup-{uuid.uuid4().hex[:10]}"
            raw_kind = "duplicate"
        else:
            text = self._template(category, lang, city, fake=is_fake)
            external_id = f"sim-{uuid.uuid4().hex[:12]}"
            raw_kind = "fake" if is_fake else "normal"
            _recent.append(text)

        _counter += 1
        media_urls: list[str] = []
        if with_media:
            media_urls = [random.choice(MEDIA_POOL).format(seed=uuid.uuid4().hex[:8])]

        hashtags = ["#IMD", f"#{category}"] + (
            ["#MumbaiRains"] if city.name == "Mumbai" and category == "rainfall" else []
        )
        return RawPost(
            source="simulator",
            external_id=external_id,
            text=text,
            source_url=f"https://social.example/@sim/{external_id}",
            author=f"sim_user_{random.randint(1000, 9999)}",
            observed_at=datetime.now(UTC),
            hashtags=hashtags,
            lat=city.lat + random.uniform(-0.08, 0.08) if random.random() < 0.4 else None,
            lon=city.lon + random.uniform(-0.08, 0.08) if random.random() < 0.4 else None,
            city_hint=city.name,
            state_hint=city.state,
            media_urls=media_urls,
            lang=lang if lang == "hi" else "en",
            raw={"kind": raw_kind, "category_hint": category, "simulated": True},
        )

    @staticmethod
    def _template(category: str, lang: str, city, fake: bool = False) -> str:
        if fake:
            return random.choice(FAKE_PHRASES).format(
                city=city.name, amount=random.randint(300, 1200)
            )
        bank = TEMPLATES_HI if lang == "hi" and category in TEMPLATES_HI else TEMPLATES_EN
        tpl = random.choice(bank.get(category) or TEMPLATES_EN["rainfall"])
        return tpl.format(
            city=city.name,
            area=random.choice(AREAS),
            amount=random.randint(40, 180),
            temp=random.randint(41, 48),
        )
