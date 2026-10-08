"use strict";

/*
 * The browser presents server results. Business research, model calls, session
 * validation, and all numerical calculations belong to the Python API.
 */
// Only the non-authorizing client ID enters the HTTP URL. The capability stays
// in the fragment until captured here, before DOM setup or provider requests.
function capturePrivateEntry() {
  const query = new URLSearchParams(location.search);
  const clients = query.getAll("client");
  const hasClient = query.has("client");
  const privatePath = location.pathname === "/p" || location.pathname.startsWith("/p/");
  if (!hasClient && !privatePath) return { isPrivate: false, clientId: "", token: "", error: "" };

  const fragment = location.hash.slice(1);
  const entry = { isPrivate: true, clientId: "", token: "", error: "" };
  const validClient = !hasClient || (clients.length === 1 && /^[A-Za-z0-9_-]{1,100}$/.test(clients[0]));
  if (hasClient && validClient) entry.clientId = clients[0];
  try {
    // Keep only the safe client ID; never preserve the fragment or CRM fields.
    const path = hasClient ? "/p" : location.pathname;
    history.replaceState(null, "", path + (entry.clientId ? `?client=${encodeURIComponent(entry.clientId)}` : ""));
  } catch (_) {
    entry.error = "The private link could not be removed from this address. Close this tab and reopen the original client link.";
    return entry;
  }
  if (!validClient) {
    entry.error = "This private link has an invalid or conflicting client identifier. Reopen the original client link.";
    return entry;
  }
  let credentialSupplied = false;
  if (fragment) {
    try {
      if (fragment.includes("=")) {
        credentialSupplied = true;
        const legacy = new URLSearchParams(fragment);
        if (legacy.getAll("token").length !== 1 || [...legacy.keys()].some((key) => key !== "token")) throw new Error();
        entry.token = legacy.get("token") || "";
      } else if (!["overview", "simulator", "voice-lab", "engineering"].includes(fragment) && !/^evidence-\d+$/.test(fragment)) {
        credentialSupplied = true;
        entry.token = decodeURIComponent(fragment);
      }
    } catch (_) { entry.error = "This private link is invalid. Reopen the original client link."; }
  }
  if (credentialSupplied && !/^[A-Za-z0-9_-]{32,128}$/.test(entry.token)) {
    entry.token = "";
    entry.error = "This private link is invalid. Reopen the original client link.";
  }
  return entry;
}

const privateEntry = capturePrivateEntry();
const state = {
  session: null,
  csrfToken: "",
  sources: new Map(),
  sourceNumbers: new Map(),
  lastCalculation: null,
  calculationSequence: 0,
  calculationTimer: null,
  calculationController: null,
  chatBusy: false,
  engineeringBusy: false,
  selectedAgent: null,
  loading: false,
  toastTimer: null,
  privateSession: privateEntry.isPrivate,
};

const $ = (id) => document.getElementById(id);
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 2 });
const quantity = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const rates = new Set(["missed_rate", "recovery_rate", "booking_rate", "close_rate"]);
const fields = ["monthly_leads", "missed_rate", "recovery_rate", "booking_rate", "close_rate", "average_sale", "monthly_cost"];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function displayText(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function safeHttpsUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch (_) { return null; }
}

function safeMediaUrl(value) {
  const external = safeHttpsUrl(value);
  if (external) return external;
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) return null;
  try {
    const url = new URL(value, location.origin);
    return url.origin === location.origin ? url.href : null;
  } catch (_) { return null; }
}

function safeVoiceBrowserUrl(value) {
  try {
    const url = new URL(value);
    const localDevelopment = url.protocol === "http:" && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
    if (url.username || url.password || url.origin === location.origin) return null;
    return url.protocol === "https:" || localDevelopment ? url.href : null;
  } catch (_) { return null; }
}

function friendlyDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function humanize(value) {
  return String(value || "unavailable").replaceAll("_", " ").replaceAll("-", " ");
}

function numerical(value, formatter = quantity) {
  return typeof value === "number" && Number.isFinite(value) ? formatter.format(value) : "—";
}

async function api(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && state.csrfToken) headers["X-CSRF-Token"] = state.csrfToken;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      cache: "no-store",
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("The application could not reach the server. Check your connection and try again.");
  }
  let payload;
  try { payload = await response.json(); } catch (_) { payload = null; }
  if (!response.ok) {
    let message;
    if (typeof payload?.detail === "string") message = payload.detail;
    else if (typeof payload?.error === "string") message = payload.error;
    else if (response.status === 429) message = "The request limit was reached. Wait a moment and try again.";
    else if (response.status === 401) message = "Your session has expired. Reopen your dashboard link or the public demo.";
    else if (response.status === 403) message = "This request could not be authorized. Reopen your dashboard to start a fresh session.";
    else if (response.status === 422) message = "Please check your inputs and try again.";
    else message = `The server could not complete this request (${response.status}). Please try again.`;
    throw new Error(message);
  }
  if (!payload || typeof payload !== "object") throw new Error("The server returned an unreadable response. Please try again.");
  return payload;
}

function status(id, text, isError = false) {
  const node = $(id);
  node.textContent = text;
  node.classList.toggle("error", isError);
}

function toast(message) {
  clearTimeout(state.toastTimer);
  $("toast").textContent = message;
  $("toast").hidden = false;
  state.toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4500);
}

