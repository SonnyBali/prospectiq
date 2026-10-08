"""All public data is fictional. Evidence fixtures have explicit synthetic labels."""
from .db import Prospect, now

DEMO_ID = "demo-copperline"


def seed_demo(db):
    if db.get(Prospect, DEMO_ID):
        return
    sources = [
        {
            "id": "demo_services", "title": "Synthetic company service profile", "url": "https://example.com/copperline/services",
            "excerpt": "Copperline Home Services is a fictional HVAC and plumbing company serving a fictional metro area.",
            "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True,
        },
        {
            "id": "demo_intake", "title": "Synthetic intake process observation", "url": "https://example.com/copperline/intake",
            "excerpt": "The fictional intake process directs after-hours callers to voicemail. Appointment requests require a staff callback.",
            "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True,
        },
        {
            "id": "demo_assumptions", "title": "Synthetic scenario worksheet", "url": "https://example.com/copperline/scenario",
            "excerpt": "All simulator inputs are editable hypothetical assumptions. No measured lead volume, conversion rate or revenue is provided.",
            "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True,
        },
    ]
    intelligence = {
        "summary": "Alex, explore how Copperline Home Services could improve after-hours intake and appointment handoffs. This is a fictional business demonstration.",
        "claims": [{"text": sources[1]["excerpt"], "source_ids": ["demo_intake"]}],
        "recommendations": [
            {"title": "After-hours AI receptionist", "rationale": "Hypothesis: offer a staffed-feeling intake path when the documented fictional process reaches voicemail. Validate escalation and coverage before implementation.", "source_ids": ["demo_intake"]},
            {"title": "Appointment request assistant", "rationale": "Hypothesis: collect service needs and preferred times to simplify staff callbacks. Calendar access and booking rules require approval.", "source_ids": ["demo_intake", "demo_services"]},
            {"title": "Consent-aware CRM follow-up", "rationale": "Hypothesis: prepare a reviewable implementation task in HighLevel. Outreach requires verified consent and operator approval.", "source_ids": ["demo_assumptions"]},
        ],
        "unknowns": ["Actual missed-call volume", "Measured appointment conversion", "Customer consent", "Integration availability"],
    }
    db.add(Prospect(id=DEMO_ID, profile={"first_name": "Alex", "company_name": "Copperline Home Services", "industry": "HVAC & plumbing", "website": "https://example.com/copperline"}, synthetic=True, sources=sources, intelligence=intelligence, research_status="complete", research_completed_at=now()))
    db.commit()


def voice_agents(settings):
    roles = [
        ("receptionist", "Ace · Receptionist", "AI receptionist", "A homeowner calls after hours about an HVAC problem. Practice service intake and a safe staff handoff.", "Act as a homeowner whose AC stopped working. Ask about service availability. Use fictional details."),
        ("sales", "Sunny · Sales advisor", "Sales qualification", "Explore a business owner's lead-response needs and an opportunity audit.", "Act as a fictional business owner losing calls after hours. Ask how an opportunity audit works."),
        ("appointments", "Ace · Appointment assistant", "Appointment setting", "Practice collecting service needs and preferred visit times without a real calendar booking.", "Ask about a fictional maintenance visit next week. Do not provide real contact information."),
    ]
    agents = []
    for id_, name, role, description, scenario in roles:
        agents.append({"id": id_, "name": name, "role": role, "description": description, "scenario": scenario,
                       "mode": "disabled", "enabled": False,
                       "reason": "Existing agents can affect real CRM workflows. A dedicated isolated demo agent must be verified before live interaction."})
    if settings.demo_video_url:
        agents[0].update(mode="recorded", enabled=True, video_url=settings.demo_video_url,
                         reason="Recorded FireWireAds demonstration; playback does not start a live agent.")
    if settings.voice_isolated and settings.voice_phone:
        agents[1].update(mode="call", enabled=True, phone=settings.voice_phone,
                         reason="Operator-configured isolated call demonstration. Your carrier may charge for the call.")
    if settings.voice_isolated and settings.voice_widget_id:
        # Served only after explicit user click; credentials are never in the configuration.
        agents[1].update(mode="browser", enabled=True, browser_url=settings.voice_browser_origin,
                         reason="Operator-configured separate-origin LeadConnector demo adapter. End-to-end audio requires validation; microphone permission required.")
    return agents
