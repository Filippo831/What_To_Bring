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

let catalog = [];
const selected = new Set();

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

async function loadCatalog() {
  try {
    const res = await fetch("/api/catalog");
    if (!res.ok) throw new Error(String(res.status));
    catalog = await res.json();
  } catch {
    statusEl.textContent = "Could not load the wardrobe catalog from the server.";
    return;
  }
  renderWardrobe();
}

function renderWardrobe() {
  const query = document.getElementById("wardrobe-search").value.trim().toLowerCase();
  const list = document.getElementById("wardrobe-list");
  list.innerHTML = "";

  const groups = {};
  for (const item of catalog) {
    (groups[item.layer] ||= []).push(item);
  }

  for (const [layer, items] of Object.entries(groups)) {
    const matches = items.filter((i) => i.name.toLowerCase().includes(query));
    if (!matches.length) continue;

    const group = document.createElement("div");
    group.className = "wardrobe-group";
    const header = document.createElement("h4");
    header.textContent = layer;
    group.appendChild(header);

    for (const item of matches) {
      const label = document.createElement("label");
      label.className = "choice";
      label.title = item.name;

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = selected.has(item.name);
      cb.addEventListener("change", () => {
        if (cb.checked) selected.add(item.name);
        else selected.delete(item.name);
        updateCount();
      });

      label.appendChild(cb);
      label.appendChild(document.createTextNode(item.name));
      group.appendChild(label);
    }

    list.appendChild(group);
  }

  updateCount();
}

function updateCount() {
  const total = document.querySelectorAll("#wardrobe-list input:checked").length;
  document.getElementById("wardrobe-count").textContent =
    `${total} selected out of ${catalog.length} items`;
}

document.getElementById("wardrobe-search").addEventListener("input", renderWardrobe);
document.getElementById("select-all").addEventListener("click", () => {
  for (const item of catalog) selected.add(item.name);
  renderWardrobe();
});
document.getElementById("clear-all").addEventListener("click", () => {
  selected.clear();
  renderWardrobe();
});

function buildPersonalInfo() {
  const info = {
    name: document.getElementById("name").value.trim(),
    surname: document.getElementById("surname").value.trim(),
    mail: document.getElementById("mail").value.trim(),
    gender: document.getElementById("gender").value,
    heat_tolerance: Number(document.getElementById("heat-tolerance").value),
  };
  const age = Number(document.getElementById("age").value);
  if (age > 0) info.age = age;
  info.wardrobe = [...selected];
  return info;
}

function buildHikeInfo() {
  const info = { type: document.getElementById("activity-type").value.trim() };
  const startingTime = document.getElementById("starting-time").value;
  if (startingTime) info.starting_time = startingTime.replace("T", " ");
  return info;
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
  if (selected.size === 0) {
    statusEl.textContent = "Select at least one item in your wardrobe.";
    return;
  }

  const formData = new FormData();
  formData.append("gpx", gpx);
  formData.append(
    "personal_information",
    new Blob([JSON.stringify(buildPersonalInfo())], { type: "application/json" }),
    "personal_information.json"
  );
  formData.append(
    "hike_information",
    new Blob([JSON.stringify(buildHikeInfo())], { type: "application/json" }),
    "hike_information.json"
  );

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

loadCatalog();