function indexSources(sources) {
  if (!Array.isArray(sources)) return;
  for (const source of sources) {
    if (!source || typeof source.id !== "string") continue;
    if (!state.sourceNumbers.has(source.id)) state.sourceNumbers.set(source.id, state.sourceNumbers.size + 1);
    state.sources.set(source.id, source);
  }
}

function citations(sourceIds) {
  const list = el("span", "citation-list");
  if (!Array.isArray(sourceIds)) return list;
  for (const id of [...new Set(sourceIds)]) {
    if (!state.sources.has(id)) continue;
    const source = state.sources.get(id);
    const number = state.sourceNumbers.get(id);
    const link = el("a", "citation-chip", `E${number}`);
    link.href = `#evidence-${number}`;
    link.title = displayText(source.title, "Evidence source");
    link.setAttribute("aria-label", `Evidence ${number}: ${displayText(source.title, "Research source")}`);
    list.append(link);
  }
  return list;
}

function renderUnknowns(container, unknowns, heading = "What we still need to verify") {
  container.replaceChildren();
  const values = Array.isArray(unknowns) ? unknowns.filter((item) => typeof item === "string" && item.trim()) : [];
  container.hidden = values.length === 0;
  if (!values.length) return;
  container.append(el("strong", "", heading));
  for (const item of values) container.append(el("p", "", item));
}

function renderSources() {
  const container = $("evidence-sources");
  container.replaceChildren();
  $("source-count").textContent = `${state.sources.size} evidence ${state.sources.size === 1 ? "source" : "sources"}`;
  if (!state.sources.size) {
    const empty = el("div", "source-card");
    empty.append(el("h3", "", "No evidence sources available"), el("p", "", "Company-specific claims require evidence. Ask the advisor what should be researched next."));
    container.append(empty);
    return;
  }
  for (const [id, source] of state.sources) {
    const number = state.sourceNumbers.get(id);
    const card = el("article", "source-card");
    card.id = `evidence-${number}`;
    const top = el("div", "source-topline");
    top.append(el("span", "source-id", `E${number} / EVIDENCE`), el("span", "source-type", source.is_synthetic ? "SYNTHETIC" : "RESEARCH SOURCE"));
    card.append(top, el("h3", "", displayText(source.title, "Research source")), el("p", "", displayText(source.excerpt, "No excerpt available.")));
    const footer = el("div", "source-card-footer");
    footer.append(el("span", "", `Observed ${friendlyDate(source.observed_at)}`));
    const url = safeHttpsUrl(source.url);
    if (url && !source.is_synthetic) {
      const link = el("a", "", "View source ↗");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      footer.append(link);
    } else if (source.is_synthetic) footer.append(el("span", "", "Demo dataset"));
    card.append(footer);
    container.append(card);
  }
}

function renderIntelligence(intelligence) {
  $("intelligence-summary").textContent = displayText(intelligence?.summary, "Saved business intelligence is not available for this company yet.");
  const container = $("intelligence-claims");
  container.replaceChildren();
  const claims = Array.isArray(intelligence?.claims) ? intelligence.claims : [];
  for (const claim of claims) {
    const text = typeof claim === "string" ? claim : displayText(claim?.text);
    if (!text) continue;
    const item = el("div", "insight-item");
    const copy = el("p", "insight-text", text);
    copy.append(citations(claim?.source_ids));
    item.append(el("span", "insight-icon", "↗"), copy);
    container.append(item);
  }
  renderUnknowns($("intelligence-unknowns"), intelligence?.unknowns);
  const recommendations = $("recommendations");
  recommendations.replaceChildren();
  const entries = Array.isArray(intelligence?.recommendations) ? intelligence.recommendations : [];
  const symbols = ["◷", "↗", "◎"];
  entries.forEach((recommendation, index) => {
    const card = el("article", "recommendation-card");
    const icon = el("span", "recommendation-icon", symbols[index % symbols.length]);
    icon.setAttribute("aria-hidden", "true");
    const title = displayText(recommendation?.title, "Opportunity to investigate");
    card.append(icon, el("h3", "", title), el("p", "", displayText(recommendation?.rationale)), citations(recommendation?.source_ids));
    const button = el("button", "recommendation-question", "Discuss this opportunity ↗");
    button.type = "button";
    button.addEventListener("click", () => {
      focusAdvisor();
      sendChat(`Explain the recommendation "${title}" and the evidence behind it. What should we verify before implementing it?`);
    });
    card.append(button);
    recommendations.append(card);
  });
  if (!entries.length) {
    const empty = el("article", "recommendation-card");
    empty.append(el("h3", "", "Start with evidence"), el("p", "", "There is not enough saved research to make company-specific recommendations. Use the advisor to identify the information needed."));
    recommendations.append(empty);
  }
}

function setAssumptions(defaults) {
  for (const field of fields) {
    const input = document.querySelector(`#simulator-form [name="${field}"]`);
    const value = Number(defaults?.[field]);
    const shownValue = Number.isFinite(value) ? (rates.has(field) ? value * 100 : value) : 0;
    input.value = String(Math.round(shownValue * 100) / 100);
    syncSlider(field);
  }
}

