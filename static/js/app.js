"use strict";

const AUTH_STORAGE_KEY   = "medsy_user_session";
const HISTORY_STORAGE_PREFIX = "medsy_history_";

// ---------------------------------------------------------------------------
// Global state
// ---------------------------------------------------------------------------
const STATE = {
  searchMode: "upload",
  medicines: [],
  results: [],
  lastSearchLat: 28.5733,
  lastSearchLng: 77.2236,
};

// Leaflet map instance (one at a time)
let _leafletMap = null;

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------
function init() {
  hydrateHeaderAuth();
  initAuthPage();
  initFinderPage();
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------
function readStoredUser() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { localStorage.removeItem(AUTH_STORAGE_KEY); return null; }
}

async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password + "_medsy_2024");
  const buffer = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function scorePassword(pw) {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score; // 0–5
}

// ---------------------------------------------------------------------------
// Header auth hydration
// ---------------------------------------------------------------------------
function hydrateHeaderAuth() {
  const pill          = document.getElementById("auth-pill");
  const dashLink      = document.getElementById("dashboard-nav-link");
  const loginLink     = document.getElementById("login-nav-link");
  const registerLink  = document.getElementById("register-nav-link");
  const user          = readStoredUser();

  if (pill) pill.textContent = user ? `${user.name}` : "Guest mode";

  if (dashLink)     dashLink.classList.toggle("hidden", !user);
  if (loginLink)    loginLink.classList.toggle("hidden", !!user);
  if (registerLink) registerLink.classList.toggle("hidden", !!user);
}

// ---------------------------------------------------------------------------
// Auth page
// ---------------------------------------------------------------------------
function initAuthPage() {
  const form = document.getElementById("auth-form");
  if (!form) return;

  const authMode      = form.dataset.authMode === "register" ? "register" : "login";
  const nameField     = document.querySelector(".auth-name-field");
  const nameInput     = document.getElementById("auth-name");
  const emailInput    = document.getElementById("auth-email");
  const passwordInput = document.getElementById("auth-password");
  const confirmInput  = document.getElementById("auth-confirm-password");
  const feedback      = document.getElementById("auth-feedback");
  const stateCopy     = document.getElementById("auth-state-copy");
  const logoutBtn     = document.getElementById("logout-btn");
  const strengthFill  = document.getElementById("pw-strength-fill");
  const strengthLabel = document.getElementById("pw-strength-label");

  syncAuthState(stateCopy, logoutBtn);

  // Live password strength meter
  if (passwordInput && strengthFill && authMode === "register") {
    passwordInput.addEventListener("input", () => {
      const score = scorePassword(passwordInput.value);
      const pct   = (score / 5) * 100;
      const colors = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#16a34a"];
      const labels = ["Too short", "Weak", "Fair", "Good", "Strong"];
      strengthFill.style.width   = pct + "%";
      strengthFill.style.background = colors[Math.max(0, score - 1)] || "#ef4444";
      if (strengthLabel) strengthLabel.textContent = passwordInput.value ? labels[Math.max(0, score - 1)] : "";
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email    = emailInput    ? emailInput.value.trim()    : "";
    const password = passwordInput ? passwordInput.value.trim() : "";
    const fullName = nameInput     ? nameInput.value.trim()     : "";
    const confirm  = confirmInput  ? confirmInput.value.trim()  : "";

    if (!email || !password) {
      if (feedback) feedback.textContent = "Enter email and password to continue.";
      return;
    }

    if (authMode === "register") {
      if (!fullName) {
        if (feedback) feedback.textContent = "Enter your full name.";
        return;
      }
      if (password.length < 8) {
        if (feedback) feedback.textContent = "Password must be at least 8 characters.";
        return;
      }
      if (!/[0-9]/.test(password)) {
        if (feedback) feedback.textContent = "Password must include at least one number.";
        return;
      }
      if (confirm && password !== confirm) {
        if (feedback) feedback.textContent = "Passwords do not match.";
        return;
      }

      const passwordHash = await hashPassword(password);
      const user = { name: fullName, email, passwordHash };
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
      hydrateHeaderAuth();
      window.location.href = "/dashboard";
      return;
    }

    // ── Login ──────────────────────────────────────────────────────────────
    const existing = readStoredUser();
    if (!existing || existing.email.toLowerCase() !== email.toLowerCase()) {
      if (feedback) feedback.textContent = "No account found for that email. Please register first.";
      return;
    }

    if (existing.passwordHash) {
      const enteredHash = await hashPassword(password);
      if (enteredHash !== existing.passwordHash) {
        if (feedback) feedback.textContent = "Incorrect password. Please try again.";
        if (passwordInput) passwordInput.value = "";
        return;
      }
    }

    // Update name if session predates hashing
    if (!existing.passwordHash) {
      const hash = await hashPassword(password);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ ...existing, passwordHash: hash }));
    }

    hydrateHeaderAuth();
    window.location.href = "/dashboard";
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      hydrateHeaderAuth();
      syncAuthState(stateCopy, logoutBtn);
      if (feedback) feedback.textContent = "Logged out. You are back in guest mode.";
    });
  }
}

