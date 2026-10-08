"""One persistence layer: SQLite locally, PostgreSQL through Cloud SQL in deployment."""
from datetime import datetime, timezone
from pathlib import Path
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def identifier():
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Prospect(Base):
    __tablename__ = "prospects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    profile: Mapped[dict] = mapped_column(JSON)
    crm_contact_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    intelligence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    research_notes: Mapped[str] = mapped_column(Text, default="")
    research_attribution_html: Mapped[str] = mapped_column(Text, default="")
    research_status: Mapped[str] = mapped_column(String(30), default="pending")
    research_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    research_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AccessLink(Base):
    __tablename__ = "access_links"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    prospect_id: Mapped[str] = mapped_column(ForeignKey("prospects.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prospect_id: Mapped[str] = mapped_column(ForeignKey("prospects.id"), index=True)
    access_link_hash: Mapped[str | None] = mapped_column(ForeignKey("access_links.token_hash"), nullable=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    session_id: Mapped[str] = mapped_column(ForeignKey("browser_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Usage(Base):
    __tablename__ = "usage_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("browser_sessions.id"), nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_reference: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(40), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RequestTrace(Base):
    __tablename__ = "request_traces"
    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    method: Mapped[str] = mapped_column(String(10))
    route: Mapped[str] = mapped_column(String(120))
    status: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FollowUp(Base):
    __tablename__ = "followups"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=identifier)
    prospect_id: Mapped[str] = mapped_column(ForeignKey("prospects.id"), index=True)
    intent: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def database(settings, secret_store):
    connector = None
    if settings.cloud_sql_instance:
        from .integrations import cloud_sql_creator
        password = secret_store.get(settings.database_password_secret)
        creator = cloud_sql_creator(settings.cloud_sql_instance, settings.database_user, password, settings.database_name)
        engine = create_engine("postgresql+pg8000://", creator=creator, pool_pre_ping=True, pool_size=5, max_overflow=2)
        connector = getattr(creator, "connector", None)
    else:
        if settings.database_url.startswith("sqlite:///") and ":memory:" not in settings.database_url:
            Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}} if settings.database_url.startswith("sqlite") else {}
        engine = create_engine(settings.database_url, pool_pre_ping=True, **kwargs)
    try:
        with engine.begin() as connection:
            if engine.dialect.name == "postgresql":
                # Fresh Cloud Run revisions may start together. Serialize DDL.
                connection.execute(text("SELECT pg_advisory_xact_lock(789316103)"))
            Base.metadata.create_all(connection)
    except Exception:
        engine.dispose()
        if connector:
            connector.close()
        raise
    return engine, sessionmaker(engine, expire_on_commit=False), connector
