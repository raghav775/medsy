"use strict";

const AUTH_STORAGE_KEY = "medsy_user_session";

const STATE = {
  searchMode: "upload",
  medicines: [],
  results: [],
};

function init() {
  hydrateHeaderAuth();
  initAuthPage();
  initFinderPage();
}

function hydrateHeaderAuth() {
  const pill = document.getElementById("auth-pill");
  if (!pill) {
    return;
  }

  const user = readStoredUser();
  pill.textContent = user ? `Logged in: ${user.name}` : "Guest mode";
}

function initAuthPage() {
  const form = document.getElementById("auth-form");
  if (!form) {
    return;
  }

  const authMode = form.dataset.authMode === "register" ? "register" : "login";
  const nameField = document.querySelector(".auth-name-field");
  const nameInput = document.getElementById("auth-name");
  const emailInput = document.getElementById("auth-email");
  const passwordInput = document.getElementById("auth-password");
  const feedback = document.getElementById("auth-feedback");
  const stateCopy = document.getElementById("auth-state-copy");
  const logoutBtn = document.getElementById("logout-btn");

  if (nameField) {
    nameField.classList.toggle("hidden", authMode !== "register");
  }

  syncAuthState(stateCopy, logoutBtn);

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const email = emailInput ? emailInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value.trim() : "";
    const fullName = nameInput ? nameInput.value.trim() : "";

    if (!email || !password) {
      if (feedback) {
        feedback.textContent = "Enter email and password to continue.";
      }
      return;
    }

    if (authMode === "register" && !fullName) {
      if (feedback) {
        feedback.textContent = "Enter a full name before registering.";
      }
      return;
    }

    const existing = readStoredUser();
    const user = {
      name: authMode === "register" ? fullName : existing && existing.email === email ? existing.name : email.split("@")[0],
      email,
    };

    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    hydrateHeaderAuth();
    syncAuthState(stateCopy, logoutBtn);

    if (feedback) {
      feedback.textContent = authMode === "register"
        ? `Registered locally as ${user.name}.`
        : `Logged in locally as ${user.name}.`;
    }

    if (passwordInput) {
      passwordInput.value = "";
    }
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      hydrateHeaderAuth();
      syncAuthState(stateCopy, logoutBtn);
      if (feedback) {
        feedback.textContent = "Logged out. You are back in guest mode.";
      }
    });
  }
}

function syncAuthState(stateCopy, logoutBtn) {
  const user = readStoredUser();

  if (stateCopy) {
    stateCopy.textContent = user
      ? `${user.name} is signed in locally with ${user.email}.`
      : "You are browsing in guest mode.";
  }

  if (logoutBtn) {
    logoutBtn.classList.toggle("hidden", !user);
  }
}

