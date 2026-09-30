
from __future__ import annotations

import csv
import difflib
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REFERENCE_DIR = Path(os.environ.get("REFERENCE_DIR", "/app/data/reference"))
if not REFERENCE_DIR.exists():
    REFERENCE_DIR = Path(__file__).resolve().parents[3] / "data" / "reference"


@dataclass(frozen=True, slots=True)
class City:
    name: str
    state: str
    district: str
    lat: float
    lon: float


def _load_cities() -> tuple[City, ...]:
    path = REFERENCE_DIR / "cities.csv"
    if not path.exists():
        return ()
    cities: list[City] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                cities.append(
                    City(
                        name=row["city"].strip(),
                        state=row["state"].strip(),
                        district=row["district"].strip(),
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                    )
                )
            except (KeyError, ValueError):
                continue
    return tuple(cities)


@lru_cache
def all_cities() -> tuple[City, ...]:
    return _load_cities()


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", "", name.lower())


@lru_cache
def _lookup_table() -> dict[str, City]:
    table: dict[str, City] = {}
    for c in all_cities():
        table[_norm(c.name)] = c
        table[_norm(c.district)] = c
    for alias, city in _city_alias_table().items():
        table.setdefault(alias, city)
    return table


@lru_cache
def _city_alias_table() -> dict[str, City]:
    path = REFERENCE_DIR / "aliases.csv"
    table: dict[str, City] = {}
    if not path.exists():
        return table
    by_name = {c.name: c for c in all_cities()}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")
        ):
            kind = (row.get("kind") or "").strip().lower()
            if kind != "city":
                continue
            target = by_name.get((row.get("target") or "").strip())
            alias = _norm(row.get("alias") or "")
            if target is not None and alias:
                table.setdefault(alias, target)
    return table


@lru_cache
def _state_alias_table() -> dict[str, str]:
    path = REFERENCE_DIR / "aliases.csv"
    table: dict[str, str] = {}
    if not path.exists():
        return table
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(
            line for line in fh if not line.lstrip().startswith("#")
        ):
            kind = (row.get("kind") or "").strip().lower()
            if kind != "state":
                continue
            alias = _norm(row.get("alias") or "")
            target = (row.get("target") or "").strip()
            if target and alias:
                table.setdefault(alias, target)
    return table


def find_state_by_name(name: str | None) -> str | None:
    if not name:
        return None
    key = _norm(name)
    if key in _state_alias_table():
        return _state_alias_table()[key]
    states = {c.state for c in all_cities()}
    for s in states:
        if _norm(s) == key:
            return s
    return None


def city_aliases() -> dict[str, City]:
    return dict(_city_alias_table())


def state_aliases() -> dict[str, str]:
    return dict(_state_alias_table())


def find_city_by_name(name: str | None) -> City | None:
    if not name:
        return None
    key = _norm(name)
    if not key:
        return None
    table = _lookup_table()
    if key in table:
        return table[key]
    for k, city in table.items():
        if key.startswith(k) or k.startswith(key):
            return city
    close = difflib.get_close_matches(key, list(table), n=1, cutoff=0.88)
    if close:
        return table[close[0]]
    return None


def nearest_city(lat: float, lon: float) -> City | None:
    best: City | None = None
    best_d2 = (75.0 / 111.0) ** 2
    for c in all_cities():
        dlat = c.lat - lat
        dlon = (c.lon - lon) * 0.85
        d2 = dlat * dlat + dlon * dlon
        if d2 < best_d2:
            best_d2 = d2
            best = c
    return best


def load_hashtags() -> frozenset[str]:
    path = REFERENCE_DIR / "hashtags.txt"
    if not path.exists():
        return frozenset()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("# "):
            continue
        out.add(line.lstrip("#").lower())
    return frozenset(out)


def load_credibility_lexicon() -> list[tuple[float, str]]:
    path = REFERENCE_DIR / "credibility_lexicon.txt"
    if not path.exists():
        return []
    entries: list[tuple[float, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        try:
            entries.append((float(parts[0]), parts[1].lower()))
        except ValueError:
            continue
    return entries
