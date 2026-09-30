
from __future__ import annotations

import argparse
import asyncio
import random
import time
from datetime import UTC, datetime

from ml.geocode import all_cities
from shared import topics as T
from shared.config import settings
from shared.kafka import Producer, ensure_topic
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("load_test")

CITIES = [c.name for c in all_cities()]
STATES = ["Maharashtra", "Bihar", "Rajasthan", "Delhi", "Kerala", "West Bengal", "Punjab", "Odisha"]

TEMPLATES: list[tuple[str, str]] = [
    (
        "rainfall",
        "Heavy rain lashing {city} since morning, waterlogging reported in low-lying areas",
    ),
    (
        "rainfall",
        "भारी बारिश के कारण {city} में जनजीवन प्रभावित, नाले उफान पर",
    ),
    (
        "flooding",
        "Flash floods after river overflow, evacuation underway in {city}",
    ),
    (
        "flooding",
        "{state} में बाढ़ की स्थिति, कई इलाकों में पानी घुसा",
    ),
    (
        "thunderstorm",
        "Severe thunderstorm with lightning strikes damages houses in {city}",
    ),
    (
        "heatwave",
        "Heatwave continues, temperature crosses 44C in {city}",
    ),
    (
        "heatwave",
        "{state} में लू का कहर, तापमान 45 डिग्री तक पहुंचा",
    ),
    (
        "fog",
        "Dense fog disrupts rail traffic, visibility below 50 metres near {city}",
    ),
    (
        "dust_storm",
        "Dust storm warning issued for {state}, low visibility on highways",
    ),
    (
        "strong_winds",
        "Gusty winds at 60 kmph uproot trees across {city}",
    ),
    (
        "other",
        "Pleasant evening weather in {city}, perfect for a stroll in the park",
    ),
]


def make_post(i: int) -> RawPost:
    category, template = random.choice(TEMPLATES)
    city = random.choice(CITIES)
    state = random.choice(STATES)
    has_coords = random.random() < 0.7
    return RawPost(
        source="loadtest",
        external_id=f"load-{i}",
        text=template.format(city=city, state=state),
        source_url=f"https://example.invalid/load/{i}",
        author=f"user{random.randint(1, 9999)}",
        observed_at=datetime.now(UTC),
        hashtags=["#IMD", "#Weather", f"#{category.title()}"],
        lat=(round(random.uniform(8.0, 35.0), 4) if has_coords else None),
        lon=(round(random.uniform(68.0, 97.0), 4) if has_coords else None),
        city_hint=(city if random.random() < 0.5 else None),
        state_hint=(state if random.random() < 0.5 else None),
        raw={"category_hint": category, "load_seq": i},
    )


async def run(count: int, topic: str, rate: int) -> int:
    try:
        await ensure_topic(topic)
    except Exception as exc:
        print(
            f"[load_test] cannot reach Redpanda at "
            f"{settings.kafka_bootstrap_servers}: {exc}"
        )
        return 1

    producer = Producer()
    await producer.start()
    started = time.perf_counter()
    batch_size = max(1, rate // 10)
    sent = 0
    try:
        while sent < count:
            batch = [make_post(i) for i in range(sent, min(sent + batch_size, count))]
            await asyncio.gather(*(producer.send(topic, p.model_dump(mode="json")) for p in batch))
            sent += len(batch)
            if sent % 1000 < batch_size or sent == count:
                elapsed = time.perf_counter() - started
                log.info(q(f"[load_test] sent={sent}/{count} ({sent / max(elapsed, 1e-9):.0f} posts/s)"))
            await asyncio.sleep(batch_size / rate if rate else 0)
    finally:
        await producer.stop()
    elapsed = time.perf_counter() - started
    print(f"[load_test] done: {sent} posts in {elapsed:.1f}s ({sent / elapsed:.0f} posts/s) -> {topic}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="VaayuDrishti pipeline load test")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--topic", default=T.RAW_POSTS)
    parser.add_argument("--rate", type=int, default=1000, help="target posts/second")
    args = parser.parse_args()
    return asyncio.run(run(args.count, args.topic, args.rate))


if __name__ == "__main__":
    raise SystemExit(main())