function initFinderPage() {
  const modeButtons = Array.from(document.querySelectorAll(".mode-btn"));
  const uploadPanel = document.getElementById("upload-panel");
  const manualPanel = document.getElementById("manual-panel");
  const fileInput = document.getElementById("rx-file");
  const dropZone = document.getElementById("rx-drop-zone");
  const uploadHelper = document.getElementById("upload-helper");
  const manualInput = document.getElementById("manual-input");
  const addressInput = document.getElementById("address-input");
  const useManualBtn = document.getElementById("use-manual-btn");
  const clearManualBtn = document.getElementById("clear-manual-btn");
  const statusBanner = document.getElementById("status-banner");
  const medicineList = document.getElementById("medicine-list");
  const resultsList = document.getElementById("results-list");
  const selectAllBtn = document.getElementById("select-all-btn");
  const clearSelectionBtn = document.getElementById("clear-selection-btn");
  const findBtn = document.getElementById("find-btn");

  if (!statusBanner || !medicineList || !resultsList || !findBtn) {
    return;
  }

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setSearchMode(button.dataset.mode, modeButtons, uploadPanel, manualPanel);
    });
  });

  if (fileInput) {
    fileInput.addEventListener("change", async (event) => {
      const file = event.target.files ? event.target.files[0] : null;
      if (file) {
        await uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn);
      }
    });
  }

  if (dropZone) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
      });
    });

    dropZone.addEventListener("drop", async (event) => {
      const file = event.dataTransfer && event.dataTransfer.files ? event.dataTransfer.files[0] : null;
      if (file) {
        await uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn);
      }
    });
  }

  if (useManualBtn && manualInput) {
    useManualBtn.addEventListener("click", async () => {
      await parseManualMedicines(manualInput.value, statusBanner, medicineList, resultsList, findBtn);
    });
  }

  if (clearManualBtn && manualInput) {
    clearManualBtn.addEventListener("click", () => {
      manualInput.value = "";
      setStatus(statusBanner, "info", "Manual text cleared.");
    });
  }

  const manualAutoInput = document.getElementById("manual-auto-input");
  const addMedicineBtn = document.getElementById("add-medicine-btn");
  if (addMedicineBtn && manualAutoInput && manualInput) {
    addMedicineBtn.addEventListener("click", () => {
      const val = manualAutoInput.value.trim();
      if (val) {
        manualInput.value = manualInput.value ? manualInput.value + "\\n" + val : val;
        manualAutoInput.value = "";
        setStatus(statusBanner, "success", `Added ${val} to manual list. Press 'Search typed list' when ready.`);
      }
    });

    manualAutoInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addMedicineBtn.click();
      }
    });
  }

  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      STATE.medicines = STATE.medicines.map((medicine) => ({ ...medicine, selected: true }));
      renderMedicines(medicineList, findBtn);
    });
  }

  if (clearSelectionBtn) {
    clearSelectionBtn.addEventListener("click", () => {
      STATE.medicines = [];
      STATE.results = [];
      renderMedicines(medicineList, findBtn);
      renderResults(resultsList);
      setStatus(statusBanner, "info", "Medicine list cleared.");
    });
  }

  medicineList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-medicine-index]");
    if (!button) {
      return;
    }

    const index = Number(button.dataset.medicineIndex);
    if (Number.isNaN(index) || !STATE.medicines[index]) {
      return;
    }

    STATE.medicines[index].selected = !STATE.medicines[index].selected;
    renderMedicines(medicineList, findBtn);
  });

  findBtn.addEventListener("click", async () => {
    await runFinder(addressInput, statusBanner, resultsList);
  });

  renderMedicines(medicineList, findBtn);
  renderResults(resultsList);
  hydrateFinderFromQuery(modeButtons, uploadPanel, manualPanel, manualInput, addressInput, statusBanner, medicineList, resultsList, findBtn);
}

function hydrateFinderFromQuery(modeButtons, uploadPanel, manualPanel, manualInput, addressInput, statusBanner, medicineList, resultsList, findBtn) {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  const text = params.get("text");
  const address = params.get("address");

  if (mode) {
    setSearchMode(mode, modeButtons, uploadPanel, manualPanel);
  }

  if (address && addressInput) {
    addressInput.value = address;
  }

  if (text && manualInput) {
    manualInput.value = text;
    parseManualMedicines(text, statusBanner, medicineList, resultsList, findBtn);
  }
}

function setSearchMode(mode, modeButtons, uploadPanel, manualPanel) {
  STATE.searchMode = mode === "manual" ? "manual" : "upload";

  modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === STATE.searchMode);
  });

  if (uploadPanel) {
    uploadPanel.classList.toggle("active", STATE.searchMode === "upload");
  }

  if (manualPanel) {
    manualPanel.classList.toggle("active", STATE.searchMode === "manual");
  }
}

async function uploadPrescription(file, uploadHelper, statusBanner, medicineList, resultsList, findBtn) {
  const formData = new FormData();
  formData.append("file", file);

  if (uploadHelper) {
    uploadHelper.textContent = `Selected file: ${file.name}`;
  }

  setStatus(statusBanner, "loading", "Reading the uploaded prescription and extracting medicines...");

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
    renderMedicines(medicineList, findBtn);
    renderResults(resultsList);
    setStatus(statusBanner, "success", `Found ${medicines.length} medicine${medicines.length > 1 ? "s" : ""} from ${file.name}.`);
  } catch (error) {
    setStatus(statusBanner, "error", error.message);
  }
}

async function parseManualMedicines(text, statusBanner, medicineList, resultsList, findBtn) {
  const cleanedText = text.trim();
  if (!cleanedText) {
    setStatus(statusBanner, "error", "Type at least one medicine before running manual search.");
    return;
  }

  setStatus(statusBanner, "loading", "Parsing the medicines you typed...");

  try {
    const response = await fetch("/api/medicines", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: cleanedText }),
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
    renderMedicines(medicineList, findBtn);
    renderResults(resultsList);
    setStatus(statusBanner, "success", `Loaded ${medicines.length} medicine${medicines.length > 1 ? "s" : ""} from typed text.`);
  } catch (error) {
    setStatus(statusBanner, "error", error.message);
  }
}

