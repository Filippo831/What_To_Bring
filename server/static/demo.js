const LAYER_LABELS = {
  base: "Base layer",
  middle: "Middle layer",
  insulation: "Insulation",
  shell: "Shell",
  pants: "Pants",
  shoes: "Shoes",
  gear: "Gear",
};

const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result-section");

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function format(value, suffix) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${Number(value).toFixed(1)}${suffix}`;
}

function renderLayers(recommendations) {
  const container = document.getElementById("layers");
  container.innerHTML = "";
  for (const [key, layer] of Object.entries(recommendations)) {
    const items = (layer.items || []).map((item) => {
      const pos = item.position
        ? `<span class="badge ${escapeHtml(item.position)}">${escapeHtml(item.position)}</span>`
        : "";
      return `<li>${escapeHtml(item.name)} ${pos}</li>`;
    });
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>${escapeHtml(LAYER_LABELS[key] || key)}</h3>
      <p class="motivation">${escapeHtml(layer.motivation || "")}</p>
      ${items.length ? `<ul>${items.join("")}</ul>` : "<p class=\"empty\">Nothing recommended</p>"}`;
    container.appendChild(card);
  }
}

function renderFeatures(features) {
  const container = document.getElementById("features");
  const rows = [];

  rows.push(["Distance", format(features.distance_km, " km")]);
  rows.push(["Elevation gain", format(features.elevation_gain_m, " m")]);
  rows.push(["Hiking time", format(features.hiking_time_minutes, " min")]);

  const surfaces = Object.entries(features.surfaces || {})
    .map(([type, pct]) => `${escapeHtml(type)}: ${format(pct, "%")}`)
    .join(", ");
  if (surfaces) rows.push(["Surfaces", surfaces]);

  const weather = features.weather || [];
  if (weather.length) {
    const temps = weather.map((p) => p.temperature_2m).filter((t) => t != null);
    const preps = weather.map((p) => p.precipitation_probability).filter((t) => t != null);
    if (temps.length) rows.push(["Temp range", `${Math.min(...temps).toFixed(0)} / ${Math.max(...temps).toFixed(0)} °C`]);
    if (preps.length) rows.push(["Max rain prob.", `${Math.max(...preps).toFixed(0)}%`]);
  }

  const climbs = features.climbs || [];
  if (climbs.length) {
    const hardest = climbs.reduce((a, b) => (b.gradient > a.gradient ? b : a));
    rows.push(["Climbs", `${climbs.length} (hardest ${format(hardest.gradient, "%")} gradient)`]);
  }

  container.innerHTML = `
    <table>
      ${rows.map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${v}</td></tr>`).join("")}
    </table>`;
}

function render(data) {
  document.getElementById("strategy").textContent =
    data.overall_strategy || "";
  renderLayers(data.recommendations || {});
  renderFeatures(data.hike_features || {});
  resultSection.hidden = false;
}

document.getElementById("estimate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  resultSection.hidden = true;

  const gpx = document.getElementById("gpx").files[0];
  if (!gpx) {
    statusEl.textContent = "Please select a GPX file.";
    return;
  }

  const formData = new FormData();
  formData.append("gpx", gpx);

  for (const [id, field] of [["personal", "personal_information"], ["hike", "hike_information"]]) {
    let value;
    try {
      value = JSON.stringify(JSON.parse(document.getElementById(id).value));
    } catch {
      statusEl.textContent = `Invalid JSON in "${id}" field.`;
      return;
    }
    formData.append(field, new Blob([value], { type: "application/json" }), `${field}.json`);
  }

  statusEl.textContent = "Analyzing... this can take a minute (weather and map analysis).";
  statusEl.classList.add("loading");

  let res;
  try {
    res = await fetch("/api/estimate", { method: "POST", body: formData });
  } catch {
    statusEl.textContent = "Network error: could not reach the server.";
    statusEl.classList.remove("loading");
    return;
  }

  const data = await res.json().catch(() => ({ error: "Invalid response from server" }));

  statusEl.classList.remove("loading");
  if (!res.ok) {
    statusEl.textContent = `Error (${res.status}): ${data.error || "unknown"}`;
    return;
  }

  statusEl.textContent = "";
  render(data);
});
