"""Configuration contains secret *names*, never provider credentials."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
import re
from urllib.parse import urlparse

PRODUCTION_VOICE_WIDGETS = {"6a76e48422509c8ee2247714", "6abf71b7cdeb03a6d5287556", "6abe29f12b6d9dcee841fc67"}


def voice_origin(value):
    parsed = urlparse(value)
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("Voice origin must be a bare web origin")
    if not parsed.hostname or (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"})):
        raise ValueError("Voice origin requires HTTPS, except loopback development")
    return value.rstrip("/")


def flag(name: str) -> bool:
    return os.getenv(name, "false").lower() == "true"


@dataclass(frozen=True)
class Settings:
    project: str = "ai-leadscore"
    region: str = "us-central1"
    database_url: str = "sqlite:///.data/prospectiq.db"
    cloud_sql_instance: str = ""
    database_user: str = "prospectiq"
    database_name: str = "prospectiq"
    database_password_secret: str = ""
    openai_secret: str = ""
    openai_model: str = "gpt-4.1-mini"
    admin_secret: str = ""
    ghl_secret: str = "FIREWIRE_GHL_API_KEY"
    ghl_location_secret: str = "FIREWIRE_GHL_LOCATION_ID"
    ghl_location: str = "aFnKcmUdTSPIjo7lCaix"
    crm_cohort_tag: str = "prospectiq-approved"
    allow_crm_followup: bool = False
    allow_crm_links: bool = False
    ghl_dashboard_field_id: str = ""
    ghl_dashboard_trigger_link_id: str = ""
    secure_cookies: bool = False
    public_origin: str = "http://127.0.0.1:8090"
    demo_origin: str = ""
    session_hours: int = 8
    link_hours: int = 72
    demo_ai_budget: int = 12
    max_session_ai_calls: int = 30
    max_global_ai_calls_per_hour: int = 100
    openai_input_rate: str = ""
    openai_cached_rate: str = ""
    openai_output_rate: str = ""
    price_reference: str = ""
    task_queue: str = ""
    worker_url: str = ""
    task_service_account: str = ""
    vertex_model: str = "gemini-2.5-flash"
    allow_cloud_tasks: bool = False
    voice_widget_id: str = ""
    voice_browser_origin: str = ""
    voice_isolated: bool = False
    voice_phone: str = ""
    demo_video_url: str = "https://blog.firewireads.com/wp-content/uploads/2026/10/ai-receptionist-live-demo-web-review.mp4"

    @classmethod
    def from_env(cls):
        return cls(
            project=os.getenv("GOOGLE_CLOUD_PROJECT", "ai-leadscore"),
            region=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///.data/prospectiq.db"),
            cloud_sql_instance=os.getenv("CLOUD_SQL_INSTANCE", ""),
            database_user=os.getenv("DATABASE_USER", "prospectiq"),
            database_name=os.getenv("DATABASE_NAME", "prospectiq"),
            database_password_secret=os.getenv("DATABASE_PASSWORD_SECRET", ""),
            openai_secret=os.getenv("OPENAI_SECRET_NAME", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            admin_secret=os.getenv("ADMIN_SECRET_NAME", ""),
            ghl_location=os.getenv("GHL_LOCATION_ID", "aFnKcmUdTSPIjo7lCaix"),
            crm_cohort_tag=os.getenv("GHL_COHORT_TAG", "prospectiq-approved"),
            allow_crm_followup=flag("ALLOW_CRM_FOLLOWUP"),
            allow_crm_links=flag("ALLOW_CRM_LINKS"),
            ghl_dashboard_field_id=os.getenv("GHL_DASHBOARD_URL_FIELD_ID", ""),
            ghl_dashboard_trigger_link_id=os.getenv("GHL_DASHBOARD_TRIGGER_LINK_ID", ""),
            secure_cookies=flag("SECURE_COOKIES") or bool(os.getenv("K_SERVICE")),
            public_origin=os.getenv("PUBLIC_ORIGIN", "http://127.0.0.1:8090").rstrip("/"),
            demo_origin=os.getenv("DEMO_ORIGIN", "").rstrip("/"),
            demo_ai_budget=int(os.getenv("DEMO_AI_BUDGET", "12")),
            max_global_ai_calls_per_hour=int(os.getenv("MAX_AI_CALLS_PER_HOUR", "100")),
            openai_input_rate=os.getenv("OPENAI_INPUT_USD_PER_MILLION", ""),
            openai_cached_rate=os.getenv("OPENAI_CACHED_USD_PER_MILLION", ""),
            openai_output_rate=os.getenv("OPENAI_OUTPUT_USD_PER_MILLION", ""),
            price_reference=os.getenv("OPENAI_PRICE_REFERENCE", ""),
            task_queue=os.getenv("TASK_QUEUE", ""),
            worker_url=os.getenv("RESEARCH_WORKER_URL", ""),
            task_service_account=os.getenv("TASK_SERVICE_ACCOUNT", ""),
            vertex_model=os.getenv("VERTEX_MODEL", "gemini-2.5-flash"),
            allow_cloud_tasks=flag("ALLOW_CLOUD_TASKS"),
            voice_widget_id=os.getenv("DEMO_VOICE_WIDGET_ID", ""),
            voice_browser_origin=os.getenv("DEMO_VOICE_BROWSER_ORIGIN", ""),
            voice_isolated=flag("DEMO_VOICE_ISOLATED"),
            voice_phone=os.getenv("DEMO_VOICE_PHONE", ""),
            demo_video_url=os.getenv("DEMO_VIDEO_URL", cls.demo_video_url),
        )

    def validate(self):
        parsed_origin = urlparse(self.public_origin)
        if parsed_origin.path not in {"", "/"} or parsed_origin.query or parsed_origin.fragment or parsed_origin.username or parsed_origin.password:
            raise ValueError("Public origin must be a bare web origin")
        if not parsed_origin.hostname or parsed_origin.scheme not in {"http", "https"}:
            raise ValueError("Public origin requires HTTP or HTTPS")
        for identifier in (self.ghl_dashboard_field_id, self.ghl_dashboard_trigger_link_id):
            if identifier and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identifier):
                raise ValueError("Dashboard CRM configuration requires valid resource identifiers")
        if self.allow_crm_links:
            if not all((self.ghl_dashboard_field_id, self.ghl_dashboard_trigger_link_id, self.crm_cohort_tag)):
                raise ValueError("CRM links require verified dashboard field, trigger link and cohort configuration")
            if parsed_origin.scheme != "https":
                raise ValueError("CRM dashboard links require an HTTPS public origin")
        if self.demo_origin:
            demo = urlparse(self.demo_origin)
            if (demo.path not in {"", "/"} or demo.query or demo.fragment or demo.username or demo.password
                    or not demo.hostname):
                raise ValueError("Demo origin must be a bare web origin")
            if demo.scheme != "https" and not (demo.scheme == "http" and demo.hostname in {"127.0.0.1", "localhost"}):
                raise ValueError("Demo origin requires HTTPS, except loopback development")
        prices = (self.openai_input_rate, self.openai_cached_rate, self.openai_output_rate, self.price_reference)
        if any(prices) and not all(prices):
            raise ValueError("Configure all model rates and their pricing reference, or leave all unset")
        if all(prices):
            try:
                parsed = [Decimal(rate) for rate in prices[:3]]
            except InvalidOperation:
                raise ValueError("Model prices must be finite nonnegative numbers") from None
            if any(not rate.is_finite() or rate < 0 for rate in parsed):
                raise ValueError("Model prices must be finite nonnegative numbers")
        if self.max_global_ai_calls_per_hour < 0 or self.demo_ai_budget < 0:
            raise ValueError("AI call budgets cannot be negative")
        if self.cloud_sql_instance and not self.database_password_secret:
            raise ValueError("Cloud SQL requires a Secret Manager database password name")
        if self.secure_cookies and not self.public_origin.startswith("https://"):
            raise ValueError("Secure deployment requires an HTTPS public origin")
        if os.getenv("K_SERVICE") and not self.cloud_sql_instance:
            raise ValueError("Cloud Run requires durable Cloud SQL; SQLite is local development only")
        if self.voice_widget_id and not self.voice_isolated:
            raise ValueError("Voice demo must be explicitly verified as isolated")
        if self.voice_browser_origin:
            voice_origin(self.voice_browser_origin)
        if self.voice_widget_id:
            if not re.fullmatch(r"[a-f0-9]{24}", self.voice_widget_id) or self.voice_widget_id in PRODUCTION_VOICE_WIDGETS:
                raise ValueError("Only a dedicated demo widget ID is allowed; production widgets are blocked")
            if not self.voice_browser_origin or voice_origin(self.voice_browser_origin) == self.public_origin:
                raise ValueError("Browser voice must run on a separate configured origin")
        if self.voice_phone and not self.voice_isolated:
            raise ValueError("Call demo must be explicitly verified as isolated")
