// Offline execution of the analytics boundary. SDK URLs are collected, never fetched.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../app/static/analytics.js", import.meta.url), "utf8");
const canonical = "https://prospect.firewireads.com/";
const ga4 = "G-6JM91XZMX2";
const ads = "AW-17005023254";
const meta = "502483969150258";
let assertions = 0;

function harness(href = canonical) {
  const scripts = [];
  const listeners = [];
  const window = {location: new URL(href)};
  const document = {
    // Sensitive strings must never become tag parameters, even in the synthetic demo.
    title: "Unrelated private company title",
    referrer: "https://example.com/private?email=fictional-sensitive@example.com",
    createElement(tag) { assert.equal(tag, "script"); return {}; },
    head: {appendChild(script) { scripts.push(script); }},
    addEventListener(...args) { listeners.push(args); },
  };
  window.addEventListener = (...args) => listeners.push(args);
  const context = vm.createContext({window, document});
  vm.runInContext(source, context, {filename: "analytics.js"});
  return {window, scripts, listeners, context};
}

function queued(state) {
  return {
    google: Array.from(state.window.dataLayer || [], args => Array.from(args)),
    meta: Array.from(state.window.fbq?.queue || [], args => Array.from(args)),
  };
}

function expectNoTracking(state, synthetic) {
  assert.equal(state.window.ProspectIQAnalytics.startPublicDemo(synthetic), false);
  assert.equal(state.scripts.length, 0);
  assert.equal(state.listeners.length, 0);
  assert.equal(state.window.gtag, undefined);
  assert.equal(state.window.fbq, undefined);
  assert.equal(state.window.dataLayer, undefined);
  assertions += 6;
}

const beforeSession = harness();
assert.equal(beforeSession.scripts.length, 0);
assert.equal(beforeSession.window.gtag, undefined);
assert.equal(beforeSession.window.fbq, undefined);
assertions += 3;

for (const synthetic of [false, undefined, null, "true", 1, {synthetic: true}]) {
  expectNoTracking(harness(), synthetic);
}
for (const url of [
  "https://prospect.firewireads.com/p",
  "https://prospect.firewireads.com/p#private-access-token",
  "https://prospect.firewireads.com/p?client=private-access-token",
  "https://prospect.firewireads.com/?client=private-access-token",
  "https://prospect.firewireads.com/?client=",
  "https://prospect.firewireads.com/p?client=first&client=second",
  "https://prospect.firewireads.com/p?client=private-access-token#overview",
  "https://prospect.firewireads.com/private",
  "http://127.0.0.1:8093/",
  "http://localhost:8093/",
  "http://prospect.firewireads.com/",
  "https://prospectiq-s4gztnjt6a-uc.a.run.app/",
  "https://prospectiq-1051896753015.us-central1.run.app/",
  "https://firewireads.com/",
  "https://prospect.firewireads.com/?token=private-access-token",
  "https://prospect.firewireads.com/?utm_campaign=demo",
  "https://prospect.firewireads.com/#private-access-token",
  "https://prospect.firewireads.com/#engineering?token=private-access-token",
  "https://prospect.firewireads.com/#chat",
]) {
  expectNoTracking(harness(url), true);
}

for (const hash of ["", "#overview", "#simulator", "#voice-lab", "#engineering"]) {
  const state = harness(`${canonical}${hash}`);
  assert.equal(state.window.ProspectIQAnalytics.startPublicDemo(true), true);
  assert.equal(state.scripts.length, 2);
  assert.deepEqual(state.scripts.map(script => script.src), [
    `https://www.googletagmanager.com/gtag/js?id=${ga4}`,
    "https://connect.facebook.net/en_US/fbevents.js",
  ]);
  assert.ok(state.scripts.every(script => script.async === true && script.referrerPolicy === "no-referrer"));
  assert.equal(state.listeners.length, 0);
  const calls = queued(state);
  assert.equal(calls.google.length, 4);
  assert.deepEqual(calls.google.map(call => call.slice(0, 2)), [
    ["js", calls.google[0][1]], ["config", ga4], ["config", ads], ["event", "page_view"],
  ]);
  for (const call of calls.google.slice(1, 3)) {
    assert.equal(call[2].send_page_view, false);
    assert.equal(call[2].allow_google_signals, false);
    assert.equal(call[2].allow_ad_personalization_signals, false);
    assert.equal(call[2].page_location, canonical);
    assert.equal(call[2].page_referrer, "");
    assert.equal(call[2].page_title, "ProspectIQ by FireWireAds — Public Demo");
  }
  assert.equal(calls.google[3][2].send_to, ga4);
  assert.equal(calls.google[3][2].page_location, canonical);
  assert.equal(calls.google[3][2].page_referrer, "");
  assert.equal(calls.google[3][2].page_title, "ProspectIQ by FireWireAds — Public Demo");
  assert.deepEqual(calls.meta, [
    ["set", "autoConfig", false, meta], ["init", meta], ["trackSingle", meta, "PageView"],
  ]);
  assert.equal(state.window.fbq.disablePushState, true);
  assert.ok(!JSON.stringify(calls).includes("fictional-sensitive"));
  assert.ok(!JSON.stringify(calls).includes("Unrelated private company"));
  // Re-rendering and re-including the local script must retain the one-time lock.
  assert.equal(state.window.ProspectIQAnalytics.startPublicDemo(true), false);
  vm.runInContext(source, state.context, {filename: "analytics.js"});
  assert.equal(state.window.ProspectIQAnalytics.startPublicDemo(true), false);
  assert.equal(state.scripts.length, 2);
  assert.equal(queued(state).google.length, 4);
  assert.equal(queued(state).meta.length, 3);
  assertions += 34;
}

// A rejected early call can become eligible after the app verifies its session.
const deferred = harness();
assert.equal(deferred.window.ProspectIQAnalytics.startPublicDemo(false), false);
assert.equal(deferred.window.ProspectIQAnalytics.startPublicDemo(true), true);
assert.equal(deferred.scripts.length, 2);
assertions += 5; // Includes the two mocked script element assertions.

// The app sanitizes a root client entry to /p before exchanging the capability.
// Removing the query must not turn the personalized visit into a public pageview.
const privateEntry = harness(`${canonical}?client=private-access-token`);
expectNoTracking(privateEntry, true);
privateEntry.window.location = new URL(`${canonical}p`);
expectNoTracking(privateEntry, true);
privateEntry.window.location.hash = "#overview";
expectNoTracking(privateEntry, true);

console.log(JSON.stringify({status: "PASS", offline_only: true, assertions,
  explicit_session_gate: true, public_canonical_only: true, private_and_token_urls_blocked: true,
  correct_public_ids: true, one_explicit_pageview_per_provider: true, no_forms_click_chat_hooks: true,
  no_contact_payloads_or_conversion_events: true, repeated_initialization_blocked: true}));
