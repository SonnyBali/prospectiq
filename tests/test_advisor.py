import json
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI

from app.advisor import Advisor, SOLUTION_CATALOGUE, estimate_cost, plain_history, safe_answer
from app.config import Settings
from app.schemas import AdvisorAnswer, SimulatorInput
from app.simulator import calculate

SOURCES = [{"id": "intake", "excerpt": "After-hours callers reach voicemail.", "title": "Intake", "url": "https://example.com/intake", "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True}]
STAFFING_SOURCE = {"id": "talent", "title": "Official talent services saved-excerpt fixture",
                   "url": "https://insightglobal.com/services/talent-services/",
                   "excerpt": "Two ways to get there: staffing for the role in front of you, RPO when hiring volume outgrows your team."}
RECRUITER_TITLES = ("Recruiter briefing assistant", "Candidate scheduling assistant",
                    "Source-grounded company research", "Candidate communication review")


def answer(**kwargs):
    return AdvisorAnswer(summary="Untrusted model summary", claims=kwargs.get("claims", []), recommendations=kwargs.get("recommendations", []), unknowns=kwargs.get("unknowns", []))


def test_source_id_alone_does_not_validate_a_claim():
    result = safe_answer(answer(claims=[{"text": "The company is the market leader.", "source_ids": ["intake"]}]), SOURCES, "Example")
    assert result.claims == []
    assert "withheld" in " ".join(result.unknowns)


def test_exact_excerpt_claim_and_valid_source_are_retained():
    result = safe_answer(answer(claims=[{"text": "After-hours callers reach voicemail.", "source_ids": ["intake"]}]), SOURCES, "Example")
    assert len(result.claims) == 1


@pytest.mark.parametrize("title,source,question", [
    ("After-hours AI receptionist", SOURCES[0], "How can we handle calls?"),
    ("Recruiter briefing assistant", STAFFING_SOURCE, "Can it help with recruiting?"),
])
def test_simple_reply_uses_reviewed_suggestion_without_model_prose_or_warning_copy(title, source, question):
    result = safe_answer(answer(recommendations=[{"title": title, "source_ids": [source["id"]],
                                                "rationale": "Guaranteed $999999 profit. Already connected to your CRM."}],
                                unknowns=["Invented private company fact"]), [source], "Example", question=question)
    assert 5 < len(result.summary.split()) <= 60
    assert "could" in result.summary
    for forbidden in ("Hypothesis", "withheld", "Evidence-based", "999999", "Already connected", "Invented", "E2", "E3"):
        assert forbidden not in result.summary
    assert result.recommendations[0].source_ids == [source["id"]]
    assert result.unknowns  # Diagnostics stay available, outside the customer reply.


@pytest.mark.parametrize("claim,source_id", [("We guarantee market-leading results.", "intake"),
                                              ("After-hours callers reach voicemail.", "missing")])
def test_unsupported_answer_remains_a_gentle_request_for_detail(claim, source_id):
    result = safe_answer(answer(claims=[{"text": claim, "source_ids": [source_id]}]), SOURCES, "Example")
    assert not result.claims and not result.recommendations
    assert result.summary == "I need a little more information to answer that. Could you share more detail?"


def test_old_history_does_not_restore_the_verbose_recommendation_appendix():
    legacy = ("Evidence-based guidance for Example. Observations quote stored research; recommendations are hypotheses to validate.\n"
              "After-hours AI receptionist: Hypothesis: test intake. Confirm permissions before implementation.")
    assert plain_history(legacy) == "An AI receptionist could take messages after hours and pass requests to your team."
    simple = "An AI receptionist could help your team."
    assert plain_history(simple) == simple


def test_refused_response_stays_incomplete_with_a_short_readable_reply():
    sdk = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(
        status="incomplete", output_parsed=None, usage=SimpleNamespace(input_tokens=10, output_tokens=0))))
    result = Advisor(Settings(), None, sdk).answer(SimpleNamespace(profile={"company_name": "Example"},
                                                                 synthetic=True, sources=SOURCES), "Can you help?", [])
    assert result.status == "refused_or_incomplete"
    assert not result.answer.claims and not result.answer.recommendations
    assert result.answer.summary == "I couldn't answer that just now. Please try asking a different way."