function syncAuthState(stateCopy, logoutBtn) {
  const user = readStoredUser();
  if (stateCopy) {
    stateCopy.textContent = user
      ? `${user.name} is signed in (${user.email}).`
      : "You are browsing in guest mode.";
  }
  if (logoutBtn) logoutBtn.classList.toggle("hidden", !user);
}

// ---------------------------------------------------------------------------
// Pharmacy finder page
// ---------------------------------------------------------------------------
function initFinderPage() {
  const modeButtons      = Array.from(document.querySelectorAll(".mode-btn"));
  const uploadPanel      = document.getElementById("upload-panel");
  const manualPanel      = document.getElementById("manual-panel");
  const fileInput        = document.getElementById("rx-file");
  const dropZone         = document.getElementById("rx-drop-zone");
  const uploadHelper     = document.getElementById("upload-helper");
  const manualInput      = document.getElementById("manual-input");
  const addressInput     = document.getElementById("address-input");
  const useManualBtn     = document.getElementById("use-manual-btn");
  const clearManualBtn   = document.getElementById("clear-manual-btn");
  const statusBanner     = document.getElementById("status-banner");
  const medicineList     = document.getElementById("medicine-list");
  const resultsList      = document.getElementById("results-list");
  const selectAllBtn     = document.getElementById("select-all-btn");
  const clearSelectionBtn= document.getElementById("clear-selection-btn");
  const findBtn          = document.getElementById("find-btn");

  if (!statusBanner || !medicineList || !resultsList || !findBtn) return;

  modeButtons.forEach((btn) =>
    btn.addEventListener("click", () =>
      setSearchMode(btn.dataset.mode, modeButtons, uploadPanel, manualPanel)
    )
  );

  if (fileInput) {
    fileInput.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (file) await uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn);
    });
  }

  if (dropZone) {
    ["dragenter", "dragover"].forEach((ev) =>
      dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); })
    );
    ["dragleave", "drop"].forEach((ev) =>
      dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove("drag-over"); })
    );
    dropZone.addEventListener("drop", async (event) => {
      const file = event.dataTransfer?.files?.[0];
      if (file) await uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn);
    });
  }

  if (useManualBtn && manualInput) {
    useManualBtn.addEventListener("click", async () =>
      parseManualMedicines(manualInput.value, statusBanner, medicineList, resultsList, findBtn)
    );
  }

  if (clearManualBtn && manualInput) {
    clearManualBtn.addEventListener("click", () => {
      manualInput.value = "";
      setStatus(statusBanner, "info", "Manual text cleared.");
    });
  }

  const manualAutoInput = document.getElementById("manual-auto-input");
  const addMedicineBtn  = document.getElementById("add-medicine-btn");
  if (addMedicineBtn && manualAutoInput && manualInput) {
    addMedicineBtn.addEventListener("click", () => {
      const val = manualAutoInput.value.trim();
      if (val) {
        manualInput.value = manualInput.value ? manualInput.value + "\n" + val : val;
        manualAutoInput.value = "";
        setStatus(statusBanner, "success", `Added ${val}. Press 'Search typed list' when ready.`);
      }
    });
    manualAutoInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); addMedicineBtn.click(); }
    });
  }

  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      STATE.medicines = STATE.medicines.map((m) => ({ ...m, selected: true }));
      renderMedicines(medicineList, findBtn);
    });
  }

  if (clearSelectionBtn) {
    clearSelectionBtn.addEventListener("click", () => {
      STATE.medicines = [];
      STATE.results   = [];
      renderMedicines(medicineList, findBtn);
      renderResults(resultsList);
      setStatus(statusBanner, "info", "Medicine list cleared.");
    });
  }

  medicineList.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-medicine-index]");
    if (!btn) return;
    const idx = Number(btn.dataset.medicineIndex);
    if (!Number.isNaN(idx) && STATE.medicines[idx]) {
      STATE.medicines[idx].selected = !STATE.medicines[idx].selected;
      renderMedicines(medicineList, findBtn);
    }
  });

  findBtn.addEventListener("click", async () => runFinder(addressInput, statusBanner, resultsList));

  renderMedicines(medicineList, findBtn);
  renderResults(resultsList);
  hydrateFinderFromQuery(modeButtons, uploadPanel, manualPanel, manualInput, addressInput, statusBanner, medicineList, resultsList, findBtn);
}

