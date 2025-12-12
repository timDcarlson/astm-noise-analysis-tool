const $ = (id) => document.getElementById(id);
const CHANNELS = {
  main: { label: "Main channel", plotId: "graph-main", metaId: "graph-main-meta", color: "#53c1a9" },
  ref: { label: "Reference channel", plotId: "graph-ref", metaId: "graph-ref-meta", color: "#f5b24a" },
};
let dataFilePath = "";
let loadModelPath = "";

function collectConfig() {
  const use_nn = $("useNN").checked;
  let model = $("model").value;
  if (!use_nn) {
    model = "conv";
  }

  return {
    use_nn,
    model,
    epochs: $("epochs").value,
    lr: $("lr").value,
    n_freq: $("nFreq").value,
    hidden: $("hidden").value,
    patience: $("patience").value,
    min_delta: $("minDelta").value,
    bell_min_amplitude: $("bellMinAmplitude").value,
    bell_min_width: $("bellMinWidth").value,
    bell_min_probability: $("bellMinProbability").value,
    file: dataFilePath,
    load_model: loadModelPath,
    save_models: $("saveModels").checked,
  };
}

function showStatus(text, isError = false) {
  const el = $("status");
  el.textContent = text;
  el.style.color = isError ? "#f27b7b" : "#93a4b3";
}

function showLog(result) {
  const log = $("log");
  const parts = [];
  parts.push(`cmd: ${result.cmd}`);
  parts.push(`returncode: ${result.returncode}`);
  if (result.stdout) {
    parts.push("\nstdout:\n" + result.stdout.trim());
  }
  if (result.stderr) {
    parts.push("\nstderr:\n" + result.stderr.trim());
  }
  log.textContent = parts.join("\n");
}

async function runAnalysis() {
  if (!dataFilePath) {
    showStatus("Choose a data file before running", true);
    return;
  }

  const cfg = collectConfig();
  const btn = $("runBtn");
  btn.disabled = true;
  btn.textContent = "Running...";
  showStatus("Working...");
  try {
    const resultStr = await eel.run_analysis(cfg)();
    const result = JSON.parse(resultStr);
    showStatus(result.returncode === 0 ? "Done" : "Finished with errors", result.returncode !== 0);
    showLog(result);
    await updateDenoisedPlots();
  } catch (err) {
    showStatus("Error running analysis", true);
    showLog({ cmd: "", returncode: -1, stdout: "", stderr: err.toString() });
    clearGraph("graph-main", "graph-main-meta", "Failed to load plot");
    clearGraph("graph-ref", "graph-ref-meta", "Failed to load plot");
    clearPlot("hist-amplitude", "Failed to load Spike histogram");
    clearPlot("hist-width", "Failed to load Spike histogram");
    clearPlot("hist-probability", "Failed to load Spike histogram");
    const probText = $("bellProbabilities");
    if (probText) {
      probText.textContent = "Unable to refresh Spike probabilities";
    }
  } finally {
    btn.disabled = false;
    btn.textContent = "Run";
  }
}

async function chooseDataFile() {
  try {
    const path = await eel.choose_file()();
    if (path) {
      dataFilePath = path;
      $("dataPathText").textContent = path;
    }
  } catch (err) {
    console.error("Failed to choose data file", err);
  }
}

async function chooseLoadModel() {
  try {
    const path = await eel.choose_load_path()();
    if (path) {
      loadModelPath = path;
      $("loadModelText").textContent = path;
    }
  } catch (err) {
    console.error("Failed to choose load model", err);
  }
}

function toFloatArray(arr) {
  if (!arr) return [];
  return arr
    .map((v) => parseFloat(v))
    .filter((v) => !Number.isNaN(v));
}

