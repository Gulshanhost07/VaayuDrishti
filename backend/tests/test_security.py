
from __future__ import annotations

import pytest

from shared.security import (
    ROLE_RANK,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    h = hash_password("vaayu@123")
    assert h != "vaayu@123"
    assert verify_password(h, "vaayu@123")
    assert not verify_password(h, "wrong")
    assert not verify_password("not-a-hash", "vaayu@123")


def test_access_token_roundtrip() -> None:
    tok = create_access_token("admin@vaayu.local", "admin")
    claims = decode_token(tok)
    assert claims["sub"] == "admin@vaayu.local"
    assert claims["role"] == "admin"
    assert claims["kind"] == "access"


def test_refresh_token_has_different_kind() -> None:
    tok = create_refresh_token("admin@vaayu.local", "admin")
    assert decode_token(tok, expected_kind="refresh")["kind"] == "refresh"


def test_access_token_rejected_as_refresh() -> None:
    tok = create_access_token("admin@vaayu.local", "admin")
    with pytest.raises(TokenError):
        decode_token(tok, expected_kind="refresh")


def test_garbage_token_rejected() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.jwt")


def test_role_ranking() -> None:
    assert ROLE_RANK["admin"] > ROLE_RANK["reviewer"] > ROLE_RANK["viewer"]
