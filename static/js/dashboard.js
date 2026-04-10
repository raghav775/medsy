"use strict";

// ---------------------------------------------------------------------------
// Dashboard bootstrap — runs after app.js
// ---------------------------------------------------------------------------
(function initDashboard() {
  // Auth gate: redirect to login if no session
  const user = readStoredUser();
  if (!user) {
    window.location.href = "/login";
    return;
  }

  // Populate sidebar user card
  const nameEl   = document.getElementById("dash-user-name");
  const emailEl  = document.getElementById("dash-user-email");
  const avatarEl = document.getElementById("dash-avatar");
  if (nameEl)   nameEl.textContent  = user.name;
  if (emailEl)  emailEl.textContent = user.email;
  if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();

  // Sidebar nav tab switching
  const tabs = Array.from(document.querySelectorAll(".dash-tab"));
  tabs.forEach((tab) =>
    tab.addEventListener("click", () => _switchDashTab(tab.dataset.tab))
  );

  // Expose globally so inline onclick in templates can call it
  window._switchDashTab = _switchDashTab;

  // Logout
  const logoutBtn = document.getElementById("dash-logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("medsy_user_session");
      window.location.href = "/login";
    });
  }

  // Map close button wired in this page's DOM
  const mapCloseBtn = document.getElementById("map-close-btn");
  if (mapCloseBtn) mapCloseBtn.addEventListener("click", closePharmacyMap);
  const mapOverlay = document.getElementById("map-overlay");
  if (mapOverlay) mapOverlay.addEventListener("click", (e) => { if (e.target === mapOverlay) closePharmacyMap(); });

  // Seed demo data on first visit so the dashboard isn't empty
  _ensureDemoData(user);

  // Initialize sections
  _loadOverview(user);
  _loadHistoryPane();
  _loadRecordsPane(user);

  // Finder is wired by app.js's initFinderPage() which runs on DOMContentLoaded
  // (it finds the same element IDs that are inside #pane-finder)
})();

