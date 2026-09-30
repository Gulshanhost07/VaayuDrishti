
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventCategoryLiteral = Literal[
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_winds",
    "other",
]


class MediaRef(BaseModel):
    bucket: str
    key: str
    content_type: str
    sha256: str | None = None
    size: int | None = None
    source_url: str | None = None


class RawPost(BaseModel):

    model_config = ConfigDict(extra="allow")

    source: str
    external_id: str
    text: str
    source_url: str | None = None
    author: str | None = None
    observed_at: datetime
    hashtags: list[str] = Field(default_factory=list)
    lat: float | None = None
    lon: float | None = None
    city_hint: str | None = None
    state_hint: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    lang: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        return v


class EnrichedPost(RawPost):

    stage: Literal["enriched"] = "enriched"
    city: str | None = None
    district: str | None = None
    state: str | None = None
    media: list[MediaRef] = Field(default_factory=list)
    geocode_method: str | None = None


class DedupedPost(EnrichedPost):

    stage: Literal["deduped"] = "deduped"
    is_duplicate: bool = False
    duplicate_of: str | None = None
    dedup_score: float | None = None


class ClassifiedPost(DedupedPost):

    stage: Literal["classified"] = "classified"
    event_category: EventCategoryLiteral = "other"
    category_confidence: float = 0.0
    severity: Literal["extreme", "severe", "moderate", "mild", "unknown"] = "unknown"
    credibility_score: float = 0.5
    credibility_features: dict[str, Any] = Field(default_factory=dict)
    plausibility: dict[str, Any] = Field(default_factory=dict)


class DLQRecord(BaseModel):
    topic: str
    stage: str
    error: str
    payload: dict[str, Any] = Field(default_factory=dict)
    failed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    source_url: str | None = None
    author: str | None = None
    text: str
    lang: str | None = None
    hashtags: list[str] | None = None
    lat: float | None = None
    lon: float | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    event_category: str | None = None
    severity: str | None = None
    confidence: float | None = None
    credibility_score: float | None = None
    verification_status: str = "pending"
    verification_note: str | None = None
    is_duplicate: bool = False
    duplicate_of: uuid.UUID | None = None
    media: list[MediaRef] | None = None
    observed_at: datetime
    ingested_at: datetime
    plausibility: dict[str, Any] | None = None


class ReportDetailOut(ReportOut):
    credibility_features: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


class CitizenReportIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    lat: float | None = None
    lon: float | None = None
    event_category: EventCategoryLiteral | None = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("describe the weather event in at least 10 characters")
        return v


class VerificationIn(BaseModel):
    status: Literal["verified", "rejected", "disputed", "pending"]
    note: str | None = Field(default=None, max_length=1000)


class BulkVerificationIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    status: Literal["verified", "rejected", "disputed", "pending"]
    note: str | None = Field(default=None, max_length=1000)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class ReportPage(BaseModel):
    items: list[ReportOut]
    meta: PageMeta


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4096)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    role: str


class SourcePatchIn(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=5, le=86400)


class TrackOut(BaseModel):

    id: uuid.UUID
    verification_status: str
    verification_note: str | None = None
    observed_at: datetime
    city: str | None = None
    state: str | None = None
    event_category: str | None = None


class CitizenSubmitOut(BaseModel):
    id: uuid.UUID
    token: str
    tracking_path: str
    status: str = "pending"