function hydrateFinderFromQuery(modeButtons, uploadPanel, manualPanel, manualInput, addressInput, statusBanner, medicineList, resultsList, findBtn) {
  const params  = new URLSearchParams(window.location.search);
  const mode    = params.get("mode");
  const text    = params.get("text");
  const address = params.get("address");

  if (mode)    setSearchMode(mode, modeButtons, uploadPanel, manualPanel);
  if (address && addressInput) addressInput.value = address;
  if (text && manualInput) {
    manualInput.value = text;
    parseManualMedicines(text, statusBanner, medicineList, resultsList, findBtn);
  }
}

function setSearchMode(mode, modeButtons, uploadPanel, manualPanel) {
  STATE.searchMode = mode === "manual" ? "manual" : "upload";
  modeButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === STATE.searchMode));
  uploadPanel?.classList.toggle("active", STATE.searchMode === "upload");
  manualPanel?.classList.toggle("active", STATE.searchMode === "manual");
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------
async function uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn) {
  const formData = new FormData();
  formData.append("file", file);
  if (uploadHelper) uploadHelper.textContent = `Selected file: ${file.name}`;
  setStatus(statusBanner, "loading", "Reading prescription…");
  try {
    const res  = await fetch("/api/ocr", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Upload failed.");

    const medicines = normaliseMedicines(data.medicines || [], "OCR");

    if (!medicines.length) {
      // No medicines detected — offer the raw text in manual mode
      const rawText = (data.raw_text || "").trim();
      const modeButtons = Array.from(document.querySelectorAll(".mode-btn"));
      const uploadPanel = document.getElementById("upload-panel");
      const manualPanel = document.getElementById("manual-panel");
      const manualInput = document.getElementById("manual-input");
      if (rawText && manualInput) {
        manualInput.value = rawText;
        setSearchMode("manual", modeButtons, uploadPanel, manualPanel);
        setStatus(statusBanner, "info",
          "No medicine names were recognised automatically. The extracted text has been placed in the manual tab — review and press 'Search typed list'.");
      } else {
        setStatus(statusBanner, "error",
          "No medicines could be detected. Try a clearer image or use 'Type Medicines'.");
      }
      return;
    }

    renderOcrPicker(medicines, medicineList, findBtn, statusBanner, resultsList);
    setStatus(statusBanner, "info",
      `Found ${medicines.length} medicine${medicines.length > 1 ? "s" : ""} — confirm your selection then press "Add selected".`);
  } catch (err) { setStatus(statusBanner, "error", err.message); }
}

// Simple keyword set used only for pre-ticking — no longer gates what the user can search
const MEDICINE_KEYWORDS = {
  paracetamol:1,acetaminophen:1,ibuprofen:1,aspirin:1,amoxicillin:1,amoxycillin:1,
  azithromycin:1,ciprofloxacin:1,metronidazole:1,doxycycline:1,cephalexin:1,
  omeprazole:1,pantoprazole:1,metformin:1,atorvastatin:1,amlodipine:1,metoprolol:1,
  losartan:1,telmisartan:1,cetirizine:1,loratadine:1,montelukast:1,salbutamol:1,
  prednisolone:1,dexamethasone:1,sertraline:1,escitalopram:1,alprazolam:1,diazepam:1,
  pregabalin:1,gabapentin:1,levothyroxine:1,vitamin:1,calcium:1,folic:1,iron:1,zinc:1,
  insulin:1,glimepiride:1,clopidogrel:1,warfarin:1,ondansetron:1,domperidone:1,
  ranitidine:1,rabeprazole:1,fluticasone:1,budesonide:1,clonazepam:1,quetiapine:1,
  olanzapine:1,risperidone:1,tramadol:1,diclofenac:1,naproxen:1,combiflam:1,
  dolo:1,crocin:1,brufen:1,augmentin:1,cipro:1,flagyl:1,zithromax:1,
};

function renderOcrPicker(medicines, medicineList, findBtn, statusBanner, resultsList) {
  if (!medicineList) return;

  const rows = medicines.map((med) => {
    return `
      <label class="ocr-pick-row ocr-pick-selected">
        <input type="checkbox" class="ocr-pick-cb" data-line="${escapeHtml(med.name)}" checked>
        <span class="ocr-pick-text">
          <strong>${escapeHtml(med.name)}</strong>
          <span style="color:var(--text-soft);font-size:0.82rem;margin-left:8px;">${escapeHtml(med.dose)} · ${escapeHtml(med.frequency)}</span>
        </span>
      </label>`;
  }).join("");

  medicineList.innerHTML = `
    <div class="ocr-picker">
      <p class="ocr-picker-hint">Tick the medicines from your prescription:</p>
      <div class="ocr-pick-list">${rows}</div>
      <div class="ocr-pick-actions">
        <button type="button" class="primary-button" id="ocr-add-btn" style="padding:9px 22px;">Add selected</button>
        <button type="button" class="text-btn" id="ocr-all-btn">Select all</button>
        <button type="button" class="text-btn" id="ocr-none-btn">None</button>
      </div>
    </div>`;

  // Toggle highlight when checkbox changes
  medicineList.querySelectorAll(".ocr-pick-cb").forEach(cb => {
    cb.addEventListener("change", () =>
      cb.closest(".ocr-pick-row").classList.toggle("ocr-pick-selected", cb.checked)
    );
  });

  document.getElementById("ocr-all-btn").addEventListener("click", () => {
    medicineList.querySelectorAll(".ocr-pick-cb").forEach(cb => {
      cb.checked = true;
      cb.closest(".ocr-pick-row").classList.add("ocr-pick-selected");
    });
  });

  document.getElementById("ocr-none-btn").addEventListener("click", () => {
    medicineList.querySelectorAll(".ocr-pick-cb").forEach(cb => {
      cb.checked = false;
      cb.closest(".ocr-pick-row").classList.remove("ocr-pick-selected");
    });
  });

  document.getElementById("ocr-add-btn").addEventListener("click", () => {
    const chosen = Array.from(medicineList.querySelectorAll(".ocr-pick-cb:checked"))
      .map(cb => cb.dataset.line.trim())
      .filter(Boolean);

    if (!chosen.length) {
      setStatus(statusBanner, "error", "Tick at least one medicine first.");
      return;
    }

    const medMap = Object.fromEntries(medicines.map(m => [m.name, m]));
    const newMeds = chosen.map(name => ({
      name,
      dose: medMap[name]?.dose || "See prescription",
      frequency: medMap[name]?.frequency || "As directed",
      source: "OCR",
      selected: true,
    }));

    STATE.medicines = [...STATE.medicines.filter(m => m.source !== "OCR"), ...newMeds];
    STATE.results = [];
    renderMedicines(medicineList, findBtn);
    renderResults(resultsList);
    setStatus(statusBanner, "success",
      `Added ${newMeds.length} medicine${newMeds.length > 1 ? "s" : ""} from prescription.`);
  });
}

async function parseManualMedicines(text, statusBanner, medicineList, resultsList, findBtn) {
  const cleaned = text.trim();
  if (!cleaned) { setStatus(statusBanner, "error", "Type at least one medicine."); return; }
  setStatus(statusBanner, "loading", "Parsing medicines...");
  try {
    const res  = await fetch("/api/medicines", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: cleaned }) });
    const data = await res.json();
    if (data.security_blocked) {
      throw new Error(data.error || "Safe search blocked that request.");
    }
    if (!res.ok || data.error) throw new Error(data.error || "Could not parse medicines.");
    const medicines = normaliseMedicines(data.medicines, "Manual entry");
    if (!medicines.length) throw new Error("No medicines found.");
    STATE.medicines = medicines;
    STATE.results   = [];
    renderMedicines(medicineList, findBtn);
    renderResults(resultsList);
    setStatus(statusBanner, "success", `Loaded ${medicines.length} medicine${medicines.length > 1 ? "s" : ""}.`);
  } catch (err) { setStatus(statusBanner, "error", err.message); }
}