// ---------------------------------------------------------------------------
// Demo data seed — runs once per user if they have no history yet
// ---------------------------------------------------------------------------
function _ensureDemoData(user) {
  const histKey  = "medsy_history_" + user.email;
  const recKey   = "medsy_records_" + user.email;
  const demoFlag = "medsy_demo_seeded_" + user.email;

  if (localStorage.getItem(demoFlag)) return; // already seeded
  if (localStorage.getItem(histKey))  return; // user has real data

  const now = Date.now();
  const daysAgo = (d) => new Date(now - d * 86400000).toISOString();

  const demoHistory = [
    {
      id: "demo_hist_1",
      timestamp: daysAgo(2),
      medicines: ["Paracetamol", "Amoxicillin 500 mg", "Vitamin D3"],
      address: "Lajpat Nagar, New Delhi",
      topResults: [
        { name: "Apollo Pharmacy, Lajpat Nagar", score: 91, coverage_pct: 100 },
        { name: "MedPlus, Defence Colony", score: 84, coverage_pct: 67 },
      ],
    },
    {
      id: "demo_hist_2",
      timestamp: daysAgo(8),
      medicines: ["Metformin 500 mg", "Atorvastatin 10 mg", "Ramipril"],
      address: "Saket, New Delhi",
      topResults: [
        { name: "Wellness Forever, Saket", score: 88, coverage_pct: 100 },
        { name: "PharmEasy, Malviya Nagar", score: 79, coverage_pct: 67 },
      ],
    },
    {
      id: "demo_hist_3",
      timestamp: daysAgo(15),
      medicines: ["Ibuprofen", "Omeprazole", "Cetirizine"],
      address: "Gurugram",
      topResults: [
        { name: "Guardian Pharmacy, Sector 14", score: 82, coverage_pct: 100 },
      ],
    },
    {
      id: "demo_hist_4",
      timestamp: daysAgo(22),
      medicines: ["Azithromycin 500 mg", "Prednisolone"],
      address: "Noida",
      topResults: [
        { name: "Apollo Pharmacy, Sector 18 Noida", score: 95, coverage_pct: 100 },
      ],
    },
  ];

  const demoRecords = [
    {
      id: "demo_rec_1",
      name: "Dr. Mehta Prescription – Apr 2025.pdf",
      mimeType: "application/pdf",
      size: 238452,
      category: "prescription",
      date: daysAgo(3),
      data: null,
    },
    {
      id: "demo_rec_2",
      name: "CBC Blood Test Report – Mar 2025.pdf",
      mimeType: "application/pdf",
      size: 512890,
      category: "lab_report",
      date: daysAgo(18),
      data: null,
    },
    {
      id: "demo_rec_3",
      name: "Discharge Summary – Feb 2025.pdf",
      mimeType: "application/pdf",
      size: 341120,
      category: "discharge",
      date: daysAgo(47),
      data: null,
    },
  ];

  try {
    localStorage.setItem(histKey, JSON.stringify(demoHistory));
    localStorage.setItem(recKey,  JSON.stringify(demoRecords));
    localStorage.setItem(demoFlag, "1");
  } catch { /* localStorage unavailable */ }
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function _switchDashTab(tabName) {
  document.querySelectorAll(".dash-tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === tabName)
  );
  document.querySelectorAll(".dash-pane").forEach((p) =>
    p.classList.toggle("active", p.id === `pane-${tabName}`)
  );
  // Refresh data when switching to live panes
  if (tabName === "history") _loadHistoryPane();
  if (tabName === "records") {
    const user = readStoredUser();
    if (user) _loadRecordsPane(user);
  }
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
function _loadOverview(user) {
  const greeting = document.getElementById("overview-greeting");
  if (greeting) {
    const hour = new Date().getHours();
    const tod  = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    greeting.textContent = `${tod}, ${user.name.split(" ")[0]}`;
  }

  const history  = loadSearchHistory();
  const records  = _loadRecords(user.email);
  const allMeds  = new Set(history.flatMap((h) => h.medicines));

  const statSearches = document.getElementById("stat-searches");
  const statMeds     = document.getElementById("stat-meds");
  const statRecords  = document.getElementById("stat-records");
  if (statSearches) statSearches.textContent = history.length;
  if (statMeds)     statMeds.textContent     = allMeds.size;
  if (statRecords)  statRecords.textContent  = records.length;

  const recentList = document.getElementById("overview-recent-list");
  if (recentList) {
    const recent = history.slice(0, 3);
    recentList.innerHTML = recent.length
      ? recent.map((entry) => _renderHistoryItem(entry, true)).join("")
      : '<div class="empty-block">No searches yet. Use the Pharmacy Finder tab to get started.</div>';
    _bindHistoryActions(recentList);
  }
}

// ---------------------------------------------------------------------------
// Medicine History pane
// ---------------------------------------------------------------------------
function _loadHistoryPane() {
  const list    = document.getElementById("history-list");
  if (!list) return;
  const history = loadSearchHistory();
  if (!history.length) {
    list.innerHTML = '<div class="empty-block">No history yet. Run a pharmacy search to see it here.</div>';
    return;
  }
  list.innerHTML = history.map((entry) => _renderHistoryItem(entry, false)).join("");
  _bindHistoryActions(list);
}

function _renderHistoryItem(entry, compact) {
  const dt      = new Date(entry.timestamp);
  const day     = dt.getDate();
  const mon     = dt.toLocaleString("en-IN", { month: "short" });
  const time    = dt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  const chips   = entry.medicines
    .map((m) => `<span class="history-med-chip">${_escDash(m)}</span>`)
    .join("");
  const top     = entry.topResults?.[0];
  const bestStr = top ? `<p class="history-best">Best match: <strong>${_escDash(top.name)}</strong> — ${top.score}%</p>` : "";
  const addr    = entry.address ? `<p class="helper-text" style="margin:0 0 6px;">📍 ${_escDash(entry.address)}</p>` : "";

  return `
    <div class="history-item" data-history-id="${_escDash(entry.id)}">
      <div class="history-time">
        <span class="history-date-day">${day}</span>
        <span class="history-date-mon">${mon}</span>
        <span class="history-date-time">${time}</span>
      </div>
      <div class="history-body">
        <h4>${entry.medicines.length} medicine${entry.medicines.length !== 1 ? "s" : ""} searched</h4>
        ${addr}
        <div class="history-meds">${chips}</div>
        ${bestStr}
        ${!compact ? `<div class="history-actions">
          <button class="secondary-button" style="padding:7px 16px;font-size:0.82rem;"
                  data-action="use-again" data-medicines="${_escAttr(JSON.stringify(entry.medicines))}" data-address="${_escAttr(entry.address || '')}">
            Use again
          </button>
          <button class="text-btn" style="color:#b91c1c;"
                  data-action="delete-history" data-id="${_escDash(entry.id)}">
            Delete
          </button>
        </div>` : ""}
      </div>
    </div>`;
}

function _bindHistoryActions(container) {
  container.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    if (btn.dataset.action === "use-again") {
      const medicines = JSON.parse(btn.dataset.medicines || "[]");
      const address   = btn.dataset.address || "";
      _prefillFinder(medicines, address);
      _switchDashTab("finder");
    }

    if (btn.dataset.action === "delete-history") {
      _deleteHistoryEntry(btn.dataset.id);
      _loadHistoryPane();
      _loadOverview(readStoredUser());
    }
  });
}

