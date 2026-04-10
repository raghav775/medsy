"use strict";

const AUTH_STORAGE_KEY = "medsy_user_session";

const STATE = {
  authMode: "login",
  searchMode: "upload",
  medicines: [],
  results: [],
};

const elements = {
  navLinks: Array.from(document.querySelectorAll(".nav-link")),
  targetButtons: Array.from(document.querySelectorAll("[data-target]")),
  authJumpButtons: Array.from(document.querySelectorAll("[data-auth-jump]")),
  authTabs: Array.from(document.querySelectorAll(".auth-toggle-btn")),
  authForm: document.getElementById("auth-form"),
  authNameField: document.querySelector(".auth-name-field"),
  authName: document.getElementById("auth-name"),
  authEmail: document.getElementById("auth-email"),
  authPassword: document.getElementById("auth-password"),
  authSubmitBtn: document.getElementById("auth-submit-btn"),
  authFeedback: document.getElementById("auth-feedback"),
  authStateCopy: document.getElementById("auth-state-copy"),
  authPill: document.getElementById("auth-pill"),
  logoutBtn: document.getElementById("logout-btn"),
  lookupStatusCopy: document.getElementById("lookup-status-copy"),
  modeButtons: Array.from(document.querySelectorAll(".mode-btn")),
  uploadPanel: document.getElementById("upload-panel"),
  manualPanel: document.getElementById("manual-panel"),
  uploadHelper: document.getElementById("upload-helper"),
  fileInput: document.getElementById("rx-file"),
  dropZone: document.getElementById("rx-drop-zone"),
  manualInput: document.getElementById("manual-input"),
  useManualBtn: document.getElementById("use-manual-btn"),
  clearManualBtn: document.getElementById("clear-manual-btn"),
  statusBanner: document.getElementById("status-banner"),
  medicineList: document.getElementById("medicine-list"),
  selectAllBtn: document.getElementById("select-all-btn"),
  clearSelectionBtn: document.getElementById("clear-selection-btn"),
  findBtn: document.getElementById("find-btn"),
  resultsList: document.getElementById("results-list"),
  latInput: document.getElementById("lat-input"),
  lngInput: document.getElementById("lng-input"),
  useLocationBtn: document.getElementById("use-location-btn"),
  quickChips: Array.from(document.querySelectorAll(".quick-chip")),
};

const sections = ["overview", "finder", "lookup", "contact"].map((id) => ({
  id,
  element: document.getElementById(id),
}));

function init() {
  bindNavigation();
  bindAuth();
  bindFinder();
  setAuthMode(STATE.authMode);
  hydrateAuthState();
  updateActiveNav();
  renderMedicines();
  renderResults();
}

function bindNavigation() {
  elements.targetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.target;
      if (target) {
        scrollToSection(target);
      }
    });
  });

  elements.authJumpButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setAuthMode(button.dataset.authJump || "login");
      scrollToSection("account");
    });
  });

  window.addEventListener("scroll", updateActiveNav, { passive: true });
}

function bindAuth() {
  elements.authTabs.forEach((tab) => {
    tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode));
  });

  elements.authForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const mode = STATE.authMode;
    const email = elements.authEmail.value.trim();
    const password = elements.authPassword.value.trim();
    const name = elements.authName.value.trim();

    if (!email || !password) {
      elements.authFeedback.textContent = "Enter email and password to continue.";
      return;
    }

    if (mode === "register" && !name) {
      elements.authFeedback.textContent = "Enter a full name to create the local account session.";
      return;
    }

    const existing = readStoredUser();
    const user = {
      name:
        mode === "register"
          ? name
          : existing?.email === email
            ? existing.name
            : email.split("@")[0],
      email,
    };

    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    hydrateAuthState();

    elements.authFeedback.textContent =
      mode === "register"
        ? `Registered locally as ${user.name}.`
        : `Logged in locally as ${user.name}.`;
    elements.authPassword.value = "";
  });

  elements.logoutBtn.addEventListener("click", () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    hydrateAuthState();
    elements.authFeedback.textContent = "Logged out. You are back in guest mode.";
  });
}

