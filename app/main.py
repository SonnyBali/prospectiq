"""FastAPI orchestration: authorization → cached research → typed advisor → durable history."""
from contextlib import asynccontextmanager
from datetime import timedelta
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import threading
import time
import uuid
from urllib.parse import parse_qs, urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, or_, select, text, update
from starlette.concurrency import run_in_threadpool

from .advisor import Advisor, plain_history, scenario_question
from .config import Settings
from .db import AccessLink, BrowserSession, FollowUp, Message, Prospect, RequestTrace, Usage, database, now
from .demo import DEMO_ID, seed_demo, voice_agents
from .integrations import CloudResearchQueue, HighLevelClient, SecretStore, VertexResearch
from .schemas import AccessInput, ChatInput, CRMImport, DeliveryInput, FollowUpInput, ProspectImport, ResearchTaskInput, SimulatorInput, Source
from .simulator import calculate

log = logging.getLogger("prospectiq")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
log.propagate = False
STATIC = Path(__file__).parent / "static"
COOKIE = "prospectiq_session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def create_app(settings=None, secret_store=None, advisor=None):
    settings = settings or Settings.from_env()
    settings.validate()
    secret_store = secret_store or SecretStore(settings.project)

    @asynccontextmanager
    async def lifespan(app):
        engine, factory, connector = database(settings, secret_store)
        app.state.engine, app.state.db = engine, factory
        app.state.advisor = advisor or Advisor(settings, secret_store)
        app.state.ai_lock = threading.Lock()
        app.state.crm_link_lock = threading.Lock()
        with factory() as db:
            if engine.dialect.name == "postgresql":
                # Serialize the synthetic fixture across overlapping revisions.
                db.execute(text("SELECT pg_advisory_xact_lock(789316104)"))
            seed_demo(db)
        yield
        if hasattr(app.state.advisor, "close"):
            app.state.advisor.close()
        engine.dispose()
        if connector:
            connector.close()

    app = FastAPI(title="ProspectIQ · FireWireAds", version="1.1.0", lifespan=lifespan)
    app.state.settings = settings

    def db_session():
        with app.state.db() as db:
            yield db

    def save_trace(request_id, session_id, method, route, status, duration_ms):
        with app.state.db() as db:
            db.add(RequestTrace(request_id=request_id, session_id=session_id,
                                method=method, route=route, status=status, duration_ms=duration_ms))
            db.commit()

    def session(request: Request, db=Depends(db_session)):
        token = request.cookies.get(COOKIE, "")
        current = db.scalar(select(BrowserSession).where(BrowserSession.token_hash == digest(token))) if token else None
        if not current or current.expires_at <= now():
            raise HTTPException(401, "Open the public demo or a valid prospect access link")
        if current.access_link_hash:
            link = db.get(AccessLink, current.access_link_hash)
            if not link or link.revoked or link.expires_at <= now():
                raise HTTPException(401, "Prospect access has expired or been revoked")
        request.state.session_id = current.id
        if request.method in {"POST", "DELETE", "PUT", "PATCH"}:
            if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), current.csrf_token):
                raise HTTPException(403, "Invalid CSRF token")
            origin = request.headers.get("Origin")
            if origin and origin != settings.public_origin:
                # An explicitly configured fallback serves only the built-in
                # public fixture. Capability-bound/private sessions stay canonical.
                public_demo = (settings.demo_origin and origin == settings.demo_origin
                               and origin == str(request.base_url).rstrip("/")
                               and current.prospect_id == DEMO_ID and not current.access_link_hash)
                prospect = db.get(Prospect, current.prospect_id) if public_demo else None
                if not prospect or not prospect.synthetic:
                    raise HTTPException(403, "Unexpected request origin")
        return current

    def admin(request: Request):
        if not settings.admin_secret:
            raise HTTPException(503, "Administrative API is not configured")
        supplied = request.headers.get("X-Admin-Key", "")
        if not supplied:
            raise HTTPException(401, "Administrative authorization required")
        try:
            expected = secret_store.get(settings.admin_secret)
        except Exception:
            raise HTTPException(503, "Administrative credential unavailable") from None
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(401, "Invalid administrative authorization")

    def new_session(db, prospect_id, response, link_hash=None):
        token = secrets.token_urlsafe(32)
        current = BrowserSession(token_hash=digest(token), prospect_id=prospect_id, csrf_token=secrets.token_urlsafe(32),
                                 expires_at=now() + timedelta(hours=settings.session_hours), access_link_hash=link_hash)
        db.add(current)
        db.commit()
        response.set_cookie(COOKIE, token, httponly=True, secure=settings.secure_cookies, samesite="strict",
                            max_age=settings.session_hours * 3600, path="/")
        return current

    def dashboard(db, current):
        prospect = db.get(Prospect, current.prospect_id)
        if not prospect or prospect.research_status != "complete" or not prospect.intelligence:
            raise HTTPException(409, "Completed research is required before dashboard access")
        return {"prospect": {"id": prospect.id, **prospect.profile, "synthetic": prospect.synthetic,
                              "research_completed_at": prospect.research_completed_at.isoformat() + "Z"},
                "intelligence": prospect.intelligence, "sources": prospect.sources,
                "advisor_mode": app.state.advisor.mode, "voice_agents": voice_agents(settings),
                "simulator_defaults": SimulatorInput().model_dump(), "csrf_token": current.csrf_token,
                "has_research_attribution": bool(prospect.research_attribution_html)}

    def reserve_ai(request_id, session_id, purpose):
        """Reserve before the provider call. A database lock enforces budgets across replicas."""
        with app.state.ai_lock, app.state.db() as db:
            if app.state.engine.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(789316102)"))
            else:
                db.execute(text("BEGIN IMMEDIATE"))
            hourly = db.scalar(select(func.count()).select_from(Usage).where(Usage.provider == "openai", Usage.created_at >= now() - timedelta(hours=1)))
            if hourly >= settings.max_global_ai_calls_per_hour:
                raise HTTPException(429, "The shared AI demonstration budget has been reached")
            if session_id:
                current = db.get(BrowserSession, session_id)
                prospect = db.get(Prospect, current.prospect_id)
                count = db.scalar(select(func.count()).select_from(Usage).where(Usage.session_id == session_id, Usage.provider == "openai"))
                budget = settings.demo_ai_budget if prospect.synthetic else settings.max_session_ai_calls
                if count >= budget:
                    raise HTTPException(429, "This session's AI demonstration budget has been reached")
            usage = Usage(request_id=request_id, session_id=session_id, provider="openai", model=settings.openai_model, purpose=purpose)
            db.add(usage)
            db.commit()
            return usage.id

    def run_advisor(db, request, prospect, message, history=None, scenario=None, purpose="chat", current=None):
        event_id = reserve_ai(request.state.request_id, current.id if current else None, purpose) if app.state.advisor.mode == "openai" else None
        try:
            result = app.state.advisor.answer(prospect, message, history or [], scenario, purpose)
        except Exception:
            if event_id:
                with app.state.db() as records:
                    records.get(Usage, event_id).status = "provider_error"
                    records.commit()
            # Do not log exception strings: SDK/HTTP errors may contain sensitive bodies.
            log.warning(json.dumps({"event": "provider_error", "request_id": request.state.request_id, "provider": "openai"}))
            raise HTTPException(502, "Advisor provider unavailable; your saved research remains available") from None
        values = {key: result.usage[key] for key in ("input_tokens", "output_tokens", "cached_input_tokens", "estimated_cost_usd", "price_reference")}
        if event_id:
            with app.state.db() as records:
                event = records.get(Usage, event_id)
                for key, value in values.items():
                    setattr(event, key, value)
                event.status = result.status
                records.commit()
        else:
            db.add(Usage(request_id=request.state.request_id, session_id=current.id if current else None, provider=result.provider,
                         model=result.usage["model"], purpose=purpose, status=result.status, **values))
            db.commit()
        log.info(json.dumps({"event": "advisor_usage", "request_id": request.state.request_id, "provider": result.provider,
                             "api_calls": result.usage.get("api_calls", 0), "usage_complete": result.usage.get("usage_complete", True),
                             "model": result.usage["model"], "status": result.status, **values}))
        return result

    def crm():
        try:
            location = secret_store.get(settings.ghl_location_secret)
            if not hmac.compare_digest(location, settings.ghl_location):
                raise ValueError("Tenant mismatch")
            return HighLevelClient(secret_store.get(settings.ghl_secret), settings.ghl_location)
        except Exception:
            raise HTTPException(503, "Tenant-bound CRM credentials unavailable") from None

    def mint(db, prospect, *, commit=True):
        if prospect.research_status != "complete" or not prospect.intelligence:
            raise HTTPException(409, "Complete research and intelligence before issuing access")
        raw = secrets.token_urlsafe(32)
        link = AccessLink(token_hash=digest(raw), prospect_id=prospect.id, expires_at=now() + timedelta(hours=settings.link_hours))
        db.add(link)
        if commit:
            db.commit()
        else:
            # Keep the prospect row lock through CRM readback; do not release
            # an unverified capability before the operator's contact write.
            db.flush()
        # The query identifies the client; it cannot authorize access. Keep the
        # capability in a fragment so ingress request-URL logs never receive it.
        return {"prospect_id": prospect.id,
                "dashboard_url": f"{settings.public_origin}/p?client={prospect.id}#{raw}",
                "expires_at": link.expires_at.isoformat() + "Z"}

    @app.middleware("http")
    async def trace_and_protect(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        started = time.perf_counter()
        length = request.headers.get("Content-Length", "")
        if length and (not length.isdigit() or int(length) > 65536):
            return JSONResponse({"detail": "Request body too large or invalid"}, status_code=413)
        if request.method in {"POST", "PUT", "PATCH"}:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 65536:
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse({"detail": "Request failed; no confidential diagnostics are exposed", "request_id": request.state.request_id}, status_code=500)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        route = getattr(request.scope.get("route"), "path", "/unmatched")
        if route.startswith("/api/"):
            await run_in_threadpool(save_trace, request.state.request_id, getattr(request.state, "session_id", None),
                                    request.method, route, response.status_code, elapsed)
            log.info(json.dumps({"event": "request_processed", "request_id": request.state.request_id, "method": request.method,
                                 "route": route, "status": response.status_code, "duration_ms": elapsed}))
        microphone = f'self "{settings.voice_browser_origin}"' if settings.voice_browser_origin else "self"
        script_sources, connect_sources, image_sources = "'self'", "'self'", "'self' data:"
        frame_sources = f"'self' {settings.voice_browser_origin}"
        # Marketing SDKs are allowed only on the public shell. The client waits
        # for a synthetic session, validates the canonical URL, and sends no
        # application fields. Private pages/API retain the strict default CSP.
        if (route == "/" and not request.url.query
                and settings.public_origin == "https://prospect.firewireads.com"
                and request.url.hostname == "prospect.firewireads.com"):
            script_sources += " https://www.googletagmanager.com https://connect.facebook.net https://www.googleadservices.com https://googleads.g.doubleclick.net https://www.google.com"
            analytics_sources = " https://*.google-analytics.com https://www.googleadservices.com https://googleads.g.doubleclick.net https://www.google.com https://www.facebook.com https://www.googletagmanager.com https://pagead2.googlesyndication.com"
            connect_sources += analytics_sources + " https://ad.doubleclick.net"
            image_sources += analytics_sources
            frame_sources += " https://td.doubleclick.net https://www.googletagmanager.com"
        response.headers.update({
            "X-Request-ID": request.state.request_id, "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Permissions-Policy": f"microphone=({microphone}), camera=(), geolocation=()",
            "Content-Security-Policy": f"default-src 'self'; script-src {script_sources}; style-src 'self'; img-src {image_sources}; connect-src {connect_sources}; media-src 'self' https://blog.firewireads.com; frame-src {frame_sources}; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        })
        if route != "/" and not route.startswith("/static/") and route not in {"/robots.txt", "/sitemap.xml"}:
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        if route == "/" and request.url.query:
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        if (route == "/" and settings.demo_origin
                and request.url.hostname == urlparse(settings.demo_origin).hostname
                and request.url.hostname != urlparse(settings.public_origin).hostname):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        if route == "/api/research-attribution":
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; script-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
        if settings.secure_cookies:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/")
    @app.get("/p")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/robots.txt")
    def robots():
        return Response("User-agent: *\nAllow: /\nDisallow: /p\nDisallow: /api/\nDisallow: /docs\nDisallow: /redoc\nDisallow: /openapi.json\n"
                        f"Sitemap: {settings.public_origin}/sitemap.xml\n", media_type="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        return Response('<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        f'<url><loc>{settings.public_origin}/</loc></url></urlset>', media_type="application/xml")

    @app.get("/health")
    def health():
        with app.state.db() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "advisor_mode": app.state.advisor.mode}

    @app.get("/api/demo")
    def demo(request: Request, response: Response, db=Depends(db_session)):
        existing = request.cookies.get(COOKIE, "")
        current = db.scalar(select(BrowserSession).where(BrowserSession.token_hash == digest(existing))) if existing else None
        if not current or current.prospect_id != DEMO_ID or current.expires_at <= now():
            current = new_session(db, DEMO_ID, response)
        request.state.session_id = current.id
        return dashboard(db, current)

    @app.post("/api/access")
    def access(payload: AccessInput, request: Request, response: Response, db=Depends(db_session)):
        origin = request.headers.get("Origin")
        if origin and origin != settings.public_origin:
            raise HTTPException(403, "Unexpected request origin")
        link = db.get(AccessLink, digest(payload.token))
        if not link or link.revoked or link.expires_at <= now():
            raise HTTPException(401, "Invalid or expired prospect link")
        if payload.client_id is not None and payload.client_id != link.prospect_id:
            raise HTTPException(401, "Invalid or expired prospect link")
        current = new_session(db, link.prospect_id, response, link.token_hash)
        request.state.session_id = current.id
        return dashboard(db, current)

    @app.get("/api/dashboard")
    def existing_dashboard(request: Request, current=Depends(session), db=Depends(db_session)):
        requested = request.query_params.getlist("client")
        if requested and (len(requested) != 1 or requested[0] != current.prospect_id):
            raise HTTPException(401, "Reopen the original access link for this client")
        return dashboard(db, current)

    @app.post("/api/simulate")
    def simulate(payload: SimulatorInput, current=Depends(session)):
        return calculate(payload)

    @app.post("/api/chat")
    def chat(payload: ChatInput, request: Request, current=Depends(session), db=Depends(db_session)):
        prospect = db.get(Prospect, current.prospect_id)
        history = list(reversed(db.scalars(select(Message).where(Message.session_id == current.id).order_by(Message.created_at.desc()).limit(12)).all()))
        scenario = calculate(payload.scenario) if payload.scenario else None
        result = run_advisor(db, request, prospect, payload.message, [{"role": m.role, "content": m.content} for m in history], scenario, current=current)
        explain_scenario = bool(scenario and scenario_question(payload.message))
        if explain_scenario:
            values = scenario["results"]
            result.answer.summary += (f" With your assumptions, the estimate is ${values['monthly_revenue']:,.2f} a month, "
                                      f"or ${values['annual_revenue']:,.2f} a year.")
        response_text = result.answer.summary
        db.add_all([Message(session_id=current.id, role="user", content=payload.message), Message(session_id=current.id, role="assistant", content=response_text)])
        db.commit()
        used = {id_ for c in result.answer.claims for id_ in c.source_ids} | {id_ for r in result.answer.recommendations for id_ in r.source_ids}
        used.update(getattr(result, "cited_source_ids", ()))
        return {"answer": result.answer.model_dump(), "plain_reply": response_text,
                "citations": [s for s in prospect.sources if s["id"] in used],
                "provider": result.provider, "advisor_status": result.status,
                "usage": result.usage, "request_id": request.state.request_id,
                "scenario": scenario, "scenario_explanation_included": explain_scenario}

    @app.get("/api/history")
    def history(current=Depends(session), db=Depends(db_session)):
        messages = db.scalars(select(Message).where(Message.session_id == current.id).order_by(Message.created_at).limit(100)).all()
        return {"messages": [{"role": m.role, "content": plain_history(m.content) if m.role == "assistant" else m.content} for m in messages]}

    @app.get("/api/research-attribution", response_class=HTMLResponse)
    def attribution(current=Depends(session), db=Depends(db_session)):
        prospect = db.get(Prospect, current.prospect_id)
        return HTMLResponse(prospect.research_attribution_html or "<p>No Google Search grounding attribution for this research.</p>")

    @app.delete("/api/session")
    def end_session(response: Response, current=Depends(session), db=Depends(db_session)):
        current.expires_at = now()
        db.add(current)
        db.commit()
        response.delete_cookie(COOKIE)
        return {"status": "ended"}

    @app.post("/api/follow-up")
    def follow_up(payload: FollowUpInput, current=Depends(session), db=Depends(db_session)):
        draft = FollowUp(prospect_id=current.prospect_id, intent=payload.intent, notes=payload.notes)
        db.add(draft)
        db.commit()
        return {"id": draft.id, "status": "draft", "message": "Implementation request saved as a draft for operator review. No CRM write or outreach occurred."}

    @app.get("/api/engineering")
    def engineering(current=Depends(session), db=Depends(db_session)):
        traces = db.scalars(select(RequestTrace).where(RequestTrace.session_id == current.id).order_by(RequestTrace.created_at.desc()).limit(15)).all()
        usage = {u.request_id: u for u in db.scalars(select(Usage).where(Usage.session_id == current.id)).all()}
        return {"architecture": [
            {"service": "HighLevel", "role": "Tenant- and cohort-bound contact read; review-only follow-up task"},
            {"service": "FastAPI", "role": "Authorization, simulator, session, typed advisor, safe request traces"},
            {"service": "Cloud Tasks + Vertex AI", "role": "Authenticated background research, source-grounded evidence persisted before access"},
            {"service": "OpenAI Responses", "role": "Structured claims and recommendations; observed claims validated against source excerpts"},
            {"service": "Cloud SQL PostgreSQL", "role": "Durable prospects, cached intelligence, hashed access links, chat, usage and review drafts"},
            {"service": "Secret Manager + Cloud Logging", "role": "Server-only credentials and JSON events without prompt/contact bodies"},
            {"service": "LeadConnector Voice AI", "role": "Recorded demo now; isolated browser/call demonstrations require verification"}],
            "integrations": {
                "database": "Cloud SQL configured" if settings.cloud_sql_instance else "Local SQLite connected; Cloud SQL unverified",
                "openai": "Responses SDK configured; see actual usage events" if app.state.advisor.mode == "openai" else "Guided scripted demo; OpenAI not configured",
                "research": "Queue configured; no operational claim without worker verification" if settings.task_queue else "Task queue not configured",
                "crm": "Server-side adapter; writes disabled" if not settings.allow_crm_followup else "Operator-approved task delivery enabled",
                "voice": "Recorded demonstration available; production agents blocked",
                "logging": "Structured JSON events on Cloud Run stdout" if os.getenv("K_SERVICE") else "Local JSON events; Cloud Logging ingestion requires deployed service verification",
            },
            "recent_requests": [{"request_id": t.request_id, "method": t.method, "route": t.route, "status": t.status,
                                 "duration_ms": t.duration_ms, "provider": usage[t.request_id].provider if t.request_id in usage else None,
                                 "usage": {"input_tokens": usage[t.request_id].input_tokens, "output_tokens": usage[t.request_id].output_tokens,
                                           "estimated_cost_usd": usage[t.request_id].estimated_cost_usd} if t.request_id in usage else None} for t in traces],
            "privacy": "Only this session's routes, timings and token totals are shown. No raw prompts, contact IDs, credentials or other sessions."}

    @app.post("/api/admin/prospects/import", dependencies=[Depends(admin)])
    def import_research(payload: ProspectImport, request: Request, db=Depends(db_session)):
        if not payload.synthetic and any(s.is_synthetic for s in payload.sources):
            raise HTTPException(422, "Real prospects cannot be grounded in synthetic evidence")
        if payload.synthetic and not all(s.is_synthetic for s in payload.sources):
            raise HTTPException(422, "Synthetic demo evidence must be explicitly marked synthetic")
        if payload.crm_contact_id:
            contact = crm().get_contact(payload.crm_contact_id)
            if settings.crm_cohort_tag not in contact.get("tags", []):
                raise HTTPException(403, "Contact is outside the approved FireWire ProspectIQ cohort")
        prospect = Prospect(profile={k: getattr(payload, k) for k in ("first_name", "company_name", "industry", "website")},
                            crm_contact_id=payload.crm_contact_id, synthetic=payload.synthetic,
                            sources=[s.model_dump(mode="json") for s in payload.sources], research_notes=payload.research_notes,
                            research_attribution_html=payload.research_attribution_html)
        # No provider call on dashboard load. Intelligence is computed here, before access is minted.
        result = run_advisor(db, request, prospect, "Summarize the business evidence and recommend a concise opportunity plan.", purpose="intelligence")
        if result.status != "completed" or not (result.answer.claims or result.answer.recommendations):
            raise HTTPException(502, "Intelligence was refused, incomplete or unsupported; no access link was issued")
        prospect.intelligence = result.answer.model_dump()
        prospect.research_status, prospect.research_completed_at = "complete", now()
        db.add(prospect)
        db.commit()
        return mint(db, prospect)

    @app.post("/api/admin/prospects/from-crm", dependencies=[Depends(admin)])
    def from_crm(payload: CRMImport, db=Depends(db_session)):
        try:
            contact = crm().get_contact(payload.contact_id)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "CRM contact could not be verified") from None
        if settings.crm_cohort_tag not in contact.get("tags", []):
            raise HTTPException(403, "Contact is outside the approved FireWire ProspectIQ cohort")
        if not contact.get("company_name"):
            raise HTTPException(422, "Company name is required before research")
        prospect = Prospect(profile={"first_name": contact.get("first_name") or "there", "company_name": contact["company_name"],
                                     "industry": "Business services", "website": contact.get("website") or ""},
                            crm_contact_id=contact["id"], synthetic=False)
        db.add(prospect)
        db.commit()
        return {"prospect_id": prospect.id, "research_status": "pending", "message": "Tenant-bound minimal company profile saved. Complete research before issuing access."}

    @app.post("/api/admin/prospects/{prospect_id}/research", dependencies=[Depends(admin)])
    def enqueue_research(prospect_id: str, db=Depends(db_session)):
        if not settings.allow_cloud_tasks:
            raise HTTPException(403, "Cloud Task creation is disabled pending operator approval")
        prospect = db.get(Prospect, prospect_id)
        if not prospect:
            raise HTTPException(404, "Prospect not found")
        if prospect.synthetic:
            raise HTTPException(403, "Synthetic demo never dispatches real research tasks")
        if prospect.research_status in {"queued", "researching", "complete"}:
            return {"prospect_id": prospect.id, "status": prospect.research_status}
        try:
            task_name = CloudResearchQueue(settings.project, settings.region, settings.task_queue,
                                           settings.worker_url, settings.task_service_account).enqueue(prospect_id)
        except Exception:
            raise HTTPException(502, "Research task could not be created; no access link was issued") from None
        # A fast worker may already have advanced this row while the task POST
        # was in flight. Never overwrite researching/complete with queued.
        db.execute(update(Prospect).where(Prospect.id == prospect.id, Prospect.research_status.in_(["pending", "failed"]))
                   .values(research_status="queued"))
        db.commit()
        db.refresh(prospect)
        return {"prospect_id": prospect.id, "status": prospect.research_status, "task": task_name}

    @app.post("/api/internal/research")
    def research_worker(payload: ResearchTaskInput, request: Request, db=Depends(db_session)):
        if not settings.worker_url or not settings.task_service_account:
            raise HTTPException(503, "Research worker identity is not configured")
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token
        bearer = request.headers.get("Authorization", "")
        try:
            worker = urlparse(settings.worker_url)
            identity = id_token.verify_oauth2_token(bearer.removeprefix("Bearer "), GoogleRequest(), audience=f"{worker.scheme}://{worker.netloc}")
            if identity.get("email") != settings.task_service_account or identity.get("email_verified") is not True:
                raise ValueError("Unexpected identity")
        except Exception:
            raise HTTPException(401, "A verified Cloud Tasks service identity is required") from None
        prospect = db.get(Prospect, payload.prospect_id)
        if not prospect or prospect.synthetic:
            raise HTTPException(404, "Research target unavailable")
        if prospect.research_status == "complete":
            return {"status": "complete", "cached": True}
        # Lease prevents duplicate provider charges on concurrent Cloud Tasks retries.
        changed = db.execute(update(Prospect).where(Prospect.id == prospect.id, or_(
            Prospect.research_status.in_(["queued", "pending", "failed"]),
            and_(Prospect.research_status == "researching", Prospect.research_lease_expires_at <= now())))
            .values(research_status="researching", research_lease_expires_at=now() + timedelta(minutes=10))).rowcount
        db.commit()
        if not changed:
            raise HTTPException(409, "Research already in progress; inspect stale leases before retry")
        try:
            evidence = VertexResearch(settings.project, settings.region, settings.vertex_model).research(prospect.profile["company_name"], prospect.profile.get("website", ""))
            sources = [Source.model_validate(item).model_dump(mode="json") for item in evidence["sources"]]
            if not sources:
                raise ValueError("No grounded evidence")
            prospect.sources, prospect.research_notes = sources, evidence["notes"]
            prospect.research_attribution_html = evidence.get("search_suggestions_html", "")
            result = run_advisor(db, request, prospect, "Summarize sourced business opportunities; abstain on missing evidence.", purpose="intelligence")
            if result.status != "completed" or not (result.answer.claims or result.answer.recommendations):
                raise ValueError("Intelligence was refused, incomplete or unsupported")
            prospect.intelligence = result.answer.model_dump()
            prospect.research_status, prospect.research_completed_at = "complete", now()
            prospect.research_lease_expires_at = None
            db.commit()
        except Exception:
            db.rollback()
            prospect = db.get(Prospect, payload.prospect_id)
            prospect.research_status = "failed"
            prospect.research_lease_expires_at = None
            db.commit()
            raise HTTPException(502, "Research could not be completed; no access link was issued") from None
        return {"status": "complete", "source_count": len(sources)}

    @app.post("/api/admin/prospects/{prospect_id}/access", dependencies=[Depends(admin)])
    def issue_link(prospect_id: str, db=Depends(db_session)):
        prospect = db.get(Prospect, prospect_id)
        if not prospect:
            raise HTTPException(404, "Prospect not found")
        return mint(db, prospect)

    @app.post("/api/admin/prospects/{prospect_id}/highlevel-link", dependencies=[Depends(admin)])
    def highlevel_link(prospect_id: str, payload: DeliveryInput, db=Depends(db_session)):
        if not settings.allow_crm_links:
            raise HTTPException(403, "HighLevel dashboard link assignment is disabled")
        with app.state.crm_link_lock:
            # PostgreSQL serializes this prospect across instances; the local
            # mutex also makes the SQLite development contract deterministic.
            prospect = db.scalar(select(Prospect).where(Prospect.id == prospect_id).with_for_update())
            if not prospect:
                raise HTTPException(404, "Prospect not found")
            if prospect.synthetic or not prospect.crm_contact_id:
                raise HTTPException(403, "Synthetic or unlinked prospects cannot receive CRM dashboard links")
            if prospect.research_status != "complete" or not prospect.intelligence:
                raise HTTPException(409, "Completed company research is required before CRM dashboard access")
            client = crm()
            try:
                field = client.get_dashboard_field(settings.ghl_dashboard_field_id)
                trigger = client.get_dashboard_trigger_link(settings.ghl_dashboard_trigger_link_id)
                contact = client.get_contact(prospect.crm_contact_id)
                tags = contact.get("tags")
                if contact.get("dnd") or not isinstance(tags, list) or settings.crm_cohort_tag not in tags:
                    raise HTTPException(403, "Contact is suppressed or outside the approved dashboard cohort")
                existing_url = client._contact_fields(contact).get(field["id"])
                if existing_url:
                    try:
                        client._validate_dashboard_url(existing_url, settings.public_origin)
                        parsed = urlparse(existing_url)
                        link = db.get(AccessLink, digest(parsed.fragment))
                        reusable = (parse_qs(parsed.query).get("client") == [prospect.id] and link is not None
                                    and link.prospect_id == prospect.id and not link.revoked and link.expires_at > now())
                    except (ValueError, TypeError):
                        reusable = False
                    if reusable:
                        db.commit()
                        return {"status": "verified", "prospect_id": prospect.id, "dashboard_url": existing_url,
                                "expires_at": link.expires_at.isoformat() + "Z", "reused": True,
                                "trigger_link_id": trigger["id"], "trigger_link_key": trigger["fieldKey"],
                                "message": "Existing active client link verified. No email or SMS was sent."}
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502, "Dashboard CRM configuration or contact could not be verified") from None
            issued = mint(db, prospect, commit=False)
            token_hash = digest(urlparse(issued["dashboard_url"]).fragment)
            try:
                verified = client.set_dashboard_url(prospect.crm_contact_id, field["id"], issued["dashboard_url"],
                                                    cohort_tag=settings.crm_cohort_tag, public_origin=settings.public_origin,
                                                    synthetic=prospect.synthetic)
                if verified.get("verified") is not True:
                    raise ValueError("Contact write not verified")
                db.commit()
            except Exception:
                # A provider timeout can still mean the URL was stored. Make
                # its capability unusable before returning a safe error; never
                # retry the provider write automatically.
                db.execute(update(AccessLink).where(AccessLink.token_hash == token_hash).values(revoked=True))
                db.commit()
                raise HTTPException(502, "HighLevel dashboard outcome unknown; new access revoked. Reconcile before retry") from None
            return {"status": "verified", **issued, "reused": False,
                    "trigger_link_id": trigger["id"], "trigger_link_key": trigger["fieldKey"],
                    "message": "Client dashboard field and native trigger link verified. No email or SMS was sent."}

    @app.delete("/api/admin/prospects/{prospect_id}/access", dependencies=[Depends(admin)])
    def revoke_links(prospect_id: str, db=Depends(db_session)):
        result = db.execute(update(AccessLink).where(AccessLink.prospect_id == prospect_id).values(revoked=True))
        db.commit()
        return {"status": "revoked", "link_count": result.rowcount}

    @app.get("/api/admin/follow-ups", dependencies=[Depends(admin)])
    def drafts(db=Depends(db_session)):
        items = db.scalars(select(FollowUp).where(FollowUp.status == "draft").order_by(FollowUp.created_at.desc()).limit(100)).all()
        return {"drafts": [{"id": item.id, "prospect_id": item.prospect_id, "intent": item.intent, "notes": item.notes, "status": item.status} for item in items]}

    @app.post("/api/admin/follow-ups/{draft_id}/deliver", dependencies=[Depends(admin)])
    def deliver(draft_id: str, payload: DeliveryInput, db=Depends(db_session)):
        if not settings.allow_crm_followup:
            raise HTTPException(403, "HighLevel delivery is disabled pending operator approval")
        draft = db.get(FollowUp, draft_id)
        if not draft:
            raise HTTPException(404, "Draft not found")
        prospect = db.get(Prospect, draft.prospect_id)
        if prospect.synthetic or not prospect.crm_contact_id:
            raise HTTPException(403, "Synthetic or unlinked prospects cannot reach HighLevel")
        client = crm()
        contact = client.get_contact(prospect.crm_contact_id)
        if contact.get("dnd") or any(tag.casefold() in {"stopai", "unsubscribe", "do not contact", "dnc"} for tag in contact.get("tags", [])):
            raise HTTPException(403, "Contact is suppressed; follow-up delivery blocked")
        if settings.crm_cohort_tag not in contact.get("tags", []):
            raise HTTPException(403, "Contact is outside the approved cohort")
        changed = db.execute(update(FollowUp).where(FollowUp.id == draft.id, FollowUp.status == "draft").values(status="delivery_pending")).rowcount
        db.commit()
        if not changed:
            return {"status": draft.status, "message": "Delivery already attempted; reconcile HighLevel before any retry"}
        try:
            # This creates an internal review task; it never sends a message or enrolls a workflow.
            result = client.create_followup_task(contact["id"], f"ProspectIQ review {draft.id}", draft.intent + "\n" + draft.notes)
            draft.provider_id, draft.status = result["id"], "delivered"
            db.commit()
        except Exception:
            draft.status = "delivery_unknown"
            db.commit()
            raise HTTPException(502, "HighLevel outcome unknown; reconcile the unique review task before retry") from None
        return {"status": draft.status, "provider_id": draft.provider_id, "message": "Internal review task created. No outreach sent."}

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
