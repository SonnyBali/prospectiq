"""Optional separate-origin native voice adapter. No CRM, database or secrets.

Run independently from main.py, only with an audited isolated demo widget.
The production widget IDs are explicitly blocked. Loading this server does not
load a provider script; a visitor must choose to load the native controls.
"""
import os
from pathlib import Path
import re

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from .config import PRODUCTION_VOICE_WIDGETS, voice_origin


def create_voice_app(widget_id="", isolated=False, parent_origin="http://127.0.0.1:8091"):
    parent_origin = voice_origin(parent_origin)
    if widget_id and (not isolated or not re.fullmatch(r"[a-f0-9]{24}", widget_id) or widget_id in PRODUCTION_VOICE_WIDGETS):
        raise ValueError("Voice adapter requires an isolated non-production widget")
    app = FastAPI(title="ProspectIQ isolated voice adapter", docs_url=None, redoc_url=None, openapi_url=None)
    static = Path(__file__).parent / "static"

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": f"default-src 'none'; script-src 'self' https://widgets.leadconnectorhq.com; style-src 'self' 'unsafe-inline' https://widgets.leadconnectorhq.com; img-src https: data:; connect-src https: wss:; media-src https: blob:; frame-src https:; font-src https: data:; object-src 'none'; base-uri 'none'; frame-ancestors {parent_origin}",
                                 "Permissions-Policy": "microphone=(self), camera=(), geolocation=()"})
        return response

    @app.get("/", response_class=HTMLResponse)
    def page():
        if not widget_id:
            return HTMLResponse("<p>Isolated browser voice demonstration is not configured.</p>", status_code=503)
        return HTMLResponse(static.joinpath("voice.html").read_text(encoding="utf-8").replace("__WIDGET_ID__", widget_id))

    @app.get("/voice.js")
    def script():
        return FileResponse(static / "voice.js", media_type="application/javascript")

    return app


app = create_voice_app(os.getenv("DEMO_VOICE_WIDGET_ID", ""), os.getenv("DEMO_VOICE_ISOLATED", "").lower() == "true",
                       os.getenv("VOICE_ALLOWED_PARENT_ORIGIN", "http://127.0.0.1:8091"))
