// Exercise the served frontend in a VM. No network, credentials or provider SDK.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../app/static/app.js", import.meta.url), "utf8");
const origin = "https://prospect.firewireads.com";
const token = "FictionalOpaqueClientCapability_0123456789abcd";
const clientId = "FictionalClient_0123456789-abcd";
let cases = 0;

function harness(path, {accessStatus = 200, dashboardStatus = 200, synthetic = false, historyFailure = false, returnedClient = clientId} = {}) {
  const location = new URL(path, origin);
  const events = [];
  const requests = [];
  const analytics = [];
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, {
      hidden: false, classList: {toggle() {}, remove() {}},
      addEventListener() {}, replaceChildren() {}, getAttribute() { return null; },
    });
    return nodes.get(id);
  };
  const document = {
    getElementById(id) { events.push("dom"); return node(id); },
    querySelector() { return node("selected"); }, querySelectorAll() { return []; },
    createElement() { return node("created"); }, createTextNode(text) { return {textContent: text}; },
  };
  const session = {prospect: {id: returnedClient, synthetic}, csrf_token: "FictionalCsrf"};
  const window = {location, ProspectIQAnalytics: {startPublicDemo(value) { analytics.push(value); }}};
  const context = vm.createContext({
    window, location, document, URL, URLSearchParams, Intl, Map, Set,
    setTimeout, clearTimeout,
    history: {replaceState(_state, _title, path) {
      events.push("scrub");
      if (historyFailure) throw new Error("Mock browser denial");
      location.href = new URL(path, location).href;
    }},
    fetch(path, options) {
      events.push("fetch");
      requests.push({path, options, address: location.href});
      const status = path === "/api/access" ? accessStatus : path.startsWith("/api/dashboard") ? dashboardStatus : 200;
      return Promise.resolve({ok: status === 200, status,
        json: async () => status === 200 ? session : {detail: "Invalid private link"}});
    },
  });
  vm.runInContext(source, context, {filename: "app.js"});
  // Entry orchestration is under test; rendering already has independent browser
  // evidence. Replace it before the mocked asynchronous fetch resolves.
  vm.runInContext("renderSession = function () {};", context);
  return {context, location, events, requests, analytics, nodes};
}

async function settle() { await new Promise(resolve => setImmediate(resolve)); }

for (const path of [
  `/p?client=${clientId}#${token}`, `/?client=${clientId}#${token}`,
  `/p?utm_source=ghl&client=${clientId}&contact_id=untrusted#${token}`,
  `/p#${token}`, `/p#token=${token}`, `/p?client=${clientId}#${token.replace("_", "%5F")}`,
]) {
  const state = harness(path, {synthetic: true});
  await settle();
  assert.equal(state.location.pathname, "/p");
  const expectedClient = path.includes("client=") ? clientId : "";
  assert.equal(state.location.search, expectedClient ? `?client=${clientId}` : "");
  assert.equal(state.location.hash, "");
  assert.equal(state.events[0], "scrub", "Address must be sanitized before DOM setup");
  assert.equal(state.requests.length, 1);
  const request = state.requests[0];
  assert.equal(request.path, "/api/access");
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.credentials, "same-origin");
  assert.equal(request.options.cache, "no-store");
  assert.equal(request.address, `${origin}/p${expectedClient ? `?client=${clientId}` : ""}`);
  assert.ok(!request.address.includes(token), "Bearer capability must never enter an HTTP request URL");
  assert.deepEqual(JSON.parse(request.options.body), expectedClient ? {token, client_id: clientId} : {token});
  assert.equal(vm.runInContext("privateEntry.token", state.context), "");
  assert.equal(state.analytics.length, 0, "Even a synthetic private entry must not start tracking");
  cases++;
}