function _deleteHistoryEntry(id) {
  const key     = "medsy_history_" + (readStoredUser()?.email ?? "guest");
  const history = loadSearchHistory().filter((e) => e.id !== id);
  localStorage.setItem(key, JSON.stringify(history));
}

function _prefillFinder(medicines, address) {
  // Switch mode to manual and pre-fill
  const manualInput  = document.getElementById("manual-input");
  const addressInput = document.getElementById("address-input");
  const useManualBtn = document.getElementById("use-manual-btn");
  const modeBtn      = document.querySelector('.mode-btn[data-mode="manual"]');

  if (modeBtn) modeBtn.click();
  if (manualInput)  manualInput.value  = medicines.join("\n");
  if (addressInput && address) addressInput.value = address;
  if (useManualBtn) useManualBtn.click();
}

// ---------------------------------------------------------------------------
// Records Library pane
// ---------------------------------------------------------------------------
const RECORDS_PREFIX = "medsy_records_";
const MAX_RECORD_BYTES = 1.5 * 1024 * 1024; // 1.5 MB

function _recordsKey(email) {
  return RECORDS_PREFIX + email;
}

function _loadRecords(email) {
  try {
    const raw = localStorage.getItem(_recordsKey(email));
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function _saveRecords(email, records) {
  localStorage.setItem(_recordsKey(email), JSON.stringify(records));
}

function _loadRecordsPane(user) {
  const dropZone   = document.getElementById("records-drop-zone");
  const fileInput  = document.getElementById("records-file-input");
  const grid       = document.getElementById("records-grid");
  const countEl    = document.getElementById("records-count");

  if (!dropZone || !grid) return;

  // Click to open file picker
  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("select") || e.target.closest("label")) return;
    fileInput?.click();
  });

  // Drag & drop
  ["dragenter", "dragover"].forEach((ev) =>
    dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove("drag-over"); })
  );
  dropZone.addEventListener("drop", (e) => {
    const files = Array.from(e.dataTransfer?.files ?? []);
    files.forEach((f) => _processRecordFile(f, user));
  });

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      Array.from(e.target.files ?? []).forEach((f) => _processRecordFile(f, user));
      fileInput.value = "";
    });
  }

  _renderRecordsGrid(user);
}

function _processRecordFile(file, user) {
  const categoryEl = document.getElementById("records-category");
  const category   = categoryEl?.value || "other";

  if (file.size > MAX_RECORD_BYTES) {
    alert(`"${file.name}" is too large (max 1.5 MB). Please reduce file size first.`);
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    const records = _loadRecords(user.email);
    records.unshift({
      id:        Date.now().toString(36) + Math.random().toString(36).slice(2),
      name:      file.name,
      mimeType:  file.type,
      size:      file.size,
      category,
      date:      new Date().toISOString(),
      data:      e.target.result, // base64 data URL
    });
    _saveRecords(user.email, records);
    _renderRecordsGrid(user);

    // Refresh overview stat
    const statRecordsEl = document.getElementById("stat-records");
    if (statRecordsEl) statRecordsEl.textContent = records.length;
  };
  reader.readAsDataURL(file);
}

