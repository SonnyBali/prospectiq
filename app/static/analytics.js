/* Public synthetic demo measurement only. IDs are public, never API credentials.
 * The application calls startPublicDemo after it knows the session is synthetic.
 * Google fields: developers.google.com/analytics/devguides/collection/ga4/reference/config
 * Meta initialization: github.com/facebook/GoogleTagManager-WebTemplate-For-FacebookPixel
 */
(function () {
  "use strict";
  if (window.ProspectIQAnalytics) return;

  const PUBLIC_ORIGIN = "https://prospect.firewireads.com";
  const PUBLIC_PAGE = `${PUBLIC_ORIGIN}/`;
  const PUBLIC_TITLE = "ProspectIQ by FireWireAds — Public Demo";
  const GA4_ID = "G-6JM91XZMX2";
  const ADS_ID = "AW-17005023254";
  const META_ID = "502483969150258";
  const SAFE_HASHES = new Set(["", "#overview", "#simulator", "#voice-lab", "#engineering"]);
  let started = false;

  function appendSdk(src) {
    const script = document.createElement("script");
    script.async = true;
    script.src = src;
    script.referrerPolicy = "no-referrer";
    document.head.appendChild(script);
  }

  function startPublicDemo(synthetic) {
    const page = window.location;
    if (started || synthetic !== true || page.origin !== PUBLIC_ORIGIN || page.pathname !== "/" ||
        page.search !== "" || !SAFE_HASHES.has(page.hash)) return false;
    // Lock before any queue/SDK work so repeated rendering/loading cannot double-track.
    started = true;

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    const pageFields = {page_location: PUBLIC_PAGE, page_referrer: "", page_title: PUBLIC_TITLE};
    const privacyFields = {allow_google_signals: false, allow_ad_personalization_signals: false};
    window.gtag("js", new Date());
    window.gtag("config", GA4_ID, {...pageFields, ...privacyFields, send_page_view: false});
    // Baseline Google Ads tag only; no conversion, purchase, lead or remarketing payload.
    window.gtag("config", ADS_ID, {...pageFields, ...privacyFields, send_page_view: false});
    window.gtag("event", "page_view", {...pageFields, send_to: GA4_ID});
    appendSdk(`https://www.googletagmanager.com/gtag/js?id=${GA4_ID}`);

    if (!window.fbq) {
      const fbq = function () {
        if (fbq.callMethod) fbq.callMethod.apply(fbq, arguments);
        else fbq.queue.push(arguments);
      };
      fbq.push = fbq;
      fbq.loaded = true;
      fbq.version = "2.0";
      fbq.queue = [];
      window.fbq = fbq;
      window._fbq = window._fbq || fbq;
    }
    // Disable automatic configuration/navigation before init; no advanced matching.
    window.fbq.disablePushState = true;
    window.fbq("set", "autoConfig", false, META_ID);
    window.fbq("init", META_ID);
    window.fbq("trackSingle", META_ID, "PageView");
    appendSdk("https://connect.facebook.net/en_US/fbevents.js");
    // True means initialization was queued, not that provider delivery was verified.
    return true;
  }

  window.ProspectIQAnalytics = Object.freeze({startPublicDemo});
})();