function safeFloat(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function clearPlot(plotId, message = "No data yet") {
  const plot = $(plotId);
  if (!plot) return;
  if (window.Plotly) {
    Plotly.purge(plot);
  }
  plot.innerHTML = `<div class="graph-placeholder">${message}</div>`;
}

function clearGraph(plotId, metaId, message = "No data yet") {
  clearPlot(plotId, message);
  const meta = $(metaId);
  if (meta) {
    meta.textContent = "";
  }
}

function renderDenoisedPlot(channelKey, payload) {
  const config = CHANNELS[channelKey];
  if (!config) return;
  const { plotId, metaId, color, label } = config;
  if (!payload || !payload.series) {
    clearGraph(plotId, metaId, `No ${label.toLowerCase()} data`);
    return;
  }
  const series = payload.series;
  const time = toFloatArray(series.time);
  if (!time.length) {
    clearGraph(plotId, metaId, `No ${label.toLowerCase()} data`);
    return;
  }
  const original = toFloatArray(series.original);
  const processed = toFloatArray(series.processed);
  const residual = toFloatArray(series.residual);
  const traces = [
    {
      name: "Original",
      x: time,
      y: original,
      mode: "lines",
      line: { color: "#53c1a9" },
    },
    {
      name: "Processed",
      x: time,
      y: processed,
      mode: "lines",
      line: { color, width: 2 },
    },
    {
      name: "Residual",
      x: time,
      y: residual,
      mode: "lines",
      line: { dash: "dot", color: "#82a5ff" },
      yaxis: "y2",
    },
  ];
  const layout = {
    title: { text: label, font: { size: 14 } },
    margin: { t: 40, b: 30, l: 40, r: 40 },
    xaxis: { title: "Time (s)", showgrid: true, gridcolor: "#1f2430" },
    yaxis: { title: "Intensity", showgrid: true, gridcolor: "#1f2430" },
    yaxis2: {
      title: "Residual",
      overlaying: "y",
      side: "right",
      showgrid: false,
    },
    legend: { orientation: "h", y: 1.12, font: { size: 11 } },
    paper_bgcolor: "#0b0d12",
    plot_bgcolor: "#0b0d12",
    font: { color: "#e6e9ef" },
  };
  const plot = $(plotId);
  if (!plot || !window.Plotly) {
    clearGraph(plotId, metaId, "Plotly not available");
    return;
  }
  Plotly.purge(plot);
  plot.innerHTML = "";
  Plotly.newPlot(plot, traces, layout, { responsive: true });
  const meta = $(metaId);
  if (meta) {
    const stats = payload.stats || {};
    const count = safeFloat(stats.bell_curve_event_count).toFixed(0);
    const perHour = safeFloat(stats.bell_curve_events_per_hour).toFixed(1);
    const meanProbPct = (safeFloat(stats.bell_curve_mean_probability) * 100).toFixed(1);
    meta.textContent = `Spike events: ${count} · ${perHour} /hr · mean prob ${meanProbPct}%`;
  }
}

function renderEventHistogram(plotId, key, title, eventsByChannel, xTitle) {
  const plot = $(plotId);
  if (!plot || !window.Plotly) {
    if (plot) {
      plot.textContent = "Plotly not available";
    }
    return;
  }
  const traces = [];
  for (const desc of Object.values(eventsByChannel)) {
    const values = (desc.events || [])
      .map((ev) => safeFloat(ev[key]))
      .filter((v) => Number.isFinite(v));
    if (!values.length) {
      continue;
    }
    traces.push({
      x: values,
      type: "histogram",
      name: desc.label,
      opacity: 0.7,
      marker: { color: desc.color },
      nbinsx: 24,
    });
  }
  if (!traces.length) {
    clearPlot(plotId, "Spike events not detected yet");
    return;
  }
  const layout = {
    title: { text: title, font: { size: 13 } },
    margin: { t: 38, b: 32, l: 40, r: 28 },
    xaxis: { title: xTitle, showgrid: true, gridcolor: "#1f2430" },
    yaxis: { title: "Count", showgrid: true, gridcolor: "#1f2430" },
    legend: { orientation: "h", y: 1.08, font: { size: 11 } },
    paper_bgcolor: "#0b0d12",
    plot_bgcolor: "#0b0d12",
    font: { color: "#e6e9ef" },
    bargap: 0.2,
  };
  Plotly.purge(plot);
  Plotly.newPlot(plot, traces, layout, { responsive: true });
}

function renderProbabilityHistogram(plotId, eventsByChannel) {
  const plot = $(plotId);
  if (!plot || !window.Plotly) {
    if (plot) {
      plot.textContent = "Plotly not available";
    }
    return;
  }
  const traces = [];
  const orientationMap = [
    { value: 1, label: "Up", opacity: 0.75, suffix: "up", colorFallback: "#53c1a9" },
    { value: -1, label: "Down", opacity: 0.55, suffix: "down", colorFallback: "#f27b7b" },
  ];
  for (const desc of Object.values(eventsByChannel)) {
    const events = desc.events || [];
    for (const orientation of orientationMap) {
      const values = events
        .filter((ev) => Number(ev.orientation) === orientation.value)
        .map((ev) => safeFloat(ev.prob) * 100)
        .filter((v) => Number.isFinite(v));
      if (!values.length) {
        continue;
      }
      traces.push({
        x: values,
        type: "histogram",
        name: `${desc.label} ${orientation.label}`,
        opacity: orientation.opacity,
        marker: { color: orientation.value === 1 ? desc.color : orientation.colorFallback },
        nbinsx: 20,
      });
    }
  }
  if (!traces.length) {
    clearPlot(plotId, "Spike probabilities not available");
    return;
  }
  const layout = {
    title: { text: "Spike probability", font: { size: 13 } },
    margin: { t: 38, b: 32, l: 40, r: 28 },
    xaxis: { title: "Probability (%)", showgrid: true, gridcolor: "#1f2430", range: [0, 101] },
    yaxis: { title: "Count", showgrid: true, gridcolor: "#1f2430" },
    legend: { orientation: "h", y: 1.08, font: { size: 11 } },
    paper_bgcolor: "#0b0d12",
    plot_bgcolor: "#0b0d12",
    font: { color: "#e6e9ef" },
    bargap: 0.2,
  };
  Plotly.purge(plot);
  Plotly.newPlot(plot, traces, layout, { responsive: true });
}

function updateProbabilityText(mainStats = {}, refStats = {}) {
  const target = $("bellProbabilities");
  if (!target) return;
  const mainPct = (safeFloat(mainStats.bell_curve_mean_probability) * 100).toFixed(1);
  const refPct = (safeFloat(refStats.bell_curve_mean_probability) * 100).toFixed(1);
  target.textContent = `Spike probability · Main ${mainPct}% · Reference ${refPct}%`;
}

function _getStatValue(stats, key) {
  if (!stats || !Object.prototype.hasOwnProperty.call(stats, key)) {
    return Number.NaN;
  }
  const value = Number(stats[key]);
  return Number.isFinite(value) ? value : Number.NaN;
}

function _formatNumber(value, decimals = 1) {
  return Number.isFinite(value) ? value.toFixed(decimals) : "—";
}

function _formatPercent(value, decimals = 1) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return `${value.toFixed(decimals)}%`;
}

