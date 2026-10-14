"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const state = { token: "", config: null, root: "", sourceKind: "folder", tracks: [], records: new Map(), summaries: new Map(), filter: "All", sort: "title-asc", alphabetical: [], batchSeen: 0, progressJobId: null, progressStarted: 0, progressTimer: null, inventoryIncomplete: false, busy: false, job: null, scanContext: null, reportJobId: null, reportTrackCount: 0, exporting: false, pollTimer: null, pollFailures: 0 };
  const basename = (path) => String(path || "").split(/[\\/]/).pop() || "Untitled file";
  const string = (value) => value === null || value === undefined ? "" : String(value);
  const element = (tag, className, content) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = string(content);
    return node;
  };
  const errorMessage = (error) => error && error.message ? error.message : string(error) || "The request could not be completed.";
  const asMessages = (values) => (Array.isArray(values) ? values : values ? [values] : []).filter(Boolean).map((value) => typeof value === "string" ? value : value.message || value.error || JSON.stringify(value));
  const organizerIssues = new Set([
    "Vocal content is unverified; review the vocal bucket.",
    "A supported broad musical group cannot be established from the genre tag.",
    "Missing artist tag. Enter an artist before applying."
  ]);
  const analysisIssues = (values) => asMessages(values).filter((message) => !organizerIssues.has(message));
  const selectedTracks = () => state.alphabetical.filter((track) => track.scan_valid && track.enabled !== false);
  const trackLimit = () => Number.isInteger(state.config && state.config.max_tracks_per_run) && state.config.max_tracks_per_run > 0 ? state.config.max_tracks_per_run : 50;
  const bulkTracks = () => state.alphabetical.filter((track) => track.scan_valid);
  const nextBatchTracks = () => state.alphabetical.filter((track) => track.scan_valid && !state.summaries.has(string(track.id)));

  try {
    state.token = new URLSearchParams(location.hash.slice(1)).get("token") || sessionStorage.getItem("song-quality-local-token") || "";
    if (state.token) sessionStorage.setItem("song-quality-local-token", state.token);
    if (location.hash.includes("token=")) history.replaceState(null, "", location.pathname + location.search);
  } catch (_) {
    state.token = new URLSearchParams(location.hash.slice(1)).get("token") || state.token;
  }

  async function api(path, body) {
    if (!state.token) throw new Error("Open the app using the local link printed by its launcher. That link includes access to this session.");
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: { "X-Local-Token": state.token, "Content-Type": "application/json", "Accept": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store"
    });
    let data;
    try { data = await response.json(); }
    catch (_) { throw new Error(response.ok ? "The local app returned an unreadable response." : "The local app could not complete this request (" + response.status + ")."); }
    if (!response.ok) {
      const error = new Error(typeof data.error === "string" ? data.error : data.error && data.error.message || data.message || "Request failed (" + response.status + ").");
      error.status = response.status;
      if (response.status === 403) invalidateSession();
      throw error;
    }
    return data;
  }

  function invalidateSession() {
    state.config = null;
    state.reportJobId = null;
    $("scanner-status").replaceChildren(element("span", "status-dot warning"), element("span", "", "Reopen local launch link"));
  }

  function alertBox(kind, title, messages) {
    const box = element("div", "alert " + kind);
    box.setAttribute("role", kind === "error" ? "alert" : "status");
    box.append(element("strong", "", title));
    const lines = asMessages(messages);
    if (lines.length === 1) box.append(element("div", "", lines[0]));
    else if (lines.length) {
      const list = element("ul");
      lines.forEach((line) => list.append(element("li", "", line)));
      box.append(list);
    }
    return box;
  }

  function setAlert(kind, title, messages) {
    $("alerts").replaceChildren(alertBox(kind, title, messages));
  }

  function setStep(step) {
    const order = ["scan", "analyze", "results", "export"];
    const current = order.indexOf(step);
    document.querySelectorAll(".steps li").forEach((node) => {
      const index = order.indexOf(node.dataset.step);
      node.classList.toggle("current", index === current);
      node.classList.toggle("complete", index < current);
    });
  }

  function updateControls() {
    const count = selectedTracks().length;
    const bulk = bulkTracks();
    const bulkSelected = bulk.length > 0 && count === bulk.length && bulk.every((track) => track.enabled !== false);
    $("scan-button").disabled = state.busy || !state.config;
    $("browse-button").disabled = state.busy || !state.config;
    $("browse-file-button").disabled = state.busy || !state.config;
    const next = nextBatchTracks();
    $("next-batch-button").disabled = state.busy || !next.length || !state.config;
    $("next-batch-button").textContent = next.length ? "Select remaining " + next.length : "All readable tracks attempted";
    $("root-path").disabled = state.busy;
    $("audit-button").disabled = state.busy || !count || !state.config || state.config.scanner_available === false || $("root-path").value.trim() !== state.root;
    $("select-all").disabled = state.busy || !bulk.length;
    $("select-all").checked = bulkSelected;
    $("select-all").indeterminate = count > 0 && !bulkSelected;
    $("select-all").title = "Select all tracks with readable audio metadata";
    $("selection-summary").textContent = count === state.tracks.length ? count + " track" + (count === 1 ? "" : "s") + " selected" : bulkSelected ? count + " readable tracks selected" : count + " of " + state.tracks.length + " tracks selected";
    $("export-button").disabled = state.busy || state.exporting || !state.reportJobId;
    document.querySelectorAll(".track-select").forEach((input) => { input.disabled = state.busy; });
    $("cancel-button").disabled = !state.job || state.job.cancelling;
    $("cancel-button").textContent = state.job && state.job.kind === "audit" ? state.job.cancelling ? "Stopping…" : "Stop" : "Cancel";
    $("pause-button").hidden = !state.job || state.job.kind !== "audit";
    $("pause-button").disabled = !state.job || state.job.cancelling || state.job.pauseUpdating;
    $("pause-button").textContent = state.job && state.job.pauseRequested ? "Resume" : "Pause";
    $("pause-button").setAttribute("aria-pressed", string(!!(state.job && state.job.pauseRequested)));
    $("rail-status").textContent = state.job ? state.job.kind === "scan" ? "Reading music" : "Analyzing tracks" : count ? count + " selected" : "Ready to start";
  }

  function coverageValue(record, key) {
    if (!record || record[key] === null || record[key] === undefined || record[key] === "") return null;
    const value = Number(record[key]);
    return Number.isFinite(value) ? Math.max(0, Math.min(100, value * 100)) : null;
  }

  function coverageRow(label, value, showThreshold) {
    const row = element("div", "coverage-item");
    row.append(element("span", "", label));
    const bar = element("div", "coverage-bar" + (showThreshold ? " threshold" : ""));
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", label + " coverage " + (value === null ? "unavailable" : formatCoverage(value)) + (showThreshold ? "; HQ threshold 40 percent" : ""));
    const fill = element("span", "coverage-fill");
    fill.style.width = (value === null ? 0 : value) + "%";
    bar.append(fill);
    const number = element("span", "coverage-value", formatCoverage(value));
    if (value !== null) number.title = value.toPrecision(12) + "% of the full decoded duration";
    row.append(bar, number);
    return row;
  }

  function formatCoverage(value) {
    if (value === null || !Number.isFinite(value)) return "—";
    const rounded = value.toFixed(Math.abs(value - 40) < .1 ? 3 : 1);
    if (value < 40 && Number(rounded) >= 40) return "<40%";
    if (value > 0 && Number(rounded) === 0) return "<0.1%";
    return rounded + "%";
  }

  function technicalMetadata(track, record) {
    const data = record || {};
    const labels = [];
    const container = string(data.container || track.container).toUpperCase();
    const codec = string(data.codec || track.codec).toUpperCase();
    if (container) labels.push(container);
    if (codec && codec !== container) labels.push(codec);
    const rate = Number(data.sample_rate_hz || data.sample_rate || track.sample_rate);
    if (Number.isFinite(rate) && rate > 0) labels.push((rate / 1000).toFixed(rate % 1000 ? 1 : 0) + " kHz");
    const channels = Number(data.channels || track.channels);
    if (channels > 0) labels.push(channels === 1 ? "Mono" : channels === 2 ? "Stereo" : channels + " channels");
    return labels;
  }

  function renderResultSummary() {
    const records = [...state.summaries.values()];
    const measured = records.filter((record) => !record.error && ["HQ", "MQ", "LQ"].includes(record.quality));
    const errors = records.filter((record) => record.error).length;
    const unmeasured = Math.max(0, state.tracks.length - records.length);
    $("result-summary").hidden = records.length === 0;
    $("folder-score").hidden = records.length === 0;
    ["HQ", "MQ", "LQ"].forEach((grade) => {
      $("summary-" + grade.toLowerCase()).textContent = string(records.filter((record) => !record.error && record.quality === grade).length);
    });
    $("summary-errors").textContent = string(errors);
    const score = measured.length ? measured.reduce((sum, record) => sum + ({ HQ: 100, MQ: 50, LQ: 0 }[record.quality]), 0) / measured.length : null;
    $("folder-score-value").textContent = score === null ? "—" : score.toFixed(1);
    const single = state.sourceKind === "file";
    $("folder-score-label").textContent = single ? "FILE SPECTRAL-GRADE SCORE" : "FOLDER SPECTRAL-GRADE SCORE";
    $("folder-score-state").textContent = single ? errors || unmeasured ? "File not measured" : "Selected file measured" : state.inventoryIncomplete ? "Partial folder inventory" : errors || unmeasured ? "Partial folder summary" : "This inventory measured";
    $("folder-score-state").classList.toggle("partial-pill", !!(errors || unmeasured || state.inventoryIncomplete));
    $("folder-score-coverage").textContent = single ? measured.length ? "1 selected file measured" : "Selected file has no completed grade" : measured.length + " of " + state.tracks.length + " folder tracks measured";
    $("folder-score-exclusions").textContent = errors + " ungraded error" + (errors === 1 ? "" : "s") + " · " + unmeasured + " unmeasured · Excluded from the score";
  }

  function coverageMetrics(record) {
    const grid = element("div", "evidence-metrics");
    const duration = Number(record.duration_seconds);
    [["20 kHz+ coverage", "coverage_20khz"], ["18 kHz+ coverage", "coverage_18khz"]].forEach(([label, key]) => {
      const value = coverageValue(record, key);
      const card = element("div", "evidence-metric");
      card.append(element("label", "", label), element("strong", "", formatCoverage(value)));
      card.append(element("small", "", Number.isFinite(duration) && value !== null ? (duration * value / 100).toFixed(3) + "s of " + duration.toFixed(3) + "s" : "Measured against the full duration"));
      grid.append(card);
    });
    const full = element("div", "evidence-metric");
    full.append(element("label", "", "Full decoded duration"), element("strong", "", formatSeconds(duration) || "—"), element("small", "", "Quiet sections are included"));
    grid.append(full);
    return grid;
  }

  function formatSeconds(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return "";
    return Math.floor(seconds / 60) + ":" + String(Math.floor(seconds % 60)).padStart(2, "0");
  }

  function timelineBins(record) {
    if (!record || !Array.isArray(record.time_bins)) return [];
    return record.time_bins.filter((bin) => bin && typeof bin === "object" && typeof bin.reaches_20khz === "boolean").map((bin) => ({
      start: Number(bin.start_seconds || 0),
      end: Number(bin.start_seconds || 0) + Number(bin.seconds || 0),
      covered: bin.reaches_20khz
    }));
  }

  function spectrumColor(level) {
    const stops = [[0, 18, 15, 31], [.3, 59, 44, 94], [.6, 113, 88, 170], [.8, 193, 171, 224], [1, 255, 234, 173]];
    const t = Math.max(0, Math.min(1, level));
    let index = 0;
    while (index < stops.length - 2 && t > stops[index + 1][0]) index += 1;
    const a = stops[index];
    const b = stops[index + 1];
    const fraction = (t - a[0]) / (b[0] - a[0]);
    return [1, 2, 3].map((channel) => Math.round(a[channel] + (b[channel] - a[channel]) * fraction));
  }

  function createSpectrogram(record) {
    const plot = record.spectrogram;
    if (!plot || !Array.isArray(plot.values) || !Number.isInteger(plot.width) || !Number.isInteger(plot.height) || plot.width < 1 || plot.height < 1 || plot.width > 1000 || plot.height > 1000 || plot.values.length !== plot.width * plot.height) return null;
    const minDb = Number.isFinite(Number(plot.min_db)) ? Number(plot.min_db) : -110;
    const maxDb = Number.isFinite(Number(plot.max_db)) ? Number(plot.max_db) : 0;
    if (maxDb <= minDb) return null;
    const maxFrequency = Number(plot.max_frequency || Number(record.sample_rate || record.sample_rate_hz) / 2);
    if (!Number.isFinite(maxFrequency) || maxFrequency <= 0) return null;
    const section = element("div", "spectrogram-section");
    section.append(element("h3", "", "Full-track spectrogram overview"));
    section.append(element("p", "spectrogram-description", "Brighter colors show stronger spectral energy. This is an overview of the decoded signal; coverage measurements determine the grade."));
    const grid = element("div", "spectrogram-grid");
    const frequencyAxis = element("div", "frequency-axis");
    const frequencies = [0, 5000, 10000, 15000, 20000].filter((frequency) => frequency < maxFrequency * .95);
    frequencies.push(maxFrequency);
    frequencies.forEach((frequency) => {
      const tick = element("span", "frequency-tick", frequency === 0 ? "0" : (frequency / 1000).toFixed(frequency === maxFrequency ? 1 : 0) + "k");
      tick.style.top = ((1 - frequency / maxFrequency) * 100) + "%";
      frequencyAxis.append(tick);
    });
    const canvas = element("canvas", "spectrogram-canvas");
    canvas.width = 720;
    canvas.height = plot.height;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Full-track spectrogram showing spectral level from 0 to " + (maxFrequency / 1000).toFixed(1) + " kHz, and " + minDb + " to " + maxDb + " dB.");
    const context = canvas.getContext("2d");
    if (!context) return null;
    const sourceCanvas = element("canvas");
    sourceCanvas.width = plot.width;
    sourceCanvas.height = plot.height;
    const sourceContext = sourceCanvas.getContext("2d");
    if (!sourceContext) return null;
    const pixels = sourceContext.createImageData(plot.width, plot.height);
    for (let x = 0; x < plot.width; x += 1) {
      for (let frequency = 0; frequency < plot.height; frequency += 1) {
        const value = Number(plot.values[x * plot.height + frequency]);
        const color = spectrumColor((Number.isFinite(value) ? value - minDb : 0) / (maxDb - minDb));
        const offset = ((plot.height - 1 - frequency) * plot.width + x) * 4;
        pixels.data[offset] = color[0];
        pixels.data[offset + 1] = color[1];
        pixels.data[offset + 2] = color[2];
        pixels.data[offset + 3] = 255;
      }
    }
    sourceContext.putImageData(pixels, 0, 0);
    context.fillStyle = "#120f1f";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.imageSmoothingEnabled = false;
    const duration = Number(plot.duration_seconds || record.duration_seconds || 0);
    const hasTiming = Array.isArray(plot.start_seconds) && Array.isArray(plot.seconds) && plot.start_seconds.length === plot.width && plot.seconds.length === plot.width && duration > 0;
    if (hasTiming) {
      for (let x = 0; x < plot.width; x += 1) {
        const start = Number(plot.start_seconds[x]);
        const seconds = Number(plot.seconds[x]);
        if (!Number.isFinite(start) || !Number.isFinite(seconds) || start < 0 || seconds <= 0) continue;
        const left = start / duration * canvas.width;
        const width = Math.min(seconds, duration - start) / duration * canvas.width;
        if (width > 0) context.drawImage(sourceCanvas, x, 0, 1, plot.height, left, 0, width, canvas.height);
      }
    } else context.drawImage(sourceCanvas, 0, 0, canvas.width, canvas.height);
    grid.append(frequencyAxis, canvas);
    const timeAxis = element("div", "spectrum-time-axis");
    [0, .25, .5, .75, 1].forEach((fraction) => timeAxis.append(element("span", "", formatSeconds(duration * fraction))));
    const legend = element("div", "spectrum-level-legend");
    legend.append(element("span", "", "Spectral level"), element("span", "", minDb + " dB"), element("span", "spectrum-level-gradient"), element("span", "", maxDb + " dB"));
    section.append(grid, timeAxis, legend);
    return section;
  }

  function createTimeline(record, track, id) {
    const row = element("tr", "timeline-row");
    row.id = id;
    row.hidden = true;
    const cell = element("td");
    cell.colSpan = 5;
    const content = element("div", "timeline-content");
    content.setAttribute("role", "region");
    content.setAttribute("aria-label", "Measured evidence for " + (track.title || basename(track.source_path)));
    content.tabIndex = 0;
    content.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      row.hidden = true;
      const button = $("evidence-button-" + id.replace("timeline-", ""));
      if (button) {
        button.setAttribute("aria-expanded", "false");
        button.textContent = "View evidence";
        button.focus();
      }
    });
    content.append(element("h3", "", "20 kHz+ signal across the track"));
    content.append(element("p", "", "Measured windows for " + (track.title || basename(track.source_path)) + ". The full track duration is the coverage denominator."));
    content.append(coverageMetrics(record));
    const bins = timelineBins(record);
    if (bins.length) {
      const timeline = element("div", "timeline-track");
      timeline.setAttribute("role", "img");
      timeline.setAttribute("aria-label", "Measured 20 kHz+ timeline. " + bins.filter((bin) => bin.covered).length + " of " + bins.length + " displayed windows contain measurable signal.");
      bins.forEach((bin) => {
        const mark = element("span", "timeline-bin" + (bin.covered ? " covered" : ""));
        if (Number.isFinite(bin.start) && Number.isFinite(bin.end) && bin.end > bin.start) mark.style.flexGrow = string(bin.end - bin.start);
        mark.title = formatSeconds(bin.start) + "–" + formatSeconds(bin.end) + ": " + (bin.covered ? "measurable 20 kHz+ signal" : "below the signal threshold");
        timeline.append(mark);
      });
      const scale = element("div", "timeline-meta");
      scale.append(element("span", "", "0:00"), element("span", "", formatSeconds(record.duration_seconds ?? bins[bins.length - 1].end)));
      const legend = element("div", "timeline-legend");
      const covered = element("span", "legend-item");
      covered.append(element("span", "legend-swatch covered"), element("span", "", "Measurable signal"));
      const missing = element("span", "legend-item");
      missing.append(element("span", "legend-swatch"), element("span", "", "Below the threshold"));
      legend.append(covered, missing);
      content.append(timeline, scale, legend);
      content.append(element("div", "timeline-caption", "The timeline shows the analyzer’s measured windows. Silence and track sections without measurable high-frequency signal still count toward total duration."));
    } else {
      content.append(element("div", "coverage-empty", "A per-window timeline is not available for this result. The full-track coverage measurements are shown in the table."));
    }
    if (record.explanation || record.reason) content.append(element("div", "timeline-caption", record.explanation || record.reason));
    const contexts = [...new Set(asMessages(record.analysis_context))];
    contexts.forEach((context) => content.append(element("div", "evidence-context", context)));
    if (record.integrity_note) content.append(element("div", "evidence-context", record.integrity_note));
    if (record.quality === "LQ" && !contexts.length) content.append(element("div", "evidence-context", "LQ describes limited high-frequency coverage. An intentionally filtered sound, vintage recording, or bass stem can still be excellent for its purpose."));
    const rate = Number(record.sample_rate || record.sample_rate_hz || track.sample_rate);
    if (rate > 0 && rate / 2 < 20000 && !contexts.some((context) => /frequency ceiling|native.*rate|sample rate/i.test(context))) content.append(element("div", "evidence-context", "This sample rate limits the available frequency range to " + (rate / 2000).toFixed(1) + " kHz. The spectral grade follows the same fixed rules."));
    const metadata = technicalMetadata(track, record);
    if (Number(track.bit_depth) > 0) metadata.push(track.bit_depth + "-bit source");
    if (Number(track.encoded_bitrate) > 0) metadata.push(Math.round(track.encoded_bitrate / 1000) + " kbps encoded (informational)");
    if (metadata.length) content.append(element("div", "technical-details", metadata.join(" · ")));
    const spectrogram = createSpectrogram(record);
    if (spectrogram) content.append(spectrogram);
    else {
      const unavailable = element("div", "spectrogram-section");
      unavailable.append(element("h3", "", "Spectrum overview unavailable"));
      const reason = record.spectrum_evidence_unavailable_reason || record.spectrogram_note;
      unavailable.append(element("p", "spectrogram-description", reason || "No spectrum overview was provided for this result. The full-track coverage and timeline remain available above."));
      const budget = Number(record.spectrum_evidence_budget_bytes);
      if (record.spectrum_evidence_unavailable_reason && /budget/i.test(record.spectrum_evidence_unavailable_reason) && Number.isFinite(budget) && budget >= 0) {
        const budgetLabel = budget > 0 && budget < 1024 * 1024 ? budget + " bytes" : (budget / (1024 * 1024)).toLocaleString("en-US", { maximumFractionDigits: 3 }) + " MiB";
        unavailable.append(element("div", "timeline-caption", "Retained-spectrum evidence budget: " + budgetLabel + ". Every decoded bin still contributes to the full-track grade."));
      }
      content.append(unavailable);
    }
    cell.append(content);
    row.append(cell);
    return row;
  }

  function renderTracks() {
    const fragment = document.createDocumentFragment();
    let visible = 0;
    const view = window.SpectracraftLibraryView.orderedTracks(state.tracks, state.sort);
    view.forEach(({ track, index }) => {
      const fullRecord = state.records.get(string(track.id));
      const record = fullRecord || state.summaries.get(string(track.id));
      const matches = state.filter === "All" || state.filter === "Unmeasured" && !record || state.filter === "Error" && record && !!record.error || ["HQ", "MQ", "LQ"].includes(state.filter) && record && !record.error && record.quality === state.filter;
      if (!matches) return;
      visible += 1;
      const row = element("tr", track.enabled === false ? "disabled-row" : "");
      const selectCell = element("td", "select-column");
      const checkbox = element("input", "track-select");
      checkbox.type = "checkbox";
      checkbox.checked = track.enabled !== false;
      checkbox.setAttribute("aria-label", "Analyze " + (track.title || basename(track.source_path)));
      checkbox.addEventListener("change", () => {
        if (checkbox.checked && !track.scan_valid) {
          checkbox.checked = false;
          return;
        }
        track.enabled = checkbox.checked;
        row.classList.toggle("disabled-row", !checkbox.checked);
        updateControls();
      });
      selectCell.append(checkbox);
      const trackCell = element("td");
      const title = element("div", "track-title", track.title || basename(track.source_path));
      title.title = title.textContent;
      const artist = element("div", "track-artist", track.artist || "Artist not tagged");
      artist.title = artist.textContent;
      trackCell.append(title, artist);
      const source = element("div", "source-name", basename(track.source_path));
      source.title = string(track.source_path);
      trackCell.append(source);
      const metadata = technicalMetadata(track, record);
      if (metadata.length) trackCell.append(element("div", "track-meta", metadata.join(" · ")));
      const gradeCell = element("td");
      const grade = record ? record.error ? "Error" : string(record.quality || "Unrated") : string(track.quality || "Unrated");
      gradeCell.append(element("span", "quality-badge " + (["HQ", "MQ", "LQ"].includes(grade) ? grade.toLowerCase() : ""), grade));
      gradeCell.append(element("div", "grade-origin", record ? record.error ? "Analysis failed" : "Measured result" : track.quality ? "Existing label" : "Not analyzed"));
      const coverageCell = element("td");
      if (record && !record.error) {
        coverageCell.append(coverageRow("20 kHz+", coverageValue(record, "coverage_20khz"), true), coverageRow("18 kHz+", coverageValue(record, "coverage_18khz"), false));
        const nearBoundary = ["coverage_20khz", "coverage_18khz"].map((key) => coverageValue(record, key)).some((value) => value !== null && value >= 39.9 && value < 40);
        if (nearBoundary) coverageCell.append(element("div", "boundary-note", "Just below the 40% boundary. The measured grade is unchanged."));
      } else {
        coverageCell.append(element("div", "coverage-empty", record && record.error ? "Measurement unavailable" : "Run a full-track analysis"));
      }
      const statusCell = element("td");
      if (record) {
        statusCell.append(element("div", "analysis-status" + (record.error ? " error-status" : ""), record.integrity_check === "duration_mismatch" ? "Duration mismatch · Needs review" : record.error ? "Could not analyze" : fullRecord ? "Analysis complete" : "Measured in an earlier batch"));
        if (record.integrity_check === "duration_mismatch") statusCell.append(element("div", "quality-details", "Decoded " + formatSeconds(record.decoded_duration_seconds) + " · Header declares " + formatSeconds(record.declared_duration_seconds) + ". The file may be incomplete or have an incorrect header."));
        if (record.error) {
          const diagnostic = element("details", "error-details");
          diagnostic.append(element("summary", "", "Technical details"));
          diagnostic.append(element("div", "raw-error", record.error));
          const issues = analysisIssues(track.issues);
          if (issues.length) diagnostic.append(element("div", "raw-error", issues.join(" · ")));
          statusCell.append(diagnostic);
        }
        if (!record.error) {
          const duration = formatSeconds(record.duration_seconds ?? record.duration);
          const info = [];
          if (duration) info.push(duration + " full track");
          if (record.sample_rate_hz || record.sample_rate) info.push((Number(record.sample_rate_hz || record.sample_rate) / 1000).toFixed(1) + " kHz sample rate");
          if (info.length) statusCell.append(element("div", "quality-details", info.join(" · ")));
          if (fullRecord) {
            const timelineId = "timeline-" + index;
            const detailsButton = element("button", "timeline-button", "View evidence");
            detailsButton.type = "button";
            detailsButton.setAttribute("aria-expanded", "false");
            detailsButton.setAttribute("aria-controls", timelineId);
            detailsButton.id = "evidence-button-" + index;
            detailsButton.addEventListener("click", () => {
              const details = $(timelineId);
              details.hidden = !details.hidden;
              detailsButton.setAttribute("aria-expanded", string(!details.hidden));
              detailsButton.textContent = details.hidden ? "View evidence" : "Hide evidence";
            });
            statusCell.append(detailsButton);
          } else statusCell.append(element("div", "quality-details", "Analyze again to inspect evidence."));
        }
      } else {
        statusCell.append(element("div", "analysis-status pending-status", "Ready to analyze"));
      }
      const issues = analysisIssues(track.issues);
      if (issues.length && !(record && record.error)) statusCell.append(element("div", "row-issues", issues.join(" · ")));
      row.append(selectCell, trackCell, gradeCell, coverageCell, statusCell);
      fragment.append(row);
      if (fullRecord && !record.error) fragment.append(createTimeline(fullRecord, track, "timeline-" + index));
    });
    if (!visible && state.tracks.length) {
      const row = element("tr", "filter-empty-row");
      const cell = element("td", "", "No tracks match this filter. Choose All tracks to see the selection.");
      cell.colSpan = 5;
      row.append(cell);
      fragment.append(row);
    }
    $("track-rows").replaceChildren(fragment);
    $("track-count").textContent = string(state.tracks.length);
    $("empty-state").hidden = state.tracks.length > 0;
    $("tracks-container").hidden = state.tracks.length === 0;
    $("review-toolbar").hidden = state.tracks.length === 0;
    $("filter-toolbar").hidden = state.tracks.length === 0;
    $("visible-count").textContent = visible + " of " + state.tracks.length + " track" + (state.tracks.length === 1 ? "" : "s") + " shown";
    renderResultSummary();
    updateControls();
  }

  function resetScanButton() {
    $("scan-button").replaceChildren(document.createTextNode("Add music "), element("span", "", "＋"));
  }

  function closeSourceMenu() {
    $("source-menu").hidden = true;
    $("scan-button").setAttribute("aria-expanded", "false");
  }

  async function loadMusic(path, force = false) {
    path = string(path).trim();
    if (path.startsWith('"') && path.endsWith('"')) path = path.slice(1, -1);
    if (!path || state.busy || !state.config || (!force && path === state.root)) return;
    closeSourceMenu();
    $("root-path").value = path;
    await scanFolder(path);
  }

  function acceptScan(result, root) {
    state.root = result.root || root;
    state.sourceKind = result.source_kind === "file" ? "file" : "folder";
    state.inventoryIncomplete = !!result.truncated;
    state.tracks = (result.tracks || []).map((track) => {
      const scanValid = track.enabled !== false;
      return { ...track, scan_valid: scanValid, enabled: scanValid };
    });
    state.alphabetical = window.SpectracraftLibraryView.analysisOrder(state.tracks);
    state.batchSeen = 0;
    state.sort = "title-asc";
    $("track-sort").value = "title-asc";
    state.records.clear();
    state.summaries.clear();
    state.filter = "All";
    $("grade-filter").value = "All";
    state.reportJobId = null;
    state.reportTrackCount = 0;
    $("root-path").value = state.root;
    $("review-status").textContent = state.tracks.length ? state.tracks.filter((track) => track.scan_valid).length > trackLimit() ? "All readable tracks selected. Batches continue automatically." : state.sourceKind === "file" ? "Your file is ready. Analyze it to see the evidence." : "Your folder is ready. Choose tracks and analyze." : "No supported audio files found.";
    $("review-status-detail").textContent = state.tracks.length ? state.sourceKind === "file" ? "Only this file was read; other songs in its folder were not scanned. Existing HQ labels are checked again." : "Loaded " + state.tracks.length + " tracks. Selected tracks process automatically in title A–Z batches of " + trackLimit() + "." : "Choose a folder or file in one of the supported formats.";
    $("analysis-summary").textContent = "Automatic batches of " + trackLimit() + " · Title A–Z";
    $("review-eyebrow").textContent = "02 / ANALYZE & INSPECT";
    $("review-description").textContent = "Selected tracks process in title A–Z order. Batches of " + trackLimit() + " continue automatically; Pause/Resume and Stop stay available.";
    $("report-detail").textContent = "Your report is ready after an analysis completes.";
    setStep(state.tracks.length ? "analyze" : "scan");
    const warnings = analysisIssues(result.warnings);
    if (result.truncated && !warnings.length) warnings.push("This folder exceeds the local inventory limit. Only the first " + (state.config.max_inventory_tracks || state.tracks.length) + " tracks are shown.");
    if (warnings.length) $("alerts").append(alertBox("", "Music reading notes", warnings));
    renderTracks();
  }

  async function scanFolder(root, keepAlerts) {
    state.busy = true;
    state.scanContext = { root, keepAlerts: !!keepAlerts };
    if (!keepAlerts) $("alerts").replaceChildren();
    $("scan-button").textContent = "Reading…";
    $("review-status").textContent = "Reading your music…";
    updateControls();
    try {
      const result = await api("/api/scan", { root });
      if (result.job_id) {
        state.job = { id: result.job_id, kind: "scan", cancelling: false };
        state.pollFailures = 0;
        showProgress({ kind: "scan", progress: { done: 0, total: 0, message: "Reading your selected folder or file." } });
        pollJob();
      } else if (Array.isArray(result.tracks)) {
        acceptScan(result, root);
        state.busy = false;
        state.scanContext = null;
        resetScanButton();
      } else throw new Error("The local app did not return a music-reading job.");
    } catch (error) {
      state.busy = false;
      state.scanContext = null;
      resetScanButton();
      setAlert("error", "The folder or file could not be read", errorMessage(error));
      $("review-status").textContent = state.tracks.length ? "Your previous selection is still shown." : "Choose an accessible music folder or file.";
    }
    updateControls();
  }

  function mergeResults(result, summaries = []) {
    const records = Array.isArray(result && result.records) ? result.records : [];
    if (records.length) state.records.clear();
    const pathIds = new Map(state.tracks.map((track) => [string(track.source_path), string(track.id)]));
    summaries.forEach(record => {
      const id = record.id !== undefined ? string(record.id) : pathIds.get(string(record.source_path));
      if (id !== undefined) state.summaries.set(id, record);
    });
    records.forEach((record) => {
      const id = record.id !== undefined ? string(record.id) : pathIds.get(string(record.source_path || record.path));
      if (id !== undefined) {
        state.records.set(id, record);
        const compact = {};
        ["id", "source_path", "quality", "status", "coverage_20khz", "coverage_18khz", "duration_seconds", "sample_rate", "sample_rate_hz", "channels", "codec", "container", "bit_depth", "encoded_bitrate", "integrity_check", "declared_duration_seconds", "decoded_duration_seconds"].forEach((field) => {
          if (record[field] !== undefined) compact[field] = record[field];
        });
        if (record.error) compact.error = string(record.error).slice(0, 700);
        state.summaries.set(id, compact);
      }
    });
    return records;
  }

  function resultsSummary() {
    const values = [...state.summaries.values()];
    const grades = ["HQ", "MQ", "LQ"].map((grade) => values.filter((record) => !record.error && record.quality === grade).length + " " + grade);
    const failures = values.filter((record) => record.error).length;
    return values.length ? grades.join(" · ") + (failures ? " · " + failures + " failed" : "") + " · Latest batch holds up to " + trackLimit() + " tracks" : "No completed measurements yet. Larger folders are analyzed in batches of " + trackLimit() + ".";
  }

  function stopProgressClock() {
    clearInterval(state.progressTimer);
    state.progressTimer = null;
    state.progressJobId = null;
  }

  function showProgress(job) {
    const key = job.id || state.job && state.job.id || job.kind;
    if (state.progressJobId !== key) {
      stopProgressClock();
      state.progressJobId = key;
      state.progressStarted = performance.now();
      const tick = () => { $("job-elapsed").textContent = formatSeconds((performance.now() - state.progressStarted) / 1000) + " elapsed"; };
      tick();
      state.progressTimer = setInterval(tick, 1000);
    }

    const progress = job.progress || {};
    const scanning = job.kind === "scan" || state.job && state.job.kind === "scan";
    const done = Math.max(0, Number(progress.done) || 0);
    const total = Math.max(0, Number(progress.total) || 0);
    $("job-panel").hidden = false;
    $("job-percentage").textContent = total ? Math.floor(Math.min(done, total) / total * 100) + "% processed" : "Loading…";
    $("job-title").textContent = scanning ? "Reading your music…" : progress.paused ? "Analysis paused" : state.job && state.job.pauseRequested ? "Pausing at a safe point…" : "Analyzing full tracks…";
    $("job-message").textContent = progress.message || (scanning ? "Reading local audio metadata." : "Measuring spectral coverage across each selected track.");
    $("job-progress").max = total || 1;
    if (total && (done > 0 || progress.paused)) $("job-progress").value = Math.min(done, total);
    else $("job-progress").removeAttribute("value");
    $("job-progress-label").textContent = scanning ? total ? done + " of " + total + " files checked. You can cancel this read." : done ? done + " files checked. Reading music…" : "Reading your selection. You can cancel this read." : total ? done + " of " + total + " tracks processed. All selected HQ labels are checked again." : "Starting the full-track analysis…";
    if (!scanning && progress.batch_count) $("job-progress-label").textContent = done + " of " + total + " tracks processed · Batch " + progress.batch_index + " of " + progress.batch_count + " · Title A–Z";
    $("rail-status").textContent = (scanning ? "Reading" : progress.paused ? "Paused" : "Analyzing") + (total ? " " + done + "/" + total : " music");
  }

  async function finishJob(job) {
    if (job.kind === "scan" || state.job && state.job.kind === "scan") {
      const context = state.scanContext || { root: $("root-path").value.trim() };
      state.busy = false;
      state.job = null;
      state.scanContext = null;
      state.pollFailures = 0;
      stopProgressClock();
    $("job-panel").hidden = true;
      $("cancel-button").textContent = "Cancel";
      resetScanButton();
      if (job.status === "complete") acceptScan(job.result || {}, context.root);
      else {
        $("review-status").textContent = job.status === "cancelled" ? "Music reading cancelled." : "The folder or file could not be read.";
        $("review-status-detail").textContent = state.tracks.length ? "Your previous tracks and measurements are still shown." : "Your music was left unchanged.";
        setAlert(job.status === "cancelled" ? "" : "error", job.status === "cancelled" ? "Music reading stopped" : "Music reading failed", job.status === "cancelled" ? "No music files were changed. Choose a folder or file when you’re ready to continue." : job.error || "The local app could not finish reading this selection.");
        setStep("scan");
      }
      updateControls();
      return;
    }
    const records = mergeResults(job.result || {}, job.summaries || []);
    const status = job.status;
    state.busy = false;
    state.job = null;
    state.pollFailures = 0;
    stopProgressClock();
    $("job-panel").hidden = true;
    $("cancel-button").textContent = "Cancel";
    renderTracks();
    $("analysis-summary").textContent = resultsSummary();
    if (status === "complete") {
      state.reportJobId = job.id;
      state.reportTrackCount = records.length;
      $("review-status").textContent = "Analysis complete. Your music is unchanged.";
      $("review-status-detail").textContent = (job.result.selected_total || records.length) + " selected tracks finished in " + (job.result.completed_batches || 1) + " batch(es). The report and detailed evidence cover the latest " + records.length + ".";
      $("review-eyebrow").textContent = "02 / MEASURED RESULTS";
      $("review-description").textContent = "Coverage is measured against the full track duration. Open the evidence to see more.";
      $("report-detail").textContent = records.length + " result" + (records.length === 1 ? "" : "s") + " in the latest run · Machine-specific paths removed; relative filenames included.";
      const failures = (job.summaries || records).filter((record) => record.error).length;
      if (failures) setAlert("", "Analysis completed with track errors", failures + " track" + (failures === 1 ? " could" : "s could") + " not be measured. See the status column and report for details.");
      else $("alerts").replaceChildren();
      setStep("results");
    } else if (status === "cancelled") {
      $("review-status").textContent = "Analysis stopped.";
      $("review-status-detail").textContent = records.length ? records.length + " results from the stopped run are shown. No files were changed." : state.records.size ? "Previous completed measurements are still shown. This run made no changes to your files." : "No files were changed. You can select tracks and try again.";
      setAlert("", "Analysis stopped", "Your audio and metadata are unchanged.");
      setStep(records.length ? "results" : "analyze");
    } else {
      $("review-status").textContent = "The analysis could not finish.";
      $("review-status-detail").textContent = "No music files were changed.";
      setAlert("error", "Analysis failed", job.error || "The local analyzer stopped before it could finish.");
      setStep("analyze");
    }
    if (status !== "complete" && job.completed_batches > 0 && records.length) {
      state.reportJobId = job.id;
      state.reportTrackCount = records.length;
      $("review-status-detail").textContent = (job.result.completed_tracks || 0) + " tracks retained from completed batches. The interrupted batch can be selected again.";
      $("report-detail").textContent = records.length + " results from the latest completed batch are available.";
    }
    updateControls();
  }

  async function pollJob() {
    if (!state.job) return;
    const currentId = state.job.id;
    try {
      const job = await api("/api/jobs/" + encodeURIComponent(currentId) + "?after_batch=" + state.batchSeen);
      if (!state.job || state.job.id !== currentId) return;
      state.pollFailures = 0;
      state.job.pauseRequested = !!job.pause_requested;
      if (job.completed_batches > state.batchSeen) {
        mergeResults(job.result || {}, job.summaries || []);
        state.batchSeen = job.completed_batches;
        renderTracks();
        $("analysis-summary").textContent = resultsSummary();
      }
      showProgress(job);
      updateControls();
      if (["complete", "failed", "cancelled"].includes(job.status)) {
        await finishJob(job);
        return;
      }
    } catch (error) {
      if (error.status === 403 || error.status === 404) {
        state.busy = false;
        state.job = null;
        state.reportJobId = null;
        state.scanContext = null;
        stopProgressClock();
    $("job-panel").hidden = true;
        $("cancel-button").textContent = "Cancel";
        resetScanButton();
        $("review-status").textContent = "This local run is no longer available.";
        $("review-status-detail").textContent = "Previously displayed measurements have not been changed.";
        setAlert("error", error.status === 403 ? "Reopen the local launch link" : "This local run is unavailable", error.status === 403 ? "The local session may have restarted. Use the fresh link printed by its launcher to reconnect." : "The local app no longer recognizes this run. Read the folder or file again before starting a new analysis.");
        if (error.status === 404) state.root = "";
        updateControls();
        return;
      }
      state.pollFailures += 1;
      $("job-message").textContent = "Waiting for the local app to respond. This run may still be processing.";
      if (state.pollFailures === 3) setAlert("error", "The job status is temporarily unavailable", errorMessage(error) + " The app will keep checking.");
    }
    state.pollTimer = setTimeout(pollJob, state.pollFailures ? 2500 : 800);
  }

  $("scan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.busy) loadMusic($("root-path").value, true);
  });

  $("root-path").addEventListener("input", updateControls);
  $("root-path").addEventListener("change", () => loadMusic($("root-path").value));
  $("root-path").addEventListener("paste", () => setTimeout(() => loadMusic($("root-path").value), 0));
  $("track-sort").addEventListener("change", () => { state.sort = $("track-sort").value; renderTracks(); });
  $("scan-button").addEventListener("click", () => {
    const bridge = window.pywebview && window.pywebview.api;
    if (!bridge) { $("root-path").focus(); return; }
    const open = $("source-menu").hidden;
    $("source-menu").hidden = !open;
    $("scan-button").setAttribute("aria-expanded", string(open));
    if (open) $("browse-file-button").focus();
  });
  document.addEventListener("click", (event) => { if (!event.target.closest(".music-picker")) closeSourceMenu(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("source-menu").hidden) { closeSourceMenu(); $("scan-button").focus(); } });
  const dropZone = $("music-drop-zone");
  document.addEventListener("dragover", (event) => { event.preventDefault(); });
  document.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-active");
    if (!(window.pywebview && window.pywebview.api)) setAlert("", "Open the desktop app to drop music", "The browser cannot read full local paths. Paste a folder or file path instead.");
  });
  dropZone.addEventListener("dragenter", () => dropZone.classList.add("drag-active"));
  dropZone.addEventListener("dragleave", (event) => { if (!dropZone.contains(event.relatedTarget)) dropZone.classList.remove("drag-active"); });

  $("theme-toggle").addEventListener("click", async () => {
    if (!state.config || !window.ResetLabCraftTheme) return;
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    window.ResetLabCraftTheme.setMode(theme);
    $("theme-toggle").disabled = true;
    try { await api("/api/preferences", { theme, scrolling: "smooth" }); }
    catch (error) { setAlert("error", "The appearance could not be saved", errorMessage(error)); }
    finally { $("theme-toggle").disabled = false; }
  });

  $("grade-filter").addEventListener("change", () => {
    state.filter = $("grade-filter").value;
    renderTracks();
  });

  $("next-batch-button").addEventListener("click", () => {
    if (state.busy) return;
    const ids = new Set(nextBatchTracks().map((track) => string(track.id)));
    state.tracks.forEach((track) => { track.enabled = ids.has(string(track.id)); });
    state.filter = "All";
    $("grade-filter").value = "All";
    renderTracks();
    $("review-status").textContent = ids.size + " unmeasured tracks selected. Ready to analyze.";
  });

  $("select-all").addEventListener("change", () => {
    const select = $("select-all").checked;
    const ids = new Set(bulkTracks().map((track) => string(track.id)));
    state.tracks.forEach((track) => { track.enabled = select && ids.has(string(track.id)); });
    renderTracks();
  });

  $("audit-button").addEventListener("click", async () => {
    if (state.busy || !selectedTracks().length) return;
    state.busy = true;
    state.batchSeen = 0;
    $("alerts").replaceChildren();
    updateControls();
    try {
      const result = await api("/api/audit", { root: state.root, tracks: selectedTracks().map((track) => ({ id: track.id, enabled: true })) });
      if (!result.job_id) throw new Error("The analyzer did not return a job identifier.");
      state.job = { id: result.job_id, kind: "audit", cancelling: false };
      state.pollFailures = 0;
      $("job-title").textContent = "Analyzing full tracks…";
      $("review-status").textContent = "Measuring the selected tracks…";
      $("review-status-detail").textContent = "Filenames, metadata, audio, and artwork stay unchanged.";
      setStep("analyze");
      showProgress({ progress: { done: 0, total: selectedTracks().length, message: "Starting the analysis." } });
      updateControls();
      pollJob();
    } catch (error) {
      state.busy = false;
      setAlert("error", "The analysis could not start", errorMessage(error));
      updateControls();
    }
  });

  $("pause-button").addEventListener("click", async () => {
    if (!state.job || state.job.kind !== "audit" || state.job.cancelling || state.job.pauseUpdating) return;
    const job = state.job;
    const wanted = !job.pauseRequested;
    job.pauseUpdating = true;
    updateControls();
    try {
      await api("/api/pause", { job_id: job.id, paused: wanted });
      if (state.job === job) {
        job.pauseRequested = wanted;
        $("job-title").textContent = wanted ? "Pausing at a safe point…" : "Resuming full-track analysis…";
      }
    } catch (error) { setAlert("error", "The pause state could not be changed", errorMessage(error)); }
    finally { job.pauseUpdating = false; updateControls(); }
  });

  $("cancel-button").addEventListener("click", async () => {
    if (!state.job || state.job.cancelling) return;
    const currentJobId = state.job.id;
    state.job.cancelling = true;
    $("cancel-button").textContent = "Stopping…";
    updateControls();
    try {
      await api("/api/cancel", { job_id: currentJobId });
      if (!state.job || state.job.id !== currentJobId) return;
      $("job-message").textContent = "Cancellation requested. Waiting for the analyzer to stop safely.";
    } catch (error) {
      if (!state.job || state.job.id !== currentJobId) return;
      state.job.cancelling = false;
      $("cancel-button").textContent = "Cancel";
      setAlert("error", "Cancellation could not be requested", errorMessage(error));
      updateControls();
    }
  });

  $("export-button").addEventListener("click", async () => {
    if (!state.reportJobId || state.busy || state.exporting) return;
    const currentReportId = state.reportJobId;
    const currentReportCount = state.reportTrackCount;
    state.exporting = true;
    updateControls();
    try {
      if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.save_report === "function") {
        const result = await window.pywebview.api.save_report(currentReportId);
        if (result && result.error) throw new Error(result.error);
        if (!result || result.cancelled) return;
        if (!result.saved) throw new Error("The report was not saved.");
        if (state.reportJobId === currentReportId) {
          setStep("export");
          $("review-status").textContent = "JSON report saved.";
          $("review-status-detail").textContent = currentReportCount + " track results saved to " + basename(result.path);
          $("report-detail").textContent = "Saved " + basename(result.path) + " · " + currentReportCount + " results";
        }
        return;
      }
      const response = await fetch("/api/report/" + encodeURIComponent(currentReportId), { headers: { "X-Local-Token": state.token }, credentials: "same-origin", cache: "no-store" });
      if (!response.ok) {
        if (response.status === 403) invalidateSession();
        let problem = null;
        try { problem = await response.json(); } catch (_) { /* The HTTP status remains useful. */ }
        throw new Error(problem && (problem.error || problem.message) || "The report could not be downloaded (" + response.status + ").");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
      const filename = filenameMatch ? filenameMatch[1].replace(/[\\/]/g, "_").trim() : "song-quality-report.json";
      const url = URL.createObjectURL(blob);
      const anchor = element("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (state.reportJobId === currentReportId) {
        setStep("export");
        $("review-status").textContent = "Report download started.";
        $("review-status-detail").textContent = "The report covers " + currentReportCount + " tracks from the latest analysis run.";
        $("report-detail").textContent = "JSON download started · " + currentReportCount + " track results";
      }
    } catch (error) {
      setAlert("error", "The report could not be downloaded", errorMessage(error));
    } finally { state.exporting = false; updateControls(); }
  });

  let dropPolling = false;
  function setupDesktopBridge() {
    const bridge = window.pywebview && window.pywebview.api;
    $("browse-button").hidden = !bridge || typeof bridge.choose_folder !== "function";
    $("browse-file-button").hidden = !bridge || typeof bridge.choose_file !== "function";
    if (bridge && typeof bridge.save_report === "function") $("export-button").replaceChildren(document.createTextNode("Save JSON report "), element("span", "", "↓"));
    if (bridge && typeof bridge.take_drop === "function" && !dropPolling) {
      dropPolling = true;
      const pollDrop = async () => {
        try {
          const status = await bridge.drop_status();
          $("drop-hint").textContent = status.available ? "Drop one audio file or folder here, or use Add music. It loads automatically." : "Use Add music to choose a file or folder. Selection loads automatically.";
          const drop = await bridge.take_drop();
          if (drop && drop.error) setAlert("", "Music could not be added", drop.error);
          else if (drop && drop.path) {
            if (state.busy) setAlert("", "An operation is already running", "Wait for it to finish or cancel before adding music.");
            else await loadMusic(drop.path, true);
          }
        } catch (_) { /* Window shutdown or reload can interrupt the native bridge. */ }
        setTimeout(pollDrop, 600);
      };
      pollDrop();
    }
  }

  async function pickMusic(kind) {
    const bridge = window.pywebview && window.pywebview.api;
    const method = kind === "folder" ? "choose_folder" : "choose_file";
    if (state.busy || !bridge || typeof bridge[method] !== "function") return;
    closeSourceMenu();
    let path;
    state.busy = true;
    updateControls();
    try { path = await bridge[method](); }
    catch (error) { setAlert("error", "Music could not be selected", errorMessage(error)); }
    finally { state.busy = false; updateControls(); }
    if (typeof path === "string" && path.trim()) await loadMusic(path, true);
  }
  $("browse-button").addEventListener("click", () => pickMusic("folder"));
  $("browse-file-button").addEventListener("click", () => pickMusic("file"));

  function setupScrollExperience() {
    if (typeof IntersectionObserver !== "function") return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sections = Array.from(document.querySelectorAll("[data-reveal]"));
    const reveals = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: .04 });
    const applyMotion = () => {
      if (motion.matches) {
        reveals.disconnect();
        sections.forEach((section) => section.classList.add("is-visible"));
      } else {
        sections.filter((section) => !section.classList.contains("is-visible")).forEach((section) => reveals.observe(section));
      }
      document.documentElement.classList.add("reveal-enabled");
    };
    applyMotion();
    if (typeof motion.addEventListener === "function") motion.addEventListener("change", applyMotion);
    else motion.addListener(applyMotion);
    const navigation = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting);
      if (!visible.length) return;
      const id = visible[visible.length - 1].target.id;
      document.querySelectorAll(".nav-link, .steps a").forEach((link) => {
        const active = link.getAttribute("href") === "#" + id;
        link.classList.toggle("in-view", active);
        if (link.classList.contains("nav-link")) link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, { rootMargin: "-90px 0px -55% 0px", threshold: 0 });
    ["library", "tracks", "report", "method"].forEach((id) => {
      const section = $(id);
      if (section) navigation.observe(section);
    });
  }

  async function initialize() {
    updateControls();
    try {
      state.config = await api("/api/config");
      if (state.config.ui_preferences) {
        if (window.ResetLabCraftTheme) window.ResetLabCraftTheme.setMode(state.config.ui_preferences.theme);
      }
      if (window.ResetLabCraftScroll) window.ResetLabCraftScroll.setMode("smooth");
      $("theme-toggle").disabled = false;
      $("review-description").textContent = "Large folders are welcome. Selected tracks run automatically in A–Z batches of " + trackLimit() + "; existing HQ labels are checked again.";
      $("root-path").value = state.config.default_root || "";
      $("app-version").textContent = state.config.version ? "v" + state.config.version : "";
      const formats = Array.isArray(state.config.supported_formats) ? state.config.supported_formats.map((format) => typeof format === "string" ? format : format.name || format.label || "").filter(Boolean) : [];
      const extensions = Array.isArray(state.config.supported_extensions) ? state.config.supported_extensions.map((extension) => string(extension).replace(/^\./, "").toUpperCase()) : [];
      $("supported-formats").textContent = formats.length || extensions.length ? "Audio formats" : "Local audio";
      $("formats-detail").textContent = formats.length || extensions.length ? "File types: " + (formats.length ? formats : extensions).join(" · ") + ". Codec support is checked during analysis." : "Files are read on your computer. Format support is checked during analysis.";
      const available = state.config.scanner_available !== false;
      $("scanner-status").replaceChildren(element("span", "status-dot" + (available ? "" : " warning")), element("span", "", available ? "Analyzer ready" : "Analyzer unavailable"));
      if (typeof state.config.quality_rule === "string" && state.config.quality_rule) $("quality-rule").textContent = state.config.quality_rule;
      if (state.config.mq_lq_rule) $("mq-lq-rule").textContent = state.config.mq_lq_rule;
      if (state.config.active_job) {
        const active = await api("/api/jobs/" + encodeURIComponent(state.config.active_job.id) + "?with_inventory=1");
        if (active.kind === "audit") {
          acceptScan({ root: active.source_root, source_kind: active.source_kind, tracks: active.inventory || [] }, active.source_root);
          const ids = new Set((active.selected_ids || []).map(string));
          state.tracks.forEach(track => { track.enabled = ids.has(string(track.id)); });
          renderTracks();
        } else state.scanContext = { root: active.source_root };
        state.busy = true;
        state.job = { id: active.id, kind: active.kind, pauseRequested: !!active.pause_requested, cancelling: false };
        pollJob();
      }
      if (!available) setAlert("error", "The analyzer is unavailable", state.config.scanner_error || "The local launcher could not find the required analysis tools. Review the setup instructions before analyzing tracks.");
    } catch (error) {
      $("scanner-status").replaceChildren(element("span", "status-dot warning"), element("span", "", "Connection needed"));
      setAlert("error", "The local app could not connect", errorMessage(error));
    }
    updateControls();
  }

  setupDesktopBridge();
  window.addEventListener("pywebviewready", setupDesktopBridge);
  setupScrollExperience();
  initialize();
})();