function _renderRecordsGrid(user) {
  const grid    = document.getElementById("records-grid");
  const countEl = document.getElementById("records-count");
  if (!grid) return;

  const records = _loadRecords(user.email);
  if (countEl) countEl.textContent = `${records.length} file${records.length !== 1 ? "s" : ""}`;

  if (!records.length) {
    grid.innerHTML = '<div class="empty-block" style="grid-column:1/-1">No records uploaded yet.</div>';
    return;
  }

  grid.innerHTML = records.map((rec) => {
    const isImage = rec.mimeType?.startsWith("image/");
    const preview = isImage
      ? `<img src="${_escAttr(rec.data)}" alt="${_escAttr(rec.name)}">`
      : `<div class="record-preview-icon">${_fileIcon(rec.mimeType, rec.name)}</div>`;

    const dateStr  = new Date(rec.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
    const sizeStr  = rec.size >= 1024 * 1024
      ? (rec.size / (1024 * 1024)).toFixed(1) + " MB"
      : Math.round(rec.size / 1024) + " KB";

    const catLabel = { prescription: "Prescription", lab_report: "Lab Report", scan: "Scan / X-Ray", discharge: "Discharge", other: "Other" }[rec.category] || "Other";

    return `
      <div class="record-card" data-record-id="${_escAttr(rec.id)}">
        <div class="record-preview">${preview}</div>
        <div class="record-body">
          <div class="record-name" title="${_escAttr(rec.name)}">${_escDash(rec.name)}</div>
          <div class="record-meta">${dateStr} · ${sizeStr}</div>
          <span class="record-category ${_escAttr(rec.category)}">${catLabel}</span>
        </div>
        <div class="record-actions">
          ${rec.data ? `<a class="secondary-button" style="padding:6px 12px;font-size:0.8rem;text-decoration:none;"
               href="${_escAttr(rec.data)}" download="${_escAttr(rec.name)}">Download</a>` : ""}
          ${(isImage && rec.data) ? `<button class="secondary-button" style="padding:6px 12px;font-size:0.8rem;"
               data-action="preview-record" data-src="${_escAttr(rec.data)}" data-name="${_escAttr(rec.name)}">
               View</button>` : ""}
          ${!rec.data ? `<span class="helper-text" style="font-size:0.75rem;">Demo record</span>` : ""}
          <button class="text-btn" style="color:#b91c1c;margin-left:auto;font-size:0.8rem;"
                  data-action="delete-record" data-id="${_escAttr(rec.id)}">Delete</button>
        </div>
      </div>`;
  }).join("");

  // Bind actions
  grid.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    if (btn.dataset.action === "delete-record") {
      if (!confirm("Delete this record? This cannot be undone.")) return;
      const updated = _loadRecords(user.email).filter((r) => r.id !== btn.dataset.id);
      _saveRecords(user.email, updated);
      _renderRecordsGrid(user);
      const statRecordsEl = document.getElementById("stat-records");
      if (statRecordsEl) statRecordsEl.textContent = updated.length;
    }

    if (btn.dataset.action === "preview-record") {
      _openImagePreview(btn.dataset.src, btn.dataset.name);
    }
  }, { once: true }); // rebind happens on re-render; use once to avoid stacking
}

// Re-bind properly (not once) — remove old listener by replacing node
function _rebindRecordsGrid(user) {
  const old  = document.getElementById("records-grid");
  if (!old) return;
  const fresh = old.cloneNode(true);
  old.parentNode.replaceChild(fresh, old);
  // After replaceChild the grid has no listeners; re-render adds them
  _renderRecordsGrid(user);
}

function _openImagePreview(src, name) {
  const existing = document.getElementById("img-preview-overlay");
  if (existing) existing.remove();
  const overlay = document.createElement("div");
  overlay.id = "img-preview-overlay";
  overlay.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;cursor:zoom-out;";
  overlay.innerHTML = `<img src="${_escAttr(src)}" alt="${_escAttr(name)}"
    style="max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">`;
  overlay.addEventListener("click", () => overlay.remove());
  document.body.appendChild(overlay);
}

function _fileIcon(mimeType, name) {
  if (!mimeType && name) {
    const ext = name.split(".").pop().toLowerCase();
    if (["jpg", "jpeg", "png", "gif", "webp"].includes(ext)) return "🖼️";
    if (ext === "pdf") return "📄";
    if (["doc", "docx"].includes(ext)) return "📝";
    if (ext === "txt") return "📃";
  }
  if (!mimeType) return "📎";
  if (mimeType.startsWith("image/"))    return "🖼️";
  if (mimeType === "application/pdf")   return "📄";
  if (mimeType.includes("word"))        return "📝";
  return "📎";
}

// ---------------------------------------------------------------------------
// Escape helpers (dashboard-local, simpler naming)
// ---------------------------------------------------------------------------
function _escDash(val) {
  return String(val ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function _escAttr(val) {
  return String(val ?? "")
    .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