function bindFinder() {
  elements.modeButtons.forEach((button) => {
    button.addEventListener("click", () => setSearchMode(button.dataset.mode));
  });

  elements.fileInput.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await uploadPrescription(file);
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.remove("drag-over");
    });
  });

  elements.dropZone.addEventListener("drop", async (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      await uploadPrescription(file);
    }
  });

  elements.useManualBtn.addEventListener("click", async () => {
    await parseManualMedicines();
  });

  elements.clearManualBtn.addEventListener("click", () => {
    elements.manualInput.value = "";
    setStatus("info", "Manual text cleared.");
  });

  elements.quickChips.forEach((chip) => {
    chip.addEventListener("click", async () => {
      setSearchMode("manual");
      elements.manualInput.value = chip.dataset.example || "";
      scrollToSection("finder");
      await parseManualMedicines();
    });
  });

  elements.selectAllBtn.addEventListener("click", () => {
    STATE.medicines = STATE.medicines.map((medicine) => ({ ...medicine, selected: true }));
    renderMedicines();
  });

  elements.clearSelectionBtn.addEventListener("click", () => {
    STATE.medicines = [];
    STATE.results = [];
    renderMedicines();
    renderResults();
    setStatus("info", "Medicine list cleared.");
  });

  elements.findBtn.addEventListener("click", async () => {
    await runPharmacyFinder();
  });

  elements.useLocationBtn.addEventListener("click", () => {
    useCurrentLocation();
  });

  elements.medicineList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-medicine-index]");
    if (!button) {
      return;
    }

    const index = Number(button.dataset.medicineIndex);
    if (Number.isNaN(index) || !STATE.medicines[index]) {
      return;
    }

    STATE.medicines[index].selected = !STATE.medicines[index].selected;
    renderMedicines();
  });
}

function setAuthMode(mode) {
  STATE.authMode = mode === "register" ? "register" : "login";

  elements.authTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.authMode === STATE.authMode);
  });

  elements.authNameField.classList.toggle("hidden", STATE.authMode !== "register");
  elements.authSubmitBtn.textContent = STATE.authMode === "register" ? "Register" : "Login";
  elements.authFeedback.textContent =
    STATE.authMode === "register"
      ? "Create a local account session for this browser."
      : "Sign in locally to simulate the account flow.";
}

function hydrateAuthState() {
  const user = readStoredUser();

  if (!user) {
    elements.authPill.textContent = "Guest mode";
    elements.authStateCopy.textContent = "You are browsing in guest mode.";
    elements.lookupStatusCopy.textContent =
      "Login is optional right now. Your public pharmacy search already works without it.";
    elements.logoutBtn.classList.add("hidden");
    return;
  }

  elements.authPill.textContent = `Logged in: ${user.name}`;
  elements.authStateCopy.textContent = `${user.name} is signed in locally with ${user.email}.`;
  elements.lookupStatusCopy.textContent =
    "A local user session is active. This is where account-based medication tools can be added next.";
  elements.logoutBtn.classList.remove("hidden");
}

function readStoredUser() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function setSearchMode(mode) {
  STATE.searchMode = mode === "manual" ? "manual" : "upload";

  elements.modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === STATE.searchMode);
  });

  elements.uploadPanel.classList.toggle("active", STATE.searchMode === "upload");
  elements.manualPanel.classList.toggle("active", STATE.searchMode === "manual");
}

async function uploadPrescription(file) {
  const formData = new FormData();
  formData.append("file", file);

  elements.uploadHelper.textContent = `Selected file: ${file.name}`;
  setStatus("loading", "Reading the uploaded prescription and extracting medicines...");

  try {
    const response = await fetch("/api/ocr", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Upload failed.");
    }

    const medicines = normaliseMedicines(data.medicines, "Upload OCR");
    if (!medicines.length) {
      throw new Error("No medicines were detected in that file.");
    }

    STATE.medicines = medicines;
    STATE.results = [];
    renderMedicines();
    renderResults();
    setStatus("success", `Found ${medicines.length} medicine${medicines.length > 1 ? "s" : ""} from ${file.name}.`);
  } catch (error) {
    setStatus("error", error.message);
  }
}

async function parseManualMedicines() {
  const text = elements.manualInput.value.trim();
  if (!text) {
    setStatus("error", "Type at least one medicine before running manual search.");
    return;
  }

  setStatus("loading", "Parsing the medicines you typed...");

  try {
    const response = await fetch("/api/medicines", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Could not parse manual medicines.");
    }

    const medicines = normaliseMedicines(data.medicines, "Manual entry");
    if (!medicines.length) {
      throw new Error("No medicines were found in the typed text.");
    }

    STATE.medicines = medicines;
    STATE.results = [];
    renderMedicines();
    renderResults();
    setStatus("success", `Loaded ${medicines.length} medicine${medicines.length > 1 ? "s" : ""} from typed text.`);
  } catch (error) {
    setStatus("error", error.message);
  }
}

function normaliseMedicines(medicines, source) {
  return (medicines || []).map((medicine) => ({
    name: medicine.name || "Unknown medicine",
    dose: medicine.dose || "As directed",
    frequency: medicine.frequency || "As directed",
    source,
    selected: medicine.selected !== false,
  }));
}

