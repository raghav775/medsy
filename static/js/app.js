/* ── Medsy frontend ──────────────────────────────────────────────────────────
   Handles:
   - Navigation between pages
   - Medical vault (localStorage)
   - Prescription OCR upload → Flask /api/ocr
   - Probability engine → Flask /api/rank
   - Auto-jump to Navigate page with Leaflet + OSRM routing
────────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── State ──────────────────────────────────────────────────────────────────────
const STATE = {
  medicines: [],          // [{name, dose, frequency, selected}]
  pharmacies: [],         // ranked results from /api/rank
  selectedPharmIdx: null, // index into pharmacies
  userLat: 28.5733,
  userLng: 77.2236,
  map: null,
  routeControl: null,
  pharmMarkers: [],
  userMarker: null,
};

// ── Vault seed data ─────────────────────────────────────────────────────────
const VAULT_SEED = [
  { id: 1, type: "scan",         badge: "b-scan",   label: "MRI scan",     name: "Brain MRI — Oct 2024",          meta: "Apollo Hospital · 12 Oct 2024 · 18 MB" },
  { id: 2, type: "report",       badge: "b-report",  label: "Lab report",   name: "CBC Blood Panel",               meta: "Dr. Lal PathLabs · 8 Oct 2024 · 2.1 MB" },
  { id: 3, type: "prescription", badge: "b-rx",      label: "Prescription", name: "Prescription #6 — Neurology",   meta: "Dr. S. Arora · 5 Oct 2024 · 0.4 MB" },
  { id: 4, type: "scan",         badge: "b-scan",   label: "X-ray",        name: "Chest X-Ray — Aug 2024",        meta: "Max Hospital · 2 Aug 2024 · 5.6 MB" },
  { id: 5, type: "report",       badge: "b-report",  label: "Lab report",   name: "Thyroid panel T3/T4",           meta: "SRL Diagnostics · 1 Aug 2024 · 1.8 MB" },
  { id: 6, type: "prescription", badge: "b-rx",      label: "Prescription", name: "Prescription #5 — Cardiology",  meta: "Dr. P. Nair · 20 Jul 2024 · 0.3 MB" },
  { id: 7, type: "scan",         badge: "b-scan",   label: "ECG",          name: "ECG Report — Jul 2024",         meta: "Fortis Escorts · 18 Jul 2024 · 0.6 MB" },
  { id: 8, type: "report",       badge: "b-report",  label: "Lab report",   name: "Lipid profile & HbA1c",         meta: "Dr. Lal PathLabs · 10 Jun 2024 · 1.4 MB" },
  { id: 9, type: "prescription", badge: "b-rx",      label: "Prescription", name: "Prescription #4 — Ortho",       meta: "Dr. K. Sharma · 1 Jun 2024 · 0.3 MB" },
];

function loadVault() {
  const stored = localStorage.getItem('medsy_vault');
  return stored ? JSON.parse(stored) : [...VAULT_SEED];
}
function saveVault(records) {
  localStorage.setItem('medsy_vault', JSON.stringify(records));
}

// ── Navigation ──────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => goTo(item.dataset.page));
});

function goTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  const navEl = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (navEl) navEl.classList.add('active');

  if (pageId === 'navigate') initMap();
  if (pageId === 'vault') renderVault();
}

// ── Vault ───────────────────────────────────────────────────────────────────
let vaultFilter = 'all';

document.querySelectorAll('.vtab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.vtab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    vaultFilter = tab.dataset.vtype;
    renderVault();
  });
});

function renderVault() {
  const records = loadVault();
  const filtered = vaultFilter === 'all' ? records : records.filter(r => r.type === vaultFilter);
  const grid = document.getElementById('records-grid');
  if (!filtered.length) {
    grid.innerHTML = '<div class="empty-state">No records found.</div>';
    return;
  }
  grid.innerHTML = filtered.map(r => `
    <div class="rec-card">
      <span class="badge ${r.badge}">${r.label}</span>
      <div class="rec-name">${r.name}</div>
      <div class="rec-meta">${r.meta}</div>
    </div>
  `).join('');
}

function handleVaultUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  addToVault(file);
}

function handleVaultDrop(event) {
  event.preventDefault();
  document.getElementById('vault-drop').classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file) addToVault(file);
}

function addToVault(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  const typeMap = {
    pdf: 'report', png: 'scan', jpg: 'scan', jpeg: 'scan',
    docx: 'prescription', doc: 'prescription', txt: 'report'
  };
  const badgeMap = {
    report: 'b-report', scan: 'b-scan', prescription: 'b-rx'
  };
  const labelMap = {
    report: 'Document', scan: 'Scan', prescription: 'Prescription'
  };
  const type = typeMap[ext] || 'report';
  const records = loadVault();
  records.unshift({
    id: Date.now(),
    type,
    badge: badgeMap[type],
    label: labelMap[type],
    name: file.name,
    meta: `Uploaded ${new Date().toLocaleDateString('en-IN')} · ${(file.size / 1024).toFixed(0)} KB`
  });
  saveVault(records);
  renderVault();
}

// ── Prescription OCR ────────────────────────────────────────────────────────
function handleRxUpload(event) {
  const file = event.target.files[0];
  if (file) processRxFile(file);
}

function handleRxDrop(event) {
  event.preventDefault();
  document.getElementById('rx-drop').classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (file) processRxFile(file);
}

async function processRxFile(file) {
  // Show spinner state
  setDropTitle(`📄 ${file.name} — scanning…`);
  showOCRStatus('Extracting medicines via OCR…', 'loading');
  document.getElementById('med-panel').style.display = 'block';
  document.getElementById('med-list').innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto 8px"></div>Processing…</div>';
  document.getElementById('run-btn').disabled = true;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch('/api/ocr', { method: 'POST', body: formData });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      showOCRStatus(`Error: ${data.error || 'OCR failed'}`, 'error');
      document.getElementById('med-list').innerHTML = '';
      return;
    }

    STATE.medicines = data.medicines || [];

    if (!STATE.medicines.length) {
      showOCRStatus('No medicines detected. Try a clearer image or type manually.', 'error');
      document.getElementById('med-list').innerHTML = '';
      return;
    }

    showOCRStatus(`Found ${STATE.medicines.length} medicine${STATE.medicines.length > 1 ? 's' : ''}`, 'done');
    document.getElementById('rx-meta').textContent = file.name;
    renderMedList();
    document.getElementById('run-btn').disabled = false;
    setDropTitle(`✅ ${file.name}`);

  } catch (err) {
    showOCRStatus(`Network error: ${err.message}`, 'error');
    document.getElementById('med-list').innerHTML = '';
  }
}

function setDropTitle(txt) {
  document.getElementById('rx-drop-title').textContent = txt;
}

function showOCRStatus(msg, type) {
  const el = document.getElementById('ocr-status');
  el.style.display = 'flex';
  el.className = 'ocr-status' + (type === 'error' ? ' error' : '');
  el.innerHTML = type === 'loading'
    ? `<div class="spinner"></div>${msg}`
    : (type === 'error' ? `⚠️ ${msg}` : `✅ ${msg}`);
}

function renderMedList() {
  const container = document.getElementById('med-list');
  container.innerHTML = STATE.medicines.map((m, i) => `
    <div class="med-item ${m.selected ? 'selected' : ''}" onclick="toggleMed(${i})">
      <div class="med-checkbox"><span class="chk">✓</span></div>
      <div class="med-info">
        <div class="med-name">${m.name}</div>
        <div class="med-dose">${m.dose} · ${m.frequency}</div>
      </div>
      <span class="stk-chip stk-high">—</span>
    </div>
  `).join('');
}

function toggleMed(i) {
  STATE.medicines[i].selected = !STATE.medicines[i].selected;
  renderMedList();
  document.getElementById('run-btn').disabled = !STATE.medicines.some(m => m.selected);
}

function selectAllMeds(val) {
  STATE.medicines.forEach(m => m.selected = val);
  renderMedList();
  document.getElementById('run-btn').disabled = !val;
}

// ── Probability Engine ──────────────────────────────────────────────────────
async function runEngine() {
  const selected = STATE.medicines.filter(m => m.selected).map(m => m.name);
  if (!selected.length) return;

  setEngineStatus('running', 'Running probability analysis…');
  document.getElementById('pharm-results').innerHTML =
    '<div class="empty-state"><div class="spinner" style="margin:0 auto 8px"></div>Analysing…</div>';

  try {
    const resp = await fetch('/api/rank', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        medicines: selected,
        lat: STATE.userLat,
        lng: STATE.userLng,
      })
    });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      setEngineStatus('error', `Error: ${data.error}`);
      return;
    }

    STATE.pharmacies = data.pharmacies || [];
    setEngineStatus('done', `${STATE.pharmacies.length} pharmacies ranked for ${selected.length} medicine${selected.length > 1 ? 's' : ''}`);
    renderPharmResults();

    // Update Navigate sidebar too
    renderNavPharmList();

  } catch (err) {
    setEngineStatus('error', `Network error: ${err.message}`);
  }
}

function setEngineStatus(type, msg) {
  const el = document.getElementById('engine-status');
  el.className = 'engine-status ' + type;
  el.innerHTML = `<div class="${type === 'running' ? 'spinner' : 'pulse-dot'}"></div>${msg}`;
}

function renderPharmResults() {
  const colors = ['#1D9E75', '#0F6E56', '#378ADD', '#EF9F27', '#888', '#aaa'];
  const container = document.getElementById('pharm-results');

  if (!STATE.pharmacies.length) {
    container.innerHTML = '<div class="empty-state">No pharmacies found.</div>';
    return;
  }

  container.innerHTML = STATE.pharmacies.map((p, i) => `
    <div class="pr-card" onclick="navigateTo(${i})">
      <div class="pr-rank ${i === 0 ? 'pr-rank-1' : ''}">${i + 1}</div>
      <div class="pr-info">
        <div class="pr-name">${p.name}</div>
        <div class="pr-meta">${p.distance_km} km · ${p.coverage_pct}% coverage · ${p.is_24h ? '24h open' : 'Limited hours'}</div>
        <div class="factors">
          <span class="factor-chip">Coverage ${p.factors.coverage}%</span>
          <span class="factor-chip">Stock ${p.factors.availability}%</span>
          <span class="factor-chip">Distance ${p.factors.distance}%</span>
          <span class="factor-chip">${p.factors.hours}</span>
          ${p.factors.category !== '—' ? `<span class="factor-chip" style="background:#e1f5ee;color:#0f6e56">${p.factors.category}</span>` : ''}
        </div>
      </div>
      <div class="pr-score">
        <div class="pr-score-val" style="color:${colors[i] || '#888'}">${p.score}%</div>
        <div class="pr-score-lbl">match</div>
      </div>
      <button class="nav-btn" onclick="navigateTo(${i});event.stopPropagation()">Navigate →</button>
    </div>
  `).join('');
}

// ── Navigate ────────────────────────────────────────────────────────────────
let mapInitialised = false;

function initMap() {
  if (mapInitialised) return;
  mapInitialised = true;

  STATE.map = L.map('map', { zoomControl: true }).setView([STATE.userLat, STATE.userLng], 14);

  // Free OpenStreetMap tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(STATE.map);

  // User marker
  STATE.userMarker = L.marker([STATE.userLat, STATE.userLng], {
    icon: makeIcon('#378ADD', 'You'),
    zIndexOffset: 1000,
  }).addTo(STATE.map).bindPopup('<b>Your location</b>');
}

function makeIcon(color, label) {
  return L.divIcon({
    html: `<div style="
      background:${color};border:2.5px solid white;
      width:28px;height:28px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      font-size:9px;font-weight:700;color:white;
      box-shadow:0 2px 8px rgba(0,0,0,0.25);
    ">${label}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    className: '',
  });
}

function renderNavPharmList() {
  const container = document.getElementById('nav-pharm-list');
  const colors = ['#1D9E75', '#0F6E56', '#378ADD', '#EF9F27', '#888', '#aaa'];

  if (!STATE.pharmacies.length) {
    container.innerHTML = '<div class="empty-state" style="padding:16px 0">Run the prescription engine to see pharmacies.</div>';
    return;
  }

  container.innerHTML = STATE.pharmacies.map((p, i) => `
    <div class="nav-pharm-card ${STATE.selectedPharmIdx === i ? 'active' : ''}" onclick="selectPharm(${i})" id="npc-${i}">
      <div class="nav-pharm-dot" style="background:${colors[i] || '#888'}"></div>
      <div class="nav-pharm-name">${p.name}</div>
      <div class="nav-pharm-score">${p.score}%</div>
    </div>
  `).join('');
}

function selectPharm(i) {
  STATE.selectedPharmIdx = i;
  const p = STATE.pharmacies[i];

  // Highlight card
  document.querySelectorAll('.nav-pharm-card').forEach((c, idx) => {
    c.classList.toggle('active', idx === i);
  });

  // Clear old markers & route
  STATE.pharmMarkers.forEach(m => STATE.map.removeLayer(m));
  STATE.pharmMarkers = [];
  if (STATE.routeControl) {
    STATE.map.removeControl(STATE.routeControl);
    STATE.routeControl = null;
  }

  // Add pharmacy marker
  const colors = ['#1D9E75', '#0F6E56', '#378ADD', '#EF9F27', '#888', '#aaa'];
  const marker = L.marker([p.lat, p.lng], {
    icon: makeIcon(colors[i] || '#1D9E75', 'Rx'),
  }).addTo(STATE.map)
    .bindPopup(`<b>${p.name}</b><br>${p.address}<br><b style="color:${colors[i]}">${p.score}% match</b><br>${p.phone}`)
    .openPopup();
  STATE.pharmMarkers.push(marker);

  // Draw route via Leaflet Routing Machine (uses free OSRM)
  STATE.routeControl = L.Routing.control({
    waypoints: [
      L.latLng(STATE.userLat, STATE.userLng),
      L.latLng(p.lat, p.lng),
    ],
    routeWhileDragging: false,
    addWaypoints: false,
    draggableWaypoints: false,
    fitSelectedRoutes: true,
    lineOptions: {
      styles: [{ color: colors[i] || '#1D9E75', weight: 5, opacity: 0.85 }],
    },
    createMarker: () => null,   // we handle markers ourselves
    show: false,                 // hide the default sidebar panel
  }).addTo(STATE.map);

  STATE.routeControl.on('routesfound', function (e) {
    const route = e.routes[0];
    const summary = route.summary;
    const distKm = (summary.totalDistance / 1000).toFixed(1);
    const etaMins = Math.ceil(summary.totalTime / 60);

    document.getElementById('route-card').style.display = 'block';
    document.getElementById('route-title').textContent = `Route to ${p.name}`;
    document.getElementById('r-dist').textContent = distKm + ' km';
    document.getElementById('r-eta').textContent = etaMins + ' min';
    document.getElementById('nav-subtitle').textContent = `Navigating to ${p.name}`;

    // Render turn-by-turn steps
    const steps = route.instructions || [];
    document.getElementById('route-steps').innerHTML = steps.map((s, idx) => `
      <div class="rstep">
        <div class="rstep-num ${idx === steps.length - 1 ? 'rstep-done' : ''}">${idx === steps.length - 1 ? '✓' : idx + 1}</div>
        <div>
          <div class="rstep-txt">${s.text}</div>
          <div class="rstep-dist">${(s.distance / 1000).toFixed(2)} km</div>
        </div>
      </div>
    `).join('');
  });

  STATE.routeControl.on('routingerror', function () {
    // OSRM fallback: draw a straight dashed line
    const fallback = L.polyline(
      [[STATE.userLat, STATE.userLng], [p.lat, p.lng]],
      { color: colors[i] || '#1D9E75', weight: 4, dashArray: '8,6' }
    ).addTo(STATE.map);
    STATE.pharmMarkers.push(fallback);
    STATE.map.fitBounds(fallback.getBounds(), { padding: [40, 40] });

    document.getElementById('route-card').style.display = 'block';
    document.getElementById('route-title').textContent = `Straight-line route to ${p.name}`;
    document.getElementById('r-dist').textContent = p.distance_km + ' km';
    document.getElementById('r-eta').textContent = '— min';
    document.getElementById('route-steps').innerHTML =
      '<div class="rstep-txt" style="color:#999">Live routing unavailable offline. Showing straight-line path.</div>';
  });
}

// Called from prescription results — auto-jumps to Navigate
function navigateTo(pharmIdx) {
  STATE.selectedPharmIdx = pharmIdx;
  goTo('navigate');
  // Wait for map init then select
  setTimeout(() => {
    renderNavPharmList();
    selectPharm(pharmIdx);
  }, 100);
}

function centerMap() {
  if (!STATE.map) return;
  STATE.map.setView([STATE.userLat, STATE.userLng], 14);
}

// ── Init ────────────────────────────────────────────────────────────────────
renderVault();