function syncSlider(field) {
  const input = document.querySelector(`#simulator-form [name="${field}"]`);
  const slider = document.querySelector(`#simulator-form [data-range="${field}"]`);
  const value = Number(input.value);
  if (!Number.isFinite(value)) return;
  if (!rates.has(field) && value > Number(slider.max)) slider.max = String(Math.ceil(value * 1.2));
  slider.value = String(value);
  const percentage = (Number(slider.value) - Number(slider.min)) / (Number(slider.max) - Number(slider.min)) * 100;
  slider.style.background = `linear-gradient(to right, var(--cyan) 0%, var(--cyan) ${percentage}%, #2a3a4f ${percentage}%, #2a3a4f 100%)`;
}

function readAssumptions() {
  const result = {};
  for (const field of fields) {
    const input = document.querySelector(`#simulator-form [name="${field}"]`);
    if (input.value.trim() === "" || !input.validity.valid) throw new Error("Enter a valid value for each assumption. Rates must be between 0% and 100%.");
    const value = Number(input.value);
    if (!Number.isFinite(value)) throw new Error("All assumptions must be valid numbers.");
    result[field] = rates.has(field) ? value / 100 : value;
  }
  return result;
}

function assumptionsMatch(first, second) {
  return Boolean(first && second) && fields.every((field) => Math.abs(Number(first[field]) - Number(second[field])) < 0.00000001);
}

function validCurrentScenario() {
  try {
    const current = readAssumptions();
    return assumptionsMatch(current, state.lastCalculation?.assumptions) ? current : null;
  } catch (_) { return null; }
}

function scheduleCalculation() {
  clearTimeout(state.calculationTimer);
  state.calculationSequence += 1;
  if (state.calculationController) state.calculationController.abort();
  $("explain-scenario").disabled = true;
  $("simulator-results").setAttribute("aria-busy", "true");
  status("simulator-status", state.lastCalculation ? "Updating scenario… previous results are shown below." : "Calculating your scenario…");
  state.calculationTimer = setTimeout(calculateScenario, 350);
}

async function calculateScenario() {
  const sequence = ++state.calculationSequence;
  if (state.calculationController) state.calculationController.abort();
  const controller = new AbortController();
  state.calculationController = controller;
  let assumptions;
  try { assumptions = readAssumptions(); }
  catch (error) {
    status("simulator-status", error.message, true);
    $("simulator-results").setAttribute("aria-busy", "true");
    $("explain-scenario").disabled = true;
    return;
  }
  try {
    const calculation = await api("/api/simulate", { method: "POST", body: assumptions, signal: controller.signal });
    if (sequence !== state.calculationSequence) return;
    if (!calculation.results || !calculation.assumptions || !assumptionsMatch(calculation.assumptions, assumptions)) throw new Error("The server returned a different scenario. Change an assumption to retry.");
    state.lastCalculation = calculation;
    renderCalculation(calculation);
    status("simulator-status", "Scenario calculated by the Python API.");
    $("simulator-results").setAttribute("aria-busy", "false");
    $("explain-scenario").disabled = false;
  } catch (error) {
    if (error.name === "AbortError" || sequence !== state.calculationSequence) return;
    status("simulator-status", error.message, true);
    $("simulator-results").setAttribute("aria-busy", "true");
    $("explain-scenario").disabled = true;
  }
}

function renderCalculation(calculation) {
  const results = calculation.results;
  for (const name of ["monthly_revenue", "annual_revenue", "monthly_net"]) $(name.replaceAll("_", "-")).textContent = numerical(results[name], money);
  for (const name of ["missed_leads", "recovered_leads", "booked_appointments", "new_customers"]) $(name.replaceAll("_", "-")).textContent = numerical(results[name]);
  $("roi-percent").textContent = results.roi_percent === null || results.roi_percent === undefined ? "N/A (zero cost)" : `${numerical(results.roi_percent)}%`;
  const formulas = $("formulas");
  formulas.replaceChildren();
  const entries = calculation.formulas;
  if (Array.isArray(entries)) {
    for (const formula of entries) {
      const text = typeof formula === "string" ? formula : [formula?.name, formula?.formula].filter((item) => typeof item === "string").join(": ");
      if (text) formulas.append(el("code", "", text));
    }
  } else if (entries && typeof entries === "object") {
    for (const [name, expression] of Object.entries(entries)) {
      if (typeof expression === "string") formulas.append(el("code", "", `${humanize(name)} = ${expression}`));
    }
  }
  const breakEven = results.break_even_customers;
  $("break-even-note").textContent = typeof breakEven === "number" && Number.isFinite(breakEven) ? `Break-even: ${quantity.format(breakEven)} additional customers cover the monthly AI cost, before other business expenses.` : "Break-even cannot be calculated when the average sale value is zero.";
}

function scenarioOptions(agent) {
  const base = displayText(agent.scenario, "A new customer asks about your business.");
  const role = `${agent.role || ""} ${agent.name || ""}`.toLowerCase();
  const options = [{ title: "Suggested scenario", description: base }];
  if (role.includes("reception")) options.push(
    { title: "After-hours inquiry", description: "It's after closing time. A new caller needs help, asks whether you serve their area, and wants to know the next step." },
    { title: "A customer with questions", description: "Ask about a service, explain what you need, and request a callback. Observe how the agent collects context." },
  );
  else if (role.includes("sale")) options.push(
    { title: "Researching a solution", description: "You are comparing providers. Describe your business needs, ask how the solution works, and raise a realistic objection." },
    { title: "Budget and fit", description: "Ask what information is needed to assess fit and pricing. Observe whether the agent avoids unsupported promises." },
  );
  else options.push(
    { title: "First appointment", description: "Ask to schedule a first consultation. Describe your availability and the service you are interested in." },
    { title: "Scheduling questions", description: "Ask what to expect at an appointment and how to arrange a time. This scenario must use an isolated demo calendar." },
  );
  return options;
}

