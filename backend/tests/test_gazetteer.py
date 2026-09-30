
from __future__ import annotations

from ml.geocode import (
    find_city_by_name,
    find_state_by_name,
    load_credibility_lexicon,
    load_hashtags,
    nearest_city,
)


def test_mumbai_lookup() -> None:
    m = find_city_by_name("Mumbai")
    assert m is not None
    assert m.name == "Mumbai"
    assert m.state == "Maharashtra"


def test_english_historic_alias() -> None:
    b = find_city_by_name("Bangalore")
    assert b is not None
    assert b.name == "Bengaluru"


def test_devanagari_city_alias() -> None:
    d = find_city_by_name("दरभंगा")
    assert d is not None
    assert d.name == "Darbhanga"


def test_hindi_state_alias() -> None:
    st = find_state_by_name("बिहार")
    assert st == "Bihar"


def test_english_state() -> None:
    assert find_state_by_name("Tamil Nadu") == "Tamil Nadu"


def test_nearest_city_coords() -> None:
    c = nearest_city(19.0760, 72.8777)
    assert c is not None
    assert c.name == "Mumbai"


def test_reference_files_load() -> None:
    assert len(load_hashtags()) > 10
    lex = load_credibility_lexicon()
    assert len(lex) > 3