function renderMedicines() {
  if (!STATE.medicines.length) {
    elements.medicineList.innerHTML = '<div class="empty-block">Your selected medicines will appear here.</div>';
    updateFindButton();
    return;
  }

  elements.medicineList.innerHTML = STATE.medicines
    .map((medicine, index) => {
      const selectedClass = medicine.selected ? "selected" : "";
      return `
        <button type="button" class="medicine-item ${selectedClass}" data-medicine-index="${index}">
          <span class="medicine-toggle">${medicine.selected ? "✓" : ""}</span>
          <span>
            <strong>${escapeHtml(medicine.name)}</strong>
            <span class="medicine-meta">${escapeHtml(medicine.dose)} | ${escapeHtml(medicine.frequency)}</span>
          </span>
          <span class="medicine-origin">${escapeHtml(medicine.source)}</span>
        </button>
      `;
    })
    .join("");

  updateFindButton();
}

function updateFindButton() {
  const hasSelection = STATE.medicines.some((medicine) => medicine.selected);
  elements.findBtn.disabled = !hasSelection;
}

async function runPharmacyFinder() {
  const selectedMedicines = STATE.medicines.filter((medicine) => medicine.selected).map((medicine) => medicine.name);
  if (!selectedMedicines.length) {
    setStatus("error", "Select at least one medicine before searching.");
    return;
  }

  const lat = Number(elements.latInput.value);
  const lng = Number(elements.lngInput.value);

  setStatus("loading", "Ranking nearby pharmacies for the current medicine list...");

  try {
    const response = await fetch("/api/rank", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        medicines: selectedMedicines,
        lat: Number.isFinite(lat) ? lat : undefined,
        lng: Number.isFinite(lng) ? lng : undefined,
      }),
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Could not rank pharmacies.");
    }

    STATE.results = data.pharmacies || [];
    renderResults();

    if (!STATE.results.length) {
      setStatus("error", "No pharmacies were returned for this search.");
      return;
    }

    setStatus("success", `Ranked ${STATE.results.length} pharmacies for ${selectedMedicines.length} selected medicine${selectedMedicines.length > 1 ? "s" : ""}.`);
  } catch (error) {
    setStatus("error", error.message);
  }
}

function renderResults() {
  if (!STATE.results.length) {
    elements.resultsList.innerHTML = '<div class="empty-block">No pharmacy results yet.</div>';
    return;
  }

  elements.resultsList.innerHTML = STATE.results
    .map((pharmacy, index) => {
      const medicineMatches = (pharmacy.medicines || [])
        .map(
          (medicine) => `
            <span class="stock-chip ${escapeHtml(medicine.stock_label)}">
              ${escapeHtml(medicine.medicine)}: ${escapeHtml(medicine.stock_label)}
            </span>
          `
        )
        .join("");

      return `
        <article class="result-card">
          <div class="result-top">
            <div>
              <h4>${index + 1}. ${escapeHtml(pharmacy.name)}</h4>
              <p class="result-address">${escapeHtml(pharmacy.address || "Address not available")}</p>
              <p class="result-note">${escapeHtml(pharmacy.phone || "No phone listed")} | ${pharmacy.is_24h ? "24h" : "Limited hours"}</p>
            </div>
            <div class="result-score">
              <strong>${escapeHtml(String(pharmacy.score))}%</strong>
              <span>match</span>
            </div>
          </div>
          <div class="result-metrics">
            <span class="metric-chip">${escapeHtml(String(pharmacy.distance_km))} km away</span>
            <span class="metric-chip">${escapeHtml(String(pharmacy.coverage_pct))}% medicine coverage</span>
            <span class="metric-chip">Reliability ${escapeHtml(String(pharmacy.factor_scores?.reliability ?? "-"))}%</span>
            <span class="metric-chip">${escapeHtml(String(pharmacy.factor_scores?.hours ?? "Hours unavailable"))}</span>
          </div>
          <div class="result-match-list">${medicineMatches}</div>
        </article>
      `;
    })
    .join("");
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    setStatus("error", "Geolocation is not available in this browser.");
    return;
  }

  setStatus("loading", "Trying to get your current location...");

  navigator.geolocation.getCurrentPosition(
    (position) => {
      elements.latInput.value = position.coords.latitude.toFixed(6);
      elements.lngInput.value = position.coords.longitude.toFixed(6);
      setStatus("success", "Current location added to the search.");
    },
    () => {
      setStatus("error", "Could not access your current location. The default coordinates are still available.");
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );
}

function setStatus(type, message) {
  elements.statusBanner.className = `status-banner ${type}`;
  elements.statusBanner.textContent = message;
}

function scrollToSection(id) {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }

  element.scrollIntoView({ behavior: "smooth", block: "start" });
  setActiveNavLink(id);
}

function updateActiveNav() {
  const marker = window.scrollY + window.innerHeight * 0.25;
  let activeId = "overview";

  sections.forEach((section) => {
    if (!section.element) {
      return;
    }

    const top = section.element.offsetTop;
    if (marker >= top) {
      activeId = section.id;
    }
  });

  setActiveNavLink(activeId);
}

function setActiveNavLink(activeId) {
  elements.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.target === activeId);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

init();