function renderAgents(agents) {
  const selector = $("agent-selector");
  selector.replaceChildren();
  const list = Array.isArray(agents) ? agents : [];
  if (!list.length) {
    $("agent-stage").hidden = true;
    selector.append(el("p", "section-description", "No voice demonstrations are configured for this session."));
    return;
  }
  list.forEach((agent, index) => {
    const button = el("button", "agent-select-button");
    button.type = "button";
    button.dataset.agentIndex = String(index);
    button.setAttribute("aria-pressed", "false");
    const copy = el("span", "");
    copy.append(el("strong", "", displayText(agent.role, displayText(agent.name, "Voice agent"))), el("small", "", agent.enabled && agent.mode === "recorded" ? "Recorded demonstration" : agent.enabled ? humanize(agent.mode) : "Live demo unavailable"));
    button.append(el("span", "agent-number", String(index + 1).padStart(2, "0")), copy);
    button.addEventListener("click", () => selectAgent(agent, index));
    selector.append(button);
  });
  selectAgent(list[0], 0);
}

function selectAgent(agent, index) {
  state.selectedAgent = agent;
  for (const button of $("agent-selector").querySelectorAll("button")) button.setAttribute("aria-pressed", String(Number(button.dataset.agentIndex) === index));
  $("agent-name").textContent = displayText(agent.name, "Voice agent");
  $("agent-description").textContent = displayText(agent.description);
  $("agent-reason").textContent = displayText(agent.reason);
  $("voice-player").pause();
  $("voice-player").removeAttribute("src");
  $("voice-player").load();
  $("voice-player-container").hidden = true;
  $("voice-browser-container").hidden = true;
  $("voice-browser-container").querySelector("iframe")?.remove();
  const options = scenarioOptions(agent);
  $("voice-scenario").replaceChildren();
  options.forEach((option, optionIndex) => {
    const node = el("option", "", option.title);
    node.value = String(optionIndex);
    $("voice-scenario").append(node);
  });
  $("scenario-brief").textContent = options[0].description;
  $("voice-scenario").onchange = () => {
    $("scenario-brief").textContent = options[Number($("voice-scenario").value)]?.description || "";
  };
  const actions = $("agent-actions");
  actions.replaceChildren();
  const mode = $("agent-mode");
  mode.classList.remove("available");
  const videoUrl = safeMediaUrl(agent.video_url);
  const browserUrl = safeVoiceBrowserUrl(agent.browser_url);
  if (agent.enabled && agent.mode === "recorded" && videoUrl) {
    mode.textContent = "RECORDED DEMONSTRATION";
    mode.classList.add("available");
    const button = el("button", "button button-primary", "Watch the demonstration ▷");
    button.type = "button";
    button.addEventListener("click", () => {
      const player = $("voice-player");
      player.src = videoUrl;
      $("voice-player-container").hidden = false;
      player.load();
      $("voice-player-container").scrollIntoView({ behavior: "smooth", block: "nearest" });
      button.textContent = "Recording opened below ↓";
    });
    actions.append(button);
    const fallback = el("a", "text-button recording-fallback", "Open the recording in a new tab ↗");
    fallback.href = videoUrl;
    fallback.target = "_blank";
    fallback.rel = "noopener noreferrer";
    fallback.style.display = "block";
    fallback.style.marginTop = "10px";
    actions.append(fallback);
    $("agent-reason").textContent = `${displayText(agent.reason)} The recording shows a fixed scenario; your selection is a briefing for a future isolated live demo.`.trim();
  } else if (agent.enabled && agent.mode === "browser" && browserUrl) {
    mode.textContent = "ISOLATED BROWSER ADAPTER CONFIGURED";
    const button = el("button", "button button-primary", "Open isolated browser demo ↗");
    button.type = "button";
    button.addEventListener("click", () => {
      const container = $("voice-browser-container");
      if (!container.querySelector("iframe")) {
        const frame = el("iframe", "voice-browser-frame");
        frame.src = browserUrl;
        frame.title = "Isolated browser voice demonstration";
        frame.allow = "microphone";
        frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms");
        container.prepend(frame);
      }
      container.hidden = false;
      button.textContent = "Provider adapter opened below ↓";
      container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    actions.append(button);
    $("agent-reason").textContent = `${displayText(agent.reason)} Provider audio is unverified until a live test succeeds. Opening the adapter may prompt you for microphone permission.`.trim();
  } else if (agent.enabled && agent.mode === "call" && typeof agent.phone === "string" && /^\+?[0-9 ()-]{7,24}$/.test(agent.phone)) {
    mode.textContent = "CALL-BASED DEMONSTRATION";
    mode.classList.add("available");
    const link = el("a", "button button-primary", "Call the demo agent ↗");
    link.href = `tel:${agent.phone.replace(/[^+0-9]/g, "")}`;
    actions.append(link);
    $("agent-reason").textContent = `${displayText(agent.reason)} Opens your phone app. Carrier charges may apply. Use the scenario above.`.trim();
  } else {
    mode.textContent = agent.mode === "recorded" ? "RECORDING UNAVAILABLE" : "LIVE DEMO NOT CONNECTED";
    const button = el("button", "button button-secondary", "Isolated demo pending");
    button.type = "button";
    button.disabled = true;
    actions.append(button);
    if (!$("agent-reason").textContent) $("agent-reason").textContent = "An isolated provider configuration must be verified before this agent can accept live interactions. No production workflow is connected here.";
  }
}

function appendMessage(role, content, { label, structured, responseMeta, scenario } = {}) {
  const wrapper = el("article", `chat-message ${role === "user" ? "user" : "assistant"}`);
  wrapper.append(el("div", "chat-message-label", label || (role === "user" ? "YOU" : "ADVISOR")));
  const bubble = el("div", "chat-bubble");
  if (structured) renderAnswer(bubble, structured);
  else {
    const paragraphs = String(content || "").split(/\n\s*\n/);
    for (const paragraph of paragraphs) bubble.append(el("p", "", paragraph));
  }
  if (scenario?.results && scenario?.assumptions) renderAdvisorScenario(bubble, scenario);
  wrapper.append(bubble);
  if (responseMeta) wrapper.append(el("span", "response-meta", responseMeta));
  $("chat-messages").append(wrapper);
  $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
  return wrapper;
}

function renderAdvisorScenario(container, scenario) {
  const block = el("div", "advisor-scenario");
  block.append(el("strong", "answer-section-title", "Submitted scenario · calculated by Python"));
  const metrics = el("div", "advisor-scenario-metrics");
  const values = [
    ["Monthly revenue", numerical(scenario.results.monthly_revenue, money)],
    ["Annual revenue", numerical(scenario.results.annual_revenue, money)],
    ["Monthly revenue less AI cost", numerical(scenario.results.monthly_net, money)],
    ["Expected new customers", numerical(scenario.results.new_customers)],
  ];
  for (const [label, value] of values) {
    const row = el("div", "");
    row.append(el("span", "", label), el("strong", "", value));
    metrics.append(row);
  }
  block.append(metrics, el("p", "", "These are the server's exact results for the assumptions sent with this message. They are hypothetical expected values."));
  container.append(block);
}

function renderAnswer(container, answer) {
  container.append(el("p", "", displayText(answer.summary, "No summary was returned.")));
  for (const claim of Array.isArray(answer.claims) ? answer.claims : []) {
    const text = displayText(claim?.text);
    if (!text) continue;
    const paragraph = el("p", "answer-claim", text);
    paragraph.append(citations(claim.source_ids));
    container.append(paragraph);
  }
  const recommendations = Array.isArray(answer.recommendations) ? answer.recommendations : [];
  if (recommendations.length) {
    const section = el("div", "answer-section");
    section.append(el("strong", "answer-section-title", "Suggested next steps"));
    for (const recommendation of recommendations) {
      const block = el("div", "answer-recommendation");
      block.append(el("strong", "", displayText(recommendation.title)));
      const paragraph = el("p", "", displayText(recommendation.rationale));
      paragraph.append(citations(recommendation.source_ids));
      block.append(paragraph);
      section.append(block);
    }
    container.append(section);
  }
  const unknowns = el("div", "answer-unknowns");
  renderUnknowns(unknowns, answer.unknowns, "Limits and unknowns");
  container.append(unknowns);
}

function focusAdvisor() {
  if (matchMedia("(max-width: 760px)").matches) $("advisor").scrollIntoView({ behavior: "smooth", block: "start" });
  $("chat-input").focus({ preventScroll: true });
}

function setChatBusy(busy) {
  state.chatBusy = busy;
  $("chat-send").disabled = busy;
  $("chat-input").disabled = busy;
  $("chat-history-button").disabled = busy;
  for (const button of document.querySelectorAll("[data-prompt], .recommendation-question")) button.disabled = busy;
}

function usageDescription(usage) {
  if (!usage || typeof usage !== "object") return "Usage unavailable";
  const input = Number(usage.input_tokens || 0);
  const output = Number(usage.output_tokens || 0);
  const cached = Number(usage.cached_input_tokens || 0);
  const parts = [`${quantity.format(input)} in / ${quantity.format(output)} out`];
  if (cached > 0) parts.push(`${quantity.format(cached)} cached`);
  const cost = usage.estimated_cost_usd;
  if (typeof cost === "number" && Number.isFinite(cost)) parts.push(`estimated $${cost.toFixed(cost < 0.01 ? 6 : 4)}`);
  else parts.push("cost estimate unavailable");
  return parts.join(" · ");
}

async function sendChat(message) {
  if (state.chatBusy || !state.session) return;
  const text = String(message || "").trim();
  if (!text) { focusAdvisor(); return; }
  if (text.length > 2000) { status("chat-status", "Keep your message under 2,000 characters.", true); return; }
  setChatBusy(true);
  $("chat-input").value = "";
  $("chat-suggestions").hidden = true;
  appendMessage("user", text);
  const provider = state.session.advisor_mode === "openai" ? "OpenAI" : "the guided demo";
  status("chat-status", `Preparing a response with ${provider}…`);
  const body = { message: text };
  const scenario = validCurrentScenario();
  if (scenario) body.scenario = scenario;
  try {
    const response = await api("/api/chat", { method: "POST", body });
    if (response.scenario && body.scenario && !assumptionsMatch(response.scenario.assumptions, body.scenario)) throw new Error("The advisor returned a different scenario. Your numerical results were not displayed; please retry.");
    indexSources(response.citations);
    renderSources();
    const responseProvider = displayText(response.provider, "unknown");
    const modelLabel = responseProvider === "openai" ? "OPENAI ADVISOR" : responseProvider.includes("guided") ? "GUIDED DEMO" : humanize(responseProvider).toUpperCase();
    const usage = usageDescription(response.usage);
    appendMessage("assistant", "", {
      label: modelLabel,
      structured: response.answer || { summary: "The server did not return an advisor answer." },
      scenario: body.scenario && response.scenario_explanation_included === true ? response.scenario : null,
      responseMeta: `Request ${displayText(response.request_id, "unavailable")} · ${usage}`,
    });
    $("chat-usage").textContent = `${humanize(responseProvider)} · ${usage}`;
    status("chat-status", "");
  } catch (error) {
    status("chat-status", error.message, true);
    $("chat-input").value = text;
  } finally {
    setChatBusy(false);
    $("chat-input").focus({ preventScroll: true });
  }
}

async function loadHistory() {
  if (state.chatBusy) return;
  $("chat-history-button").disabled = true;
  status("chat-status", "Loading the current session's history…");
  try {
    const response = await api("/api/history");
    const messages = Array.isArray(response.messages) ? response.messages : [];
    if (!messages.length) { status("chat-status", "No stored messages in this session yet."); return; }
    $("chat-messages").replaceChildren();
    for (const message of messages) appendMessage(message.role === "user" ? "user" : "assistant", displayText(message.content), { label: message.role === "user" ? "YOU · SESSION HISTORY" : "ADVISOR · SESSION HISTORY" });
    $("chat-suggestions").hidden = true;
    status("chat-status", `${messages.length} stored session messages loaded.`);
  } catch (error) { status("chat-status", error.message, true); }
  finally { $("chat-history-button").disabled = false; }
}

function integrationEntries(value) {
  if (Array.isArray(value)) return value.filter((item) => item && typeof item === "object");
  if (value && typeof value === "object") return Object.entries(value).map(([name, item]) => {
    if (typeof item !== "string") return { ...item, name: item?.name || name };
    const names = { database: "Database", openai: "OpenAI Responses", research: "Google Cloud research", crm: "HighLevel CRM", voice: "FireWireAds Voice AI", logging: "Application logging" };
    let label = "Configuration shown";
    if (item.includes("not configured")) label = "Not configured";
    else if (item.includes("Guided scripted demo")) label = "Guided demo";
    else if (item.includes("Local SQLite")) label = "Local connected";
    else if (item.includes("writes disabled")) label = "Writes disabled";
    else if (item.includes("Recorded demonstration")) label = "Recording available";
    else if (item.includes("Local JSON")) label = "Local events";
    else if (item.toLowerCase().includes("configured")) label = "Configured";
    return { name: names[name] || humanize(name), status: label, detail: item };
  });
  return [];
}

function renderEngineering(response) {
  const architecture = response.architecture;
  if (typeof architecture === "string") $("architecture-detail").textContent = architecture;
  else if (Array.isArray(architecture)) {
    $("architecture-detail").replaceChildren();
    for (const item of architecture) {
      if (typeof item === "string") { $("architecture-detail").append(el("span", "architecture-service", item)); continue; }
      const row = el("span", "architecture-service");
      row.append(el("strong", "", displayText(item?.service, displayText(item?.name))), document.createTextNode(` · ${displayText(item?.role, displayText(item?.description))}`));
      $("architecture-detail").append(row);
    }
  }
  else if (architecture && typeof architecture === "object") $("architecture-detail").textContent = displayText(architecture.description, displayText(architecture.summary));
  const container = $("integration-statuses");
  container.replaceChildren();
  for (const item of integrationEntries(response.integrations)) {
    const card = el("article", "integration-card");
    const top = el("div", "integration-card-top");
    const label = el("span", "integration-state", humanize(item.status || item.state));
    if (["verified", "tested", "operational", "working", "local_verified", "live_verified"].includes(item.status || item.state)) label.classList.add("verified");
    top.append(el("strong", "", displayText(item.name, displayText(item.service, "Integration"))), label);
    card.append(top, el("p", "", displayText(item.detail, displayText(item.description, displayText(item.reason)))));
    container.append(card);
  }
  const table = $("request-traces");
  table.replaceChildren();
  const requests = Array.isArray(response.recent_requests) ? response.recent_requests : [];
  for (const request of requests.slice(0, 30)) {
    const row = el("tr", "");
    const route = el("td", "");
    route.append(el("code", "", `${displayText(request.method, "GET")} ${displayText(request.route, "unknown")}`), el("span", "trace-id", displayText(request.request_id, "Request ID unavailable")));
    const result = el("td", "");
    const code = Number(request.status || request.status_code);
    result.append(el("span", `trace-result${code >= 400 ? " error" : ""}`, Number.isFinite(code) && code > 0 ? String(code) : "—"));
    const duration = el("td", "", typeof request.duration_ms === "number" ? `${quantity.format(request.duration_ms)} ms` : "—");
    const usage = request.usage;
    const provider = el("td", "", displayText(request.provider, "—"));
    if (usage && typeof usage === "object") provider.append(el("span", "trace-id", `${quantity.format(Number(usage.input_tokens || 0))} in / ${quantity.format(Number(usage.output_tokens || 0))} out`));
    row.append(route, result, duration, provider);
    table.append(row);
  }
  if (!requests.length) {
    const row = el("tr", "");
    const empty = el("td", "trace-empty", "No recorded requests are available yet.");
    empty.colSpan = 4;
    row.append(empty);
    table.append(row);
  }
}

async function loadEngineering() {
  if (state.engineeringBusy || !state.session) return;
  state.engineeringBusy = true;
  $("refresh-engineering").disabled = true;
  status("engineering-status", "Reading integration status and request traces…");
  try {
    const response = await api("/api/engineering");
    renderEngineering(response);
    status("engineering-status", `Read at ${new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" })} in your browser's time zone.`);
  } catch (error) { status("engineering-status", error.message, true); }
  finally { state.engineeringBusy = false; $("refresh-engineering").disabled = false; }
}

async function saveFollowUp(event) {
  event.preventDefault();
  const notes = $("follow-up-notes").value.trim();
  $("save-follow-up").disabled = true;
  status("follow-up-status", "Saving a follow-up draft…");
  try {
    const response = await api("/api/follow-up", { method: "POST", body: { intent: "Request an implementation plan", notes } });
    if (response.status !== "draft") throw new Error("The server returned an unexpected follow-up state. Check Engineering View before retrying.");
    status("follow-up-status", `${displayText(response.message, "Draft saved. No email or SMS was sent.")} Draft ID: ${displayText(response.id, "unavailable")}`);
    toast("Your implementation-plan draft is saved.");
  } catch (error) { status("follow-up-status", error.message, true); }
  finally { $("save-follow-up").disabled = false; }
}

function personalizationDisclosure(session) {
  const company = displayText(session.prospect?.company_name, "your business");
  if (session.prospect?.synthetic === true) {
    return `AI-personalized demonstration for ${company}, using fictional company data and synthetic evidence. Explore the sources and test your own assumptions.`;
  }
  const basis = session.has_research_attribution === true ? "saved public website research" : "your saved business context and evidence";
  return `AI-personalized for ${company} using ${basis}. Findings link to sources; opportunities need your confirmation.`;
}

function renderSession(session) {
  const prospect = session.prospect || {};
  const synthetic = prospect.synthetic === true;
  $("demo-banner").hidden = !synthetic;
  $("session-label").replaceChildren(el("span", "badge-dot"), document.createTextNode(synthetic ? "Synthetic demo session" : "Private prospect session"));
  $("session-label").classList.add("ready");
  const title = $("hero-title");
  title.replaceChildren();
  const firstName = displayText(prospect.first_name, "there");
  const company = displayText(prospect.company_name, "your business");
  title.append(document.createTextNode(`Hello ${firstName}. Let's explore `), el("span", "company-name", company), document.createTextNode("."));
  $("hero-subtitle").textContent = synthetic ? "A working preview of personalized business intelligence. Explore the evidence, adjust the numbers, and ask what comes next." : "Your research is ready. Explore evidence-grounded opportunities, test your assumptions, and plan a measurable next step.";
  $("personalization-note").textContent = personalizationDisclosure(session);
  $("industry-label").textContent = displayText(prospect.industry, "Industry not available");
  $("research-label").textContent = prospect.research_completed_at ? `Research saved ${friendlyDate(prospect.research_completed_at)}` : "Research date unavailable";
  $("evidence-badge").textContent = synthetic ? "Synthetic research" : "Saved research";
  const website = synthetic ? null : safeHttpsUrl(prospect.website);
  $("company-website").hidden = !website;
  if (website) {
    $("company-website").href = website;
    $("company-website").textContent = new URL(website).hostname;
  }
  indexSources(session.sources);
  renderIntelligence(session.intelligence);
  renderSources();
  const attribution = $("research-attribution");
  attribution.hidden = !session.has_research_attribution;
  attribution.querySelector("iframe")?.remove();
  if (session.has_research_attribution) {
    const frame = el("iframe", "research-attribution-frame");
    frame.src = "/api/research-attribution";
    frame.title = "Google Search grounding attribution";
      // Preserve the response origin for SAMEORIGIN framing; sandbox and CSP still block scripts.
      frame.setAttribute("sandbox", "allow-same-origin allow-popups allow-popups-to-escape-sandbox");
    frame.loading = "lazy";
    attribution.append(frame);
  }
  setAssumptions(session.simulator_defaults);
  renderAgents(session.voice_agents);
  $("advisor-company").textContent = `Context: ${company}`;
  const openai = session.advisor_mode === "openai";
  $("advisor-provider").textContent = openai ? "OPENAI · RESPONSES API" : "GUIDED DEMO · NO MODEL CALL";
  $("advisor-provider").classList.toggle("guided", !openai);
  $("advisor-mode-note").textContent = openai ? "Responses use your saved research and calculated scenario. The advisor will flag missing evidence." : "OpenAI is not configured for this session. This guided demo uses saved evidence and deterministic scenario results; it does not call an AI model.";
  $("chat-messages").replaceChildren();
  appendMessage("assistant", `Welcome, ${firstName}. This workspace brings together the saved research for ${company} and a transparent opportunity simulator. Ask about an opportunity, its supporting evidence, or the assumptions behind your scenario.`, { label: "WORKSPACE GUIDE" });
  $("chat-suggestions").hidden = false;
  $("main-content").hidden = false;
  $("advisor-shortcut").hidden = false;
  $("load-state").hidden = true;
  $("load-error").hidden = true;
  calculateScenario();
}

async function loadSession() {
  if (state.loading) return;
  state.loading = true;
  $("load-state").hidden = false;
  $("load-error").hidden = true;
  $("main-content").hidden = true;
  try {
    if (privateEntry.error) throw new Error(privateEntry.error);
    let session;
    if (state.privateSession) {
      if (privateEntry.token) {
        const token = privateEntry.token;
        privateEntry.token = "";
        // A failed exchange must not fall back to a previous company's cookie
        // when retry is clicked after the URL's capability has been removed.
        privateEntry.error = "This private link could not be opened. Reopen the original client link to try again.";
        const body = privateEntry.clientId ? { token, client_id: privateEntry.clientId } : { token };
        session = await api("/api/access", { method: "POST", body });
      } else {
        // Refreshing a private page should recover its existing HttpOnly session
        // without storing the dashboard's bearer token in browser storage.
        const path = privateEntry.clientId ? `/api/dashboard?client=${encodeURIComponent(privateEntry.clientId)}` : "/api/dashboard";
        session = await api(path);
      }
    } else session = await api("/api/demo");
    if (!session.prospect || typeof session.csrf_token !== "string") throw new Error("The dashboard response is incomplete. Please reopen the application.");
    if (privateEntry.clientId && session.prospect.id !== privateEntry.clientId) throw new Error("This session does not match the client link. Reopen the original private dashboard link.");
    privateEntry.error = "";
    state.session = session;
    state.csrfToken = session.csrf_token;
    state.sources.clear();
    state.sourceNumbers.clear();
    renderSession(session);
    if (!state.privateSession) window.ProspectIQAnalytics?.startPublicDemo(session.prospect.synthetic === true);
  } catch (error) {
    $("load-state").hidden = true;
    $("load-error").hidden = false;
    $("load-error-message").textContent = state.privateSession ? `${error.message} If your session has expired, reopen the original private dashboard link.` : error.message;
    $("session-label").replaceChildren(el("span", "badge-dot"), document.createTextNode("Session unavailable"));
    $("session-label").classList.remove("ready");
  } finally { state.loading = false; }
}

$("retry-load").addEventListener("click", loadSession);
$("simulator-form").addEventListener("submit", (event) => event.preventDefault());
for (const field of fields) {
  const input = document.querySelector(`#simulator-form [name="${field}"]`);
  const slider = document.querySelector(`#simulator-form [data-range="${field}"]`);
  input.addEventListener("input", () => { syncSlider(field); scheduleCalculation(); });
  slider.addEventListener("input", () => { input.value = slider.value; syncSlider(field); scheduleCalculation(); });
}
$("explain-scenario").addEventListener("click", () => {
  if (!validCurrentScenario()) { toast("Wait for the current scenario to finish calculating."); return; }
  focusAdvisor();
  sendChat("Explain my current calculated scenario, the assumptions that matter most, and what I should validate. Use the exact simulator results; do not invent or recalculate numbers.");
});
$("chat-form").addEventListener("submit", (event) => { event.preventDefault(); sendChat($("chat-input").value); });
$("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendChat($("chat-input").value); }
});
for (const button of document.querySelectorAll("[data-prompt]")) button.addEventListener("click", () => sendChat(button.dataset.prompt));
$("chat-history-button").addEventListener("click", loadHistory);
$("advisor-shortcut").addEventListener("click", focusAdvisor);
$("open-follow-up").addEventListener("click", () => {
  $("follow-up-form").hidden = !$("follow-up-form").hidden;
  $("open-follow-up").setAttribute("aria-expanded", String(!$("follow-up-form").hidden));
  if (!$("follow-up-form").hidden) $("follow-up-notes").focus({ preventScroll: true });
});
$("follow-up-form").addEventListener("submit", saveFollowUp);
$("refresh-engineering").addEventListener("click", loadEngineering);
$("engineering").addEventListener("toggle", () => { if ($("engineering").open) loadEngineering(); });
document.querySelector('a[href="#engineering"]')?.addEventListener("click", () => { $("engineering").open = true; });
for (const link of document.querySelectorAll('.header-nav a[href="#engineering"]')) link.addEventListener("click", () => { $("engineering").open = true; });
$("voice-player").addEventListener("error", () => {
  if (!$("voice-player").getAttribute("src")) return;
  $("voice-player-container").querySelector("p").textContent = "The embedded player could not load this recording. Use ‘Open the recording in a new tab’ above. No call has been initiated.";
});
if ("IntersectionObserver" in window) {
  const advisorObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) $("advisor-shortcut").hidden = entry.isIntersecting || !state.session;
  }, { threshold: 0 });
  advisorObserver.observe($("advisor"));
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) if (entry.isIntersecting) {
      for (const link of document.querySelectorAll(".header-nav a")) link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
    }
  }, { rootMargin: "-110px 0px -65% 0px", threshold: 0 });
  for (const id of ["overview", "simulator", "voice-lab", "engineering"]) observer.observe($(id));
}
loadSession();
