"use strict";
document.getElementById("load-voice").addEventListener("click", (event) => {
  const button = event.currentTarget;
  const status = document.getElementById("voice-status");
  const widget = document.querySelector('meta[name="demo-widget"]').content;
  if (!/^[a-f0-9]{24}$/.test(widget)) { status.textContent = "Dedicated demo widget is unavailable."; return; }
  button.disabled = true;
  status.textContent = "Loading the provider's native controls. Start and end the conversation using those controls.";
  const script = document.createElement("script");
  // Same public embed protocol verified in the existing FireWire controller.
  // Never import the production global loader: it hardcodes production widgets.
  script.src = "https://widgets.leadconnectorhq.com/loader.js";
  script.dataset.resourcesUrl = "https://widgets.leadconnectorhq.com/chat-widget/loader.js";
  script.dataset.widgetId = widget;
  script.dataset.source = "FUNNEL";
  script.onerror = () => { status.textContent = "Provider controls failed to load. Audio demonstration is unavailable."; button.disabled = false; script.remove(); };
  document.body.append(script);
});
