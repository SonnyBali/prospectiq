from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=250)
    url: str = Field(max_length=2000)
    excerpt: str = Field(min_length=1, max_length=5000)
    observed_at: datetime
    is_synthetic: bool = False

    @field_validator("url")
    @classmethod
    def safe_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Evidence links require HTTPS and no embedded credentials")
        return value


class Claim(StrictModel):
    text: str
    source_ids: list[str]


class Recommendation(StrictModel):
    title: str
    rationale: str
    source_ids: list[str]


class AdvisorAnswer(StrictModel):
    summary: str
    claims: list[Claim]
    recommendations: list[Recommendation]
    unknowns: list[str]


class SimulatorInput(StrictModel):
    monthly_leads: int = Field(default=300, ge=0, le=100000)
    missed_rate: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    recovery_rate: float = Field(default=0.60, ge=0, le=1, allow_inf_nan=False)
    booking_rate: float = Field(default=0.50, ge=0, le=1, allow_inf_nan=False)
    close_rate: float = Field(default=0.30, ge=0, le=1, allow_inf_nan=False)
    average_sale: float = Field(default=1200, ge=0, le=1000000, allow_inf_nan=False)
    monthly_cost: float = Field(default=497, ge=0, le=1000000, allow_inf_nan=False)

    @field_validator("average_sale", "monthly_cost")
    @classmethod
    def minimum_currency(cls, value):
        if 0 < value < .01:
            raise ValueError("Positive currency assumptions must be at least one cent")
        return value


class ChatInput(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    scenario: SimulatorInput | None = None

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class AccessInput(StrictModel):
    token: str = Field(min_length=32, max_length=128)
    client_id: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class ProspectImport(StrictModel):
    first_name: str = Field(min_length=1, max_length=80)
    company_name: str = Field(min_length=1, max_length=200)
    industry: str = Field(min_length=1, max_length=100)
    website: str = Field(max_length=2000)
    crm_contact_id: str | None = Field(default=None, max_length=100)
    sources: list[Source] = Field(min_length=1, max_length=30)
    research_notes: str = Field(default="", max_length=12000)
    research_attribution_html: str = Field(default="", max_length=50000)
    synthetic: bool = False

    @field_validator("sources")
    @classmethod
    def distinct_sources(cls, values):
        if len({s.id for s in values}) != len(values):
            raise ValueError("Evidence IDs must be unique")
        return values


class CRMImport(StrictModel):
    contact_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class FollowUpInput(StrictModel):
    intent: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=1000)


class DeliveryInput(StrictModel):
    approved: Literal[True]


class ResearchTaskInput(StrictModel):
    prospect_id: str = Field(min_length=1, max_length=100)