function updateSummaryRow(rowId, label, stats) {
  const row = $(rowId);
  if (!row) return;
  const cells = row.querySelectorAll("span");
  if (cells.length < 4) return;
  cells[0].textContent = label;
  const count = _getStatValue(stats, "bell_curve_event_count");
  const perHour = _getStatValue(stats, "bell_curve_events_per_hour");
  const meanProb = _getStatValue(stats, "bell_curve_mean_probability") * 100;
  cells[1].textContent = _formatNumber(count, 0);
  cells[2].textContent = _formatNumber(perHour, 1);
  cells[3].textContent = _formatPercent(meanProb, 1);
}

function updateSummaryPanel(mainStats = {}, refStats = {}) {
  updateSummaryRow("summary-main", "Main", mainStats);
  updateSummaryRow("summary-ref", "Reference", refStats);
}

async function updateDenoisedPlots() {
  if (!dataFilePath) {
    clearGraph("graph-main", "graph-main-meta", "No file selected");
    clearGraph("graph-ref", "graph-ref-meta", "No file selected");
    clearPlot("hist-amplitude", "No Spike data");
    clearPlot("hist-width", "No Spike data");
    clearPlot("hist-probability", "No Spike data");
    const probText = $("bellProbabilities");
    if (probText) {
      probText.textContent = "Spike probabilities will appear after running.";
    }
    updateSummaryPanel({}, {});
    return;
  }
  try {
    const payloadStr = await eel.load_denoised_data(dataFilePath)();
    const payload = JSON.parse(payloadStr);
    const mainPayload = payload.main || {};
    const refPayload = payload.ref || {};
    renderDenoisedPlot("main", mainPayload);
    renderDenoisedPlot("ref", refPayload);
    const eventSeries = {
      main: { label: "Main", color: CHANNELS.main.color, events: mainPayload.events || [] },
      ref: { label: "Reference", color: CHANNELS.ref.color, events: refPayload.events || [] },
    };
    renderEventHistogram("hist-amplitude", "amplitude", "Spike amplitudes", eventSeries, "Amplitude");
    renderEventHistogram("hist-width", "width_s", "Event widths", eventSeries, "Width (s)");
    renderProbabilityHistogram("hist-probability", eventSeries);
    updateProbabilityText(mainPayload.stats || {}, refPayload.stats || {});
    updateSummaryPanel(mainPayload.stats || {}, refPayload.stats || {});
  } catch (err) {
    console.error("Failed to load denoised outputs", err);
    clearGraph("graph-main", "graph-main-meta", "Unable to load data");
    clearGraph("graph-ref", "graph-ref-meta", "Unable to load data");
    clearPlot("hist-amplitude", "Unable to load histograms");
    clearPlot("hist-width", "Unable to load histograms");
    clearPlot("hist-probability", "Unable to load histograms");
    const probText = $("bellProbabilities");
    if (probText) {
      probText.textContent = "Unable to load Spike probabilities";
    }
    updateSummaryPanel({}, {});
  }
}

function init() {
  $("runBtn").addEventListener("click", runAnalysis);
  $("dataBtn").addEventListener("click", chooseDataFile);
  $("loadModelBtn").addEventListener("click", chooseLoadModel);
  clearGraph("graph-main", "graph-main-meta", "No file selected");
  clearGraph("graph-ref", "graph-ref-meta", "No file selected");
  clearPlot("hist-amplitude", "Spike events will show here");
  clearPlot("hist-width", "Spike events will show here");
  clearPlot("hist-probability", "Spike probabilities will show here");
  updateProbabilityText({}, {});
  updateSummaryPanel({}, {});
}

document.addEventListener("DOMContentLoaded", init);