for (const path of [
  "/p?client=", "/?client=bad!", `/p?client=${clientId}&client=${clientId}#${token}`,
  `/p?client=${clientId}&client=other#${token}`, "/p?client=%2532%2533",
  `/p?client=${"a".repeat(101)}`, `/p?client=${clientId}%2Funsafe`,
  "/p#token=", `/p#token=${token}&token=${token}`,
  `/p#token=${token}&contact_id=untrusted`, "/p#%E0%A4%A", "/p#invalid-fragment",
]) {
  const state = harness(path);
  await settle();
  assert.equal(state.location.href, `${origin}/p`);
  assert.equal(state.events[0], "scrub");
  assert.equal(state.requests.length, 0, "Malformed/ambiguous capability cannot fall back to a cookie or demo");
  assert.equal(state.analytics.length, 0);
  assert.equal(state.nodes.get("load-error").hidden, false);
  cases++;
}

for (const fragment of ["short", "a".repeat(129), token + "/unsafe", "token=", `token=${token}&token=${token}`]) {
  const state = harness(`/p?client=${clientId}#${fragment}`);
  await settle();
  assert.equal(state.location.href, `${origin}/p?client=${clientId}`);
  assert.equal(state.requests.length, 0);
  assert.equal(state.analytics.length, 0);
  assert.equal(state.nodes.get("load-error").hidden, false);
  cases++;
}

// Failed exchange cannot show an older company's cookie through the retry action.
const rejected = harness(`/p?client=${clientId}#${token}`, {accessStatus: 401});
await settle();
await vm.runInContext("loadSession()", rejected.context);
assert.equal(rejected.requests.length, 1);
assert.equal(rejected.requests[0].path, "/api/access");
assert.equal(rejected.analytics.length, 0);
assert.equal(rejected.nodes.get("load-error").hidden, false);
cases++;

// An address-scrubbing failure must never send a token or load public tracking.
const denied = harness(`/p?client=${clientId}#${token}`, {historyFailure: true});
await settle();
assert.equal(denied.requests.length, 0);
assert.equal(denied.analytics.length, 0);
assert.equal(denied.nodes.get("load-error").hidden, false);
cases++;

for (const path of ["/p", "/p#overview", "/p#evidence-2"]) {
  const refresh = harness(path);
  await settle();
  assert.equal(refresh.requests.length, 1);
  assert.equal(refresh.requests[0].path, "/api/dashboard");
  assert.equal(refresh.analytics.length, 0);
  cases++;
}

// Client ID alone carries no authority. The server must validate the existing
// session against it before returning research; the UI never falls back to demo.
for (const path of [`/p?client=${clientId}`, `/?client=${clientId}`, `/p?client=${clientId}#overview`]) {
  const refresh = harness(path, {synthetic: true});
  await settle();
  assert.equal(refresh.location.href, `${origin}/p?client=${clientId}`);
  assert.equal(refresh.requests.length, 1);
  assert.equal(refresh.requests[0].path, `/api/dashboard?client=${clientId}`);
  assert.equal(refresh.analytics.length, 0);
  cases++;
}
for (const status of [401, 403]) {
  const unauthorized = harness(`/p?client=${clientId}`, {dashboardStatus: status});
  await settle();
  assert.equal(unauthorized.requests.length, 1);
  assert.equal(unauthorized.requests[0].path, `/api/dashboard?client=${clientId}`);
  assert.equal(unauthorized.analytics.length, 0);
  assert.equal(unauthorized.nodes.get("load-error").hidden, false);
  cases++;
}
const mismatch = harness(`/p?client=${clientId}#${token}`, {returnedClient: "OtherClient"});
await settle();
assert.equal(vm.runInContext("state.session", mismatch.context), null);
assert.equal(mismatch.analytics.length, 0);
assert.equal(mismatch.nodes.get("load-error").hidden, false);
cases++;

const publicDemo = harness("/#overview", {synthetic: true});
await settle();
assert.equal(publicDemo.requests.length, 1);
assert.equal(publicDemo.requests[0].path, "/api/demo");
assert.deepEqual(publicDemo.analytics, [true]);
cases++;

