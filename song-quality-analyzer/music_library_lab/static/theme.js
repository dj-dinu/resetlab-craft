"use strict";

(() => {
  const key = "resetlabcraft:theme";
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  let mode = "system";
  try { const saved = localStorage.getItem(key) || localStorage.getItem("audraloom-theme"); if (["system", "light", "dark"].includes(saved)) mode = saved; } catch (_) { /* Preserve earlier choices; storage can be unavailable in private windows. */ }
  const initial = document.documentElement.dataset.initialTheme;
  if (["system", "light", "dark"].includes(initial)) mode = initial;
  const textKey = "resetlabcraft:text-size";
  const sizes = Object.freeze(["90", "100", "110", "125", "150"]);
  let textSize = "100";
  try { const saved = localStorage.getItem(textKey); if (sizes.includes(saved)) textSize = saved; } catch (_) { /* The server preference works without browser storage. */ }
  const initialSize = document.documentElement.dataset.initialTextSize;
  if (sizes.includes(initialSize)) textSize = initialSize;

  function applyTextSize() {
    document.documentElement.dataset.textSize = textSize;
    const value = document.getElementById("text-size-value");
    if (value) value.textContent = textSize + "%";
    const reset = document.getElementById("text-size-reset");
    if (reset) reset.setAttribute("aria-label", "Text size " + textSize + " percent. Reset to default");
  }

  function setTextSize(value) {
    if (!sizes.includes(value)) return;
    textSize = value;
    try { localStorage.setItem(textKey, textSize); } catch (_) { /* The current session can still resize text. */ }
    applyTextSize();
  }

  window.ResetLabCraftTextSize = Object.freeze({ setSize: setTextSize, getSize: () => textSize, sizes });
  applyTextSize();

  function apply() {
    const theme = mode === "system" ? media.matches ? "dark" : "light" : mode;
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    const control = document.getElementById("theme-toggle");
    if (control) {
      const label = theme === "dark" ? "Switch to light appearance" : "Switch to dark appearance";
      control.setAttribute("aria-label", label);
      control.setAttribute("aria-pressed", String(theme === "dark"));
      control.title = label;
    }
    window.dispatchEvent(new CustomEvent("resetlabcraft:themechange", { detail: { mode, theme } }));
  }

  function setMode(value) {
    if (!["system", "light", "dark"].includes(value)) return;
    mode = value;
    try { localStorage.setItem(key, mode); } catch (_) { /* The current session can still use its chosen theme. */ }
    apply();
  }

  window.ResetLabCraftTheme = Object.freeze({ setMode, getMode: () => mode });
  apply();
  media.addEventListener("change", () => { if (mode === "system") apply(); });
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    applyTextSize();
  }, { once: true });
})();