async function runFinder(addressInput, statusBanner, resultsList) {
  const selected = STATE.medicines.filter((m) => m.selected).map((m) => m.name);
  if (!selected.length) { setStatus(statusBanner, "error", "Select at least one medicine."); return; }
  const address = addressInput?.value.trim() ?? "";
  setStatus(statusBanner, "loading", "Ranking nearby pharmacies...");
  try {
    const res  = await fetch("/api/rank", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ medicines: selected, address }) });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Could not rank pharmacies.");

    STATE.results = data.pharmacies || [];

    // Capture resolved search location for map
    if (data.location) {
      STATE.lastSearchLat = data.location.lat  ?? STATE.lastSearchLat;
      STATE.lastSearchLng = data.location.lng  ?? STATE.lastSearchLng;
    }

    renderResults(resultsList);
    if (!STATE.results.length) { setStatus(statusBanner, "error", "No pharmacies returned."); return; }

    const label = data.location?.resolved_label ?? "your area";
    const note  = data.location?.used_default && address ? " Address not matched exactly; using Delhi sample area." : "";
    setStatus(statusBanner, "success", `Showing ${STATE.results.length} pharmacies near ${label}.${note}`);

    // Persist to search history
    saveSearchHistory(selected, address, STATE.results);
  } catch (err) { setStatus(statusBanner, "error", err.message); }
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------
function renderMedicines(medicineList, findBtn) {
  if (!medicineList || !findBtn) return;
  if (!STATE.medicines.length) {
    medicineList.innerHTML = '<div class="empty-block">Your selected medicines will appear here.</div>';
    findBtn.disabled = true;
    return;
  }
  medicineList.innerHTML = STATE.medicines.map((m, i) => `
    <button type="button" class="medicine-item ${m.selected ? "selected" : ""}" data-medicine-index="${i}">
      <span class="medicine-toggle">${m.selected ? "&#10003;" : ""}</span>
      <span>
        <strong>${escapeHtml(m.name)}</strong>
        <span class="medicine-meta">${escapeHtml(m.dose)} | ${escapeHtml(m.frequency)}</span>
      </span>
      <span class="medicine-origin">${escapeHtml(m.source)}</span>
    </button>
  `).join("");
  findBtn.disabled = !STATE.medicines.some((m) => m.selected);
}