def test_unknown_citations_fail_closed():
    result = safe_answer(answer(recommendations=[{"title": "Evidence validation", "rationale": "Anything", "source_ids": ["imaginary"]}]), SOURCES, "Example")
    assert result.recommendations == []


def test_model_cannot_smuggle_facts_or_numbers_through_recommendations():
    unsafe = answer(recommendations=[{"title": "Revenue scenario review", "rationale": "This business is bankrupt. Double {{monthly_revenue}} for one million dollars guaranteed!", "source_ids": ["intake"]}])
    scenario = calculate(SimulatorInput())
    result = safe_answer(unsafe, SOURCES, "Example", scenario)
    text = result.recommendations[0].rationale
    assert "bankrupt" not in text and "million" not in text and "Double" not in text and "guaranteed!" not in text
    assert "$8,100.00" in text
    assert scenario["results"]["monthly_revenue"] == 8100


def test_unknown_solutions_are_not_accepted():
    result = safe_answer(answer(recommendations=[{"title": "Invented miracle service", "rationale": "Guaranteed", "source_ids": ["intake"]}]), SOURCES, "Example")
    assert not result.recommendations


@pytest.mark.parametrize("title", RECRUITER_TITLES)
def test_staffing_recommendation_is_a_reviewed_hypothesis_without_generated_facts(title):
    scenario = calculate(SimulatorInput())
    proposed = answer(recommendations=[{"title": title,
                      "rationale": "Insight Global loses $999999 from missed calls; automatically reject candidates and guarantee placements.",
                      "source_ids": ["talent"]}])
    checked = safe_answer(proposed, [STAFFING_SOURCE], "Insight Global", scenario)
    assert len(checked.recommendations) == 1
    result = checked.recommendations[0]
    assert result.rationale.startswith("Hypothesis:")
    assert result.source_ids == ["talent"]
    assert "999999" not in result.rationale and "missed calls" not in result.rationale
    assert "automatically reject" not in result.rationale and "guarantee placements" not in result.rationale
    assert not any(character.isdigit() for character in result.rationale)
    assert scenario["results"]["monthly_revenue"] == 8100


@pytest.mark.parametrize("title", RECRUITER_TITLES)
def test_recruiter_recommendation_requires_relevance_in_its_own_cited_excerpt(title):
    # A relevant company name/profile, source URL or an uncited staffing excerpt
    # cannot make the cited voicemail evidence support a recruiter suggestion.
    irrelevant = {**SOURCES[0], "title": "Staffing and AI", "url": STAFFING_SOURCE["url"]}
    proposed = answer(recommendations=[{"title": title, "rationale": "Hypothesis: test.", "source_ids": ["intake"]}])
    checked = safe_answer(proposed, [irrelevant, STAFFING_SOURCE], "Insight Global Staffing AI")
    assert checked.recommendations == []
    assert "withheld" in " ".join(checked.unknowns)


def test_technology_research_hypothesis_does_not_authorize_candidate_workflows():
    technology = {"id": "technology", "excerpt": "The saved test source describes cloud and machine learning services."}
    proposed = answer(recommendations=[{"title": title, "rationale": "Untrusted", "source_ids": ["technology"]}
                                      for title in RECRUITER_TITLES])
    checked = safe_answer(proposed, [technology], "Test technology provider")
    assert [item.title for item in checked.recommendations] == ["Source-grounded company research"]


def test_recruiter_source_acronyms_require_whole_terms_not_substrings():
    unrelated = {"id": "unrelated", "excerpt": "The business said it repaired a broken air conditioner."}
    proposed = answer(recommendations=[{"title": "Source-grounded company research", "rationale": "Untrusted", "source_ids": ["unrelated"]}])
    assert safe_answer(proposed, [unrelated], "Test company").recommendations == []


def test_recruiter_company_facts_still_require_the_complete_saved_excerpt():
    checked = safe_answer(answer(claims=[
        {"text": "Insight Global guarantees placements and has a private hiring budget of $999999.", "source_ids": ["talent"]},
        {"text": "staffing for the role in front of you", "source_ids": ["talent"]},
        {"text": STAFFING_SOURCE["excerpt"], "source_ids": ["talent"]},
    ]), [STAFFING_SOURCE], "Insight Global")
    assert [item.text for item in checked.claims] == [STAFFING_SOURCE["excerpt"]]
    assert "999999" not in checked.summary
    assert "withheld" in " ".join(checked.unknowns)


