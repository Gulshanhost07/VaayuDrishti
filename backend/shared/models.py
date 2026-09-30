
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ReportSource(enum.StrEnum):
    imd = "imd"
    open_meteo = "open_meteo"
    reddit = "reddit"
    rss = "rss"
    citizen = "citizen"
    twitter = "twitter"
    mastodon = "mastodon"
    dataset = "dataset"
    simulator = "simulator"


class EventCategory(enum.StrEnum):

    rainfall = "rainfall"
    thunderstorm = "thunderstorm"
    flooding = "flooding"
    heatwave = "heatwave"
    fog = "fog"
    dust_storm = "dust_storm"
    strong_winds = "strong_winds"
    other = "other"


class VerificationStatus(enum.StrEnum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    disputed = "disputed"


class UserRole(enum.StrEnum):
    admin = "admin"
    reviewer = "reviewer"
    viewer = "viewer"


class RunStatus(enum.StrEnum):
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict] = {dict[str, Any]: JSONB, list[str]: ARRAY(Text)}


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_reports_source_external"),
        Index("ix_reports_event_observed", "event_category", "observed_at"),
        Index("ix_reports_observed_at", "observed_at"),
        Index("ix_reports_verification", "verification_status"),
        Index("ix_reports_state", "state"),
        Index("ix_reports_city", "city"),
        Index("ix_reports_credibility", "credibility_score"),
        Index("ix_reports_duplicate_of", "duplicate_of"),
        Index("ix_reports_text_fts", text("to_tsvector('simple', text)"), postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))

    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str | None] = mapped_column(String(8))
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)

    city: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))

    event_category: Mapped[str | None] = mapped_column(
        Enum(
            EventCategory,
            name="event_category",
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
        ),
    )
    severity: Mapped[str | None] = mapped_column(String(16))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))

    credibility_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    credibility_features: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    plausibility: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    verification_status: Mapped[str] = mapped_column(
        Enum(
            VerificationStatus,
            name="verification_status",
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
        ),
        default=VerificationStatus.pending.value,
        server_default=VerificationStatus.pending.value,
        nullable=False,
    )
    verification_note: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL")
    )

    media: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    verifier: Mapped[AdminUser | None] = relationship("AdminUser", foreign_keys=[verified_by])


class IngestRun(Base):
    __tablename__ = "ingest_runs"
    __table_args__ = (Index("ix_ingest_runs_source_started", "source", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        Enum(
            RunStatus,
            name="run_status",
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
        ),
        default=RunStatus.running.value,
        server_default=RunStatus.running.value,
    )
    fetched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    published: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicates: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errors: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda e: [m.value for m in e],
            create_constraint=False,
        ),
        default=UserRole.reviewer.value,
        server_default=UserRole.reviewer.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RollupHourly(Base):
    __tablename__ = "rollup_hourly"
    __table_args__ = (
        UniqueConstraint(
            "bucket_start", "state", "event_category", "source", name="uq_rollup_hourly_dims"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120))
    event_category: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    report_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verified_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_credibility: Mapped[float | None] = mapped_column(Numeric(4, 3))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RollupDaily(Base):
    __tablename__ = "rollup_daily"
    __table_args__ = (
        UniqueConstraint(
            "bucket_start", "state", "event_category", "source", name="uq_rollup_daily_dims"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120))
    event_category: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    report_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    verified_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_credibility: Mapped[float | None] = mapped_column(Numeric(4, 3))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferenceObservation(Base):

    __tablename__ = "reference_observations"
    __table_args__ = (
        UniqueConstraint(
            "provider", "station", "observed_at", name="uq_refobs_provider_station_time"
        ),
        Index("ix_refobs_space_time", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    station: Mapped[str] = mapped_column(String(120), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temp_c: Mapped[float | None] = mapped_column(Float)
    precip_mm: Mapped[float | None] = mapped_column(Float)
    wind_kph: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class CitizenToken(Base):
    __tablename__ = "citizen_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SourceConfig(Base):

    __tablename__ = "source_config"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    interval_seconds: Mapped[int] = mapped_column(Integer, default=600, server_default="600")
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
