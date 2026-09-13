const LAYER_LABELS = {
  base: "Base layer",
  middle: "Middle layer",
  insulation: "Insulation",
  shell: "Shell",
  pants: "Pants",
  shoes: "Shoes",
  gear: "Gear",
};

const CATALOG_LAYER_BY_CATEGORY = {
  base: "BASE LAYER",
  middle: "MIDDLE LAYER",
  insulation: "INSULATION LAYER",
  shell: "SHELL LAYER",
};

const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result-section");
const feedbackSection = document.getElementById("feedback-section");
const feedbackCategoriesEl = document.getElementById("feedback-categories");
const feedbackStatusEl = document.getElementById("feedback-status");
const feedbackSubmitBtn = document.getElementById("feedback-submit");

let catalog = [];
const selected = new Set();

let currentCaseId = null;
let feedbackState = {};

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

  currentCaseId = data.case_id || null;
  initFeedback(data.recommendations || {});
}

function initFeedback(recommendations) {
  feedbackState = {};
  feedbackStatusEl.textContent = "";
  feedbackSubmitBtn.disabled = false;

  if (!currentCaseId) {
    feedbackSection.hidden = true;
    return;
  }

  for (const key of Object.keys(recommendations)) {
    feedbackState[key] = { accurate: null, items: [] };
  }
  renderFeedbackCategories(recommendations);
  feedbackSection.hidden = false;
}

function renderFeedbackCategories(recommendations) {
  feedbackCategoriesEl.innerHTML = "";

  for (const [key, layer] of Object.entries(recommendations)) {
    const items = layer.items || [];
    const card = document.createElement("div");
    card.className = "feedback-card";

    const header = document.createElement("div");
    header.className = "feedback-card-header";
    header.innerHTML = `<h4>${escapeHtml(LAYER_LABELS[key] || key)}</h4>`;

    const suggested = document.createElement("p");
    suggested.className = "feedback-suggested";
    suggested.textContent = items.length
      ? `Suggested: ${items.map((i) => i.name).join(", ")}`
      : "Suggested: nothing";
    header.appendChild(suggested);
    card.appendChild(header);

    const toggle = document.createElement("div");
    toggle.className = "feedback-toggle";

    const accurateBtn = document.createElement("button");
    accurateBtn.type = "button";
    accurateBtn.className = "feedback-btn accurate";
    accurateBtn.textContent = "👍 Accurate";

    const wrongBtn = document.createElement("button");
    wrongBtn.type = "button";
    wrongBtn.className = "feedback-btn inaccurate";
    wrongBtn.textContent = "✏️ Not quite";

    const editor = document.createElement("div");
    editor.className = "feedback-editor";
    editor.hidden = true;

    function refreshToggle() {
      const state = feedbackState[key].accurate;
      accurateBtn.classList.toggle("active", state === true);
      wrongBtn.classList.toggle("active", state === false);
      editor.hidden = state !== false;
    }

    accurateBtn.addEventListener("click", () => {
      feedbackState[key].accurate = true;
      refreshToggle();
    });
    wrongBtn.addEventListener("click", () => {
      feedbackState[key].accurate = false;
      refreshToggle();
    });

    toggle.appendChild(accurateBtn);
    toggle.appendChild(wrongBtn);
    card.appendChild(toggle);

    buildEditor(editor, key);
    card.appendChild(editor);

    feedbackCategoriesEl.appendChild(card);
  }
}

function buildEditor(editor, category) {
  editor.innerHTML = `
    <p class="feedback-editor-hint">What did you actually bring for this layer?</p>
    <div class="feedback-add-row">
      <input type="text" class="feedback-item-name" placeholder="Item name" list="feedback-catalog-${category}" />
      <select class="feedback-item-position">
        <option value="worn">worn</option>
        <option value="backpack">backpack</option>
      </select>
      <button type="button" class="feedback-add-item">Add</button>
    </div>
    <ul class="feedback-item-list"></ul>
  `;

  const catalogLayer = CATALOG_LAYER_BY_CATEGORY[category];
  if (catalogLayer) {
    const datalist = document.createElement("datalist");
    datalist.id = `feedback-catalog-${category}`;
    for (const item of catalog) {
      if (item.layer !== catalogLayer) continue;
      const option = document.createElement("option");
      option.value = item.name;
      datalist.appendChild(option);
    }
    editor.appendChild(datalist);
  }

  const nameInput = editor.querySelector(".feedback-item-name");
  const positionSelect = editor.querySelector(".feedback-item-position");
  const addBtn = editor.querySelector(".feedback-add-item");
  const list = editor.querySelector(".feedback-item-list");

  function renderList() {
    list.innerHTML = "";
    feedbackState[category].items.forEach((item, index) => {
      const li = document.createElement("li");
      li.innerHTML = `${escapeHtml(item.name)} <span class="badge ${escapeHtml(item.position)}">${escapeHtml(item.position)}</span>`;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "feedback-remove-item";
      removeBtn.textContent = "×";
      removeBtn.addEventListener("click", () => {
        feedbackState[category].items.splice(index, 1);
        renderList();
      });
      li.appendChild(removeBtn);
      list.appendChild(li);
    });
  }

  addBtn.addEventListener("click", () => {
    const name = nameInput.value.trim();
    if (!name) return;
    feedbackState[category].items.push({
      name,
      position: positionSelect.value,
    });
    nameInput.value = "";
    renderList();
  });

  renderList();
}

feedbackSubmitBtn.addEventListener("click", async () => {
  if (!currentCaseId) return;

  const categories = {};
  for (const [key, state] of Object.entries(feedbackState)) {
    if (state.accurate === null) continue; // no opinion given, skip
    categories[key] = state.accurate
      ? { accurate: true }
      : { accurate: false, actual_items: state.items };
  }

  if (Object.keys(categories).length === 0) {
    feedbackStatusEl.textContent = "Mark at least one category before sending.";
    return;
  }

  feedbackSubmitBtn.disabled = true;
  feedbackStatusEl.classList.remove("loading");
  feedbackStatusEl.textContent = "Sending...";
  feedbackStatusEl.classList.add("loading");

  try {
    const res = await fetch(`/api/feedback/${currentCaseId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        categories,
        comment: document.getElementById("feedback-comment").value.trim(),
      }),
    });
    const data = await res.json().catch(() => ({}));
    feedbackStatusEl.classList.remove("loading");
    if (!res.ok) {
      feedbackStatusEl.textContent = `Error (${res.status}): ${data.error || "unknown"}`;
      feedbackSubmitBtn.disabled = false;
      return;
    }
    feedbackStatusEl.textContent = "Thanks! Your feedback was recorded.";
  } catch {
    feedbackStatusEl.classList.remove("loading");
    feedbackStatusEl.textContent = "Network error: could not send feedback.";
    feedbackSubmitBtn.disabled = false;
  }
});

document.getElementById("estimate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  resultSection.hidden = true;
  feedbackSection.hidden = true;

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