// Disclosures must distinguish a fictional fixture from completed public research.
const fixture = vm.runInContext('personalizationDisclosure({prospect: {synthetic: true, company_name: "Fixture Co"}, has_research_attribution: true})', publicDemo.context);
assert.ok(fixture.includes("fictional company data and synthetic evidence"));
assert.ok(!fixture.includes("public website research"));
const researched = vm.runInContext('personalizationDisclosure({prospect: {synthetic: false, company_name: "<Client Co>"}, has_research_attribution: true})', publicDemo.context);
assert.ok(researched.includes("AI-personalized for <Client Co> using saved public website research"));
assert.ok(researched.includes("opportunities need your confirmation"));
const imported = vm.runInContext('personalizationDisclosure({prospect: {synthetic: false, company_name: "Imported Co"}})', publicDemo.context);
assert.ok(!imported.includes("public website research"));
assert.ok(imported.includes("saved business context and evidence"));
cases += 3;

// Exercise the actual conversation renderer in the same offline frontend VM.
// Text is never interpreted as HTML; grounding/usage remains outside chat bubbles.
class RenderNode {
  constructor(tag = "div") {
    this.tagName = tag;
    this.children = [];
    this.className = "";
    this.attributes = {};
    this.value = "";
    this.hidden = false;
    this.classList = {toggle() {}, remove() {}, add() {}};
    this.ownText = "";
  }
  set textContent(value) { this.ownText = String(value); this.children = []; }
  get textContent() { return this.ownText + this.children.map(child => child.textContent || "").join(""); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.ownText = ""; this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  focus() {}
}
const conversation = publicDemo.context;
const renderNodes = new Map();
conversation.document.getElementById = id => {
  if (!renderNodes.has(id)) renderNodes.set(id, new RenderNode());
  return renderNodes.get(id);
};
conversation.document.createElement = tag => new RenderNode(tag);
let chatRendererCases = 0;
assert.equal(vm.runInContext('advisorReply({plain_reply: "A simple answer.", answer: {summary: "Old summary"}})', conversation), "A simple answer.");
assert.equal(vm.runInContext('advisorReply({answer: {summary: "Compatible summary"}})', conversation), "Compatible summary");
assert.equal(vm.runInContext('advisorReply({plain_reply: "  ", answer: {summary: "Fallback summary"}})', conversation), "Fallback summary");
assert.ok(vm.runInContext('advisorReply({})', conversation).includes("try asking again"));
chatRendererCases += 4;

const escaped = vm.runInContext('appendMessage("assistant", "<img src=x onerror=alert(1)>\\n\\nSecond paragraph")', conversation);
const escapedBubble = escaped.children[1];
assert.equal(escapedBubble.children.length, 2);
assert.equal(escapedBubble.children[0].tagName, "p");
assert.equal(escapedBubble.children[0].textContent, "<img src=x onerror=alert(1)>");
assert.ok(!escapedBubble.children.some(child => child.tagName === "img"));
chatRendererCases++;

const assumptions = {monthly_leads: 400, missed_rate: 0.25, recovery_rate: 0.6,
  booking_rate: 0.5, close_rate: 0.3, average_sale: 1200, monthly_cost: 497};
const results = {monthly_revenue: 10800, annual_revenue: 129600, monthly_net: 10303, new_customers: 9};
conversation.responseFixture = {plain_reply: "Start with a recruiter briefing assistant.",
  answer: {summary: "Legacy summary", claims: [{text: "Raw quote E2", source_ids: ["source2"]}],
    recommendations: [{title: "Verbose title", rationale: "Hypothesis: long implementation details", source_ids: ["source2"]}],
    unknowns: ["Some generated statements were withheld."]},
  citations: [{id: "source2", title: "Staffing context", excerpt: "Retained public staffing evidence", url: "https://example.com/services", observed_at: "2026-10-08T00:00:00Z"}],
  provider: "openai", request_id: "FictionalRequest", usage: {input_tokens: 100, output_tokens: 20, estimated_cost_usd: 0.001},
  scenario: {assumptions, results}, scenario_explanation_included: false};
vm.runInContext('state.session = {advisor_mode: "openai"}; api = async () => responseFixture; validCurrentScenario = () => responseFixture.scenario.assumptions;', conversation);
await vm.runInContext('sendChat("Can it connect to recruiting?")', conversation);
let messages = renderNodes.get("chat-messages");
let last = messages.children.at(-1);
assert.equal(last.children[0].textContent, "Advisor");
assert.equal(last.children[1].textContent, conversation.responseFixture.plain_reply);
for (const excluded of ["E2", "E3", "Raw quote", "Verbose title", "Hypothesis", "withheld", "Limits", "FictionalRequest", "tokens", "$0.001"]) {
  assert.ok(!last.textContent.includes(excluded), `Chat must not expose ${excluded}`);
}
assert.equal(last.children.length, 2, "No per-message diagnostics are appended");
assert.ok(!last.textContent.includes("Your estimate"), "Unrelated questions do not display scenario rows");
chatRendererCases++;
assert.equal(vm.runInContext('state.sources.get("source2").excerpt', conversation), "Retained public staffing evidence");
assert.ok(renderNodes.get("evidence-sources").textContent.includes("Retained public staffing evidence"));
chatRendererCases++;

const citation = vm.runInContext('citations(["source2"])', conversation).children[0];
const sourceNumber = vm.runInContext('state.sourceNumbers.get("source2")', conversation);
assert.equal(citation.textContent, "Source");
assert.equal(citation.href, `#evidence-${sourceNumber}`);
assert.equal(citation.attributes["aria-label"], "Source: Staffing context");
const evidenceCard = renderNodes.get("evidence-sources").children.find(card => card.id === `evidence-${sourceNumber}`);
assert.equal(evidenceCard.children[0].children[0].textContent, "Research");
assert.ok(!/\bE\d+\b/.test(citation.textContent + evidenceCard.textContent));
const externalSource = evidenceCard.children.at(-1).children.find(child => child.tagName === "a");
assert.equal(externalSource.href, "https://example.com/services");
assert.equal(externalSource.rel, "noopener noreferrer");
chatRendererCases++;

conversation.responseFixture.scenario_explanation_included = true;
await vm.runInContext('sendChat("Explain my revenue scenario")', conversation);
last = messages.children.at(-1);
const scenarioBlock = last.children[1].children[1];
assert.equal(scenarioBlock.children[0].textContent, "Your estimate");
const displayed = scenarioBlock.children[1].children.map(row => row.children[1].textContent);
assert.deepEqual(displayed, ["$10,800", "$129,600", "$10,303", "9"]);
assert.equal(scenarioBlock.children.length, 2, "Do not repeat the warning paragraph");
chatRendererCases++;

conversation.responseFixture = {messages: [{role: "user", content: "Where should I start?"},
  {role: "assistant", content: "Start with a recruiter briefing assistant."}]};
await vm.runInContext("loadHistory()", conversation);
messages = renderNodes.get("chat-messages");
assert.equal(messages.children.length, 2);
assert.equal(messages.children[1].children[0].textContent, "Advisor");
assert.equal(messages.children[1].children[1].textContent, "Start with a recruiter briefing assistant.");
assert.equal(renderNodes.get("chat-status").textContent, "Your conversation is ready.");
chatRendererCases++;

conversation.responseFixture = {plain_reply: "A scripted answer.", provider: "guided_demo", citations: []};
vm.runInContext('state.session = {advisor_mode: "guided_demo"}; validCurrentScenario = () => null;', conversation);
await vm.runInContext('sendChat("Try the preview")', conversation);
assert.equal(messages.children.at(-1).children[0].textContent, "Guided demo");
assert.equal(messages.children.at(-1).children[1].textContent, "A scripted answer.");
chatRendererCases++;

vm.runInContext('api = async () => { throw new Error("The server could not complete this request. Please try again."); };', conversation);
await vm.runInContext('sendChat("Retryable question")', conversation);
assert.ok(renderNodes.get("chat-status").textContent.includes("Please try again"));
assert.equal(renderNodes.get("chat-input").value, "Retryable question");
chatRendererCases++;

console.log(JSON.stringify({status: "PASS", offline_only: true, cases,
  chat_renderer_cases: chatRendererCases,
  query_and_legacy_entry: true, scrub_before_dom_and_requests: true,
  ambiguous_entries_blocked: true, failed_exchange_cannot_reuse_old_cookie: true,
  private_tracking_blocked: true, no_browser_storage: true}));