function renderResults(resultsList) {
  if (!resultsList) return;
  if (!STATE.results.length) {
    resultsList.innerHTML = '<div class="empty-block">No pharmacy results yet.</div>';
    return;
  }
  resultsList.innerHTML = STATE.results.map((pharmacy, index) => {
    const reliability = pharmacy.factor_scores?.reliability ? `${pharmacy.factor_scores.reliability}%` : "N/A";
    const hours       = pharmacy.factor_scores?.hours       ?? "Hours unavailable";
    const medChips    = (pharmacy.medicines || []).map((m) => `
      <span class="stock-chip ${escapeHtml(m.stock_label)}">${escapeHtml(m.medicine)}: ${escapeHtml(m.stock_label)}</span>
    `).join("");

    return `
      <article class="result-card">
        <div class="result-top">
          <div>
            <h3>${index + 1}. ${escapeHtml(pharmacy.name)}</h3>
            <p class="result-address">${escapeHtml(pharmacy.address || "")}</p>
            <p class="result-note">📞 ${escapeHtml(pharmacy.phone || "—")} | 🕒 ${escapeHtml(hours)}</p>
          </div>
          <div class="result-score">
            <strong>${escapeHtml(String(pharmacy.score))}%</strong>
            <span>match</span>
          </div>
        </div>
        <div class="result-metrics">
          <span class="metric-chip">${escapeHtml(String(pharmacy.distance_km))} km away</span>
          <span class="metric-chip">${escapeHtml(String(pharmacy.coverage_pct))}% coverage</span>
          <span class="metric-chip">Reliability ${escapeHtml(reliability)}</span>
        </div>
        <div class="result-match-list">${medChips}</div>
        <div style="margin-top:12px;">
          <button type="button" class="secondary-button" style="padding:8px 16px;font-size:0.85rem;"
            onclick="openPharmacyMap(${JSON.stringify(pharmacy).replace(/"/g, '&quot;')}, ${STATE.lastSearchLat}, ${STATE.lastSearchLng})">
            🗺 View on Map
          </button>
        </div>
      </article>
    `;
  }).join("");
}

