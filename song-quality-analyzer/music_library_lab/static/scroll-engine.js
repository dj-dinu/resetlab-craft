/* A small local wheel engine. The document itself scrolls; touch, trackpad,
   keyboard, links, focus, and nested scroll containers keep browser behavior. */
(() => {
  "use strict";

  const root = document.documentElement;
  const preferenceKey = "resetlabcraft:scroll-mode";
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const choice = document.getElementById("scroll-mode");
  let mode = "smooth";
  try {
    if ((localStorage.getItem(preferenceKey) || localStorage.getItem("audraloom:scroll-mode")) === "native") mode = "native";
  } catch (_) { /* Preferences are optional when storage is unavailable. */ }

  let animation = 0;
  let target = 0;
  let expectedPosition = window.scrollY;
  let direction = 0;
  let lastFrame = 0;
  let maximum = 0;

  function effectiveMode() {
    return motion.matches ? "native" : mode;
  }

  function clamp(position) {
    return Math.min(maximum, Math.max(0, position));
  }

  function updateProgress() {
    const progress = maximum > 0 ? Math.min(1, Math.max(0, window.scrollY / maximum)) : 0;
    root.style.setProperty("--scroll-progress", progress.toFixed(5));
  }

  function updateBounds() {
    const page = document.scrollingElement || root;
    maximum = Math.max(0, page.scrollHeight - window.innerHeight);
    target = clamp(target);
    updateProgress();
  }

  function stop() {
    if (animation) cancelAnimationFrame(animation);
    animation = 0;
    direction = 0;
    target = clamp(window.scrollY);
    expectedPosition = window.scrollY;
    updateProgress();
    // CSS smooth anchors remain available in Smooth mode, outside our RAF loop.
    root.style.scrollBehavior = effectiveMode() === "native" ? "auto" : "";
  }

  function publishMode() {
    root.dataset.scrollMode = effectiveMode();
    if (choice) {
      choice.value = mode;
      choice.title = motion.matches ? "Reduced motion is enabled. Scrolling uses native browser behavior." : "Choose smooth mouse-wheel scrolling or native browser scrolling.";
    }
    window.dispatchEvent(new CustomEvent("resetlabcraft:scroll-modechange", {
      detail: { mode, effectiveMode: effectiveMode(), reducedMotion: motion.matches }
    }));
  }

  function setMode(next) {
    if (next !== "smooth" && next !== "native") return;
    mode = next;
    try { localStorage.setItem(preferenceKey, mode); } catch (_) { /* Keep the current session preference. */ }
    stop();
    publishMode();
  }

  function nativeArea(event) {
    const path = typeof event.composedPath === "function" ? event.composedPath() : [];
    let element = event.target instanceof Element ? event.target : null;
    const elements = path.length ? path.filter((item) => item instanceof Element) : [];
    if (!elements.length) {
      while (element) { elements.push(element); element = element.parentElement; }
    }
    return elements.some((item) => {
      if (item === root || item === document.body) return false;
      if (item.matches("input, textarea, select, button, option, dialog[open], [data-native-scroll], [role='listbox'], [role='menu']") || item.isContentEditable) return true;
      const style = window.getComputedStyle(item);
      const scrollable = /^(auto|scroll|overlay)$/;
      return (scrollable.test(style.overflowY) && item.scrollHeight > item.clientHeight + 1)
        || (scrollable.test(style.overflowX) && item.scrollWidth > item.clientWidth + 1);
    });
  }

  function mouseWheelDelta(event) {
    // WheelEvent has no trustworthy device identifier. Only discrete, vertical
    // wheel-like steps opt in; fine/mixed-axis gestures deliberately stay native.
    if (Math.abs(event.deltaX) > .5 || !Number.isFinite(event.deltaY) || !event.deltaY) return null;
    const amount = Math.abs(event.deltaY);
    const whole = Math.abs(amount - Math.round(amount)) < .01;
    if (event.deltaMode === 1) return whole && amount >= 1 ? event.deltaY * 20 : null;
    if (event.deltaMode === 2) return whole && amount >= 1 ? event.deltaY * window.innerHeight : null;
    const discretePixels = whole && amount >= 100 && amount <= 600
      && (Math.abs(amount % 100) < .01 || Math.abs(amount % 120) < .01);
    return discretePixels ? event.deltaY : null;
  }

  function frame(time) {
    // Never retain a target beyond a resize, expanded evidence, or a new batch.
    updateBounds();
    const position = window.scrollY;
    if (Math.abs(position - expectedPosition) > 3) { stop(); return; }
    const distance = target - position;
    if (Math.abs(distance) <= .75) {
      window.scrollTo(window.scrollX, target);
      expectedPosition = window.scrollY;
      stop();
      return;
    }
    const elapsed = Math.min(50, Math.max(1, time - lastFrame));
    lastFrame = time;
    const next = clamp(position + distance * (1 - Math.exp(-elapsed / 75)));
    window.scrollTo(window.scrollX, next);
    expectedPosition = window.scrollY;
    // Browsers may round the scroll position. End if the remaining fractional
    // step can no longer move, rather than leaving a perpetual animation loop.
    if (Math.abs(expectedPosition - position) < .01) { stop(); return; }
    animation = requestAnimationFrame(frame);
  }

  function wheel(event) {
    if (effectiveMode() !== "smooth" || event.defaultPrevented || !event.cancelable
      || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey
      || document.visibilityState === "hidden" || nativeArea(event)) {
      stop();
      return;
    }
    const delta = mouseWheelDelta(event);
    if (delta === null) { stop(); return; }
    updateBounds();
    const position = window.scrollY;
    const nextDirection = Math.sign(delta);
    const origin = animation && direction === nextDirection ? target : position;
    // Limit queued travel to two viewports so rapid wheel bursts stay responsive.
    const nextTarget = clamp(Math.min(position + window.innerHeight * 2,
      Math.max(position - window.innerHeight * 2, origin + delta)));
    if (Math.abs(nextTarget - origin) < .75) { stop(); return; }
    event.preventDefault();
    target = nextTarget;
    direction = nextDirection;
    if (!animation) {
      root.style.scrollBehavior = "auto";
      expectedPosition = position;
      lastFrame = performance.now();
      animation = requestAnimationFrame(frame);
    }
  }

  window.ResetLabCraftScroll = Object.freeze({
    setMode,
    getMode: () => mode,
    getEffectiveMode: effectiveMode
  });
  if (choice) choice.addEventListener("change", () => setMode(choice.value));
  window.addEventListener("wheel", wheel, { passive: false });
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateBounds, { passive: true });
  ["pointerdown", "touchstart", "keydown", "focusin"].forEach((event) => {
    window.addEventListener(event, stop, { capture: true, passive: true });
  });
  window.addEventListener("hashchange", stop);
  window.addEventListener("blur", stop);
  document.addEventListener("visibilitychange", stop);
  const motionChanged = () => { stop(); publishMode(); };
  if (typeof motion.addEventListener === "function") motion.addEventListener("change", motionChanged);
  else motion.addListener(motionChanged);
  window.addEventListener("storage", (event) => {
    if (event.key !== preferenceKey) return;
    mode = event.newValue === "native" ? "native" : "smooth";
    stop();
    publishMode();
  });
  if (typeof ResizeObserver === "function") {
    const resize = new ResizeObserver(updateBounds);
    resize.observe(document.body);
  } else if (typeof MutationObserver === "function") {
    const changes = new MutationObserver(updateBounds);
    changes.observe(document.body, { subtree: true, childList: true });
  }
  updateBounds();
  stop();
  publishMode();
})();