def test_model_prompt_and_server_acceptance_share_the_reviewed_catalogue():
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", usage=SimpleNamespace(input_tokens=1, output_tokens=1),
                               output_parsed=answer(recommendations=[{"title": "Recruiter briefing assistant",
                                                     "rationale": "Untrusted candidate rank", "source_ids": ["talent"]}]))
    sdk = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    result = Advisor(Settings(), None, sdk).answer(SimpleNamespace(profile={"company_name": "Insight Global"},
                                                 synthetic=False, sources=[STAFFING_SOURCE]), "Suggest an interview demonstration", [])
    instruction = requests[0]["instructions"]
    prompted_titles = {line.split(":", 1)[0][2:] for line in instruction.splitlines() if line.startswith("- ")}
    assert prompted_titles == set(SOLUTION_CATALOGUE)
    assert "Never make or automate hiring decisions" in instruction
    assert result.answer.recommendations[0].title == "Recruiter briefing assistant"
    assert "Untrusted candidate rank" not in result.answer.recommendations[0].rationale


@pytest.mark.parametrize("question", ["recruiting?", "Can it be connected to recruiting?"])
def test_short_recruiting_questions_receive_scoped_sdk_instruction_and_concrete_pilot(question):
    requests = []
    def parse(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(status="completed", usage=SimpleNamespace(input_tokens=1, output_tokens=1),
                               output_parsed=answer(recommendations=[{"title": "Recruiter briefing assistant",
                                                                     "rationale": "Untrusted", "source_ids": ["talent"]}]))
    sdk = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    result = Advisor(Settings(), None, sdk).answer(SimpleNamespace(profile={"company_name": "Insight Global"},
                                                 synthetic=False, sources=[STAFFING_SOURCE]), question, [])
    assert "current question explicitly concerns recruiting" in requests[0]["instructions"]
    assert "return claims=[]" in requests[0]["instructions"]
    assert "can be adapted for recruiting" in result.answer.summary
    assert "Python/FastAPI" in result.answer.recommendations[0].rationale
    assert "Untrusted" not in result.answer.recommendations[0].rationale
    assert "withheld" not in " ".join(result.answer.unknowns)


def test_cost_uses_uncached_and_cached_rates_separately():
    settings = Settings(openai_input_rate="0.40", openai_cached_rate="0.10", openai_output_rate="1.60", price_reference="test fixture")
    assert estimate_cost(settings, 1000, 400, 200) == .0006
    assert estimate_cost(Settings(), 1000, 400, 200) is None


def test_official_sdk_responses_parse_and_store_false():
    captured = []
    def transport(request):
        payload = json.loads(request.content)
        captured.append(payload)
        assert request.url.path == "/v1/responses"
        content = answer(claims=[{"text": "After-hours callers reach voicemail.", "source_ids": ["intake"]}], recommendations=[{"title": "After-hours AI receptionist", "rationale": "Hypothesis: test intake.", "source_ids": ["intake"]}]).model_dump_json()
        return httpx.Response(200, json={"id": "resp_test", "object": "response", "created_at": 1, "status": "completed", "model": "gpt-4.1-mini", "output": [{"id": "msg_test", "type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": content, "annotations": []}]}], "usage": {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 20}, "output_tokens": 50, "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 150}})
    sdk = OpenAI(api_key="test-only", http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    settings = Settings(openai_model="gpt-4.1-mini")
    result = Advisor(settings, None, sdk).answer(SimpleNamespace(profile={"company_name": "Example"}, synthetic=True, sources=SOURCES), "What should we do?", [{"role": "user", "content": "Earlier turn"}])
    assert result.provider == "openai"
    assert result.usage["cached_input_tokens"] == 20
    assert result.answer.claims[0].source_ids == ["intake"]
    assert captured[0]["store"] is False
    assert captured[0]["model"] == "gpt-4.1-mini"
    assert captured[0]["text"]["format"]["type"] == "json_schema"
    assert captured[0]["input"][1]["content"] == "Earlier turn"
    sdk.close()