// ---------------------------------------------------------------------------
// Leaflet map
// ---------------------------------------------------------------------------

// Tell Leaflet where to find its marker images (we host them locally).
(function fixLeafletIconPaths() {
  if (!window.L) return;
  const base = "/static/leaflet/";
  delete window.L.Icon.Default.prototype._getIconUrl;
  window.L.Icon.Default.mergeOptions({
    iconUrl:      base + "marker-icon.png",
    iconRetinaUrl: base + "marker-icon-2x.png",
    shadowUrl:    base + "marker-shadow.png",
  });
})();

function openPharmacyMap(pharmacy, userLat, userLng) {
  // Ensure overlay exists (injected either by template or dynamically)
  let overlay = document.getElementById("map-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "map-overlay";
    overlay.id = "map-overlay";
    overlay.innerHTML = `
      <div class="map-panel">
        <div class="map-panel-head">
          <div class="map-panel-info">
            <h3 id="map-pharmacy-title"></h3>
            <p id="map-pharmacy-addr" class="helper-text"></p>
            <p id="map-pharmacy-meta" class="helper-text"></p>
          </div>
          <button class="map-close-btn" id="map-close-btn">&#x2715; Close</button>
        </div>
        <div id="pharmacy-map"></div>
        <div class="map-actions">
          <a id="map-gmaps-link" href="#" target="_blank" rel="noopener" class="primary-link primary-button">
            Open turn-by-turn in Google Maps
          </a>
          <span class="helper-text" id="map-distance-info"></span>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.getElementById("map-close-btn").addEventListener("click", closePharmacyMap);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) closePharmacyMap(); });
  }

  // Populate text
  document.getElementById("map-pharmacy-title").textContent = pharmacy.name;
  document.getElementById("map-pharmacy-addr").textContent  = pharmacy.address || "";
  document.getElementById("map-pharmacy-meta").textContent  =
    `📞 ${pharmacy.phone || "—"}  ·  🕒 ${pharmacy.factor_scores?.hours ?? ""}  ·  ${pharmacy.distance_km} km away`;
  document.getElementById("map-distance-info").textContent  = `${pharmacy.distance_km} km from your search location`;

  // Google Maps directions link
  const gmaps = document.getElementById("map-gmaps-link");
  gmaps.href = `https://www.google.com/maps/dir/?api=1&origin=${userLat},${userLng}&destination=${pharmacy.lat},${pharmacy.lng}&travelmode=driving`;

  overlay.classList.add("active");
  document.body.style.overflow = "hidden";

  // Destroy previous map instance
  if (_leafletMap) { _leafletMap.remove(); _leafletMap = null; }

  // Init Leaflet — local tiles first, OSM as fallback for uncached zoom/areas
  const map = window.L.map("pharmacy-map");
  window.L.tileLayer("/tiles/{z}/{x}/{y}.png", {
    attribution: "© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
    maxZoom: 15,
    minZoom: 10,
    errorTileUrl: "/static/tiles/blank.png",
  }).addTo(map);

  // User location marker
  const userIcon = window.L.divIcon({
    className: "",
    html: '<div class="map-user-dot">📍</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
  window.L.marker([userLat, userLng], { icon: userIcon })
    .addTo(map)
    .bindPopup("<strong>Your search location</strong>");

  // Pharmacy marker
  const pharmIcon = window.L.divIcon({
    className: "",
    html: '<div class="map-pharmacy-dot">🏥</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
  window.L.marker([pharmacy.lat, pharmacy.lng], { icon: pharmIcon })
    .addTo(map)
    .bindPopup(`<strong>${pharmacy.name}</strong><br>${pharmacy.address || ""}`)
    .openPopup();

  // Dashed route line
  window.L.polyline([[userLat, userLng], [pharmacy.lat, pharmacy.lng]], {
    color: "#0088cc",
    weight: 3,
    dashArray: "10 8",
    opacity: 0.75,
  }).addTo(map);

  const bounds = window.L.latLngBounds([[userLat, userLng], [pharmacy.lat, pharmacy.lng]]);
  map.fitBounds(bounds, { padding: [44, 44] });
  _leafletMap = map;
}

function closePharmacyMap() {
  const overlay = document.getElementById("map-overlay");
  if (overlay) overlay.classList.remove("active");
  document.body.style.overflow = "";
  if (_leafletMap) { _leafletMap.remove(); _leafletMap = null; }
}

// ---------------------------------------------------------------------------
// Search history (localStorage per user)
// ---------------------------------------------------------------------------
function _historyKey() {
  const user = readStoredUser();
  return HISTORY_STORAGE_PREFIX + (user?.email ?? "guest");
}

function saveSearchHistory(medicines, address, results) {
  try {
    const key     = _historyKey();
    const history = loadSearchHistory();
    const entry = {
      id:        Date.now().toString(36) + Math.random().toString(36).slice(2),
      timestamp: new Date().toISOString(),
      medicines,
      address,
      topResults: results.slice(0, 3).map((r) => ({ name: r.name, score: r.score, coverage_pct: r.coverage_pct })),
    };
    history.unshift(entry);
    localStorage.setItem(key, JSON.stringify(history.slice(0, 50)));
  } catch { /* localStorage full or unavailable */ }
}

function loadSearchHistory() {
  try {
    const raw = localStorage.getItem(_historyKey());
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function setStatus(statusBanner, type, message) {
  if (!statusBanner) return;
  statusBanner.className = `status-banner ${type}`;
  statusBanner.textContent = message;
}

function normaliseMedicines(medicines, source) {
  return (medicines || []).map((m) => ({
    name:      m.name      || "Unknown",
    dose:      m.dose      || "As directed",
    frequency: m.frequency || "As directed",
    source,
    selected: m.selected !== false,
  }));
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

init();