async function runFinder(addressInput, statusBanner, resultsList) {
  const selectedMedicines = STATE.medicines.filter((medicine) => medicine.selected).map((medicine) => medicine.name);
  if (!selectedMedicines.length) {
    setStatus(statusBanner, "error", "Select at least one medicine before searching.");
    return;
  }

  const address = addressInput ? addressInput.value.trim() : "";
  setStatus(statusBanner, "loading", "Ranking nearby pharmacies for the current medicine list...");

  try {
    const response = await fetch("/api/rank", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        medicines: selectedMedicines,
        address,
      }),
    });
    const data = await response.json();

    if (!response.ok || data.error) {
      throw new Error(data.error || "Could not rank pharmacies.");
    }

    STATE.results = data.pharmacies || [];
    renderResults(resultsList);

    if (!STATE.results.length) {
      setStatus(statusBanner, "error", "No pharmacies were returned for this search.");
      return;
    }

    const locationLabel = data.location && data.location.resolved_label ? data.location.resolved_label : "your area";
    const locationNote = data.location && data.location.used_default && address
      ? ` Address not matched exactly, so the Delhi sample area was used.`
      : "";

    setStatus(
      statusBanner,
      "success",
      `Showing ${STATE.results.length} pharmacies near ${locationLabel}.${locationNote}`
    );
  } catch (error) {
    setStatus(statusBanner, "error", error.message);
  }
}

function renderMedicines(medicineList, findBtn) {
  if (!medicineList || !findBtn) {
    return;
  }

  if (!STATE.medicines.length) {
    medicineList.innerHTML = '<div class="empty-block">Your selected medicines will appear here.</div>';
    findBtn.disabled = true;
    return;
  }

  medicineList.innerHTML = STATE.medicines.map((medicine, index) => {
    const selectedClass = medicine.selected ? "selected" : "";
    return `
      <button type="button" class="medicine-item ${selectedClass}" data-medicine-index="${index}">
        <span class="medicine-toggle">${medicine.selected ? "&#10003;" : ""}</span>
        <span>
          <strong>${escapeHtml(medicine.name)}</strong>
          <span class="medicine-meta">${escapeHtml(medicine.dose)} | ${escapeHtml(medicine.frequency)}</span>
        </span>
        <span class="medicine-origin">${escapeHtml(medicine.source)}</span>
      </button>
    `;
  }).join("");

  findBtn.disabled = !STATE.medicines.some((medicine) => medicine.selected);
}

function renderResults(resultsList) {
  if (!resultsList) {
    return;
  }

  if (!STATE.results.length) {
    resultsList.innerHTML = '<div class="empty-block">No pharmacy results yet.</div>';
    return;
  }

  resultsList.innerHTML = STATE.results.map((pharmacy, index) => {
    const reliability = pharmacy.factor_scores && pharmacy.factor_scores.reliability
      ? `${pharmacy.factor_scores.reliability}%`
      : "N/A";
    const hours = pharmacy.factor_scores && pharmacy.factor_scores.hours
      ? pharmacy.factor_scores.hours
      : "Hours unavailable";
    const medicineMatches = (pharmacy.medicines || []).map((medicine) => {
      return `
        <span class="stock-chip ${escapeHtml(medicine.stock_label)}">
          ${escapeHtml(medicine.medicine)}: ${escapeHtml(medicine.stock_label)}
        </span>
      `;
    }).join("");

    return `
      <article class="result-card">
        <div class="result-top">
          <div>
            <h3>${index + 1}. ${escapeHtml(pharmacy.name)}</h3>
            <p class="result-address">${escapeHtml(pharmacy.address || "Address not available")}</p>
            <p class="result-note">📞 ${escapeHtml(pharmacy.phone || "No phone listed")} | 🕒 ${escapeHtml(hours)}</p>
          </div>
          <div class="result-score">
            <strong>${escapeHtml(String(pharmacy.score))}%</strong>
            <span>match</span>
          </div>
        </div>
        <div class="result-metrics">
          <span class="metric-chip">${escapeHtml(String(pharmacy.distance_km))} km away</span>
          <span class="metric-chip">${escapeHtml(String(pharmacy.coverage_pct))}% medicine coverage</span>
          <span class="metric-chip">Reliability ${escapeHtml(reliability)}</span>
          <span class="metric-chip">${escapeHtml(hours)}</span>
        </div>
        <div class="result-match-list">${medicineMatches}</div>
      </article>
    `;
  }).join("");
}

function setStatus(statusBanner, type, message) {
  statusBanner.className = `status-banner ${type}`;
  statusBanner.textContent = message;
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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

init();
